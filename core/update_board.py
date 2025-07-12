import discord
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def update_board_message(guild: discord.Guild, bot_user: Optional[discord.User] = None, team: str = "all"):
    """
    Update the bingo board message in the board channel
    
    Args:
        guild: Discord guild
        bot_user: Bot user object (optional, will be fetched if not provided)
        team: Team to update board for (defaults to "all")
    """
    from config import BOARD_CHANNEL_NAME, TEAM_ROLES, DEFAULT_TEAM
    from board import generate_board_image, OUTPUT_FILE, load_placeholders
    from storage import get_completed

    board_channel = discord.utils.get(guild.text_channels, name=BOARD_CHANNEL_NAME)
    if not board_channel:
        logger.warning(f"Board channel '{BOARD_CHANNEL_NAME}' not found")
        return

    # Get bot user if not provided
    if not bot_user:
        bot_user = guild.me

    completed_dict = get_completed()
    placeholders = load_placeholders()

    # Generate board image with timestamp to prevent caching
    timestamp = int(time.time())
    temp_output_file = f"board_{timestamp}.png"
    
    try:
        # Generate the board image
        success = generate_board_image(placeholders, completed_dict, team=team)
        if not success:
            logger.error("Failed to generate board image")
            return

        # Create a copy with timestamp to prevent Discord caching
        import shutil
        shutil.copy2(OUTPUT_FILE, temp_output_file)
        
        # Find existing board message for this team
        existing_message = None
        async for message in board_channel.history(limit=50):
            if (message.author == bot_user and 
                message.attachments and 
                f"Team: **{team.capitalize()}" in message.content):
                existing_message = message
                break

        # Create file object
        file = discord.File(temp_output_file, filename=f"bingo_board_{team}_{timestamp}.png")

        if existing_message:
            # Update existing message
            try:
                await existing_message.edit(
                    content=f"📊 Updated Bingo Board (Team: **{team.capitalize()}**) - Last updated: <t:{timestamp}:R>",
                    attachments=[file]
                )
                logger.info(f"Updated existing board message for team: {team}")
            except Exception as e:
                logger.error(f"Failed to update existing message: {e}")
                # Fallback: send new message
                await board_channel.send(
                    content=f"📊 Updated Bingo Board (Team: **{team.capitalize()}**) - Last updated: <t:{timestamp}:R>",
                    file=file
                )
        else:
            # Send new message
            await board_channel.send(
                content=f"📊 Updated Bingo Board (Team: **{team.capitalize()}**) - Last updated: <t:{timestamp}:R>",
                file=file
            )
            logger.info(f"Sent new board message for team: {team}")

    except Exception as e:
        logger.error(f"Error updating board message: {e}")
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_output_file):
                os.remove(temp_output_file)
        except Exception as e:
            logger.error(f"Failed to clean up temporary file: {e}")

async def update_all_team_boards(guild: discord.Guild, bot_user: Optional[discord.User] = None):
    """Update board messages for all teams"""
    for team in TEAM_ROLES:
        await update_board_message(guild, bot_user, team.lower())
