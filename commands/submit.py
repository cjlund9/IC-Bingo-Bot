import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from utils.access import team_member_access_check

import config
from storage import mark_tile_submission
from board import generate_board_image, OUTPUT_FILE
from utils import get_user_team
from views.approval import ApprovalView

logger = logging.getLogger(__name__)

# Autocomplete for tile selection
async def tile_autocomplete(interaction: Interaction, current: str):
    placeholders = config.load_placeholders()
    return [
        app_commands.Choice(name=t["name"], value=str(i))
        for i, t in enumerate(placeholders)
        if current.lower() in t["name"].lower()
    ][:25]

# Autocomplete for drop item based on selected tile
async def item_autocomplete(interaction: Interaction, current: str):
    tile_value = None
    if interaction.data and "options" in interaction.data:
        for option in interaction.data["options"]:
            if option["name"] == "tile":
                tile_value = option.get("value")
                break

    try:
        tile_index = int(tile_value)
        placeholders = config.load_placeholders()
        tile_data = placeholders[tile_index]
    except (TypeError, ValueError, IndexError) as e:
        return [app_commands.Choice(name="⚠️ Select a tile first", value="invalid")]

    drops = tile_data.get("drops_required", [])
    if not isinstance(drops, list):
        logger.warning(f"drops_required is not a list: {drops}")
        drops = []

    return [
        app_commands.Choice(name=item, value=item)
        for item in drops
        if current.lower() in item.lower()
    ][:25]


def setup_submit_command(bot: Bot):
    @bot.tree.command(
        name="submit",
        description="Submit a completed bingo tile with screenshot",
        guild=discord.Object(id=config.GUILD_ID)
    )
    @app_commands.check(team_member_access_check)
    @app_commands.describe(
        tile="Select the tile you completed",
        item="Which item did you get?",
        attachment="Upload screenshot"
    )
    @app_commands.autocomplete(tile=tile_autocomplete, item=item_autocomplete)
    async def submit(interaction: Interaction, tile: str, item: str, attachment: discord.Attachment):
        member = interaction.user

        # ✅ Defer immediately to avoid "Unknown Interaction" errors
        await interaction.response.defer(ephemeral=True)

        if not attachment:
            await interaction.followup.send("❌ You must upload a screenshot.", ephemeral=True)
            return

        try:
            tile_index = int(tile)
            placeholders = config.load_placeholders()
            tile_data = placeholders[tile_index]
        except (ValueError, IndexError):
            await interaction.followup.send("❌ Invalid tile selection.", ephemeral=True)
            return

        tile_name = tile_data["name"]
        team = get_user_team(member)

        review_channel = discord.utils.get(interaction.guild.text_channels, name=config.REVIEW_CHANNEL_NAME)
        if not review_channel:
            await interaction.followup.send(
                f"❌ Review channel #{config.REVIEW_CHANNEL_NAME} not found.",
                ephemeral=True
            )
            return

        file = await attachment.to_file()
        view = ApprovalView(member, tile_index, team, drop=item)

        await review_channel.send(
            content=(
                f"📥 Submission from {member.mention} for **{tile_name}** (Team: {team})\n"
                f"Drop: **{item}**"
            ),
            file=file,
            view=view
        )

        await interaction.followup.send("✅ Submission sent for review!", ephemeral=True)
