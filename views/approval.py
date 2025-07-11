import discord
from discord.ui import View, Button
from discord import Interaction
from views.modals import HoldReasonModal, DenyReasonModal
from storage import completed_dict, save_completed
import board
from views.hold import HoldReviewView
from config import EVENT_COORDINATOR_ROLE, ADMIN_ROLE, PLACEHOLDERS, HOLD_REVIEW_CHANNEL_NAME
from core.update_board import update_board_message

class ApprovalView(View):
    def __init__(self, submitter: discord.User, tile_index: int, team: str):
        super().__init__(timeout=None)
        self.submitter = submitter
        self.tile_index = tile_index
        self.team = team

    async def interaction_allowed(self, interaction: Interaction) -> bool:
        roles = [r.name for r in interaction.user.roles]
        return EVENT_COORDINATOR_ROLE in roles or ADMIN_ROLE in roles

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission to accept.", ephemeral=True)
            return

        if self.team not in completed_dict:
            completed_dict[self.team] = []

        if self.tile_index not in completed_dict[self.team]:
            completed_dict[self.team].append(self.tile_index)
            save_completed()
            board.generate_board_image(PLACEHOLDERS, completed_dict)
            await update_board_message(interaction.guild)

        tile_name = PLACEHOLDERS[self.tile_index]

        await interaction.message.edit(content=f"✅ Accepted **{self.submitter.display_name}** for tile **{tile_name}** (Team: {self.team})", view=None)
        await interaction.response.send_message("Submission accepted and board updated!", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission to deny.", ephemeral=True)
            return

        tile_name = PLACEHOLDERS[self.tile_index]
        await interaction.message.edit(content=f"❌ Denied **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})", view=None)
        await interaction.response.send_message("Submission denied.", ephemeral=True)

    @discord.ui.button(label="⏸️ Hold", style=discord.ButtonStyle.secondary)
    async def hold(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission to hold submissions.", ephemeral=True)
            return

        guild = interaction.guild
        hold_channel = discord.utils.get(guild.text_channels, name=HOLD_REVIEW_CHANNEL_NAME)
        if not hold_channel:
            await interaction.response.send_message("❌ Hold-review channel not found.", ephemeral=True)
            return

        tile_name = PLACEHOLDERS[self.tile_index]
        files = [await att.to_file() for att in interaction.message.attachments]

        view = HoldReviewView(self.submitter, self.tile_index, interaction.message.channel.id, self.team)

        await hold_channel.send(
            content=(
                f"⏸️ Submission ON HOLD from {self.submitter.mention} "
                f"for **{tile_name}** (Team: {self.team})\nMarked by: {interaction.user.mention}"
            ),
            files=files,
            view=view
        )

        await interaction.message.edit(content=f"⏸️ On Hold: **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})", view=None)
        await interaction.response.send_message("Submission marked on hold and sent to hold-review channel.", ephemeral=True)
