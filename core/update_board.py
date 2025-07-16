import discord
import os
import time
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

async def update_board_message(guild: discord.Guild, bot_user: Optional[discord.User] = None, team: str = "all"):
    """
    Update the bingo board message in the appropriate channels
    """
    from config import BOARD_CHANNEL_NAME, TEAM_ROLES, DEFAULT_TEAM
    from board import generate_board_image, OUTPUT_FILE, load_placeholders

    # Determine which channels to post to based on team
    channels_to_update = []
    
    # Always post to the main bingo-board channel
    board_channel = discord.utils.get(guild.text_channels, name=BOARD_CHANNEL_NAME)
    if board_channel:
        channels_to_update.append(board_channel)
    else:
        logger.warning(f"Board channel '{BOARD_CHANNEL_NAME}' not found")
    
    # Add team-specific channels
    if team.lower() == "moles":
        moles_channel = discord.utils.get(guild.text_channels, name="moles-board")
        if moles_channel:
            channels_to_update.append(moles_channel)
        else:
            logger.warning("Moles board channel 'moles-board' not found")
    elif team.lower() == "obor":
        obor_channel = discord.utils.get(guild.text_channels, name="obor-board")
        if obor_channel:
            channels_to_update.append(obor_channel)
        else:
            logger.warning("Obor board channel 'obor-board' not found")
    
    if not channels_to_update:
        logger.error("No valid channels found to update board")
        return

    # Get bot user if not provided
    if not bot_user:
        bot_user = guild.me

    placeholders = load_placeholders()

    # Generate board image with timestamp to prevent caching
    timestamp = int(time.time())
    temp_output_file = f"board_{timestamp}.png"
    
    try:
        # Generate the board image (DB-backed)
        success = generate_board_image(placeholders, None, team=team)
        if not success:
            logger.error("Failed to generate board image")
            return

        # Create a copy with timestamp to prevent Discord caching
        import shutil
        shutil.copy2(OUTPUT_FILE, temp_output_file)
        
        # Update each channel with a fresh file object
        for channel in channels_to_update:
            file = discord.File(temp_output_file, filename=f"bingo_board_{team}_{timestamp}.png")
            await update_channel_board_message(channel, bot_user, team, file, timestamp)

    except Exception as e:
        logger.error(f"Error updating board message: {e}")
    finally:
        try:
            os.remove(temp_output_file)
        except Exception:
            pass

async def update_channel_board_message(channel: discord.TextChannel, bot_user: discord.User, team: str, file: discord.File, timestamp: int):
    """
    Update the board message in a specific channel
    
    Args:
        channel: Discord text channel to update
        bot_user: Bot user object
        team: Team name
        file: Discord file object with board image
        timestamp: Current timestamp
    """
    try:
        # Find existing board message for this team in this channel
        existing_message = None
        async for message in channel.history(limit=50):
            if (message.author == bot_user and 
                message.attachments and 
                f"Team: **{team.capitalize()}" in message.content):
                existing_message = message
                break

        if existing_message:
            # Update existing message
            try:
                await existing_message.edit(
                    content=f"📊 Updated Bingo Board (Team: **{team.capitalize()}**) - Last updated: <t:{timestamp}:R>",
                    attachments=[file]
                )
                logger.info(f"Updated existing board message for team: {team} in channel: {channel.name}")
            except Exception as e:
                logger.error(f"Failed to update existing message in {channel.name}: {e}")
                # Fallback: send new message
                await channel.send(
                    content=f"📊 Updated Bingo Board (Team: **{team.capitalize()}**) - Last updated: <t:{timestamp}:R>",
                    file=file
                )
        else:
            # Send new message
            await channel.send(
                content=f"📊 Updated Bingo Board (Team: **{team.capitalize()}**) - Last updated: <t:{timestamp}:R>",
                file=file
            )
            logger.info(f"Sent new board message for team: {team} in channel: {channel.name}")
            
    except Exception as e:
        logger.error(f"Error updating board message in channel {channel.name}: {e}")

async def update_all_team_boards(guild: discord.Guild, bot_user: Optional[discord.User] = None):
    """Update board messages for all teams"""
    for team in TEAM_ROLES:
        await update_board_message(guild, bot_user, team.lower())
