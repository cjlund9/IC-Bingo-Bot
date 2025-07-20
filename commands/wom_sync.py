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

async def get_bingo_role_rsns(guild: discord.Guild) -> List[str]:
    """Get RSNs (nick or username) for all members with the 'Summer 2025 Bingo' role."""
    role = discord.utils.get(guild.roles, name="Summer 2025 Bingo")
    if not role:
        return []
    rsns = []
    for member in role.members:
        if not member.bot:
            rsn = member.nick or member.name
            if rsn:
                rsns.append(rsn)
    return rsns

class WOMDataSync:
    def __init__(self, db: DatabaseManager, bot: Bot):
        self.db = db
        self.bot = bot
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

                # Get list of players to sync from Discord role
                for guild in self.bot.guilds:
                    if guild.id == config.GUILD_ID:
                        players_to_sync = await get_bingo_role_rsns(guild)
                        break
                else:
                    players_to_sync = []

                if not players_to_sync:
                    logger.info("No players with 'Summer 2025 Bingo' role found for auto-sync")
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
    wom_sync_instance = WOMDataSync(db, bot)

    # @bot.tree.command(
    #     name="womsync",
    #     description="Sync player data from WiseOldMan API to local database",
    #     guild=discord.Object(id=config.GUILD_ID)
    # )
    @app_commands.describe(
        rsns="Comma-separated list of RSNs to sync (leave blank to sync all with the Summer 2025 Bingo role)",
        auto_sync="Enable automatic sync every5minutes"
    )
    async def wom_sync_cmd(interaction: Interaction, rsns: Optional[str] = None, auto_sync: bool = False):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # If no RSNs provided, sync all with the bingo role
            if not rsns:
                rsn_list = await get_bingo_role_rsns(interaction.guild)
                if not rsn_list:
                    await interaction.followup.send("❌ No members with the 'Summer 2025 Bingo' role found.")
                    return
            else:
                rsn_list = [rsn.strip() for rsn in rsns.split(',') if rsn.strip()]
                if not rsn_list:
                    await interaction.followup.send("❌ Please provide at least one RSN to sync.")
                    return
            
            if len(rsn_list) > 50:
                await interaction.followup.send("❌ Maximum 50 players can be synced at once.")
                return

            # Check if sync is already in progress
            if wom_sync_instance.sync_in_progress:
                await interaction.followup.send("❌ A sync is already in progress. Please wait.")
                return
            
            wom_sync_instance.sync_in_progress = True
            # Start sync
            await interaction.followup.send(f"🔄 Starting WOM sync for {len(rsn_list)} players...")
            
            results = await wom_sync_instance.sync_multiple_players(rsn_list)
            
            success_count = sum(1 for r in results if r.get('success'))
            fail_count = len(results) - success_count
            await interaction.followup.send(f"✅ WOM sync complete! Success: {success_count}, Failed: {fail_count}")
            wom_sync_instance.sync_in_progress = False
        except Exception as e:
            wom_sync_instance.sync_in_progress = False
            logger.error(f"Error in womsync command: {e}")
            await interaction.followup.send(f"❌ Error during WOM sync: {e}")

    # @bot.tree.command(
    #     name="womstatus",
    #     description="Check the status of WOM data sync",
    #     guild=discord.Object(id=config.GUILD_ID)
    # )
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

    # @bot.tree.command(
    #     name="womautostart",
    #     description="Start the background auto-sync task",
    #     guild=discord.Object(id=config.GUILD_ID)
    # )
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

    # @bot.tree.command(
    #     name="womautostop",
    #     description="Stop the background auto-sync task",
    #     guild=discord.Object(id=config.GUILD_ID)
    # )
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

    # @bot.tree.command(
    #     name="womroster",
    #     description="Compare Discord nicknames to WOM roster and show sync status",
    #     guild=discord.Object(id=config.GUILD_ID)
    # )
    async def wom_roster_cmd(interaction: Interaction):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Get all members with the bingo role
            discord_rsns = await get_bingo_role_rsns(interaction.guild)
            
            if not discord_rsns:
                await interaction.followup.send("❌ No members with the 'Summer 2025 Bingo' role found.")
                return
            
            await interaction.followup.send(f"🔍 Checking {len(discord_rsns)} players against WOM roster...")
            
            # Check each player against WOM
            found_players = []
            not_found_players = []
            error_players = []
            
            for rsn in discord_rsns:
                try:
                    # Check if player exists on WOM
                    url = f"https://api.wiseoldman.net/v2/players/{rsn}/hiscores"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        found_players.append({
                            'rsn': rsn,
                            'skills_count': len(data.get('skills', [])),
                            'bosses_count': len(data.get('bosses', [])),
                            'clues_count': len(data.get('clues', [])),
                            'activities_count': len(data.get('activities', []))
                        })
                    elif response.status_code == 404:
                        not_found_players.append(rsn)
                    else:
                        error_players.append(f"{rsn} (HTTP {response.status_code})")
                        
                except Exception as e:
                    error_players.append(f"{rsn} (Error: {str(e)})")
                
                # Small delay to be respectful to WOM API
                await asyncio.sleep(0.5)
            # Create detailed report embed
            embed = discord.Embed(
                title="🌐 WOM Roster Comparison",
                description=f"**Total Discord Members:** {len(discord_rsns)}\n**Role:** Summer 2025 Bingo",
                color=0x0099FF,
                timestamp=datetime.now()
            )
            
            # Found players
            if found_players:
                found_text = "\n".join([
                    f"✅ **{p['rsn']}**: {p['skills_count']} skills, {p['bosses_count']} bosses, {p['clues_count']} clues"
                    for p in found_players[:10]  # Show first 10
                ])
                if len(found_players) > 10:
                    found_text += f"\n... and {len(found_players) - 10} more"
                embed.add_field(
                    name=f"✅ Found on WOM ({len(found_players)})",
                    value=found_text,
                    inline=False
                )
            
            # Not found players
            if not_found_players:
                not_found_text = "\n".join([
                    f"❌ **{rsn}**"
                    for rsn in not_found_players[:10]  # Show first 10
                ])
                if len(not_found_players) > 10:
                    not_found_text += f"\n... and {len(not_found_players) - 10} more"
                embed.add_field(
                    name=f"❌ Not Found on WOM ({len(not_found_players)})",
                    value=not_found_text,
                    inline=False
                )
            
            # Error players
            if error_players:
                error_text = "\n".join(error_players[:5])  # Show first 5
                if len(error_players) > 5:
                    error_text += f"\n... and {len(error_players) - 5} more"
                embed.add_field(
                    name=f"⚠️ Errors ({len(error_players)})",
                    value=error_text,
                    inline=False
                )
            
            # Summary
            summary_text = f"**Sync Rate:** {len(found_players)}/{len(discord_rsns)} ({len(found_players)/len(discord_rsns)*100:.1f}%)\n"
            if not_found_players:
                summary_text += f"**Need to be added to WOM:** {len(not_found_players)} players\n"
            if found_players:
                summary_text += f"**Ready for sync:** {len(found_players)} players"
            
            embed.add_field(
                name="📊 Summary",
                value=summary_text,
                inline=False
            )
            
            embed.set_footer(text="💡 Players not found need to be added to WOM or have matching RSNs")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in womroster command: {e}")
            await interaction.followup.send(f"❌ Error during roster check: {e}") 

    # @bot.tree.command(
    #     name="womnickname",
    #     description="Update Discord nicknames to match WOM roster names for better sync",
    #     guild=discord.Object(id=config.GUILD_ID)
    # )
    async def wom_nickname_cmd(interaction: Interaction):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires administrator permissions.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Get all members with the bingo role
            role = discord.utils.get(interaction.guild.roles, name="Summer 2025 Bingo")
            if not role:
                await interaction.followup.send("❌ Role 'Summer 2025 Bingo' not found.")
                return
            
            members = [m for m in role.members if not m.bot]
            
            if not members:
                await interaction.followup.send("❌ No members with the 'Summer 2025 Bingo' role found.")
                return
            
            await interaction.followup.send(f"🔍 Checking {len(members)} members and updating nicknames to match WOM...")
            
            # Track results
            updated_nicknames = []
            not_found_on_wom = []
            already_correct = []
            errors = []
            
            for member in members:
                try:
                    current_nick = member.nick or member.name
                    
                    # Try to find the player on WOM with their current nickname
                    url = f"https://api.wiseoldman.net/v2/players/{current_nick}/hiscores"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # If they exist on WOM, their current nickname is correct
                        already_correct.append(current_nick)
                    elif response.status_code == 404:
                        # Player not found on WOM with current nickname
                        not_found_on_wom.append(current_nick)
                    else:
                        errors.append(f"{current_nick} (HTTP {response.status_code})")
                        
                except Exception as e:
                    errors.append(f"{current_nick} (Error: {str(e)})")
                
                # Small delay to be respectful to WOM API
                await asyncio.sleep(0.5)
            
            # Create detailed report embed
            embed = discord.Embed(
                title="🎭 Discord Nickname Analysis",
                description=f"**Total Members:** {len(members)}\n**Role:** Summer 2025 Bingo",
                color=0x0099FF,
                timestamp=datetime.now()
            )
            
            # Already correct nicknames
            if already_correct:
                correct_text = "\n".join([
                    f"✅ **{nick}**"
                    for nick in already_correct[:10]  # Show first 10
                ])
                if len(already_correct) > 10:
                    correct_text += f"\n... and {len(already_correct) - 10} more"
                embed.add_field(
                    name=f"✅ Already Correct ({len(already_correct)})",
                    value=correct_text,
                    inline=False
                )
            
            # Not found on WOM
            if not_found_on_wom:
                not_found_text = "\n".join([
                    f"❌ **{nick}**"
                    for nick in not_found_on_wom[:10]  # Show first 10
                ])
                if len(not_found_on_wom) > 10:
                    not_found_text += f"\n... and {len(not_found_on_wom) - 10} more"
                embed.add_field(
                    name=f"❌ Not Found on WOM ({len(not_found_on_wom)})",
                    value=not_found_text,
                    inline=False
                )
            
            # Errors
            if errors:
                error_text = "\n".join(errors[:5])  # Show first 5
                if len(errors) > 5:
                    error_text += f"\n... and {len(errors) - 5} more"
                embed.add_field(
                    name=f"⚠️ Errors ({len(errors)})",
                    value=error_text,
                    inline=False
                )
            
            # Summary
            summary_text = f"**Sync Ready:** {len(already_correct)}/{len(members)} ({len(already_correct)/len(members)*100:.1f}%)\n"
            if not_found_on_wom:
                summary_text += f"**Need WOM Account:** {len(not_found_on_wom)} players\n"
            if already_correct:
                summary_text += f"**Ready for Sync:** {len(already_correct)} players"
            
            embed.add_field(
                name="📊 Summary",
                value=summary_text,
                inline=False
            )
            
            embed.set_footer(text="💡 Players not found need to be added to WOM or have different RSNs")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in womnickname command: {e}")
            await interaction.followup.send(f"❌ Error during nickname analysis: {e}") 