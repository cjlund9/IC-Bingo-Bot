import discord
from config import TEAM_ROLES, DEFAULT_TEAM

def get_user_team(member: discord.Member) -> str:
    for role in member.roles:
        if role.name in TEAM_ROLES:
            return role.name.lower()
    return DEFAULT_TEAM