import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from storage import get_tile_progress, get_team_progress
from views.submission_management import SubmissionManagementView, SubmissionRemovalView

logger = logging.getLogger(__name__)

def create_management_embed(team: str, tile_index: int) -> discord.Embed:
    """Create a Discord embed for managing a specific tile"""
    
    progress = get_tile_progress(team, tile_index)
    if not progress:
        embed = discord.Embed(
            title="❌ Error",
            description="Could not load tile information.",
            color=0xFF0000
        )
        return embed, None
    
    tile_name = progress.get("tile_name", f"Tile {tile_index}")
    completed_count = progress.get("completed_count", 0)
    total_required = progress.get("total_required", 1)
    progress_percentage = progress.get("progress_percentage", 0)
    submissions = progress.get("submissions", [])
    missing_drops = progress.get("missing_drops", [])
    
    # Determine color based on progress
    if progress.get("is_complete", False):
        color = 0x00FF00  # Green for complete
    elif completed_count > 0:
        color = 0xFFA500  # Orange for in progress
    else:
        color = 0x808080  # Gray for not started
        
    embed = discord.Embed(
        title=f"🔧 Manage {tile_name}",
        description=f"**Team:** {team.capitalize()}",
        color=color
    )
    
    # Progress information
    progress_bar = "█" * int(progress_percentage / 10) + "░" * (10 - int(progress_percentage / 10))
    embed.add_field(
        name="📊 Progress",
        value=f"{progress_bar} {completed_count}/{total_required} ({progress_percentage:.1f}%)",
        inline=False
    )
    
    # Submissions
    if submissions:
        submission_text = "\n".join([
            f"• {sub['drop']} (x{sub['quantity']}) by <@{sub['user_id']}>"
            for sub in submissions
        ])
        embed.add_field(
            name="📝 Current Submissions",
            value=submission_text[:1024] + "..." if len(submission_text) > 1024 else submission_text,
            inline=False
        )
    
    # Missing drops
    if missing_drops:
        missing_text = "\n".join([f"• {drop}" for drop in missing_drops[:10]])
        if len(missing_drops) > 10:
            missing_text += f"\n... and {len(missing_drops) - 10} more"
        embed.add_field(
            name="❌ Missing Drops",
            value=missing_text,
            inline=False
        )
    
    # Create management view
    view = SubmissionRemovalView(team, tile_index)
    
    embed.set_footer(text=f"Team: {team.capitalize()} | Tile: {tile_index}")
    return embed, view

def setup_manage_command(bot: Bot):
    @bot.tree.command(
        name="manage",
        description="Manage submissions for a specific tile (Admin/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.describe(
        team="Team to manage (optional, defaults to your team)",
        tile="Tile index to manage"
    )
    async def manage_cmd(interaction: Interaction, tile: int, team: Optional[str] = None):
        try:
            # Check permissions
            roles = [r.name for r in interaction.user.roles]
            if ADMIN_ROLE not in roles and EVENT_COORDINATOR_ROLE not in roles:
                await interaction.response.send_message(
                    "❌ You don't have permission to manage submissions.",
                    ephemeral=True
                )
                return
            
            # Determine team
            if team:
                team = team.lower()
                if team not in {role.lower() for role in TEAM_ROLES} and team != DEFAULT_TEAM:
                    await interaction.response.send_message(
                        f"❌ Invalid team '{team}'. Valid teams: {', '.join(TEAM_ROLES)} or 'all'.",
                        ephemeral=True
                    )
                    return
            else:
                # Get user's team
                from utils import get_user_team
                team = get_user_team(interaction.user)
                if team == DEFAULT_TEAM:
                    await interaction.response.send_message(
                        "❌ You must be on a team to manage submissions, or specify a team name.",
                        ephemeral=True
                    )
                    return
            
            # Validate tile index
            from config import load_placeholders
            placeholders = load_placeholders()
            if tile < 0 or tile >= len(placeholders):
                await interaction.response.send_message(
                    f"❌ Invalid tile index. Must be between 0 and {len(placeholders) - 1}.",
                    ephemeral=True
                )
                return
            
            # Create and send embed with management view
            embed, view = create_management_embed(team, tile)
            await interaction.response.send_message(embed=embed, view=view)
            
            logger.info(f"Management view opened: Team={team}, Tile={tile}, User={interaction.user.id}")
            
        except Exception as e:
            logger.error(f"Error in manage command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while loading management information.",
                ephemeral=True
            )

    @bot.tree.command(
        name="stats",
        description="Show detailed statistics for all teams (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    async def stats_cmd(interaction: Interaction):
        try:
            # Check permissions
            roles = [r.name for r in interaction.user.roles]
            if ADMIN_ROLE not in roles:
                await interaction.response.send_message(
                    "❌ Only admins can view detailed statistics.",
                    ephemeral=True
                )
                return
            
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
                    
                    # Calculate average progress for in-progress tiles
                    tile_progress = team_progress.get("tile_progress", {})
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