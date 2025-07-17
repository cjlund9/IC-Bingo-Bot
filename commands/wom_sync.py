import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from database import DatabaseManager
import config

logger = logging.getLogger(__name__)

# WOM API rate limiting
WOM_COOLDOWN = 5  # seconds between API calls
wom_last_call = 0
wom_lock = asyncio.Lock()

# Auto-sync configuration
AUTO_SYNC_INTERVAL = 300  #5nutes between sync loops
PLAYER_SYNC_INTERVAL = 5  #5ds between players

class WOMDataSync:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.sync_in_progress = False
        self.auto_sync_task = None
        self.auto_sync_enabled = False
    async def start_auto_sync(self):
        if self.auto_sync_task and not self.auto_sync_task.done():
            logger.info("Auto-sync already running")
            return

        self.auto_sync_enabled = True
        self.auto_sync_task = asyncio.create_task(self._auto_sync_loop())
        logger.info("Auto-sync started")

    async def stop_auto_sync(self):
        self.auto_sync_enabled = False
        if self.auto_sync_task and not self.auto_sync_task.done():
            self.auto_sync_task.cancel()
            try:
                await self.auto_sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-sync stopped")

    async def _auto_sync_loop(self):
        while self.auto_sync_enabled:
            try:
                logger.info("Starting auto-sync loop")

                # Get list of players to sync
                players_to_sync = self.db.get_all_wom_players()

                if not players_to_sync:
                    logger.info("No players configured for auto-sync")
                    await asyncio.sleep(AUTO_SYNC_INTERVAL)
                    continue

                # Sync each player with rate limiting
                for rsn in players_to_sync:
                    if not self.auto_sync_enabled:
                        break

                    try:
                        result = await self.sync_player_data(rsn)
                        if result['success']:
                            logger.info(f"Auto-sync: Successfully synced {rsn}")
                        else:
                            logger.warning(f"Auto-sync: Failed to sync {rsn}: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"Auto-sync: Error syncing {rsn}: {e}")

                    # Wait between players
                    await asyncio.sleep(PLAYER_SYNC_INTERVAL)

                # Update last sync time
                self.db.update_auto_sync_last_run()

                logger.info(f"Auto-sync loop completed. Next sync in {AUTO_SYNC_INTERVAL} seconds")

                # Wait before next loop
                await asyncio.sleep(AUTO_SYNC_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Auto-sync loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in auto-sync loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def sync_player_data(self, rsn: str) -> Dict:
        global wom_last_call

        async with wom_lock:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - wom_last_call
            if time_since_last < WOM_COOLDOWN:
                sleep_time = WOM_COOLDOWN - time_since_last
                await asyncio.sleep(sleep_time)
            wom_last_call = time.time()

            try:
                # Fetch player data from WOM API
                url = f"https://api.wiseoldman.net/v2/players/{rsn}/hiscores"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    # Store the data in database
                    player_data = {
                        'rsn': rsn,
                        'last_updated': datetime.now(),
                        'skills': data.get('skills', []),
                        'bosses': data.get('bosses', []),
                        'clues': data.get('clues', []),
                        'activities': data.get('activities', [])
                    }

                    # Store in database
                    success = self.db.store_wom_player_data(player_data)

                    if success:
                        logger.info(f"Successfully synced WOM data for {rsn}")
                        return {
                            'success': True,
                            'rsn': rsn,
                            'skills_count': len(data.get('skills', [])),
                            'bosses_count': len(data.get('bosses', [])),
                            'clues_count': len(data.get('clues', [])),
                            'activities_count': len(data.get('activities', []))
                        }
                    else:
                        logger.error(f"Failed to store WOM data for {rsn}")
                        return {'success': False, 'error': 'Database storage failed'}

                elif response.status_code == 404:
                    logger.warning(f"Player {rsn} not found on WOM")
                    return {'success': False, 'error': 'Player not found'}
                else:
                    logger.error(f"WOM API error for {rsn}: {response.status_code}")
                    return {'success': False, 'error': f'API error: {response.status_code}'}

            except Exception as e:
                logger.error(f"Error syncing WOM data for {rsn}: {e}")
                return {'success': False, 'error': str(e)}

    async def sync_multiple_players(self, rsns: List[str]) -> List[Dict]:
        results = []

        for rsn in rsns:
            result = await self.sync_player_data(rsn)
            results.append(result)

            # Small delay between players
            await asyncio.sleep(0.5)
        return results

# Global sync instance
wom_sync_instance = None

def setup_wom_sync_commands(bot: Bot):
    global wom_sync_instance

    # Initialize the sync instance
    db = DatabaseManager()
    wom_sync_instance = WOMDataSync(db)

    @bot.tree.command(
        name="womsync",
        description="Sync player data from WiseOldMan API to local database",
        guild=discord.Object(id=config.GUILD_ID)
    )
    @app_commands.describe(
        rsns="Comma-separated list of RSNs to sync (e.g., zezima,lynx titan')",
        auto_sync="Enable automatic sync every5minutes"
    )
    async def wom_sync_cmd(interaction: Interaction, rsns: str, auto_sync: bool = False):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Parse RSNs
            rsn_list = [rsn.strip() for rsn in rsns.split(',') if rsn.strip()]
            
            if not rsn_list:
                await interaction.followup.send("❌ Please provide at least one RSN to sync.")
                return
            
            if len(rsn_list) > 10:
                await interaction.followup.send("❌ Maximum10players can be synced at once.")
                return
            
            # Check if sync is already in progress
            if wom_sync_instance.sync_in_progress:
                await interaction.followup.send("❌ A sync is already in progress. Please wait.")
                return
            
            wom_sync_instance.sync_in_progress = True
            # Start sync
            await interaction.followup.send(f"🔄 Starting WOM sync for {len(rsn_list)} players...")
            
            results = await wom_sync_instance.sync_multiple_players(rsn_list)
            
            # Process results
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            # Create result embed
            embed = discord.Embed(
                title="🌐 WOM Data Sync Results",
                description=f"Synced {len(rsn_list)} players from WiseOldMan API",
                color=0x00FF00 if successful else 0xFF0000,
                timestamp=datetime.now()
            )
            
            if successful:
                success_text = "\n".join([
                    f"✅ **{r['rsn']}**: {r['skills_count']} skills, {r['bosses_count']} bosses"
                    for r in successful
                ])
                embed.add_field(name="✅ Successful", value=success_text, inline=False)
            
            if failed:
                fail_text = "\n".join([
                    f"❌ **{r['rsn']}**: {r.get('error', 'Unknown error')}"
                    for r in failed
                ])
                embed.add_field(name="❌ Failed", value=fail_text, inline=False)
            
            embed.set_footer(text=f"🌐 WOM Sync • {len(successful)}/{len(rsn_list)} successful")
            
            await interaction.followup.send(embed=embed)
            
            # Set up auto-sync if requested
            if auto_sync and successful:
                # Store auto-sync configuration
                db.set_auto_sync_config(rsn_list, enabled=True)
                await wom_sync_instance.start_auto_sync()
                await interaction.followup.send("🔄 Auto-sync enabled! Data will be updated every 5 minutes.")
            
        except Exception as e:
            logger.error(f"Error in WOM sync command: {e}")
            await interaction.followup.send(f"❌ An error occurred during sync: {e}")
        finally:
            if wom_sync_instance:
                wom_sync_instance.sync_in_progress = False
    
    @bot.tree.command(
        name="womstatus",
        description="Check the status of WOM data sync",
        guild=discord.Object(id=config.GUILD_ID)
    )
    async def wom_status_cmd(interaction: Interaction):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Get sync status from database
            sync_status = db.get_wom_sync_status()
            
            embed = discord.Embed(
                title="🌐 WOM Sync Status",
                description="Current status of WiseOldMan data synchronization",
                color=0x0099FF,
                timestamp=datetime.now()
            )
            
            if sync_status:
                embed.add_field(
                    name="📊 Sync Statistics",
                    value=f"**Players tracked**: {sync_status.get('player_count', 0)}\n"
                          f"**Last sync**: {sync_status.get('last_sync', 'Never')}\n"
                          f"**Auto-sync**: {'✅ Enabled' if sync_status.get('auto_sync', False) else '❌ Disabled'}",
                    inline=False
                )
                
                if sync_status.get('recent_updates'):
                    recent_text = "\n".join([
                        f"• **{update['rsn']}**: {update['last_updated']}"
                        for update in sync_status['recent_updates'][:5]
                    ])
                    embed.add_field(name="🕒 Recent Updates", value=recent_text, inline=False)
            else:
                embed.add_field(
                    name="❌ No Data",
                    value="No WOM sync data found. Use `/womsync` to start syncing players.",
                    inline=False
                )
            
            embed.set_footer(text="🌐 WOM Sync Status")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in WOM status command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {e}")

    @bot.tree.command(
        name="womautostart",
        description="Start the background auto-sync task",
        guild=discord.Object(id=config.GUILD_ID)
    )
    async def wom_auto_start_cmd(interaction: Interaction):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            if wom_sync_instance.auto_sync_enabled:
                await interaction.followup.send("🔄 Auto-sync is already running!")
                return
            
            await wom_sync_instance.start_auto_sync()
            await interaction.followup.send("✅ Auto-sync started! Data will be updated every 5 minutes.")
            
        except Exception as e:
            logger.error(f"Error starting auto-sync: {e}")
            await interaction.followup.send(f"❌ Error starting auto-sync: {e}")

    @bot.tree.command(
        name="womautostop",
        description="Stop the background auto-sync task",
        guild=discord.Object(id=config.GUILD_ID)
    )
    async def wom_auto_stop_cmd(interaction: Interaction):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            if not wom_sync_instance.auto_sync_enabled:
                await interaction.followup.send("❌ Auto-sync is not running!")
                return
            
            await wom_sync_instance.stop_auto_sync()
            await interaction.followup.send("✅ Auto-sync stopped!")
            
        except Exception as e:
            logger.error(f"Error stopping auto-sync: {e}")
            await interaction.followup.send(f"❌ Error stopping auto-sync: {e}") 