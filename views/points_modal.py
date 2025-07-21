import discord
from discord.ui import Modal, TextInput
from discord import Interaction
import logging

logger = logging.getLogger(__name__)

class PointsSubmissionModal(Modal, title="Submit Points"):
    points = TextInput(
        label="Points Earned",
        placeholder="Enter the number of points you earned (e.g., 1500)",
        required=True,
        min_length=1,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    notes = TextInput(
        label="Notes (Optional)",
        placeholder="Add any notes about how you earned these points...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, tile_name: str, tile_index: int, team: str, target_points: int):
        super().__init__()
        self.tile_name = tile_name
        self.tile_index = tile_index
        self.team = team
        self.target_points = target_points
        
        # Update the title to be more specific
        self.title = f"Submit Points for {tile_name}"
        
        # Update the points label to show target
        self.points.label = f"Points Earned (Target: {target_points:,})"
        self.points.placeholder = f"Enter points earned (target: {target_points:,})"

    async def on_submit(self, interaction: Interaction):
        try:
            # Validate points input
            points_value = int(self.points.value.replace(',', ''))
            
            if points_value <= 0:
                await interaction.response.send_message(
                    "❌ Points must be greater than 0.", 
                    ephemeral=True
                )
                return
            
            if points_value > 999999999:
                await interaction.response.send_message(
                    "❌ Points value too large. Please enter a smaller number.", 
                    ephemeral=True
                )
                return
            
            # Store the points value for the submission process
            self.points_value = points_value
            self.notes_value = self.notes.value.strip() if self.notes.value else ""
            
            # Send confirmation message
            embed = discord.Embed(
                title="✅ Points Ready for Submission",
                description=f"**Tile:** {self.tile_name}\n**Points:** {points_value:,}\n**Target:** {self.target_points:,}",
                color=0x00FF00
            )
            
            if self.notes_value:
                embed.add_field(name="Notes", value=self.notes_value, inline=False)
            
            embed.add_field(
                name="Next Steps", 
                value="Please upload a screenshot and use `/submit` to complete your submission.", 
                inline=False
            )
            
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number for points.", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in points modal submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.", 
                ephemeral=True
            )

class ResinSubmissionModal(Modal, title="Submit Resin Points"):
    resin_type = TextInput(
        label="Resin Type",
        placeholder="Mox resin, Aga resin, or Lye resin",
        required=True,
        max_length=20,
        style=discord.TextStyle.short
    )
    
    quantity = TextInput(
        label="Quantity",
        placeholder="Enter the quantity of resin (e.g., 1000)",
        required=True,
        min_length=1,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    notes = TextInput(
        label="Notes (Optional)",
        placeholder="Add any notes about your resin collection...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, tile_name: str, tile_index: int, team: str):
        super().__init__()
        self.tile_name = tile_name
        self.tile_index = tile_index
        self.team = team
        
        # Update the title
        self.title = f"Submit Resin for {tile_name}"
        
        # Add resin point values to the description
        self.resin_type.placeholder = "Mox resin (17,250 pts), Aga resin (14,000 pts), or Lye resin (18,600 pts)"

    async def on_submit(self, interaction: Interaction):
        try:
            # Validate quantity input
            quantity_value = int(self.quantity.value.replace(',', ''))
            
            if quantity_value <= 0:
                await interaction.response.send_message(
                    "❌ Quantity must be greater than 0.", 
                    ephemeral=True
                )
                return
            
            if quantity_value > 999999999:
                await interaction.response.send_message(
                    "❌ Quantity value too large. Please enter a smaller number.", 
                    ephemeral=True
                )
                return
            
            # Validate resin type
            resin_type = self.resin_type.value.strip().lower()
            valid_resins = {
                "mox resin": 17250,
                "aga resin": 14000,
                "lye resin": 18600
            }
            
            if resin_type not in valid_resins:
                await interaction.response.send_message(
                    "❌ Invalid resin type. Please enter: Mox resin, Aga resin, or Lye resin.", 
                    ephemeral=True
                )
                return
            
            # Calculate points based on resin type and quantity
            points_per_resin = valid_resins[resin_type]
            total_points = quantity_value * points_per_resin
            
            # Store values for submission process
            self.resin_type_value = self.resin_type.value.strip()
            self.quantity_value = quantity_value
            self.total_points = total_points
            self.notes_value = self.notes.value.strip() if self.notes.value else ""
            
            # Send confirmation message
            embed = discord.Embed(
                title="✅ Resin Points Ready for Submission",
                description=f"**Tile:** {self.tile_name}\n**Resin:** {self.resin_type_value}\n**Quantity:** {quantity_value:,}\n**Total Points:** {total_points:,}",
                color=0x00FF00
            )
            
            if self.notes_value:
                embed.add_field(name="Notes", value=self.notes_value, inline=False)
            
            embed.add_field(
                name="Next Steps", 
                value="Please upload a screenshot and use `/submit` to complete your submission.", 
                inline=False
            )
            
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number for quantity.", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in resin modal submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.", 
                ephemeral=True
            ) 