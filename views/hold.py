import discord
import board
from discord.ui import View, Button
from discord import Interaction
from views.modals import DenyReasonModal
import logging

logger = logging.getLogger(__name__)
from board import generate_board_image
from config import ADMIN_ROLE, EVENT_COORDINATOR_ROLE, ADMIN_ROLE_ID, EVENT_COORDINATOR_ROLE_ID
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
        # Normalize tile_index from user input (1-based to 0-based)
        self.tile_index = tile_index - 1
        self.original_channel_id = original_channel_id
        self.team = team
        self.drop = drop  # 🧠 Store the drop item

    def is_admin(self, interaction: Interaction) -> bool:
        """Leadership or event coordinators can handle hold submissions"""
        user_role_ids = [r.id for r in interaction.user.roles]
        user_role_names = [r.name for r in interaction.user.roles]
        if (ADMIN_ROLE_ID and int(ADMIN_ROLE_ID) in user_role_ids) or (EVENT_COORDINATOR_ROLE_ID and int(EVENT_COORDINATOR_ROLE_ID) in user_role_ids):
            return True
        return EVENT_COORDINATOR_ROLE in user_role_names or ADMIN_ROLE in user_role_names

    @discord.ui.button(label="✅ Approve (Leadership or Event Coordinator)", style=discord.ButtonStyle.success)
    async def approve(self, interaction: Interaction, button: Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can approve submissions from hold.", ephemeral=True)
            return

        from storage import mark_tile_submission
        # Use self.tile_index for DB and placeholder lookups (already normalized)
        success = mark_tile_submission(self.team, self.tile_index, self.submitter.id, self.drop, quantity=1)
        if not success:
            logger.error(f"[HOLD APPROVE] Failed to mark tile submission for team={self.team}, tile_index={self.tile_index + 1}, submitter={getattr(self.submitter, 'id', None)}, drop={self.drop}")
            await interaction.response.send_message("❌ Failed to approve submission in the database. Please contact an admin.", ephemeral=True)
            return
        try:
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

    @discord.ui.button(label="❌ Deny (Leadership or Event Coordinator)", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can deny submissions from hold.", ephemeral=True)
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
