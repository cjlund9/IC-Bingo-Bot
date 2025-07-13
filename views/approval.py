import discord
from discord.ui import View, Button
from discord import Interaction
from views.modals import HoldReasonModal, DenyReasonModal
from storage import completed_dict, save_completed
import board
from views.hold import HoldReviewView
from config import EVENT_COORDINATOR_ROLE, ADMIN_ROLE, HOLD_REVIEW_CHANNEL_NAME
from core.update_board import update_board_message

class ApprovalView(View):
    def __init__(self, submitter: discord.User, tile_index: int, team: str, drop: str):
        super().__init__(timeout=None)
        self.submitter = submitter
        self.tile_index = tile_index
        self.team = team
        self.drop = drop  # 🆕 Store drop

    async def interaction_allowed(self, interaction: Interaction) -> bool:
        roles = [r.name for r in interaction.user.roles]
        return EVENT_COORDINATOR_ROLE in roles or ADMIN_ROLE in roles

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can accept submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Use the new storage system
        from storage import mark_tile_submission
        success = mark_tile_submission(self.team, self.tile_index, self.submitter.id, self.drop, quantity=1)
        
        if success:
            from config import load_placeholders
            placeholders = load_placeholders()
            from storage import get_completed
            completed_dict = get_completed()
            board.generate_board_image(placeholders, completed_dict, team=self.team)
            await update_board_message(interaction.guild, interaction.guild.me, team=self.team)

        from config import load_placeholders
        placeholders = load_placeholders()
        tile_name = placeholders[self.tile_index]["name"]

        await interaction.message.edit(
            content=f"✅ Accepted **{self.submitter.display_name}** for tile **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
            view=None
        )
        await interaction.followup.send("Submission accepted and board updated!", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can deny submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from config import load_placeholders
        placeholders = load_placeholders()
        tile_name = placeholders[self.tile_index]["name"]

        await interaction.message.edit(
            content=f"❌ Denied **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
            view=None
        )
        await interaction.followup.send("Submission denied.", ephemeral=True)

    @discord.ui.button(label="⏸️ Hold", style=discord.ButtonStyle.secondary)
    async def hold(self, interaction: Interaction, button: Button):
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can hold submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        hold_channel = discord.utils.get(guild.text_channels, name=HOLD_REVIEW_CHANNEL_NAME)
        if not hold_channel:
            await interaction.followup.send("❌ Hold-review channel not found.", ephemeral=True)
            return

        from config import load_placeholders
        placeholders = load_placeholders()
        tile_name = placeholders[self.tile_index]["name"]
        files = [await att.to_file() for att in interaction.message.attachments]

        # Pass drop to HoldReviewView
        view = HoldReviewView(self.submitter, self.tile_index, interaction.message.channel.id, self.team, self.drop)

        await hold_channel.send(
            content=(
                f"⏸️ Submission ON HOLD from {self.submitter.mention} "
                f"for **{tile_name}** (Team: {self.team})\n"
                f"Drop: **{self.drop}**\nMarked by: {interaction.user.mention}"
            ),
            files=files,
            view=view
        )

        await interaction.message.edit(
            content=f"⏸️ On Hold: **{self.submitter.display_name}** for **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
            view=None
        )

        await interaction.followup.send("Submission marked on hold and sent to hold-review channel.", ephemeral=True)
