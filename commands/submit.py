import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
import time
import asyncio
from utils.access import team_member_access_check
from utils.rate_limiter import rate_limit

import config
from storage import mark_tile_submission
from board import generate_board_image, OUTPUT_FILE
from utils import get_user_team
from views.approval import ApprovalView

logger = logging.getLogger(__name__)

# Autocomplete for tile selection
async def tile_autocomplete(interaction: Interaction, current: str):
    placeholders = config.load_placeholders()
    choices = []
    
    for i, t in enumerate(placeholders):
        # Calculate tile coordinates (A1, A2, etc.)
        row = i // 10  # 10x10 board
        col = i % 10
        row_letter = chr(65 + row)  # A=65, B=66, etc.
        col_number = col + 1  # 1-based column numbers
        tile_indicator = f"{row_letter}{col_number}"
        
        # Create display name with indicator
        display_name = f"{tile_indicator}: {t['name']}"
        
        # Check if current input matches either the indicator or the tile name
        if (current.lower() in display_name.lower() or 
            current.lower() in tile_indicator.lower() or 
            current.lower() in t["name"].lower()):
            choices.append(app_commands.Choice(name=display_name, value=str(i)))
    
    return choices[:25]

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
    @rate_limit(cooldown_seconds=5.0, max_requests_per_hour=50)  # Rate limit submissions
    async def submit(interaction: Interaction, tile: str, item: str, attachment: discord.Attachment):
        start_time = time.time()
        member = interaction.user

        try:
            # ✅ Defer immediately to avoid "Unknown Interaction" errors
            await interaction.response.defer(ephemeral=True)

            if not attachment:
                await interaction.followup.send("❌ You must upload a screenshot.", ephemeral=True)
                return

            # Validate file size (max 25MB)
            if attachment.size > 25 * 1024 * 1024:
                await interaction.followup.send("❌ File too large. Please upload a smaller screenshot (max 25MB).", ephemeral=True)
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

            # Convert attachment to file with timeout
            try:
                file = await asyncio.wait_for(attachment.to_file(), timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.followup.send("❌ Failed to process attachment. Please try again.", ephemeral=True)
                return

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
            
            # Log performance
            execution_time = time.time() - start_time
            logger.info(f"Submit command completed in {execution_time:.3f}s for user {member.id}")
        except Exception as e:
            logger.error(f"Error in submit command: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while processing your submission. Please try again.", ephemeral=True)
            except:
                pass  # Interaction might already be responded to
