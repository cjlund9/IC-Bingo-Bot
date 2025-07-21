import discord
from discord.ui import View, Button
from discord import Interaction
import logging
from views.points_modal import PointsSubmissionModal, ResinSubmissionModal
from utils import get_user_team

logger = logging.getLogger(__name__)

class PointsTileButtonView(View):
    def __init__(self, tile_name: str, tile_index: int, target_points: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.tile_name = tile_name
        self.tile_index = tile_index
        self.target_points = target_points

    @discord.ui.button(label="📝 Enter Points", style=discord.ButtonStyle.primary, emoji="🎯")
    async def enter_points(self, interaction: Interaction, button: Button):
        """Open points input modal"""
        try:
            team = get_user_team(interaction.user)
            
            if self.tile_name == "Chugging Barrel":
                # Use resin modal for Chugging Barrel
                modal = ResinSubmissionModal(self.tile_name, self.tile_index, team)
            else:
                # Use regular points modal for other points-based tiles
                modal = PointsSubmissionModal(self.tile_name, self.tile_index, team, self.target_points)
            
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error opening points modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while opening the points input form.", 
                ephemeral=True
            )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        """Cancel the points input"""
        await interaction.response.send_message(
            "❌ Points input cancelled.", 
            ephemeral=True
        )
        # Remove the view
        await interaction.message.edit(view=None) 