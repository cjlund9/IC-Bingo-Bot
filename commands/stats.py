# Entire file commented out for minimal bingo bot
import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM
from storage import get_team_progress
from utils.access import team_member_access_check

logger = logging.getLogger(__name__)

def setup_stats_command(bot: Bot):
    @bot.tree.command(
        name="stats",
        description="Show detailed statistics for all teams",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(team_member_access_check)
    async def stats_cmd(interaction: Interaction):
        try:
            embed = discord.Embed(
                title="📈 Detailed Team Statistics",
                description="Comprehensive progress analysis",
                color=0x0099FF
            )
            
            team_stats = []
            
            # Calculate detailed stats for each team
            for team_role in TEAM_ROLES:
                team = team_role.lower()
                team_progress = get_team_progress(team)
                if team_progress:
                    total_tiles = team_progress.get("total_tiles", 0)
                    completed_tiles = team_progress.get("completed_tiles", 0)
                    in_progress_tiles = team_progress.get("in_progress_tiles", 0)
                    completion_percentage = team_progress.get("completion_percentage", 0)
                    tile_progress = team_progress.get("tile_progress", {})
                    tile_indices = list(tile_progress.keys())
                    print(f"[DEBUG] Team: {team}, total_tiles: {total_tiles}, completed_tiles: {completed_tiles}, tile_indices: {tile_indices}")
                    
                    # Calculate average progress for in-progress tiles
                    total_progress = 0
                    in_progress_count = 0
                    
                    for progress in tile_progress.values():
                        if progress.get("completed_count", 0) > 0 and not progress.get("is_complete", False):
                            total_progress += progress.get("progress_percentage", 0)
                            in_progress_count += 1
                    
                    avg_progress = total_progress / in_progress_count if in_progress_count > 0 else 0
                    
                    team_stats.append({
                        "team": team_role,
                        "completed": completed_tiles,
                        "in_progress": in_progress_tiles,
                        "total": total_tiles,
                        "completion_percentage": completion_percentage,
                        "avg_progress": avg_progress
                    })
            
            # Sort by completion percentage
            team_stats.sort(key=lambda x: x["completion_percentage"], reverse=True)
            
            # Create detailed stats
            stats_text = ""
            for i, stats in enumerate(team_stats):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                stats_text += (
                    f"{medal} **{stats['team']}**\n"
                    f"   ✅ Completed: {stats['completed']}/{stats['total']} ({stats['completion_percentage']:.1f}%)\n"
                    f"   🟡 In Progress: {stats['in_progress']} tiles\n"
                    f"   📊 Avg Progress: {stats['avg_progress']:.1f}%\n\n"
                )
            
            if stats_text:
                embed.add_field(
                    name="Team Rankings",
                    value=stats_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="No Data",
                    value="No team progress data available.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info("Detailed statistics viewed")
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while loading statistics.",
                ephemeral=True
            ) 