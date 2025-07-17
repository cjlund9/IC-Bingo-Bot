import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional, List, Dict
from database import DatabaseManager
from config import GUILD_ID, ADMIN_ROLE, EVENT_COORDINATOR_ROLE, TEAM_ROLES, DEFAULT_TEAM
from utils.access import leadership_or_event_coordinator_check
from storage import get_team_progress, get_tile_progress
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

# Static lists for demonstration (can be expanded or fetched from WOM API)
BOSSES = [
    "zulrah", "vorkath", "cerberus", "alchemical-hydra", "chambers-of-xeric", "theatre-of-blood", "nex", "general-graardor", "kree'arra", "kril-tsutsaroth", "commander-zilyana", "giant-mole", "kalphite-queen", "king-black-dragon", "sarachnis", "skotizo", "venenatis", "vetion", "callisto", "chaos-elemental", "chaos-fanatic", "crazy-archaeologist", "scorpia", "deranged-archaeologist", "barrows-chests"
]
SKILLS = [
    "overall", "attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic", "cooking", "woodcutting", "fletching", "fishing", "firemaking", "crafting", "smithing", "mining", "herblore", "agility", "thieving", "slayer", "farming", "runecraft", "hunter", "construction"
]
CLUES = [
    "all", "beginner", "easy", "medium", "hard", "elite", "master"
]

