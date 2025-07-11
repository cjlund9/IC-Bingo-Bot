import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot

import config
from storage import mark_tile_complete
from board import generate_board_image, OUTPUT_FILE
from utils import get_user_team
from views.approval import ApprovalView

async def tile_autocomplete(interaction: Interaction, current: str):
    choices = [
        app_commands.Choice(name=t, value=str(i))
        for i, t in enumerate(config.PLACEHOLDERS)
        if current.lower() in t.lower()
    ]
    return choices[:25]

def setup_submit_command(bot: Bot):
    @bot.tree.command(name="submit", description="Submit a completed bingo tile with screenshot", guild=discord.Object(id=config.GUILD_ID))
    @app_commands.describe(tile="Select the tile you completed", attachment="Upload screenshot")
    @app_commands.autocomplete(tile=tile_autocomplete)
    async def submit(interaction: Interaction, tile: str, attachment: discord.Attachment):
        if not attachment:
            await interaction.response.send_message("\u274C You must upload a screenshot.", ephemeral=True)
            return

        tile_index = int(tile)
        tile_name = config.PLACEHOLDERS[tile_index]
        member = interaction.user
        team = get_user_team(member)

        review_channel = discord.utils.get(interaction.guild.text_channels, name=config.REVIEW_CHANNEL_NAME)
        if not review_channel:
            await interaction.response.send_message(f"\u274C Review channel #{config.REVIEW_CHANNEL_NAME} not found.", ephemeral=True)
            return

        file = await attachment.to_file()
        view = ApprovalView(member, tile_index, team)

        await review_channel.send(content=f"\ud83d\udce5 Submission from {member.mention} for **{tile_name}** (Team: {team})", file=file, view=view)
        await interaction.response.send_message("\u2705 Submission sent for review!", ephemeral=True)
