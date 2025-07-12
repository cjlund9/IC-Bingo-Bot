import discord
from discord.ext import commands
import requests
import json
import os

TEAMS_FILE = os.path.join(os.path.dirname(__file__), '..', 'teams.json')
ROLE_NAME = 'Summer 2025 Bingo'
LEADERSHIP_ROLE = 'leadership'

# Helper to fetch stats from Wise Old Man
async def fetch_wom_stats(rsn):
    url = f'https://api.wiseoldman.net/v2/players/{rsn}'
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        ehb = data.get('ehb', 0)
        ehp = data.get('ehp', 0)
        slayer_level = data.get('latestSnapshot', {}).get('data', {}).get('skills', {}).get('slayer', {}).get('level', 1)
        return {'rsn': rsn, 'ehb': ehb, 'ehp': ehp, 'slayer_level': slayer_level}
    except Exception:
        return None

def save_teams(teams):
    with open(TEAMS_FILE, 'w') as f:
        json.dump(teams, f, indent=2)

def load_teams():
    if not os.path.exists(TEAMS_FILE):
        return {}
    with open(TEAMS_FILE, 'r') as f:
        return json.load(f)

class TeamGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='generate_teams')
    @commands.has_role(LEADERSHIP_ROLE)
    async def generate_teams(self, ctx):
        """Generate 2 balanced teams from members with the event role."""
        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if not role:
            await ctx.send(f"Role '{ROLE_NAME}' not found.")
            return
        members = [m for m in role.members if not m.bot]
        if len(members) < 2:
            await ctx.send("Not enough participants to form teams.")
            return
        await ctx.send(f"Fetching stats for {len(members)} participants...")
        player_stats = []
        not_found = []
        for member in members:
            rsn = member.nick or member.name
            stats = await fetch_wom_stats(rsn)
            if stats:
                player_stats.append(stats)
            else:
                not_found.append(rsn)
        if not_found:
            await ctx.send(f"Could not find WOM profiles for: {', '.join(not_found)}. Please update your nickname or register on WOM.")
        if len(player_stats) < 2:
            await ctx.send("Not enough valid participants to form teams.")
            return
        # Sort by sum of stats
        player_stats.sort(key=lambda x: (x['ehb'] + x['ehp'] + x['slayer_level']), reverse=True)
        teams = {"Team 1": [], "Team 2": []}
        team_totals = {"Team 1": 0, "Team 2": 0}
        for i, player in enumerate(player_stats):
            # Assign to team with lower total
            t1 = team_totals["Team 1"]
            t2 = team_totals["Team 2"]
            team = "Team 1" if t1 <= t2 else "Team 2"
            teams[team].append(player)
            team_totals[team] += player['ehb'] + player['ehp'] + player['slayer_level']
        save_teams(teams)
        msg = "**Teams generated!**\n"
        for team, players in teams.items():
            msg += f"\n__{team}__\n"
            for p in players:
                msg += f"- {p['rsn']} (EHB: {p['ehb']}, EHP: {p['ehp']}, Slayer: {p['slayer_level']})\n"
            msg += f"Total: {sum(p['ehb'] + p['ehp'] + p['slayer_level'] for p in players)}\n"
        await ctx.send(msg)

    @commands.command(name='move_player')
    @commands.has_role(LEADERSHIP_ROLE)
    async def move_player(self, ctx, player: str, team: str):
        """Move a player to a different team (leadership only)."""
        await ctx.send("(Stub) This command will move a player to a different team.")

    @commands.command(name='swap_players')
    @commands.has_role(LEADERSHIP_ROLE)
    async def swap_players(self, ctx, player1: str, player2: str):
        """Swap two players between teams (leadership only)."""
        await ctx.send("(Stub) This command will swap two players between teams.")

    @commands.command(name='show_teams')
    async def show_teams(self, ctx):
        """Show the current teams."""
        teams = load_teams()
        if not teams:
            await ctx.send("No teams have been generated yet.")
            return
        msg = "**Current Teams:**\n"
        for team, players in teams.items():
            msg += f"\n__{team}__\n"
            for p in players:
                msg += f"- {p['rsn']} (EHB: {p['ehb']}, EHP: {p['ehp']}, Slayer: {p['slayer_level']})\n"
            msg += f"Total: {sum(p['ehb'] + p['ehp'] + p['slayer_level'] for p in players)}\n"
        await ctx.send(msg)

def setup(bot):
    bot.add_cog(TeamGen(bot)) 