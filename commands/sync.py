import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
import json
import os

from config import GUILD_ID, ADMIN_ROLE
from storage import sync_completed_data_with_tiles
from utils.access import bot_access_check, admin_access_check
from database import DatabaseManager

logger = logging.getLogger(__name__)

def setup_sync_command(bot: Bot):
    @bot.tree.command(
        name="sync",
        description="Sync completed.json data with current tiles.json values (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(admin_access_check)
    async def sync_cmd(interaction: Interaction):
        try:
            
            await interaction.response.defer(ephemeral=True)
            
            # Perform sync
            sync_results = sync_completed_data_with_tiles()
            
            # Create response embed
            embed = discord.Embed(
                title="🔄 Data Sync Results",
                description="Sync completed.json with tiles.json",
                color=0x0099FF
            )
            
            updated_tiles = sync_results.get("updated_tiles", 0)
            errors = sync_results.get("errors", [])
            
            if updated_tiles > 0:
                embed.add_field(
                    name="✅ Success",
                    value=f"Updated {updated_tiles} tiles with current drops_needed values",
                    inline=False
                )
                embed.color = 0x00FF00
            else:
                embed.add_field(
                    name="ℹ️ No Changes",
                    value="All tiles already have correct total_required values",
                    inline=False
                )
            
            if errors:
                error_text = "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_text += f"\n... and {len(errors) - 5} more errors"
                embed.add_field(
                    name="⚠️ Errors",
                    value=error_text,
                    inline=False
                )
                embed.color = 0xFFA500
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in sync command: {e}")
            await interaction.followup.send(f"❌ Error during sync: {str(e)}", ephemeral=True)

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
            
            # Load completed.json
            completed_file = "data/completed.json"
            completed_data = {}
            if os.path.exists(completed_file):
                with open(completed_file, 'r', encoding='utf-8') as f:
                    completed_data = json.load(f)
            
            # Migrate completed data
            migration_success = db.migrate_json_to_database(completed_data)
            
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
            
            if migration_success:
                # Count migrated data
                team_count = len(completed_data)
                total_submissions = sum(
                    len(tile_data.get('submissions', []))
                    for team_data in completed_data.values()
                    for tile_data in team_data.values()
                    if isinstance(tile_data, dict)
                )
                
                embed.add_field(
                    name="✅ Data Migration",
                    value=f"Successfully migrated {team_count} teams and {total_submissions} submissions",
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ Data Migration",
                    value="Failed to migrate completed data to database",
                    inline=False
                )
                embed.color = 0xFF0000
            
            if tiles_success and migration_success:
                embed.color = 0x00FF00
                embed.add_field(
                    name="🎉 Migration Complete",
                    value="All data has been successfully migrated to the database!",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in migrate_to_db command: {e}")
            await interaction.followup.send(f"❌ Error during migration: {str(e)}", ephemeral=True)

    @bot.tree.command(
        name="validate_db",
        description="Validate database integrity and show statistics (Admin only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(admin_access_check)
    async def validate_db_cmd(interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            db = DatabaseManager()
            
            # Get database statistics
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Count tiles
                cursor.execute("SELECT COUNT(*) as count FROM bingo_tiles")
                tile_count = cursor.fetchone()['count']
                
                # Count teams
                cursor.execute("SELECT COUNT(DISTINCT team_name) as count FROM bingo_team_progress")
                team_count = cursor.fetchone()['count']
                
                # Count submissions by status
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM bingo_submissions 
                    GROUP BY status
                """)
                submission_stats = {row['status']: row['count'] for row in cursor.fetchall()}
                
                # Count completed tiles
                cursor.execute("SELECT COUNT(*) as count FROM bingo_team_progress WHERE is_complete = 1")
                completed_tiles = cursor.fetchone()['count']
                
                # Get team progress
                cursor.execute("""
                    SELECT team_name, COUNT(*) as total_tiles, 
                           SUM(CASE WHEN is_complete = 1 THEN 1 ELSE 0 END) as completed_tiles
                    FROM bingo_team_progress 
                    GROUP BY team_name
                """)
                team_progress = [dict(row) for row in cursor.fetchall()]
            
            # Create response embed
            embed = discord.Embed(
                title="📊 Database Validation Results",
                description="Database integrity check and statistics",
                color=0x00FF00
            )
            
            embed.add_field(
                name="🎯 Tiles",
                value=f"**Total Tiles:** {tile_count}\n**Completed Tiles:** {completed_tiles}",
                inline=True
            )
            
            embed.add_field(
                name="👥 Teams",
                value=f"**Active Teams:** {team_count}",
                inline=True
            )
            
            # Submission statistics
            submission_text = ""
            for status, count in submission_stats.items():
                submission_text += f"**{status.title()}:** {count}\n"
            if not submission_text:
                submission_text = "No submissions found"
            
            embed.add_field(
                name="📝 Submissions",
                value=submission_text,
                inline=False
            )
            
            # Team progress
            if team_progress:
                progress_text = ""
                for team in team_progress:
                    completion_rate = (team['completed_tiles'] / team['total_tiles'] * 100) if team['total_tiles'] > 0 else 0
                    progress_text += f"**{team['team_name']}:** {team['completed_tiles']}/{team['total_tiles']} ({completion_rate:.1f}%)\n"
                
                embed.add_field(
                    name="🏆 Team Progress",
                    value=progress_text,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in validate_db command: {e}")
            await interaction.followup.send(f"❌ Error during validation: {str(e)}", ephemeral=True) 