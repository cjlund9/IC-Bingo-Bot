import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging

from config import GUILD_ID, ADMIN_ROLE
from storage import sync_completed_data_with_tiles

logger = logging.getLogger(__name__)

def setup_sync_command(bot: Bot):
    @bot.tree.command(
        name="sync",
        description="Sync completed.json data with current tiles.json values (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    async def sync_cmd(interaction: Interaction):
        try:
            # Check permissions
            roles = [r.name for r in interaction.user.roles]
            if ADMIN_ROLE not in roles:
                await interaction.response.send_message(
                    "❌ Only admins can sync data.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Perform sync
            sync_results = sync_completed_data_with_tiles()
            
            # Create response embed
            embed = discord.Embed(
                title="🔄 Data Sync Results",
                description="Sync completed.json with tiles.json",
                color=0x0099FF
            )
            
            updated_tiles = sync_results.get("updated_tiles", 0)
            errors = sync_results.get("errors", [])
            
            if updated_tiles > 0:
                embed.add_field(
                    name="✅ Success",
                    value=f"Updated {updated_tiles} tiles with current drops_needed values",
                    inline=False
                )
                embed.color = 0x00FF00
            else:
                embed.add_field(
                    name="ℹ️ No Changes",
                    value="All tiles already have correct total_required values",
                    inline=False
                )
            
            if errors:
                error_text = "\n".join([f"• {error}" for error in errors[:5]])  # Show first 5 errors
                if len(errors) > 5:
                    error_text += f"\n... and {len(errors) - 5} more errors"
                
                embed.add_field(
                    name="⚠️ Errors",
                    value=error_text,
                    inline=False
                )
                embed.color = 0xFFA500 if updated_tiles > 0 else 0xFF0000
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Data sync completed: {updated_tiles} tiles updated, {len(errors)} errors")
            
        except Exception as e:
            logger.error(f"Error in sync command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while syncing data.",
                ephemeral=True
            )

    @bot.tree.command(
        name="validate",
        description="Validate all tile data and show discrepancies (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    async def validate_cmd(interaction: Interaction):
        try:
            # Check permissions
            roles = [r.name for r in interaction.user.roles]
            if ADMIN_ROLE not in roles:
                await interaction.response.send_message(
                    "❌ Only admins can validate data.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer(ephemeral=True)
            
            from config import load_placeholders
            from storage import get_completed
            
            placeholders = load_placeholders()
            completed_dict = get_completed()
            
            discrepancies = []
            
            # Check each team's data
            for team_name, team_data in completed_dict.items():
                if not isinstance(team_data, dict):
                    continue
                    
                for tile_key, tile_data in team_data.items():
                    try:
                        tile_index = int(tile_key)
                        
                        if tile_index >= len(placeholders):
                            discrepancies.append(f"Team {team_name}, Tile {tile_index}: Invalid tile index")
                            continue
                        
                        tile_info = placeholders[tile_index]
                        current_drops_needed = tile_info.get("drops_needed", 1)
                        stored_total_required = tile_data.get("total_required", 1)
                        
                        if stored_total_required != current_drops_needed:
                            discrepancies.append(
                                f"Team {team_name}, Tile {tile_index} ({tile_info.get('name', 'Unknown')}): "
                                f"total_required={stored_total_required}, drops_needed={current_drops_needed}"
                            )
                        
                        # Check for completed_count exceeding total_required
                        completed_count = tile_data.get("completed_count", 0)
                        if completed_count > stored_total_required:
                            discrepancies.append(
                                f"Team {team_name}, Tile {tile_index}: "
                                f"completed_count ({completed_count}) > total_required ({stored_total_required})"
                            )
                            
                    except (ValueError, KeyError) as e:
                        discrepancies.append(f"Team {team_name}, Tile {tile_key}: Error - {e}")
            
            # Create response embed
            embed = discord.Embed(
                title="🔍 Data Validation Results",
                description="Validation of completed.json against tiles.json",
                color=0x0099FF
            )
            
            if discrepancies:
                discrepancy_text = "\n".join(discrepancies[:10])  # Show first 10
                if len(discrepancies) > 10:
                    discrepancy_text += f"\n... and {len(discrepancies) - 10} more discrepancies"
                
                embed.add_field(
                    name="⚠️ Discrepancies Found",
                    value=discrepancy_text,
                    inline=False
                )
                embed.color = 0xFFA500
                
                embed.add_field(
                    name="💡 Recommendation",
                    value="Use `/sync` command to fix these discrepancies",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ All Good",
                    value="No discrepancies found. All data is consistent.",
                    inline=False
                )
                embed.color = 0x00FF00
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Data validation completed: {len(discrepancies)} discrepancies found")
            
        except Exception as e:
            logger.error(f"Error in validate command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while validating data.",
                ephemeral=True
            ) 