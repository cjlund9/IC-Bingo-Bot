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

# Complete WOM metric lists
SKILLS = [
    "overall", "attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic",
    "cooking", "woodcutting", "fletching", "fishing", "firemaking", "crafting", "smithing",
    "mining", "herblore", "agility", "thieving", "slayer", "farming", "runecrafting", "hunter", "construction"
]

BOSSES = [
    "abyssal-sire", "alchemical-hydra", "artio", "barrows-chests", "bryophyta", "callisto", "calvarion", "cerberus",
    "chambers-of-xeric", "chambers-of-xeric-challenge-mode", "chaos-elemental", "chaos-fanatic", "commander-zilyana",
    "corporeal-beast", "crazy-archaeologist", "dagannoth-prime", "dagannoth-rex", "dagannoth-supreme",
    "deranged-archaeologist", "duke-sucellus", "general-graardor", "giant-mole", "grotesque-guardians", "hespori",
    "kalphite-queen", "king-black-dragon", "kraken", "kree'arra", "kril-tsutsaroth", "mimic", "nex", "nightmare",
    "phosanis-nightmare", "obor", "phantom-muspah", "sarachnis", "scorpia", "skotizo", "spindel", "tempoross",
    "the-gauntlet", "the-corrupted-gauntlet", "the-leviathan", "the-whisperer", "theatre-of-blood",
    "theatre-of-blood-hard", "thermonuclear-smoke-devil", "tzkal-zuk", "tztok-jad", "venenatis", "vetion", "vorkath",
    "wintertodt", "zalcano", "zulrah"
]

CLUES = [
    "all", "beginner", "easy", "medium", "hard", "elite", "master"
]

ACTIVITIES = [
    "bounty-hunter-hunter", "bounty-hunter-rogue", "last-man-standing", "pvp-arena", "soul-wars-zeal",
    "rifts-closed", "colosseum-gladiator"
]

VIRTUAL = [
    "ehp", "ehb"
]

class WOMMetricModal(discord.ui.Modal, title="Search WOM Metric"):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.metric_input = discord.ui.TextInput(
            label="Enter metric name (boss, skill, or clue)",
            placeholder="e.g., zulrah, slayer, master, etc.",
            min_length=1,
            max_length=50,
            required=True
        )
        self.add_item(self.metric_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.metric_input.value.lower().strip()
        metric_type, metric = self.find_metric(user_input)
        if metric_type and metric:
            self.parent_view.selected_metric_type = metric_type
            self.parent_view.selected_metric = metric
            embed = await self.parent_view.create_wom_leaderboard_embed()
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
        else:
            suggestions = self.get_suggestions(user_input)
            await interaction.response.send_message(
                f"❌ Metric {user_input} not found.\n\n**Suggestions:**\n{suggestions}", ephemeral=True
            )

    def find_metric(self, user_input: str) -> tuple:
        # Check bosses
        for boss in BOSSES:
            if user_input in boss.lower() or boss.lower() in user_input:
                return "boss", boss
        # Check skills
        for skill in SKILLS:
            if user_input in skill.lower() or skill.lower() in user_input:
                return "skill", skill
        # Check clues
        for clue in CLUES:
            if user_input in clue.lower() or clue.lower() in user_input:
                return "clue", clue
        # Check activities
        for activity in ACTIVITIES:
            if user_input in activity.lower() or activity.lower() in user_input:
                return "activity", activity
        # Check virtual
        for virtual in VIRTUAL:
            if user_input in virtual.lower() or virtual.lower() in user_input:
                return virtual, virtual
        return None, None

    def get_suggestions(self, user_input: str) -> str:
        suggestions = []
        for boss in BOSSES[:10]:
            if user_input in boss.lower():
                suggestions.append(f"• Boss: {boss.replace('-', ' ').title()}")
        for skill in SKILLS[:5]:
            if user_input in skill.lower():
                suggestions.append(f"• Skill: {skill.title()}")
        for clue in CLUES:
            if user_input in clue.lower():
                suggestions.append(f"• Clue: {clue.title()}")
        if not suggestions:
            suggestions = [
                "• Popular bosses: zulrah, vorkath, cerberus",
                "• Popular skills: slayer, agility, thieving",
                "• Clues: all, beginner, easy, medium, hard, elite, master",
                "• Activities: bounty-hunter-hunter, last-man-standing, pvp-arena, soul-wars-zeal",
                "• Virtual: ehp, ehb"
            ]
        return '\n'.join(suggestions[:8])

class WOMAPISearchModal(discord.ui.Modal, title="Search WOM API Leaderboard"):
    def __init__(self):
        super().__init__()
        self.username = discord.ui.TextInput(
            label="Username (optional)",
            placeholder="e.g., zezima",
            required=False,
            max_length=12
        )
        self.metric = discord.ui.TextInput(
            label="Metric (e.g., overall, attack, ehp)",
            placeholder="overall",
            required=False,
            max_length=20
        )
        self.period = discord.ui.TextInput(
            label="Period (e.g., day, week, month)",
            placeholder="week",
            required=False,
            max_length=10
        )
        self.add_item(self.username)
        self.add_item(self.metric)
        self.add_item(self.period)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        username = self.username.value.strip()
        metric = self.metric.value.strip() or "overall"
        period = self.period.value.strip() or "week"

        params = {"metric": metric, "period": period}
        if username:
            params["username"] = username

        try:
            response = requests.get("https://api.wiseoldman.net/v2/competitions/leaderboard", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if not data or not data.get("players"):
                    await interaction.followup.send("❌ No leaderboard data found for your query.", ephemeral=True)
                    return
                players = data["players"]
                embed = discord.Embed(
                    title=f"🌐 WOM API: {metric.capitalize()} ({period})",
                    description=f"Top results for your query.",
                    color=0xFFD700,
                    timestamp=datetime.now()
                )
                for i, player in enumerate(players[:10], 1):
                    name = player.get("displayName", "Unknown")
                    value = player.get("value", "N/A")
                    embed.add_field(
                        name=f"#{i}: {name}",
                        value=f"Value: {value}",
                        inline=False
                    )
                embed.set_footer(text=f"🌐 WOM API • {metric.capitalize()} • {period})")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ WOM API error: {response.status_code}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error querying WOM API: {e}")
            await interaction.followup.send(f"❌ Error querying WOM API: {e}", ephemeral=True)

class LeaderboardView(discord.ui.View):
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)
        self.db = db
        self.current_page = 0
        self.leaderboard_type = "points"  # points, bingo, activity, team, wom
        self.selected_metric_type = None
        self.selected_metric = None

    @discord.ui.button(label="🏆 Points", style=discord.ButtonStyle.primary, custom_id="points")
    async def points_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "points"
        self.selected_metric_type = None
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎯 Bingo", style=discord.ButtonStyle.primary, custom_id="bingo")
    async def bingo_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "bingo"
        self.selected_metric_type = None
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⚡ Activity", style=discord.ButtonStyle.primary, custom_id="activity")
    async def activity_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "activity"
        self.selected_metric_type = None
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="👥 Teams", style=discord.ButtonStyle.primary, custom_id="teams")
    async def teams_button(self, interaction: Interaction, button: discord.ui.Button):
        self.leaderboard_type = "teams"
        self.selected_metric_type = None
        embed = await self.create_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔍 WOM Search", style=discord.ButtonStyle.secondary, custom_id="wom_search")
    async def wom_search_button(self, interaction: Interaction, button: discord.ui.Button):
        modal = WOMMetricModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🌐 WOM API", style=discord.ButtonStyle.secondary, custom_id="wom_api")
    async def wom_api_button(self, interaction: Interaction, button: discord.ui.Button):
        modal = WOMAPISearchModal()
        await interaction.response.send_modal(modal)

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
            badges = self.get_achievement_badges(user['total_points'], user.get('team'))
            points = user['total_points']
            progress_bar = self.create_progress_bar(points, 1000)
            display_name = user.get('display_name') or user['username']
            team_display = f"({user['team']})" if user.get('team') else ""
            leaderboard_text += f"{self.get_medal(i)} **{display_name}** {team_display} {badges}\n"
            leaderboard_text += f"└ {progress_bar} **{points:,}** pts\n\n"
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text="🏆 Points Leaderboard • Use buttons to switch views")
        return embed

    async def create_bingo_leaderboard(self) -> discord.Embed:
        team_scores = []
        for team_role in TEAM_ROLES:
            team = team_role.lower()
            team_progress = get_team_progress(team)
            if team_progress:
                completed_tiles = team_progress.get("completed_tiles", 0)
                total_tiles = team_progress.get("total_tiles", 0)
                completion_percentage = team_progress.get("completion_percentage", 0)
                team_scores.append({
                    "team": team_role,
                    "completed": completed_tiles,
                    "total": total_tiles,
                    "percentage": completion_percentage
                })
        team_scores.sort(key=lambda x: x["percentage"], reverse=True)
        embed = discord.Embed(
            title="🎯 Bingo Completion Leaderboard",
            description="Team standings by bingo completion",
            color=0x00FF00,
            timestamp=datetime.now()
        )
        if not team_scores:
            embed.add_field(
                name="No Data",
                value="No team progress data available.",
                inline=False
            )
            return embed
        leaderboard_text = ""
        for i, score in enumerate(team_scores):
            medal = self.get_medal(i)
            progress_bar = self.create_progress_bar(score["completed"], score["total"], 10)
            leaderboard_text += f"{medal} **{score['team']}**\n"
            leaderboard_text += f"└ {progress_bar} **{score['completed']}/{score['total']}** tiles ({score['percentage']:.1f}%)\n\n"
        embed.add_field(
            name="Team Rankings",
            value=leaderboard_text,
            inline=False
        )
        embed.set_footer(text="🎯 Bingo Leaderboard • Use buttons to switch views")
        return embed

    async def create_activity_leaderboard(self) -> discord.Embed:
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
            display_name = user.get('display_name') or user.get('username', 'Unknown')
            activity_text += f"{self.get_medal(i)} **{display_name}** {badges}\n"
            activity_text += f"└ **{user['activity_count']}** actions this week\n\n"
        embed.add_field(name="Recent Activity", value=activity_text, inline=False)
        embed.set_footer(text="⚡ Activity Leaderboard • Use buttons to switch views")
        return embed

    async def create_team_leaderboard(self) -> discord.Embed:
        team_scores = []
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
        team_scores.sort(key=lambda x: x["percentage"], reverse=True)
        embed = discord.Embed(
            title="👥 Team Leaderboard",
            description="Team standings by bingo completion",
            color=0x4ECDC4,
            timestamp=datetime.now()
        )
        if not team_scores:
            embed.add_field(name="No Data", value="No team data available.", inline=False)
            return embed
        leaderboard_text = ""
        for i, score in enumerate(team_scores):
            medal = self.get_medal(i)
            leaderboard_text += f"{medal} **{score['team']}**: {score['completed']} tiles ({score['percentage']:.1f}%)\n"
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text="👥 Team Leaderboard • Use buttons to switch views")
        return embed

    async def create_wom_leaderboard_embed(self) -> discord.Embed:
        if not self.selected_metric_type or not self.selected_metric:
            return await self.create_points_leaderboard()
        # Example user list - replace with your actual user list
        users = [
            {"rsn": "User1", "display_name": "User1"},
            {"rsn": "User2", "display_name": "User2"},
            {"rsn": "User3", "display_name": "User3"},
        ]
        leaderboard = []
        for user in users:
            value = await self.get_wom_metric(user["rsn"], self.selected_metric_type, self.selected_metric)
            leaderboard.append({"rsn": user["rsn"], "display_name": user["display_name"], "value": value})
        leaderboard.sort(key=lambda x: x["value"], reverse=True)
        metric_display = self.selected_metric.replace('-', ' ').title()
        embed = discord.Embed(
            title=f"🔍 WOM {metric_display} Leaderboard",
            description=f"Top players by {self.selected_metric_type}",
            color=0x9B59B6,
            timestamp=datetime.now()
        )
        if not leaderboard:
            embed.add_field(name="No Data", value="No data available.", inline=False)
            return embed
        leaderboard_text = ""
        for i, entry in enumerate(leaderboard[:10]):
            medal = self.get_medal(i)
            value = entry["value"]
            if self.selected_metric_type == "skill":
                value_str = f"{value:,}" if value > 0 else "0"
            else:
                value_str = str(value)
            leaderboard_text += f"{medal} **{entry['display_name']}**: {value_str}\n"
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text=f"🔍 WOM {metric_display} • Use buttons to switch views")
        return embed

    def get_medal(self, position: int) -> str:
        if position == 0:
            return "🥇"
        elif position == 1:
            return "🥈"
        elif position == 2:
            return "🥉"
        else:
            return f"{position + 1}."

    def get_achievement_badges(self, points: int, team: Optional[str]) -> str:
        badges = []
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
        if team:
            badges.append("👥")
        return "".join(badges)

    def get_activity_badges(self, activity_count: int) -> str:
        badges = []
        if activity_count >= 50:
            badges.append("🔥")
        elif activity_count >= 30:
            badges.append("⚡")
        elif activity_count >= 20:
            badges.append("🚀")
        elif activity_count >= 10:
            badges.append("💪")
        return "".join(badges)

    def create_progress_bar(self, current: int, maximum: int, length: int = 10) -> str:
        if maximum == 0:
            return "░" * length
        percentage = min(current / maximum, 1)
        filled = int(percentage * length)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        return bar

    def get_recent_activity_users(self) -> List[Dict]:
        return [
            {"display_name": "Sample User", "activity_count": 15},
            {"display_name": "Another User", "activity_count": 12},
            {"display_name": "3rd User", "activity_count": 8}
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