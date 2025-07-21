import discord
import os
import time
import logging
from datetime import datetime, timezone
from discord import app_commands, Interaction
from discord.ext.commands import Bot
from utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, BOARD_CHANNEL_NAME, ADMIN_ROLE
from utils.access import leadership_or_event_coordinator_check
from board import generate_board_image, OUTPUT_FILE
from database import DatabaseManager

ALLOWED_USER_ID = 169282701046710272  # Temporary: Only this user can run /board

def setup_board_command(bot: Bot):
    @bot.tree.command(
        name="board",
        description="Display the current bingo board",
        guild=discord.Object(id=GUILD_ID)
    )
    # @app_commands.check(leadership_or_event_coordinator_check)  # Temporarily disabled
    @app_commands.describe(team="Team to display board for (optional, leadership/event coordinator only)")
    @rate_limit(cooldown_seconds=10.0, max_requests_per_hour=30)  # Rate limit board updates
    async def board_cmd(interaction: Interaction, team: str = None):
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message("❌ Only the event host can use this command right now.", ephemeral=True)
            return
        start_time = time.time()
        
        # Check if board is released
        db = DatabaseManager()
        release_time_str = db.get_board_release_time()
        
        if release_time_str:
            try:
                release_time = datetime.fromisoformat(release_time_str.replace('Z', '+00:00'))
                if release_time.tzinfo is None:
                    release_time = release_time.replace(tzinfo=timezone.utc)
                
                if datetime.now(timezone.utc) < release_time:
                    time_until_release = release_time - datetime.now(timezone.utc)
                    hours = int(time_until_release.total_seconds() // 3600)
                    minutes = int((time_until_release.total_seconds() % 3600) // 60)
                    
                    await interaction.response.send_message(
                        f"⏰ **Board not yet released!**\n"
                        f"The bingo board will be available in **{hours}h {minutes}m**\n"
                        f"Release time: <t:{int(release_time.timestamp())}:F>",
                        ephemeral=True
                    )
                    return
            except Exception as e:
                logger.error(f"Error parsing release time: {e}")
                # If there's an error parsing the time, allow access
        
        team = team.lower() if team else DEFAULT_TEAM

        if team != DEFAULT_TEAM and team.capitalize() not in TEAM_ROLES:
            await interaction.response.send_message(
                f"❌ Invalid team '{team}'. Valid teams: {', '.join(TEAM_ROLES)} or 'all'.",
                ephemeral=True
            )
            return

        try:
            # 1. Defer the response to avoid interaction timeout
            await interaction.response.defer(ephemeral=False)

            # No completed_dict needed; board image will use DB-backed progress
            success = generate_board_image(team=team)
            
            if success and os.path.exists(OUTPUT_FILE):
                file = discord.File(OUTPUT_FILE)
                #3the final response with the image
                await interaction.followup.send(file=file)
                
                execution_time = time.time() - start_time
                logger.info(f"Board command completed in {execution_time:.3f}s for team {team}")
            else:
                await interaction.followup.send("❌ Failed to generate board image.")
                
        except Exception as e:
            logger.error(f"Error displaying board: {e}")
            await interaction.followup.send(f"❌ Error generating board: {str(e)}")

    @bot.tree.command(
        name="set_board_release",
        description="Set the time when the bingo board will be released",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(
        release_time="When to release the board (e.g., '2025-07-21 14:00 UTC' or 'tomorrow 2pm')"
    )
    async def set_board_release_cmd(interaction: Interaction, release_time: str):
        db = DatabaseManager()
        
        try:
            # Parse the release time
            if release_time.lower() == "now":
                success = db.clear_board_release_time()
                if success:
                    await interaction.response.send_message(
                        "✅ **Board released immediately!** The board is now available to all users.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ Error clearing board release time.",
                        ephemeral=True
                    )
                return
            
            # Try to parse various time formats
            parsed_time = None
            
            # Try ISO format first
            try:
                parsed_time = datetime.fromisoformat(release_time.replace('Z', '+00:00'))
                if parsed_time.tzinfo is None:
                    parsed_time = parsed_time.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
            
            # Try common formats
            if not parsed_time:
                try:
                    # Try "YYYY-MM-DD HH:MM UTC" format
                    parsed_time = datetime.strptime(release_time, "%Y-%m-%d %H:%M UTC")
                    parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            
            if not parsed_time:
                await interaction.response.send_message(
                    "❌ **Invalid time format!** Please use one of these formats:\n"
                    "• `2025-07-21 14:00 UTC`\n"
                    "• `2025-07-21T14:00:00Z`\n"
                    "• `now` (to release immediately)",
                    ephemeral=True
                )
                return
            
            # Check if time is in the future
            if parsed_time <= datetime.now(timezone.utc):
                await interaction.response.send_message(
                    "❌ **Release time must be in the future!** Please set a future time.",
                    ephemeral=True
                )
                return
            
            # Store in database
            success = db.set_board_release_time(
                parsed_time.isoformat(), 
                f"{interaction.user.name}#{interaction.user.discriminator}"
            )
            
            if success:
                await interaction.response.send_message(
                    f"✅ **Board release time set!**\n"
                    f"The bingo board will be released at: <t:{int(parsed_time.timestamp())}:F>\n"
                    f"That's <t:{int(parsed_time.timestamp())}:R> from now.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Error saving board release time to database.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error setting board release time: {e}")
            await interaction.response.send_message(
                f"❌ Error setting release time: {str(e)}",
                ephemeral=True
            )

    @bot.tree.command(
        name="board_status",
        description="Check the current board release status",
        guild=discord.Object(id=GUILD_ID)
    )
    async def board_status_cmd(interaction: Interaction):
        db = DatabaseManager()
        status = db.get_board_release_status()
        
        if not status.get('is_scheduled'):
            await interaction.response.send_message(
                "✅ **Board is currently available!** No release time is set.",
                ephemeral=True
            )
        else:
            try:
                release_time = datetime.fromisoformat(status['release_time'].replace('Z', '+00:00'))
                if release_time.tzinfo is None:
                    release_time = release_time.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                if now >= release_time:
                    await interaction.response.send_message(
                        "✅ **Board is available!** The release time has passed.",
                        ephemeral=True
                    )
                else:
                    time_until_release = release_time - now
                    hours = int(time_until_release.total_seconds() // 3600)
                    minutes = int((time_until_release.total_seconds() % 3600) // 60)
                    
                    await interaction.response.send_message(
                        f"⏰ **Board release scheduled!**\n"
                        f"Release time: <t:{int(release_time.timestamp())}:F>\n"
                        f"Time remaining: **{hours}h {minutes}m**\n"
                        f"That's <t:{int(release_time.timestamp())}:R>\n"
                        f"Set by: {status['created_by']}",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Error parsing release time in status: {e}")
                await interaction.response.send_message(
                    "❌ Error checking board status.",
                    ephemeral=True
                )

def update_board_message(guild: discord.Guild, bot_user: discord.User, team: str = DEFAULT_TEAM):
    from core.update_board import update_board_message as update_board
    return update_board(guild, bot_user, team)
