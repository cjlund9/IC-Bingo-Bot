import discord
from discord.ui import View, Button, Select
from discord import Interaction
import logging
from typing import List, Dict, Any

from config import ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from storage import get_tile_progress, remove_tile_submission, mark_tile_submission
from board import generate_board_image
from core.update_board import update_board_message

logger = logging.getLogger(__name__)

class SubmissionManagementView(View):
    def __init__(self, team: str, tile_index: int, drop: str):
        super().__init__(timeout=None)
        self.team = team
        self.tile_index = tile_index
        self.drop = drop

    async def interaction_allowed(self, interaction: Interaction) -> bool:
        roles = [r.name for r in interaction.user.roles]
        return EVENT_COORDINATOR_ROLE in roles or ADMIN_ROLE in roles

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission to approve submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Mark the submission
            success = mark_tile_submission(self.team, self.tile_index, interaction.user.id, self.drop, quantity=1)
            
            if success:
                # Update board
                from config import load_placeholders
                placeholders = load_placeholders()
                generate_board_image(placeholders, {}, team=self.team)
                await update_board_message(interaction.guild, interaction.guild.me, team=self.team)

                # Get tile info for response
                progress = get_tile_progress(self.team, self.tile_index)
                tile_name = progress.get("tile_name", f"Tile {self.tile_index}")
                
                await interaction.message.edit(
                    content=f"✅ Approved submission for **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
                    view=None
                )
                await interaction.followup.send("Submission approved and board updated!", ephemeral=True)
                logger.info(f"Submission approved: Team={self.team}, Tile={self.tile_index}, Drop={self.drop}")
            else:
                await interaction.followup.send("❌ Failed to approve submission.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error approving submission: {e}")
            await interaction.followup.send("❌ An error occurred while approving the submission.", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission to deny submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Get tile info for response
            progress = get_tile_progress(self.team, self.tile_index)
            tile_name = progress.get("tile_name", f"Tile {self.tile_index}")
            
            await interaction.message.edit(
                content=f"❌ Denied submission for **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
                view=None
            )
            await interaction.followup.send("Submission denied.", ephemeral=True)
            logger.info(f"Submission denied: Team={self.team}, Tile={self.tile_index}, Drop={self.drop}")
            
        except Exception as e:
            logger.error(f"Error denying submission: {e}")
            await interaction.followup.send("❌ An error occurred while denying the submission.", ephemeral=True)

    @discord.ui.button(label="⏸️ Hold", style=discord.ButtonStyle.secondary)
    async def hold(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ You don't have permission to hold submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Get tile info for response
            progress = get_tile_progress(self.team, self.tile_index)
            tile_name = progress.get("tile_name", f"Tile {self.tile_index}")
            
            await interaction.message.edit(
                content=f"⏸️ On Hold: **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
                view=None
            )
            await interaction.followup.send("Submission marked on hold.", ephemeral=True)
            logger.info(f"Submission held: Team={self.team}, Tile={self.tile_index}, Drop={self.drop}")
            
        except Exception as e:
            logger.error(f"Error holding submission: {e}")
            await interaction.followup.send("❌ An error occurred while holding the submission.", ephemeral=True)

class SubmissionRemovalView(View):
    def __init__(self, team: str, tile_index: int):
        super().__init__(timeout=None)
        self.team = team
        self.tile_index = tile_index
        self.submissions = []

    async def interaction_allowed(self, interaction: Interaction) -> bool:
        roles = [r.name for r in interaction.user.roles]
        return ADMIN_ROLE in roles  # Only admins can remove submissions

    async def load_submissions(self):
        """Load submissions for the tile"""
        progress = get_tile_progress(self.team, self.tile_index)
        self.submissions = progress.get("submissions", [])
        return self.submissions

    @discord.ui.button(label="🗑️ Remove Submission", style=discord.ButtonStyle.danger)
    async def remove_submission(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ Only admins can remove submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Load submissions if not already loaded
            if not self.submissions:
                await self.load_submissions()

            if not self.submissions:
                await interaction.followup.send("❌ No submissions found for this tile.", ephemeral=True)
                return

            # Create selection menu for submissions
            options = []
            for i, submission in enumerate(self.submissions):
                options.append(discord.SelectOption(
                    label=f"{submission['drop']} (x{submission['quantity']})",
                    description=f"By <@{submission['user_id']}>",
                    value=str(i)
                ))

            # Create selection view
            select_view = SubmissionSelectView(self.team, self.tile_index, self.submissions)
            await interaction.followup.send(
                "Select a submission to remove:",
                view=select_view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error loading submissions for removal: {e}")
            await interaction.followup.send("❌ An error occurred while loading submissions.", ephemeral=True)

class SubmissionSelectView(View):
    def __init__(self, team: str, tile_index: int, submissions: List[Dict[str, Any]]):
        super().__init__(timeout=60)  # 60 second timeout
        self.team = team
        self.tile_index = tile_index
        self.submissions = submissions

        # Create select menu
        options = []
        for i, submission in enumerate(submissions):
            options.append(discord.SelectOption(
                label=f"{submission['drop']} (x{submission['quantity']})",
                description=f"By <@{submission['user_id']}>",
                value=str(i)
            ))

        self.add_item(SubmissionSelect(options))

class SubmissionSelect(Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(
            placeholder="Choose a submission to remove...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            submission_index = int(self.values[0])
            view = self.view
            
            # Remove the submission
            success = remove_tile_submission(view.team, view.tile_index, submission_index)
            
            if success:
                # Update board
                from config import load_placeholders
                placeholders = load_placeholders()
                generate_board_image(placeholders, {}, team=view.team)
                await update_board_message(interaction.guild, interaction.guild.me, team=view.team)

                removed_submission = view.submissions[submission_index]
                await interaction.followup.send(
                    f"✅ Removed submission: **{removed_submission['drop']}** (x{removed_submission['quantity']})\n"
                    f"Board has been updated.",
                    ephemeral=True
                )
                logger.info(f"Submission removed: Team={view.team}, Tile={view.tile_index}, Index={submission_index}")
            else:
                await interaction.followup.send("❌ Failed to remove submission.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error removing submission: {e}")
            await interaction.followup.send("❌ An error occurred while removing the submission.", ephemeral=True) 