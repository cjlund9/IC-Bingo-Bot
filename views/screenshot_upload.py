import discord
from discord.ui import View, Button
from discord import Interaction
import logging
import asyncio
import sqlite3
from views.approval import ApprovalView
import config

logger = logging.getLogger(__name__)

class ScreenshotUploadView(View):
    def __init__(self, tile_name: str, tile_index: int, team: str, points: int, notes: str, user: discord.User):
        super().__init__(timeout=300)  # 5 minute timeout
        self.tile_name = tile_name
        self.tile_index = tile_index
        self.team = team
        self.points = points
        self.notes = notes
        self.user = user

    @discord.ui.button(label="📸 Upload Screenshot", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def upload_screenshot(self, interaction: Interaction, button: Button):
        """Handle screenshot upload and complete submission"""
        try:
            # Check if the user has uploaded any attachments
            if not interaction.message.attachments:
                await interaction.response.send_message(
                    "❌ No screenshot found. Please upload a screenshot first, then click this button.",
                    ephemeral=True
                )
                return

            # Get the first attachment (screenshot)
            attachment = interaction.message.attachments[0]
            
            # Validate file size (max 25MB)
            if attachment.size > 25 * 1024 * 1024:
                await interaction.response.send_message(
                    "❌ File too large. Please upload a smaller screenshot (max 25MB).",
                    ephemeral=True
                )
                return

            # Convert attachment to file with timeout
            try:
                file = await asyncio.wait_for(attachment.to_file(), timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.response.send_message(
                    "❌ Failed to process attachment. Please try again.",
                    ephemeral=True
                )
                return

            # Find the review channel
            review_channel = discord.utils.get(interaction.guild.text_channels, name=config.REVIEW_CHANNEL_NAME)
            if not review_channel:
                await interaction.response.send_message(
                    f"❌ Review channel #{config.REVIEW_CHANNEL_NAME} not found.",
                    ephemeral=True
                )
                return

            # Create the submission in the database first
            conn = sqlite3.connect('leaderboard.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bingo_submissions (team_name, tile_id, user_id, drop_name, quantity, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (self.team, self.tile_index, self.user.id, "points", self.points))
            
            submission_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Create the approval view
            view = ApprovalView(self.user, self.tile_index, self.team, drop=f"{self.points:,} points", submission_id=submission_id)

            # Create submission message
            submission_content = (
                f"📥 Points Submission from {self.user.mention} for **{self.tile_name}** (Team: {self.team})\n"
                f"Points: **{self.points:,}**"
            )
            
            if self.notes:
                submission_content += f"\nNotes: {self.notes}"

            # Send to review channel
            await review_channel.send(
                content=submission_content,
                file=file,
                view=view
            )

            # Update the original message to show success
            embed = discord.Embed(
                title="✅ Submission Sent!",
                description=f"**Tile:** {self.tile_name}\n**Points:** {self.points:,}\n\nYour submission has been sent to the review channel for approval.",
                color=0x00FF00
            )
            
            if self.notes:
                embed.add_field(name="Notes", value=self.notes, inline=False)

            await interaction.message.edit(
                embed=embed,
                view=None  # Remove the button
            )
            
            await interaction.response.send_message(
                "✅ Points submission sent for review!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in screenshot upload: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your submission. Please try again.",
                ephemeral=True
            )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        """Cancel the submission"""
        embed = discord.Embed(
            title="❌ Submission Cancelled",
            description="Points submission has been cancelled.",
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