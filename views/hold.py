import discord
import board
from discord.ui import View, Button
from discord import Interaction
from views.modals import DenyReasonModal
from storage import completed_dict, save_completed, get_completed
from board import generate_board_image
from config import ADMIN_ROLE, PLACEHOLDERS
from core.update_board import update_board_message

class HoldReviewView(View):
    def __init__(self, submitter: discord.User, tile_index: int, original_channel_id: int, team: str):
        super().__init__(timeout=None)
        self.submitter = submitter
        self.tile_index = tile_index
        self.original_channel_id = original_channel_id
        self.team = team

    def is_admin(self, interaction: Interaction) -> bool:
        return ADMIN_ROLE in [role.name for role in interaction.user.roles]

    @discord.ui.button(label="✅ Approve (Admin only)", style=discord.ButtonStyle.success)
    async def approve(self, interaction: Interaction, button: Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Only admins can approve submissions from hold.", ephemeral=True)
            return

        completed_dict = get_completed()

        if self.team not in completed_dict:
            completed_dict[self.team] = []

        if self.tile_index not in completed_dict[self.team]:
            completed_dict[self.team].append(self.tile_index)
            save_completed()
            board.generate_board_image(PLACEHOLDERS, completed_dict, team=self.team)
            await update_board_message(interaction.guild, team=self.team)

        tile_name = PLACEHOLDERS[self.tile_index]
        guild = interaction.guild
        orig_channel = guild.get_channel(self.original_channel_id)
        if orig_channel:
            files = [await att.to_file() for att in interaction.message.attachments]
            await orig_channel.send(
                content=f"✅ Submission APPROVED from hold by {interaction.user.mention} for {self.submitter.mention} on **{tile_name}** (Team: {self.team}).",
                files=files
            )

        await interaction.message.edit(content=f"✅ Approved (from HOLD) **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})", view=None)
        await interaction.response.send_message("Submission approved and sent back to original submissions channel!", ephemeral=True)

    @discord.ui.button(label="❌ Deny (Admin only)", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Only admins can deny submissions from hold.", ephemeral=True)
            return

        modal = DenyReasonModal(self.submitter, self.tile_index, self.original_channel_id, interaction.message, self.team)
        await interaction.response.send_modal(modal)