class WOMMetricDropdown(discord.ui.Select):
    def __init__(self, parent_view):
        options = []
        # Group: Bosses
        for boss in BOSSES:
            options.append(discord.SelectOption(label=boss.replace("-", " ").title(), value=f"boss:{boss}", description="Boss KC"))
        # Group: Skills
        for skill in SKILLS:
            options.append(discord.SelectOption(label=skill.title(), value=f"skill:{skill}", description="Skill XP/Level"))
        # Group: Clues
        for clue in CLUES:
            options.append(discord.SelectOption(label=f"Clue: {clue.title()}", value=f"clue:{clue}", description="Clue Count"))
        super().__init__(placeholder="Select a metric (Boss, Skill, Clue)", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        metric_type, metric = self.values[0].split(":", 1)
        self.parent_view.selected_metric_type = metric_type
        self.parent_view.selected_metric = metric
        embed = await self.parent_view.create_wom_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

class LeaderboardView(discord.ui.View):
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)  #5)  # 5es timeout
        self.db = db
        self.current_page = 0
        self.leaderboard_type = "points"  # points, bingo, activity, team, wom
        self.selected_metric_type = None
        self.selected_metric = None
        self.add_item(WOMMetricDropdown(self))
        
    @discord.ui.button(label="🏆 Points", style=discord.ButtonStyle.primary, custom_id="points")
    async def points_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "points"
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
    @discord.ui.button(label="🎯 Bingo", style=discord.ButtonStyle.primary, custom_id="bingo")
    async def bingo_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "bingo"
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
    @discord.ui.button(label="⚡ Activity", style=discord.ButtonStyle.primary, custom_id="activity")
    async def activity_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "activity"
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
    @discord.ui.button(label="👥 Teams", style=discord.ButtonStyle.primary, custom_id="teams")
    async def teams_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "teams"
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def create_leaderboard_embed(self) -> discord.Embed:
        if self.selected_metric_type:
            return await self.create_wom_leaderboard_embed()
        if self.leaderboard_type == "points":
            return await self.create_points_leaderboard()
        elif self.leaderboard_type == "bingo":
            return await self.create_bingo_leaderboard()
        elif self.leaderboard_type == "activity":
            return await self.create_activity_leaderboard()
        elif self.leaderboard_type == "teams":
            return await self.create_team_leaderboard()
        else:
            return await self.create_points_leaderboard()
    
    async def create_points_leaderboard(self) -> discord.Embed:
        leaderboard = self.db.get_leaderboard(limit=15)
        
        embed = discord.Embed(
            title="🏆 Points Leaderboard",
            description="Top players by total points earned",
            color=0xFFD700,
            timestamp=datetime.now()
        )
        
        if not leaderboard:
            embed.add_field(name="No Data", value="No players found.", inline=False)
            return embed
        
        leaderboard_text = ""
        for i, user in enumerate(leaderboard):
            # Get achievement badges
            badges = self.get_achievement_badges(user['total_points'], user['team'])
            
            # Create progress bar for points (assuming max 1000 points for visual)
            points = user['total_points']
            progress_bar = self.create_progress_bar(points, 1000, 10)
            # Format display name
            display_name = user['display_name'] or user['username']
            team_display = f"({user['team']})" if user['team'] else ""
            
            leaderboard_text += f"{self.get_medal(i)} **{display_name}** {team_display} {badges}\n"
            leaderboard_text += f"└ {progress_bar} **{points:,}** pts\n\n"
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text="🏆 Points Leaderboard • Use buttons to switch views")
        
        return embed
    
    async def create_bingo_leaderboard(self) -> discord.Embed:
        # This would need to be implemented based on your bingo data structure
        # For now, showing a placeholder
        embed = discord.Embed(
            title="🎯 Bingo Completion Leaderboard",
            description="Players with most bingo tiles completed",
            color=0x00FF00,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Coming Soon", 
            value="Bingo completion tracking will be implemented soon!", 
            inline=False
        )
        embed.set_footer(text="🎯 Bingo Leaderboard • Use buttons to switch views")
        
        return embed
    
    async def create_activity_leaderboard(self) -> discord.Embed:
        # This would need to be implemented based on your activity tracking
        # For now, returning a sample
        recent_users = self.get_recent_activity_users()
        
        embed = discord.Embed(
            title="⚡ Activity Leaderboard",
            description="Most active players (last 7 days)",
            color=0xFF6B6B,
            timestamp=datetime.now()
        )
        
        if not recent_users:
            embed.add_field(name="No Recent Activity", value="No activity data available.", inline=False)
            return embed
        
        activity_text = ""
        for i, user in enumerate(recent_users):
            badges = self.get_activity_badges(user['activity_count'])
            display_name = user['display_name'] or user['username']
            
            activity_text += f"{self.get_medal(i)} **{display_name}** {badges}\n"
            activity_text += f"└ **{user['activity_count']}** actions this week\n\n"
        embed.add_field(name="Recent Activity", value=activity_text, inline=False)
        embed.set_footer(text="⚡ Activity Leaderboard • Use buttons to switch views")
        
        return embed
    
    async def create_team_leaderboard(self) -> discord.Embed:
        team_scores = []
        
        # Calculate scores for each team
        for team_role in TEAM_ROLES:
            team = team_role.lower()
            team_progress = get_team_progress(team)
            if team_progress:
                completed_tiles = team_progress.get("completed_tiles", 0)
                completion_percentage = team_progress.get("completion_percentage", 0)
                team_scores.append({
                   "team": team_role,
                   "completed": completed_tiles,
                   "percentage": completion_percentage
                })
        
        # Sort by completion percentage
        team_scores.sort(key=lambda x: x["percentage"], reverse=True)
        
        embed = discord.Embed(
            title="👥 Team Leaderboard",
            description="Team standings by bingo completion",
            color=0x4ECDC4,
            timestamp=datetime.now()
        )
        
        if not team_scores:
            embed.add_field(name="No Data", value="No team progress data available.", inline=False)
            return embed
        
        team_text = ""
        for i, score in enumerate(team_scores):
            medal = self.get_medal(i)
            progress_bar = self.create_progress_bar(score["percentage"], 100, 8)
            
            team_text += f"{medal} **{score['team']}**\n"
            team_text += f"└ {progress_bar} **{score['completed']}** tiles ({score['percentage']:.1f}%)\n\n"
        embed.add_field(name="Team Rankings", value=team_text, inline=False)
        embed.set_footer(text="👥 Team Leaderboard • Use buttons to switch views")
        
        return embed
    
    async def create_wom_leaderboard_embed(self) -> discord.Embed:
        leaderboard = self.db.get_leaderboard(limit=30)
        metric_type = self.selected_metric_type
        metric = self.selected_metric
        results = []
        for user in leaderboard:
            rsn = user['display_name'] or user['username']
            value = await self.get_wom_metric(rsn, metric_type, metric)
            results.append({
                "rsn": rsn,
                "value": value,
                "team": user.get("team", ""),
            })
        results.sort(key=lambda x: x["value"], reverse=True)
        # Title and description
        if metric_type == "boss":
            title = f"🏆 {metric.replace('-', ' ').title()} KC Leaderboard"
            desc = f"Top {metric.replace('-', ' ').title()} kill counts (Wise Old Man API)"
        elif metric_type == "skill":
            title = f"🏆 {metric.title()} XP Leaderboard"
            desc = f"Top {metric.title()} XP (Wise Old Man API)"
        elif metric_type == "clue":
            title = f"🏆 {metric.title()} Clue Leaderboard"
            desc = f"Top {metric.title()} clues completed (Wise Old Man API)"
        else:
            title = "🏆 WOM Leaderboard"
            desc = "Wise Old Man API Leaderboard"
        embed = discord.Embed(title=title, description=desc, color=0x4ECDC4)
        text = ""
        for i, entry in enumerate(results[:15]):
            medal = self.get_medal(i)
            text += f"{medal} **{entry['rsn']}** ({entry['team']}) — {entry['value']:,}\n"
        embed.add_field(name="Rankings", value=text or "No data", inline=False)
        embed.set_footer(text="Data from wiseoldman.net")
        return embed

    def get_medal(self, position: int) -> str:
        # This would need to be implemented based on your medal emoji logic
        if position == 0:
            return "🥇"
        elif position == 1:
            return "🥈"
        elif position == 2:
            return "🥉"
        else:
            return f"**{position + 1}.**"
    
    def get_achievement_badges(self, points: int, team: str) -> str:
        badges = []
        
        # Points milestones
        if points >= 1000:
            badges.append("👑")
        elif points >= 500:
            badges.append("💎")
        elif points >= 250:
            badges.append("🏅")
        elif points >= 100:
            badges.append("🎖️")
        elif points >= 50:
            badges.append("⭐")
        
        # Team badges (if you have specific team achievements)
        if team:
            badges.append("👥")
        
        return " ".join(badges)
    
    def get_activity_badges(self, activity_count: int) -> str:
        badges = []
        
        if activity_count >= 50:
            badges.append("🔥")
        elif activity_count >= 25:
            badges.append("⚡")
        elif activity_count >= 10:
            badges.append("🚀")
        elif activity_count >= 5:
            badges.append("💪")
        
        return " ".join(badges)
    
    def create_progress_bar(self, current: int, maximum: int, length: int = 10) -> str:
        # This would need to be implemented based on your progress bar ASCII logic
        if maximum == 0:
            return "░" * length
        
        percentage = min(current / maximum, 1.0)
        filled = int(percentage * length)
        empty = length - filled
        
        bar = "█" * filled + "░" * empty
        return bar
    
    def get_recent_activity_users(self) -> List[Dict]:
        # This would need to be implemented based on your activity tracking
        # For now, returning a sample
        return [
            {"display_name": "Sample User", "activity_count": 15},
            {"display_name": "Another User", "activity_count": 12},
            {"display_name": "d User", "activity_count": 8}
        ]

    async def get_wom_metric(self, rsn, metric_type, metric):
        url = f"https://api.wiseoldman.net/v2/players/{rsn}/hiscores"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if metric_type == "boss":
                    for b in data.get("bosses", []):
                        if b["metric"].lower() == metric.lower():
                            return b["value"]
                elif metric_type == "skill":
                    for s in data.get("skills", []):
                        if s["metric"].lower() == metric.lower():
                            return s["experience"]
                elif metric_type == "clue":
                    for c in data.get("clues", []):
                        if c["metric"].lower() == metric.lower():
                            return c["value"]
            return 0
        except Exception:
            return 0

