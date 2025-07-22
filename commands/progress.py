import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional, List

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, ADMIN_ROLE
from storage import get_tile_progress, get_team_progress, get_tile_progress_by_name, get_tile_by_name
from utils import get_user_team
from utils.access import team_member_access_check

logger = logging.getLogger(__name__)

def create_progress_embed(team: str, tile_index: Optional[int] = None, tile_name: Optional[str] = None) -> discord.Embed:
    """Create a Discord embed showing progress information for a specific tile"""
    
    # Show specific tile progress
    if tile_name is not None:
        progress = get_tile_progress_by_name(team, tile_name)
        if not progress:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not find tile matching '{tile_name}'. Try a different search term.",
                color=0xFF0000
            )
            return embed
        # Get the actual tile index for display
        db_tile_id = get_tile_by_name(tile_name)
        # Convert database ID (1-based) to board index (0-based)
        actual_tile_index = db_tile_id - 1 if db_tile_id is not None else 0
        display_tile_name = progress.get("tile_name", tile_name)
    else:
        # Use tile_index as provided (0-based)
        progress = get_tile_progress(team, tile_index)
        if not progress:
            embed = discord.Embed(
                title="❌ Error",
                description="Could not load tile progress information.",
                color=0xFF0000
            )
            return embed
        actual_tile_index = tile_index
        display_tile_name = progress.get("tile_name", f"Tile {tile_index + 1}")
    
    # Add tile indicator (A1, A2, etc.)
    row = actual_tile_index // 10  # 10x10 board
    col = actual_tile_index % 10
    row_letter = chr(65 + row)  # A=65, B=66, etc.
    col_number = col + 1  # 1-based column numbers
    tile_indicator = f"{row_letter}{col_number}"
    
    embed = discord.Embed(
        title=f"Progress for {display_tile_name} ({tile_indicator})",
        color=0x00FF00
    )
    embed.add_field(name="Tile Index", value=str(actual_tile_index + 1), inline=True)
    embed.add_field(name="Indicator", value=tile_indicator, inline=True)
    embed.add_field(name="Progress", value=f"{progress.get('completed_count', 0)}/{progress.get('total_required', 1)}", inline=True)
    if progress.get("is_complete", False):
        embed.add_field(name="Status", value="✅ Complete", inline=False)
    elif progress.get("completed_count", 0) > 0:
        embed.add_field(name="Status", value="🟡 In Progress", inline=False)
    else:
        embed.add_field(name="Status", value="⬜ Not Started", inline=False)
    return embed

def setup_progress_command(bot: Bot):
    async def tile_name_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for tile names"""
        try:
            from config import load_placeholders
            placeholders = load_placeholders()
            
            # Filter tiles that match the current input (case-insensitive)
            matching_tiles = []
            for i, tile_data in enumerate(placeholders):
                if current.lower() in tile_data.get('name', '').lower():
                    # Calculate board position (A1, B2, etc.)
                    row = i // 10
                    col = i % 10
                    row_letter = chr(65 + row)  # A=65, B=66, etc.
                    col_number = col + 1  # 1-based column numbers
                    board_pos = f"{row_letter}{col_number}"
                    matching_tiles.append((i, tile_data.get('name', ''), board_pos))
            
            # Sort by relevance (exact matches first, then alphabetical)
            matching_tiles.sort(key=lambda x: (
                not x[1].lower().startswith(current.lower()),
                x[1].lower()
            ))
            
            # Return up to 25 choices
            return [
                app_commands.Choice(name=f"{tile[1]} ({tile[2]})", value=tile[1])
                for tile in matching_tiles[:25]
            ]
        except Exception as e:
            logger.error(f"Error in tile name autocomplete: {e}")
            return []

    @bot.tree.command(
        name="progress",
        description="View progress for a specific tile",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(team_member_access_check)
    @app_commands.describe(
        team="Team to show progress for (optional, defaults to your assigned team)",
        tile="Tile index to show specific progress (1-based)",
        tile_name="Tile name to search for (autocomplete available)"
    )
    @app_commands.autocomplete(tile_name=tile_name_autocomplete)
    async def progress_cmd(interaction: Interaction, team: Optional[str] = None, tile: Optional[int] = None, tile_name: Optional[str] = None):
        try:
            # Determine team
            if not team:
                roles = [r.name for r in interaction.user.roles]
                team = DEFAULT_TEAM
                for role in TEAM_ROLES:
                    if role in roles:
                        team = role.lower()
                        break
            
            # Validate team
            if team.lower() not in [t.lower() for t in TEAM_ROLES] and team.lower() != DEFAULT_TEAM:
                await interaction.response.send_message(
                    f"❌ Invalid team '{team}'. Valid teams: {', '.join(TEAM_ROLES)} or 'all'.",
                    ephemeral=True
                )
                return
            
            # Normalize tile index if provided
            normalized_tile_index = tile - 1 if tile is not None else None
            embed = create_progress_embed(team, tile_index=tile, tile_name=tile_name)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            logger.info(f"Progress viewed: Team={team}, Tile={tile}, TileName={tile_name}")
            
        except Exception as e:
            logger.error(f"Error in progress command: {e}")
            
            # Check if interaction has already been responded to
            if interaction.response.is_done():
                logger.warning("Progress command interaction already responded to, skipping error response")
                return
                
            try:
                await interaction.response.send_message(
                    "❌ An error occurred while loading progress information.",
                    ephemeral=True
                )
            except Exception as response_error:
                logger.error(f"Error sending progress error response: {response_error}")
                # If interaction is already responded to, try followup
                try:
                    await interaction.followup.send(
                        "❌ An error occurred while loading progress information.",
                        ephemeral=True
                    )
                except Exception as followup_error:
                    logger.error(f"Could not send error message to user: {followup_error}")

    @bot.tree.command(
        name="leaderboard",
        description="Show team leaderboard",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(team_member_access_check)
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