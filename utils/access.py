import discord
from discord import app_commands

def has_bot_access(member: discord.Member) -> bool:
    """Check if a member has access to bot commands (leadership, event coordinator, or team member)"""
    guild = member.guild
    
    # Check for leadership role
    leadership_role = discord.utils.get(guild.roles, name="leadership")
    if leadership_role and leadership_role in member.roles:
        return True
    
    # Check for event coordinator role
    event_coordinator_role = discord.utils.get(guild.roles, name="Event Coordinator")
    if event_coordinator_role and event_coordinator_role in member.roles:
        return True
    
    # Check for team roles
    moles_role = discord.utils.get(guild.roles, name="Moles")
    obor_role = discord.utils.get(guild.roles, name="Obor")
    
    if moles_role and moles_role in member.roles:
        return True
    if obor_role and obor_role in member.roles:
        return True
    
    return False

def has_admin_access(member: discord.Member) -> bool:
    """Check if a member has admin access (leadership only)"""
    guild = member.guild
    
    # Check for leadership role only
    leadership_role = discord.utils.get(guild.roles, name="leadership")
    if leadership_role and leadership_role in member.roles:
        return True
    
    return False

def has_leadership_or_event_coordinator_access(member: discord.Member) -> bool:
    """Check if a member has leadership or event coordinator access"""
    guild = member.guild
    
    # Check for leadership role
    leadership_role = discord.utils.get(guild.roles, name="leadership")
    if leadership_role and leadership_role in member.roles:
        return True
    
    # Check for event coordinator role
    event_coordinator_role = discord.utils.get(guild.roles, name="Event Coordinator")
    if event_coordinator_role and event_coordinator_role in member.roles:
        return True
    
    return False

def has_team_member_access(member: discord.Member) -> bool:
    """Check if a member has team member access (leadership, event coordinator, or team member)"""
    guild = member.guild
    
    # Check for leadership role
    leadership_role = discord.utils.get(guild.roles, name="leadership")
    if leadership_role and leadership_role in member.roles:
        return True
    
    # Check for event coordinator role
    event_coordinator_role = discord.utils.get(guild.roles, name="Event Coordinator")
    if event_coordinator_role and event_coordinator_role in member.roles:
        return True
    
    # Check for team roles
    moles_role = discord.utils.get(guild.roles, name="Moles")
    obor_role = discord.utils.get(guild.roles, name="Obor")
    
    if moles_role and moles_role in member.roles:
        return True
    if obor_role and obor_role in member.roles:
        return True
    
    return False

def bot_access_check(interaction: discord.Interaction) -> bool:
    """Custom check for bot access (leadership, event coordinator, or team member)"""
    if not has_bot_access(interaction.user):
        raise app_commands.errors.MissingRole("leadership, Event Coordinator, or team role")
    return True

def admin_access_check(interaction: discord.Interaction) -> bool:
    """Custom check for admin access (leadership only)"""
    if not has_admin_access(interaction.user):
        raise app_commands.errors.MissingRole("leadership")
    return True

def leadership_or_event_coordinator_check(interaction: discord.Interaction) -> bool:
    """Custom check for leadership or event coordinator access"""
    if not has_leadership_or_event_coordinator_access(interaction.user):
        raise app_commands.errors.MissingRole("leadership or Event Coordinator role")
    return True

def team_member_access_check(interaction: discord.Interaction) -> bool:
    """Custom check for team member access (leadership, event coordinator, or team member)"""
    if not has_team_member_access(interaction.user):
        raise app_commands.errors.MissingRole("leadership, Event Coordinator, or team role")
    return True 