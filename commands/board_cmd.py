import discord
import os
import time
import logging
from discord import app_commands, Interaction
from discord.ext.commands import Bot
from utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, BOARD_CHANNEL_NAME, ADMIN_ROLE
from storage import get_completed
from utils.access import leadership_or_event_coordinator_check

def setup_board_command(bot: Bot):
    @bot.tree.command(
        name="board",
        description="Display the current bingo board",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(team="Team to display board for (optional, leadership/event coordinator only)")
    @rate_limit(cooldown_seconds=10.0, max_requests_per_hour=30)  # Rate limit board updates
    async def board_cmd(interaction: Interaction, team: str = None):
        start_time = time.time()
        
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=False)
        
        team = team.lower() if team else DEFAULT_TEAM

        if team != DEFAULT_TEAM and team.capitalize() not in TEAM_ROLES:
            await interaction.followup.send(
                f"❌ Invalid team '{team}'. Valid teams: {', '.join(TEAM_ROLES)} or 'all'.",
                ephemeral=True
            )
            return

        try:
            completed_dict = get_completed()
            from board import generate_board_image, OUTPUT_FILE
            
            # Generate the board image
            success = generate_board_image(placeholders=None, completed_dict=completed_dict, team=team)
            
            if success and os.path.exists(OUTPUT_FILE):
                file = discord.File(OUTPUT_FILE)
                await interaction.followup.send(file=file)
                
                # Log performance
                execution_time = time.time() - start_time
                logger.info(f"Board command completed in {execution_time:.3f}s for team {team}")
            else:
                await interaction.followup.send("❌ Failed to generate board image.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error displaying board: {e}")
            await interaction.followup.send(f"❌ Error generating board: {str(e)}", ephemeral=True)

async def update_board_message(guild: discord.Guild, bot_user: discord.User, team: str = DEFAULT_TEAM):
    from core.update_board import update_board_message as update_board
    await update_board(guild, bot_user, team)
