import discord
from discord.ui import View, Button
from discord import Interaction
from views.modals import HoldReasonModal, DenyReasonModal
import board
from views.hold import HoldReviewView
from config import EVENT_COORDINATOR_ROLE, ADMIN_ROLE, EVENT_COORDINATOR_ROLE_ID, ADMIN_ROLE_ID, HOLD_REVIEW_CHANNEL_NAME
from core.update_board import update_board_message

class ApprovalView(View):
    def __init__(self, submitter: discord.User, tile_index: int, team: str, drop: str, submission_id: int = None):
        super().__init__(timeout=None)
        self.submitter = submitter
        # Use tile_index as received (already 0-based from UI)
        self.tile_index = tile_index
        self.team = team
        self.drop = drop
        self.submission_id = submission_id  # Store submission ID for approval
        # Strict validation: mark as invalid if tile_index is out of range
        from config import load_placeholders
        self.placeholders = load_placeholders()
        self.is_valid_index = 0 <= self.tile_index < len(self.placeholders)
        if not self.is_valid_index:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[APPROVAL INIT] Invalid tile index: {self.tile_index}, placeholders length: {len(self.placeholders)}, submission_id: {self.submission_id}, team: {self.team}, drop: {self.drop}, submitter: {getattr(self.submitter, 'id', None)}")

    async def interaction_allowed(self, interaction: Interaction) -> bool:
        # Check by role ID if provided, else by name
        user_role_ids = [r.id for r in interaction.user.roles]
        user_role_names = [r.name for r in interaction.user.roles]
        if (ADMIN_ROLE_ID and int(ADMIN_ROLE_ID) in user_role_ids) or (EVENT_COORDINATOR_ROLE_ID and int(EVENT_COORDINATOR_ROLE_ID) in user_role_ids):
            return True
        return EVENT_COORDINATOR_ROLE in user_role_names or ADMIN_ROLE in user_role_names

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: Interaction, button: Button):
        if not self.is_valid_index:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[APPROVAL] Attempted to approve invalid tile index: {self.tile_index}, submission_id: {self.submission_id}, team: {self.team}, drop: {self.drop}, submitter: {getattr(self.submitter, 'id', None)}. Approval denied.")
            await interaction.response.send_message(f"❌ Invalid tile index: {self.tile_index}. Approval denied. Please contact an admin.", ephemeral=True)
            return
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can accept submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from config import load_placeholders
        placeholders = load_placeholders()
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] Approving submission: tile_index={self.tile_index}, tile_name={placeholders[self.tile_index]['name'] if 0 <= self.tile_index < len(placeholders) else 'OUT OF RANGE'}")
        logger.info(f"[APPROVAL] Loaded {len(placeholders)} placeholders. Submission tile_index={self.tile_index}")
        # Defensive check for tile index
        if not (0 <= self.tile_index < len(placeholders)):
            logger.warning(f"[APPROVAL] Invalid tile index: {self.tile_index}, placeholders length: {len(placeholders)}. Approval denied.")
            await interaction.followup.send(f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.", ephemeral=True)
            return

        # Use the new approval system
        from storage import approve_submission
        if self.submission_id:
            success = approve_submission(self.submission_id, interaction.user.id)
        else:
            # Fallback to old system if no submission_id
            from storage import mark_tile_submission
            success = mark_tile_submission(self.team, self.tile_index, self.submitter.id, self.drop, quantity=1)
        
        if success:
            await update_board_message(interaction.guild, interaction.guild.me, team=self.team)

        from config import load_placeholders
        placeholders = load_placeholders()
        # Defensive check for tile index
        if not (0 <= self.tile_index < len(placeholders)):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid tile index: {self.tile_index}, placeholders length: {len(placeholders)}")
            await interaction.message.edit(
                content=f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.",
                view=None
            )
            await interaction.followup.send(f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.", ephemeral=True)
            return
        tile_name = placeholders[self.tile_index]["name"]

        await interaction.message.edit(
            content=f"✅ Accepted **{self.submitter.display_name}** for tile **{tile_name}** (Team: {self.team})\nDrop: **{self.drop}**",
            view=None
        )
        await interaction.followup.send("Submission accepted and board updated!", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: Interaction, button: Button):
        if not self.is_valid_index:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[APPROVAL] Attempted to deny invalid tile index: {self.tile_index}, submission_id: {self.submission_id}, team: {self.team}, drop: {self.drop}, submitter: {getattr(self.submitter, 'id', None)}. Denial denied.")
            await interaction.response.send_message(f"❌ Invalid tile index: {self.tile_index}. Denial denied. Please contact an admin.", ephemeral=True)
            return
        if not await self.interaction_allowed(interaction):
            await interaction.response.send_message("❌ Only leadership or event coordinators can deny submissions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from config import load_placeholders
        placeholders = load_placeholders()
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[APPROVAL] Loaded {len(placeholders)} placeholders. Submission tile_index={self.tile_index}")
        # Defensive check for tile index
        if not (0 <= self.tile_index < len(placeholders)):
            logger.warning(f"[APPROVAL] Invalid tile index: {self.tile_index}, placeholders length: {len(placeholders)}. Approval denied.")
            await interaction.followup.send(f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.", ephemeral=True)
            return

        # Use the new approval system
        from storage import approve_submission
        if self.submission_id:
            success = approve_submission(self.submission_id, interaction.user.id)
        else:
            # Fallback to old system if no submission_id
            from storage import mark_tile_submission
            success = mark_tile_submission(self.team, self.tile_index, self.submitter.id, self.drop, quantity=1)
        
        if success:
            from config import load_placeholders
            placeholders = load_placeholders()
            # Defensive check for tile index
            if not (0 <= self.tile_index < len(placeholders)):
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Invalid tile index: {self.tile_index}, placeholders length: {len(placeholders)}")
                await interaction.followup.send(f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.", ephemeral=True)
                return
            from board import generate_board_image
            generate_board_image(placeholders, None, team=self.team)
            await update_board_message(interaction.guild, interaction.guild.me, team=self.team)

        from config import load_placeholders
        placeholders = load_placeholders()
        # Defensive check for tile index
        if not (0 <= self.tile_index < len(placeholders)):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid tile index: {self.tile_index}, placeholders length: {len(placeholders)}")
            await interaction.message.edit(
                content=f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.",
                view=None
            )
            await interaction.followup.send(f"❌ Invalid tile index: {self.tile_index}. Please contact an admin.", ephemeral=True)
            return
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
