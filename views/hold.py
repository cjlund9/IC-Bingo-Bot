import discord
import board
from discord.ui import View, Button
from discord import Interaction
from views.modals import DenyReasonModal
import logging

logger = logging.getLogger(__name__)
from board import generate_board_image
from config import ADMIN_ROLE
from core.update_board import update_board_message

class HoldReviewView(View):
    def __init__(
        self,
        submitter: discord.User,
        tile_index: int,
        original_channel_id: int,
        team: str,
        drop: str  # 🆕 Added drop name to constructor
    ):
        super().__init__(timeout=None)
        self.submitter = submitter
        self.tile_index = tile_index
        self.original_channel_id = original_channel_id
        self.team = team
        self.drop = drop  # 🧠 Store the drop item

    def is_admin(self, interaction: Interaction) -> bool:
        """Only leadership can handle hold submissions"""
        return ADMIN_ROLE in [role.name for role in interaction.user.roles]

    @discord.ui.button(label="✅ Approve (Leadership only)", style=discord.ButtonStyle.success)
    async def approve(self, interaction: Interaction, button: Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Only leadership can approve submissions from hold.", ephemeral=True)
            return

        from storage import mark_tile_submission
        success = mark_tile_submission(self.team, self.tile_index, self.submitter.id, self.drop, quantity=1)
        if not success:
            logger.error(f"[HOLD APPROVE] Failed to mark tile submission for team={self.team}, tile_index={self.tile_index}, submitter={getattr(self.submitter, 'id', None)}, drop={self.drop}")
            await interaction.response.send_message("❌ Failed to approve submission in the database. Please contact an admin.", ephemeral=True)
            return
        try:
            from config import load_placeholders
            placeholders = load_placeholders()
            from board import generate_board_image
            image_success = generate_board_image(placeholders, None, team=self.team)
            if not image_success:
                logger.error(f"[HOLD APPROVE] Failed to generate board image for team: {self.team}")
                await interaction.followup.send("❌ Failed to generate board image. Please contact an admin.", ephemeral=True)
                return
            try:
                await update_board_message(interaction.guild, interaction.guild.me, team=self.team)
                logger.info(f"Board message updated for team: {self.team}")
            except Exception as e:
                logger.error(f"Error updating board message in Discord after hold approval: {e}")
                await interaction.followup.send("❌ Failed to update board message in Discord. Please contact an admin.", ephemeral=True)
                return
        except Exception as e:
            logger.error(f"Error updating board after hold approval: {e}")
            await interaction.followup.send("❌ Error updating board after approval. Please contact an admin.", ephemeral=True)
            return

        from config import load_placeholders
        placeholders = load_placeholders()
        tile = placeholders[self.tile_index]
        tile_name = tile["name"]

        guild = interaction.guild
        orig_channel = guild.get_channel(self.original_channel_id)
        if orig_channel:
            files = [await att.to_file() for att in interaction.message.attachments]
            await orig_channel.send(
                content=(
                    f"✅ Submission APPROVED from hold by {interaction.user.mention} for "
                    f"{self.submitter.mention} on **{tile_name}** (Team: {self.team})\n"
                    f"Drop: **{self.drop}**"
                ),
                files=files
            )

        await interaction.message.edit(
            content=(
                f"✅ Approved (from HOLD) **{self.submitter.display_name}** for "
                f"tile **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**"
            ),
            view=None
        )
        await interaction.followup.send("Submission approved and board updated!", ephemeral=True)

    @discord.ui.button(label="❌ Deny (Leadership only)", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Only leadership can deny submissions from hold.", ephemeral=True)
            return

        # Pass `drop` here to match updated DenyReasonModal constructor
        modal = DenyReasonModal(
            self.submitter,
            self.tile_index,
            self.original_channel_id,
            interaction.message,
            self.team,
            self.drop
        )
        await interaction.response.send_modal(modal)
