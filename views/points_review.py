import discord
from discord.ui import View, Button
from discord import Interaction
import logging
import asyncio
from views.approval import ApprovalView
import config

logger = logging.getLogger(__name__)

class PointsReviewView(View):
    def __init__(self, tile_name: str, tile_id: int, team: str, submission_id: int, user: discord.User, screenshot_file = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.tile_name = tile_name
        self.tile_id = tile_id
        self.team = team
        self.submission_id = submission_id
        self.user = user
        self.screenshot_file = screenshot_file

    @discord.ui.button(label="📤 Send to Review", style=discord.ButtonStyle.primary, emoji="✅")
    async def send_to_review(self, interaction: Interaction, button: Button):
        """Send the points submission to the review channel"""
        try:
            # Get the submission details
            import sqlite3
            conn = sqlite3.connect('leaderboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT drop_name, quantity 
                FROM bingo_submissions 
                WHERE id = ?
            ''', (self.submission_id,))
            submission = cursor.fetchone()
            conn.close()
            
            if not submission:
                await interaction.response.send_message(
                    "❌ Submission not found.",
                    ephemeral=True
                )
                return
                
            drop_name, quantity = submission
            
            # Find the review channel
            review_channel = discord.utils.get(interaction.guild.text_channels, name=config.REVIEW_CHANNEL_NAME)
            if not review_channel:
                await interaction.response.send_message(
                    f"❌ Review channel #{config.REVIEW_CHANNEL_NAME} not found.",
                    ephemeral=True
                )
                return

            # Create the approval view
            view = ApprovalView(self.user, self.tile_id, self.team, drop=f"{quantity:,} points", submission_id=self.submission_id)

            # Create submission message
            submission_content = (
                f"📥 Points Submission from {self.user.mention} for **{self.tile_name}** (Team: {self.team})\n"
                f"Points: **{quantity:,}**"
            )

            # Send to review channel
            if self.screenshot_file:
                await review_channel.send(
                    content=submission_content,
                    file=self.screenshot_file,
                    view=view
                )
            else:
                await review_channel.send(
                    content=submission_content,
                    view=view
                )

            # Update the original message to show success
            embed = discord.Embed(
                title="✅ Submission Sent!",
                description=f"**Tile:** {self.tile_name}\n**Points:** {quantity:,}\n\nYour submission has been sent to the review channel for approval.",
                color=0x00FF00
            )

            await interaction.message.edit(
                embed=embed,
                view=None  # Remove the button
            )
            
            await interaction.response.send_message(
                "✅ Points submission sent for review!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error sending points submission to review: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while sending your submission to review. Please try again.",
                ephemeral=True
            )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        """Cancel the submission"""
        try:
            # Delete the submission from database
            import sqlite3
            conn = sqlite3.connect('leaderboard.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM bingo_submissions WHERE id = ?', (self.submission_id,))
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="❌ Submission Cancelled",
                description="Points submission has been cancelled and removed.",
                color=0xFF0000
            )
            
            await interaction.message.edit(
                embed=embed,
                view=None
            )
            
            await interaction.response.send_message(
                "❌ Points submission cancelled.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error cancelling submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while cancelling the submission.",
                ephemeral=True
            ) 