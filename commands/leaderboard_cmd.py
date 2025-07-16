import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional
from database import DatabaseManager
from config import GUILD_ID, ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from utils.access import leadership_or_event_coordinator_check

logger = logging.getLogger(__name__)

def setup_leaderboard_commands(bot: Bot):
    
    @bot.tree.command(
        name="mystats",
        description="View your personal statistics and points history",
        guild=discord.Object(id=GUILD_ID)
    )
    async def mystats_cmd(interaction: Interaction):
        await interaction.response.defer()
        
        try:
            # Get or create user
            db = DatabaseManager()
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
    
    # Removed /iceventleaderboard, /award_points, /event_penalty, and /icpoints commands and their helpers

def _get_ordinal_suffix(n: int) -> str:
    """Get ordinal suffix for numbers (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix 