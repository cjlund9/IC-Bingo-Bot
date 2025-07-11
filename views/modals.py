import discord
from discord.ui import Modal, TextInput
from discord import Interaction
from config import PLACEHOLDERS
from storage import save_completed, completed_dict

HOLD_REVIEW_CHANNEL_NAME = "hold-review"  # or import from config if you have

class HoldReasonModal(Modal, title="Hold Submission Explanation"):
    reason = TextInput(
        label="Reason for holding this submission",
        style=discord.TextStyle.paragraph,
        placeholder="Explain why this submission is on hold...",
        required=True,
        max_length=300,
    )

    def __init__(self, submitter: discord.User, tile_index: int, original_message: discord.Message, team: str):
        super().__init__()
        self.submitter = submitter
        self.tile_index = tile_index
        self.original_message = original_message
        self.team = team

    async def on_submit(self, interaction: Interaction):
        guild = interaction.guild
        hold_channel = discord.utils.get(guild.text_channels, name=HOLD_REVIEW_CHANNEL_NAME)
        if not hold_channel:
            await interaction.response.send_message("❌ Hold-review channel not found.", ephemeral=True)
            return

        tile_name = PLACEHOLDERS[self.tile_index]
        files = [await att.to_file() for att in self.original_message.attachments]

        content = (
            f"⏸️ Submission ON HOLD from {self.submitter.mention} "
            f"for **{tile_name}** (Team: **{self.team}**)\n"
            f"Marked by: {interaction.user.mention}\n"
            f"**Reason:** {self.reason.value}\n"
            f"Original submission channel ID: {self.original_message.channel.id}\n"
            f"Original submission message ID: {self.original_message.id}"
        )

        view = HoldReviewView(self.submitter, self.tile_index, self.original_message.channel.id, self.team)

        await hold_channel.send(content=content, files=files, view=view)
        await self.original_message.edit(content=f"⏸️ On Hold: **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})", view=None)
        await interaction.response.send_message("Submission marked on hold and sent to hold-review channel.", ephemeral=True)


class DenyReasonModal(Modal, title="Deny Submission Explanation"):
    reason = TextInput(
        label="Reason for denying this submission",
        style=discord.TextStyle.paragraph,
        placeholder="Explain why this submission is denied...",
        required=True,
        max_length=300,
    )

    def __init__(self, submitter: discord.User, tile_index: int, original_channel_id: int, interaction_message: discord.Message, team: str):
        super().__init__()
        self.submitter = submitter
        self.tile_index = tile_index
        self.original_channel_id = original_channel_id
        self.interaction_message = interaction_message
        self.team = team

    async def on_submit(self, interaction: Interaction):
        tile_name = PLACEHOLDERS[self.tile_index]
        guild = interaction.guild
        orig_channel = guild.get_channel(self.original_channel_id)

        if orig_channel:
            await orig_channel.send(
                content=(
                    f"❌ Submission DENIED from hold by {interaction.user.mention} for {self.submitter.mention} "
                    f"on **{tile_name}** (Team: **{self.team}**).\n"
                    f"**Reason:** {self.reason.value}"
                )
            )

        await self.interaction_message.edit(content=f"❌ Denied (from HOLD) **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})", view=None)
        await interaction.response.send_message("Submission denied from hold with reason and notified original submissions channel.", ephemeral=True)
