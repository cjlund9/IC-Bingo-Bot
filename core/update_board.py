import discord

async def update_board_message(guild: discord.Guild, bot_user: discord.User = None):
    from config import BOARD_CHANNEL_NAME, TEAM_ROLES, DEFAULT_TEAM
    from board import generate_board_image, OUTPUT_FILE, load_placeholders
    from storage import get_completed

    board_channel = discord.utils.get(guild.text_channels, name=BOARD_CHANNEL_NAME)
    if not board_channel:
        return

    completed_dict = get_completed()
    placeholders = load_placeholders()

    # First delete old bot messages (optional: for cleanliness)
    async for message in board_channel.history(limit=20):
        if bot_user and message.author == bot_user and message.attachments:
            await message.delete()

    for team in list(TEAM_ROLES):
        generate_board_image(placeholders, completed_dict, team=team)
        file = discord.File(OUTPUT_FILE)

        await board_channel.send(
            content=f"📊 Updated Bingo Board (Team: **{team}**)",
            file=file
        )
