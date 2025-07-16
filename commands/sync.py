import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
import json
import os

from config import GUILD_ID, ADMIN_ROLE
from utils.access import bot_access_check, admin_access_check
from database import DatabaseManager

logger = logging.getLogger(__name__)

def setup_sync_command(bot: Bot):
    @bot.tree.command(
        name="migrate_to_db",
        description="Migrate bingo data from JSON files to database (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(admin_access_check)
    async def migrate_to_db_cmd(interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Initialize database
            db = DatabaseManager()
            
            # Load tiles.json
            tiles_file = "data/tiles.json"
            if not os.path.exists(tiles_file):
                await interaction.followup.send("❌ tiles.json not found", ephemeral=True)
                return
            
            with open(tiles_file, 'r', encoding='utf-8') as f:
                tiles_data = json.load(f)
            
            # Sync tiles to database
            tiles_success = db.sync_bingo_tiles_from_json(tiles_data)
            
            # Create response embed
            embed = discord.Embed(
                title="🔄 Database Migration Results",
                description="Migration from JSON files to database",
                color=0x0099FF
            )
            
            if tiles_success:
                embed.add_field(
                    name="✅ Tiles Migration",
                    value=f"Successfully synced {len(tiles_data)} tiles to database",
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ Tiles Migration",
                    value="Failed to sync tiles to database",
                    inline=False
                )
                embed.color = 0xFF0000
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in migrate_to_db command: {e}")
            await interaction.followup.send(f"❌ Error during migration: {str(e)}", ephemeral=True)

    @bot.tree.command(
        name="clear_progress",
        description="Clear all team progress and submissions from database (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(admin_access_check)
    async def clear_progress_cmd(interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Clear all progress and submissions
            db = DatabaseManager()
            success = db.clear_all_progress()
            
            if success:
                embed = discord.Embed(
                    title="✅ Progress Cleared",
                    description="All team progress and submissions have been cleared from the database",
                    color=0x00FF00
                )
                embed.add_field(
                    name="Cleared Data",
                    value="• All team progress\n• All submissions\n• Database ready for fresh start",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to clear progress from database",
                    color=0xFF0000
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in clear_progress command: {e}")
            await interaction.followup.send(f"❌ Error clearing progress: {str(e)}", ephemeral=True) 