def setup_leaderboard_commands(bot: Bot):
    
    @bot.tree.command(
        name="totalleaderboard",
        description="View the cool interactive total leaderboard",
        guild=discord.Object(id=GUILD_ID)
    )
    async def leaderboard_cmd(interaction: Interaction):
        await interaction.response.defer()
        
        try:
            db = DatabaseManager()
            view = LeaderboardView(db)
            embed = await view.create_leaderboard_embed()
            
            await interaction.followup.send(embed=embed, view=view)
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
            
            # Create embed with cool visual elements
            embed = discord.Embed(
                title=f"📊 {interaction.user.display_name}'s Statistics",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            
            # User info with progress bar
            points = user['total_points']
            progress_bar = self.create_progress_bar(points, 1000)
            badges = self.get_user_badges(points, user['team'])
            
            embed.add_field(
                name="👤 User Info",
                value=f"**Total Points:** {points:,}\n"
                      f"**Team:** {user['team'] or None} {badges}\n"
                      f"**Member Since:** {user['created_at'][:10]}\n"
                      f"**Progress:** {progress_bar}",
                inline=False
            )
            
            # Competition stats
            competitions = stats.get('competitions', [])
            if competitions:
                comp_text = ""
                for comp in competitions[:5]:  # Show last 5
                    comp_text += f"• {comp['competition_name']}: {comp['placement']}{_get_ordinal_suffix(comp['placement'])} ({comp['points_awarded']} pts)\n"
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
                    clog_text += f"• {clog['tier_name']}: {clog['current_count']} items ({clog['points_awarded']} pts)\n"
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
                    ca_text += f"• {ca['tier_name']}: {ca['points_awarded']} pts\n"
                if len(cas) > 3:
                    ca_text += f"... and {len(cas) - 3} more"
            else:
                ca_text = "No CA submissions yet"
            
            embed.add_field(
                name="⚔️ Combat Achievements",
                value=ca_text,
                inline=True
            )
            
            embed.set_footer(text=f"📊 Personal Statistics • {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
            logger.info(f"Stats viewed by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error in mystats command: {e}")
            await interaction.followup.send("❌ An error occurred while loading your statistics.")

def create_progress_bar(current: int, maximum: int, length: int = 10) -> str:
    if maximum == 0:
        return "░" * length
    
    percentage = min(current / maximum, 1.0)
    filled = int(percentage * length)
    empty = length - filled
    
    bar = "█" * filled + "░" * empty
    return bar

def get_user_badges(points: int, team: str) -> str:
    badges = []
    
    # Points milestones
    if points >= 100:
        badges.append("👑")
    elif points >= 50:
        badges.append("💎")
    elif points >= 250:
        badges.append("🏅")
    elif points >= 100:
        badges.append("🎖️")
    elif points >= 50:
        badges.append("⭐")
    # Team badges
    if team:
        badges.append("👥")
    
    return " ".join(badges)

def _get_ordinal_suffix(n: int) -> str:
    """Get ordinal suffix for numbers (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix 