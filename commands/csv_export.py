# Entire file commented out for minimal bingo bot
"""
Simple CSV export for tracking user completions and stats
Exports data to CSV files that can be easily imported into Google Sheets
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
import csv
import os
from datetime import datetime

import config
from utils.access import admin_access_check
from database import DatabaseManager

logger = logging.getLogger(__name__)

def setup_csv_export_command(bot: commands.Bot):
    """Setup the CSV export command"""
    
    @bot.tree.command(
        name="export_csv",
        description="Export bingo data to CSV files for Google Sheets",
        guild=discord.Object(id=config.GUILD_ID)
    )
    @app_commands.describe(
        report_type="Type of data to export"
    )
    @app_commands.choices(report_type=[
        app_commands.Choice(name="All Data", value="all"),
        app_commands.Choice(name="User Completions", value="completions"),
        app_commands.Choice(name="User Stats", value="stats"),
        app_commands.Choice(name="Team Progress", value="teams"),
        app_commands.Choice(name="Submissions", value="submissions")
    ])
    async def export_csv_cmd(interaction: discord.Interaction, report_type: str):
        """Export bingo data to CSV files"""
        
        # Check admin access
        if not admin_access_check(interaction):
            return
        
        await interaction.response.defer()
        
        try:
            db = DatabaseManager()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if report_type == "all" or report_type == "completions":
                # Export user completions
                completions_file = f"exports/user_completions_{timestamp}.csv"
                os.makedirs("exports", exist_ok=True)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT 
                            u.username,
                            u.display_name,
                            u.team,
                            bt.name as tile_name,
                            bt.id as tile_id,
                            bs.drop_name,
                            bs.quantity,
                            bs.status,
                            bs.created_at
                        FROM bingo_submissions bs
                        JOIN users u ON bs.user_id = u.discord_id
                        JOIN bingo_tiles bt ON bs.tile_id = bt.id
                        WHERE bs.status = 'approved'
                        ORDER BY u.username, bt.name, bs.created_at
                    """)
                    
                    results = cursor.fetchall()
                
                with open(completions_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Username', 'Display Name', 'Team', 'Tile Name', 'Tile ID', 'Drop Name', 'Quantity', 'Status', 'Date'])
                    writer.writerows(results)
                
                await interaction.followup.send(
                    f"✅ User completions exported to `{completions_file}`\n"
                    f"📊 **{len(results)}** approved submissions\n\n"
                    "**To import to Google Sheets:**\n"
                    "1. Open Google Sheets\n"
                    "2. File → Import → Upload → Select this CSV file\n"
                    "3. Choose 'Replace current sheet' or 'Insert new sheet'",
                    ephemeral=True
                )
            
            elif report_type == "stats":
                # Export user statistics
                stats_file = f"exports/user_stats_{timestamp}.csv"
                os.makedirs("exports", exist_ok=True)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT 
                            u.username,
                            u.display_name,
                            u.team,
                            COUNT(bs.id) as total_submissions,
                            COUNT(CASE WHEN bs.status = 'approved' THEN 1 END) as approved_submissions,
                            COUNT(CASE WHEN bs.status = 'pending' THEN 1 END) as pending_submissions,
                            COUNT(CASE WHEN bs.status = 'denied' THEN 1 END) as denied_submissions,
                            SUM(bs.quantity) as total_quantity,
                            MAX(bs.created_at) as last_submission
                        FROM users u
                        LEFT JOIN bingo_submissions bs ON u.discord_id = bs.user_id
                        GROUP BY u.discord_id, u.username, u.display_name, u.team
                        ORDER BY approved_submissions DESC, total_submissions DESC
                    """)
                    
                    results = cursor.fetchall()
                
                with open(stats_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Username', 'Display Name', 'Team', 'Total Submissions', 'Approved', 'Pending', 'Denied', 'Total Quantity', 'Last Submission'])
                    writer.writerows(results)
                
                await interaction.followup.send(
                    f"✅ User stats exported to `{stats_file}`\n"
                    f"📊 **{len(results)}** users with data\n\n"
                    "**To import to Google Sheets:**\n"
                    "1. Open Google Sheets\n"
                    "2. File → Import → Upload → Select this CSV file\n"
                    "3. Choose 'Replace current sheet' or 'Insert new sheet'",
                    ephemeral=True
                )
            
            elif report_type == "teams":
                # Export team progress
                teams_file = f"exports/team_progress_{timestamp}.csv"
                os.makedirs("exports", exist_ok=True)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT 
                            btp.team_name,
                            bt.name as tile_name,
                            bt.id as tile_id,
                            btp.total_required,
                            btp.completed_count,
                            CASE WHEN btp.is_complete = 1 THEN 'Yes' ELSE 'No' END as is_complete,
                            btp.updated_at
                        FROM bingo_team_progress btp
                        JOIN bingo_tiles bt ON btp.tile_id = bt.id
                        ORDER BY btp.team_name, bt.id
                    """)
                    
                    results = cursor.fetchall()
                
                with open(teams_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Team', 'Tile Name', 'Tile ID', 'Required', 'Completed', 'Is Complete', 'Last Updated'])
                    writer.writerows(results)
                
                await interaction.followup.send(
                    f"✅ Team progress exported to `{teams_file}`\n"
                    f"📊 **{len(results)}** team-tile combinations\n\n"
                    "**To import to Google Sheets:**\n"
                    "1. Open Google Sheets\n"
                    "2. File → Import → Upload → Select this CSV file\n"
                    "3. Choose 'Replace current sheet' or 'Insert new sheet'",
                    ephemeral=True
                )
            
            elif report_type == "submissions":
                # Export all submissions
                submissions_file = f"exports/all_submissions_{timestamp}.csv"
                os.makedirs("exports", exist_ok=True)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT 
                            bs.id,
                            u.username,
                            u.display_name,
                            u.team,
                            bt.name as tile_name,
                            bs.drop_name,
                            bs.quantity,
                            bs.status,
                            bs.created_at,
                            bs.updated_at
                        FROM bingo_submissions bs
                        JOIN users u ON bs.user_id = u.discord_id
                        JOIN bingo_tiles bt ON bs.tile_id = bt.id
                        ORDER BY bs.created_at DESC
                    """)
                    
                    results = cursor.fetchall()
                
                with open(submissions_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Submission ID', 'Username', 'Display Name', 'Team', 'Tile Name', 'Drop Name', 'Quantity', 'Status', 'Submitted At', 'Updated At'])
                    writer.writerows(results)
                
                await interaction.followup.send(
                    f"✅ All submissions exported to `{submissions_file}`\n"
                    f"📊 **{len(results)}** total submissions\n\n"
                    "**To import to Google Sheets:**\n"
                    "1. Open Google Sheets\n"
                    "2. File → Import → Upload → Select this CSV file\n"
                    "3. Choose 'Replace current sheet' or 'Insert new sheet'",
                    ephemeral=True
                )
            
            else:
                await interaction.followup.send(
                    "❌ Invalid report type. Please choose from: all, completions, stats, teams, submissions",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in CSV export command: {e}")
            await interaction.followup.send(
                f"❌ An error occurred during export: {str(e)}",
                ephemeral=True
            ) 