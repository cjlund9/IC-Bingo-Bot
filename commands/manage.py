import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from storage import get_tile_progress, get_team_progress
from views.submission_management import SubmissionManagementView, SubmissionRemovalView
from utils.access import bot_access_check
from config import load_placeholders

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
    
    # Add tile indicator (A1, A2, etc.)
    row = tile_index // 10  # 10x10 board
    col = tile_index % 10
    row_letter = chr(65 + row)  # A=65, B=66, etc.
    col_number = col + 1  # 1-based column numbers
    tile_indicator = f"{row_letter}{col_number}"
    tile_name_with_indicator = f"{tile_indicator}: {tile_name}"
    
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
        title=f"🔧 Manage {tile_name_with_indicator}",
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
    
    embed.set_footer(text=f"Team: {team.capitalize()} | Tile: {tile_indicator} ({tile_index})")
    return embed, view

def setup_manage_command(bot: Bot):
    @bot.tree.command(
        name="manage",
        description="Manage submissions for a specific tile (Admin/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(bot_access_check)
    @app_commands.describe(
        team="Team to manage (optional, defaults to your team)",
        tile="Tile index or name to manage"
    )
    async def manage_cmd(interaction: Interaction, tile: str, team: Optional[str] = None):
        try:
            # Check permissions - only leadership and event coordinators can manage
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

            # --- Tile index or name resolution ---
            placeholders = load_placeholders()
            tile_index = None
            # Try to interpret as integer index
            try:
                tile_index = int(tile)
            except (ValueError, TypeError):
                # Try to match by name (case-insensitive, exact match)
                for idx, t in enumerate(placeholders):
                    if t.get("name", "").strip().lower() == str(tile).strip().lower():
                        tile_index = idx
                        break
            if tile_index is None or tile_index < 0 or tile_index >= len(placeholders):
                valid_names = [t.get("name", f"Tile {i}") for i, t in enumerate(placeholders)]
                await interaction.response.send_message(
                    f"❌ Invalid tile '{tile}'. Please use a valid tile index or name.\nValid names: {', '.join(valid_names[:15])}{'...' if len(valid_names) > 15 else ''}",
                    ephemeral=True
                )
                return

            # Create and send embed with management view
            embed, view = create_management_embed(team, tile_index)
            await interaction.response.send_message(embed=embed, view=view)

            logger.info(f"Management view opened: Team={team}, Tile={tile_index}, User={interaction.user.id}")

        except Exception as e:
            logger.error(f"Error in manage command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while loading management information.",
                ephemeral=True
            )

 