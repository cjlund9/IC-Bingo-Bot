import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, ADMIN_ROLE
from storage import get_tile_progress, get_team_progress, get_completed
from utils import get_user_team

logger = logging.getLogger(__name__)

def create_progress_embed(team: str, tile_index: Optional[int] = None) -> discord.Embed:
    """Create a Discord embed showing progress information"""
    
    if tile_index is not None:
        # Show specific tile progress
        progress = get_tile_progress(team, tile_index)
        if not progress:
            embed = discord.Embed(
                title="❌ Error",
                description="Could not load tile progress information.",
                color=0xFF0000
            )
            return embed
            
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
            title=f"📊 {tile_name} Progress",
            description=f"**Team:** {team.capitalize()}",
            color=color
        )
        
        # Progress bar
        progress_bar = "█" * int(progress_percentage / 10) + "░" * (10 - int(progress_percentage / 10))
        embed.add_field(
            name="Progress",
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
                name="📝 Submissions",
                value=submission_text[:1024] + "..." if len(submission_text) > 1024 else submission_text,
                inline=False
            )
        
        # Missing drops
        if missing_drops:
            missing_text = "\n".join([f"• {drop}" for drop in missing_drops[:10]])  # Limit to 10 items
            if len(missing_drops) > 10:
                missing_text += f"\n... and {len(missing_drops) - 10} more"
            embed.add_field(
                name="❌ Missing Drops",
                value=missing_text,
                inline=False
            )
            
    else:
        # Show team overall progress
        team_progress = get_team_progress(team)
        if not team_progress:
            embed = discord.Embed(
                title="❌ Error",
                description="Could not load team progress information.",
                color=0xFF0000
            )
            return embed
            
        total_tiles = team_progress.get("total_tiles", 0)
        completed_tiles = team_progress.get("completed_tiles", 0)
        in_progress_tiles = team_progress.get("in_progress_tiles", 0)
        not_started_tiles = team_progress.get("not_started_tiles", 0)
        completion_percentage = team_progress.get("completion_percentage", 0)
        
        embed = discord.Embed(
            title=f"🏆 {team.capitalize()} Team Progress",
            description=f"Overall completion: **{completion_percentage:.1f}%**",
            color=0x0099FF
        )
        
        # Progress summary
        embed.add_field(
            name="📊 Summary",
            value=f"✅ **Completed:** {completed_tiles}/{total_tiles}\n"
                  f"🟡 **In Progress:** {in_progress_tiles}\n"
                  f"⚪ **Not Started:** {not_started_tiles}",
            inline=False
        )
        
        # Progress bar
        progress_bar = "█" * int(completion_percentage / 10) + "░" * (10 - int(completion_percentage / 10))
        embed.add_field(
            name="Progress Bar",
            value=f"{progress_bar} {completion_percentage:.1f}%",
            inline=False
        )
        
        # Show in-progress tiles
        tile_progress = team_progress.get("tile_progress", {})
        in_progress_list = []
        
        for tile_idx, progress in tile_progress.items():
            if progress.get("completed_count", 0) > 0 and not progress.get("is_complete", False):
                tile_name = progress.get("tile_name", f"Tile {tile_idx}")
                completed = progress.get("completed_count", 0)
                total = progress.get("total_required", 1)
                in_progress_list.append(f"• {tile_name}: {completed}/{total}")
        
        if in_progress_list:
            in_progress_text = "\n".join(in_progress_list[:5])  # Show top 5
            if len(in_progress_list) > 5:
                in_progress_text += f"\n... and {len(in_progress_list) - 5} more"
            embed.add_field(
                name="🟡 In Progress Tiles",
                value=in_progress_text,
                inline=False
            )
    
    embed.set_footer(text=f"Team: {team.capitalize()}")
    return embed

def setup_progress_command(bot: Bot):
    @bot.tree.command(
        name="progress",
        description="View progress for a team or specific tile",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.describe(
        team="Team to show progress for (optional, defaults to your team)",
        tile="Tile index to show specific progress (optional)"
    )
    async def progress_cmd(interaction: Interaction, team: Optional[str] = None, tile: Optional[int] = None):
        try:
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
                team = get_user_team(interaction.user)
                if team == DEFAULT_TEAM:
                    await interaction.response.send_message(
                        "❌ You must be on a team to view progress, or specify a team name.",
                        ephemeral=True
                    )
                    return
            
            # Validate tile index if provided
            if tile is not None:
                from config import load_placeholders
                placeholders = load_placeholders()
                if tile < 0 or tile >= len(placeholders):
                    await interaction.response.send_message(
                        f"❌ Invalid tile index. Must be between 0 and {len(placeholders) - 1}.",
                        ephemeral=True
                    )
                    return
            
            # Create and send embed
            embed = create_progress_embed(team, tile)
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"Progress viewed: Team={team}, Tile={tile}")
            
        except Exception as e:
            logger.error(f"Error in progress command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while loading progress information.",
                ephemeral=True
            )

    @bot.tree.command(
        name="leaderboard",
        description="Show team leaderboard",
        guild=discord.Object(id=GUILD_ID)
    )
    async def leaderboard_cmd(interaction: Interaction):
        try:
            # Check if user has permission
            roles = [r.name for r in interaction.user.roles]
            if ADMIN_ROLE not in roles:
                await interaction.response.send_message(
                    "❌ You don't have permission to view the leaderboard.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🏆 Team Leaderboard",
                description="Current team standings",
                color=0xFFD700
            )
            
            team_scores = []
            
            # Calculate scores for each team
            for team_role in TEAM_ROLES:
                team = team_role.lower()
                team_progress = get_team_progress(team)
                if team_progress:
                    completed_tiles = team_progress.get("completed_tiles", 0)
                    completion_percentage = team_progress.get("completion_percentage", 0)
                    team_scores.append({
                        "team": team_role,
                        "completed": completed_tiles,
                        "percentage": completion_percentage
                    })
            
            # Sort by completion percentage (descending)
            team_scores.sort(key=lambda x: x["percentage"], reverse=True)
            
            # Create leaderboard
            leaderboard_text = ""
            for i, score in enumerate(team_scores):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                leaderboard_text += f"{medal} **{score['team']}**: {score['completed']} tiles ({score['percentage']:.1f}%)\n"
            
            if leaderboard_text:
                embed.add_field(
                    name="Rankings",
                    value=leaderboard_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="No Data",
                    value="No team progress data available.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info("Leaderboard viewed")
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while loading the leaderboard.",
                ephemeral=True
            ) 