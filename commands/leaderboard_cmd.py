import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional
from database import db
from config import GUILD_ID, ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from utils.access import leadership_or_event_coordinator_check

logger = logging.getLogger(__name__)

def setup_leaderboard_commands(bot: Bot):
    
    @bot.tree.command(
        name="iceventleaderboard",
        description="Show the Ironclad Events leaderboard",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(limit="Number of users to show (default: 20)")
    async def leaderboard_cmd(interaction: Interaction, limit: int = 20):
        await interaction.response.defer()
        
        try:
            # Get leaderboard data
            leaderboard = db.get_leaderboard(limit)
            
            if not leaderboard:
                await interaction.followup.send("❌ No users found in the leaderboard.")
                return
            
            # Create embed
            embed = discord.Embed(
                title="🏆 Ironclad Events Leaderboard",
                description="Current standings based on event participation",
                color=0xFFD700
            )
            
            # Add leaderboard entries
            leaderboard_text = ""
            for i, user in enumerate(leaderboard):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                team_text = f" ({user['team']})" if user['team'] else ""
                leaderboard_text += f"{medal} **{user['display_name'] or user['username']}**{team_text}: {user['total_points']} pts\n"
            
            embed.add_field(
                name="Rankings",
                value=leaderboard_text,
                inline=False
            )
            
            embed.set_footer(text=f"Showing top {len(leaderboard)} users")
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Leaderboard viewed by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await interaction.followup.send("❌ An error occurred while loading the leaderboard.")
    
    @bot.tree.command(
        name="mystats",
        description="View your personal statistics and points history",
        guild=discord.Object(id=GUILD_ID)
    )
    async def mystats_cmd(interaction: Interaction):
        await interaction.response.defer()
        
        try:
            # Get or create user
            user = db.get_or_create_user(
                interaction.user.id,
                interaction.user.name,
                interaction.user.display_name
            )
            
            # Get detailed stats
            stats = db.get_user_stats(interaction.user.id)
            
            if not stats:
                await interaction.followup.send("❌ Unable to load your statistics.")
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 {interaction.user.display_name}'s Statistics",
                color=0x00FF00
            )
            
            # User info
            embed.add_field(
                name="👤 User Info",
                value=f"**Total Points:** {user['total_points']}\n"
                      f"**Team:** {user['team'] or 'None'}\n"
                      f"**Member Since:** {user['created_at'][:10]}",
                inline=True
            )
            
            # Competition stats
            competitions = stats.get('competitions', [])
            if competitions:
                comp_text = ""
                for comp in competitions[:5]:  # Show last 5
                    comp_text += f"• {comp['name']}: {comp['placement']}{_get_ordinal_suffix(comp['placement'])} ({comp['points_awarded']} pts)\n"
                if len(competitions) > 5:
                    comp_text += f"... and {len(competitions) - 5} more"
            else:
                comp_text = "No competitions yet"
            
            embed.add_field(
                name="🏆 Competitions",
                value=comp_text,
                inline=True
            )
            
            # CLOG stats
            clogs = stats.get('clogs', [])
            if clogs:
                clog_text = ""
                for clog in clogs[:3]:  # Show last 3
                    clog_text += f"• {clog['name']}: {clog['current_count']} items ({clog['points_awarded']} pts)\n"
                if len(clogs) > 3:
                    clog_text += f"... and {len(clogs) - 3} more"
            else:
                clog_text = "No CLOG submissions yet"
            
            embed.add_field(
                name="📚 Collection Log",
                value=clog_text,
                inline=True
            )
            
            # CA stats
            cas = stats.get('cas', [])
            if cas:
                ca_text = ""
                for ca in cas[:3]:  # Show last 3
                    ca_text += f"• {ca['name']}: {ca['points_awarded']} pts\n"
                if len(cas) > 3:
                    ca_text += f"... and {len(cas) - 3} more"
            else:
                ca_text = "No CA submissions yet"
            
            embed.add_field(
                name="⚔️ Combat Achievements",
                value=ca_text,
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Stats viewed by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error in mystats command: {e}")
            await interaction.followup.send("❌ An error occurred while loading your statistics.")
    
    @bot.tree.command(
        name="award_points",
        description="Award points to a user (Leadership/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(
        user="User to award points to",
        points="Number of points to award (can be negative)",
        reason="Reason for awarding points"
    )
    async def award_points_cmd(interaction: Interaction, user: discord.Member, points: int, reason: str):
        await interaction.response.defer()
        
        try:
            # Get or create user
            db.get_or_create_user(
                user.id,
                user.name,
                user.display_name
            )
            
            # Award points
            success = db.update_user_points(
                user.id,
                points,
                reason,
                'manual',
                awarded_by=interaction.user.id
            )
            
            if success:
                # Get updated user info
                user_info = db.get_user(user.id)
                
                embed = discord.Embed(
                    title="✅ Points Awarded",
                    description=f"Successfully awarded **{points}** points to {user.mention}",
                    color=0x00FF00
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="New Total", value=f"{user_info['total_points']} points", inline=True)
                embed.add_field(name="Awarded By", value=interaction.user.mention, inline=True)
                
                await interaction.followup.send(embed=embed)
                logger.info(f"Points awarded: {user.display_name} +{points} by {interaction.user.display_name}")
            else:
                await interaction.followup.send("❌ Failed to award points.")
                
        except Exception as e:
            logger.error(f"Error in award_points command: {e}")
            await interaction.followup.send("❌ An error occurred while awarding points.")
    
    @bot.tree.command(
        name="submit_clog",
        description="Submit collection log progress for points (Leadership/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(
        user="User submitting CLOG progress",
        count="Current collection log count",
        notes="Additional notes (optional)"
    )
    async def submit_clog_cmd(interaction: Interaction, user: discord.Member, count: int, notes: str = None):
        await interaction.response.defer()
        
        try:
            # Get or create user
            db.get_or_create_user(
                user.id,
                user.name,
                user.display_name
            )
            
            # Submit CLOG
            success = db.submit_clog(
                user.id,
                count,
                interaction.user.id,
                notes
            )
            
            if success:
                # Get updated user info
                user_info = db.get_user(user.id)
                
                embed = discord.Embed(
                    title="📚 Collection Log Submitted",
                    description=f"Successfully processed CLOG submission for {user.mention}",
                    color=0x00FF00
                )
                embed.add_field(name="Current Count", value=str(count), inline=True)
                embed.add_field(name="New Total Points", value=f"{user_info['total_points']} points", inline=True)
                if notes:
                    embed.add_field(name="Notes", value=notes, inline=False)
                
                await interaction.followup.send(embed=embed)
                logger.info(f"CLOG submitted: {user.display_name} count={count} by {interaction.user.display_name}")
            else:
                await interaction.followup.send("❌ Failed to process CLOG submission.")
                
        except Exception as e:
            logger.error(f"Error in submit_clog command: {e}")
            await interaction.followup.send("❌ An error occurred while processing CLOG submission.")
    
    @bot.tree.command(
        name="submit_ca",
        description="Submit combat achievement tier for points (Leadership/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.choices(tier=[
        app_commands.Choice(name="Grandmaster", value="Grandmaster"),
        app_commands.Choice(name="Master", value="Master"),
        app_commands.Choice(name="Elite", value="Elite"),
        app_commands.Choice(name="Hard", value="Hard"),
        app_commands.Choice(name="Medium", value="Medium"),
        app_commands.Choice(name="Easy", value="Easy")
    ])
    @app_commands.describe(
        user="User submitting CA tier",
        tier="Combat achievement tier",
        notes="Additional notes (optional)"
    )
    async def submit_ca_cmd(interaction: Interaction, user: discord.Member, tier: str, notes: str = None):
        await interaction.response.defer()
        
        try:
            # Get or create user
            db.get_or_create_user(
                user.id,
                user.name,
                user.display_name
            )
            
            # Submit CA
            success = db.submit_ca(
                user.id,
                tier,
                interaction.user.id,
                notes
            )
            
            if success:
                # Get updated user info
                user_info = db.get_user(user.id)
                
                embed = discord.Embed(
                    title="⚔️ Combat Achievement Submitted",
                    description=f"Successfully processed CA submission for {user.mention}",
                    color=0x00FF00
                )
                embed.add_field(name="Tier", value=tier, inline=True)
                embed.add_field(name="New Total Points", value=f"{user_info['total_points']} points", inline=True)
                if notes:
                    embed.add_field(name="Notes", value=notes, inline=False)
                
                await interaction.followup.send(embed=embed)
                logger.info(f"CA submitted: {user.display_name} tier={tier} by {interaction.user.display_name}")
            else:
                await interaction.followup.send("❌ Failed to process CA submission.")
                
        except Exception as e:
            logger.error(f"Error in submit_ca command: {e}")
            await interaction.followup.send("❌ An error occurred while processing CA submission.")

def _get_ordinal_suffix(n: int) -> str:
    """Get ordinal suffix for numbers (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix 