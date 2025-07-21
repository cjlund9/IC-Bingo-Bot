import discord
from discord import app_commands
from config import ADMIN_ROLE, EVENT_COORDINATOR_ROLE, ADMIN_ROLE_ID, EVENT_COORDINATOR_ROLE_ID
import logging

logger = logging.getLogger("access_check")

def has_bot_access(member: discord.Member) -> bool:
    """Check if a member has access to bot commands (leadership, event coordinator, or team member)"""
    guild = member.guild
    
    # Check for leadership role by ID or name
    leadership_role = None
    if ADMIN_ROLE_ID:
        leadership_role = discord.utils.get(guild.roles, id=int(ADMIN_ROLE_ID))
    if not leadership_role:
        leadership_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if leadership_role and leadership_role in member.roles:
        return True
    
    # Check for event coordinator role by ID or name
    event_coordinator_role = None
    if EVENT_COORDINATOR_ROLE_ID:
        event_coordinator_role = discord.utils.get(guild.roles, id=int(EVENT_COORDINATOR_ROLE_ID))
    if not event_coordinator_role:
        event_coordinator_role = discord.utils.get(guild.roles, name=EVENT_COORDINATOR_ROLE)
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
    user_role_ids = [r.id for r in member.roles]
    user_role_names = [r.name for r in member.roles]
    logger.info(f"[has_admin_access] User: {member} | Role IDs: {user_role_ids} | Role Names: {user_role_names} | Expected ADMIN_ROLE_ID: {ADMIN_ROLE_ID} | ADMIN_ROLE: {ADMIN_ROLE}")
    # Check for leadership role only
    leadership_role = None
    if ADMIN_ROLE_ID:
        leadership_role = discord.utils.get(guild.roles, id=int(ADMIN_ROLE_ID))
    if not leadership_role:
        leadership_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if leadership_role and leadership_role in member.roles:
        return True
    
    return False

def has_leadership_or_event_coordinator_access(member: discord.Member) -> bool:
    """Check if a member has leadership or event coordinator access"""
    guild = member.guild
    user_role_ids = [r.id for r in member.roles]
    user_role_names = [r.name for r in member.roles]
    logger.info(f"[has_leadership_or_event_coordinator_access] User: {member} | Role IDs: {user_role_ids} | Role Names: {user_role_names} | Expected ADMIN_ROLE_ID: {ADMIN_ROLE_ID}, EVENT_COORDINATOR_ROLE_ID: {EVENT_COORDINATOR_ROLE_ID} | ADMIN_ROLE: {ADMIN_ROLE}, EVENT_COORDINATOR_ROLE: {EVENT_COORDINATOR_ROLE}")
    # Check for leadership role
    leadership_role = None
    if ADMIN_ROLE_ID:
        leadership_role = discord.utils.get(guild.roles, id=int(ADMIN_ROLE_ID))
    if not leadership_role:
        leadership_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if leadership_role and leadership_role in member.roles:
        return True
    
    # Check for event coordinator role
    event_coordinator_role = None
    if EVENT_COORDINATOR_ROLE_ID:
        event_coordinator_role = discord.utils.get(guild.roles, id=int(EVENT_COORDINATOR_ROLE_ID))
    if not event_coordinator_role:
        event_coordinator_role = discord.utils.get(guild.roles, name=EVENT_COORDINATOR_ROLE)
    if event_coordinator_role and event_coordinator_role in member.roles:
        return True
    
    return False

def has_team_member_access(member: discord.Member) -> bool:
    """Check if a member has team member access (leadership, event coordinator, or team member)"""
    guild = member.guild
    user_role_ids = [r.id for r in member.roles]
    user_role_names = [r.name for r in member.roles]
    logger.info(f"[has_team_member_access] User: {member} | Role IDs: {user_role_ids} | Role Names: {user_role_names} | Expected ADMIN_ROLE_ID: {ADMIN_ROLE_ID}, EVENT_COORDINATOR_ROLE_ID: {EVENT_COORDINATOR_ROLE_ID} | ADMIN_ROLE: {ADMIN_ROLE}, EVENT_COORDINATOR_ROLE: {EVENT_COORDINATOR_ROLE}")
    # Check for leadership role
    leadership_role = None
    if ADMIN_ROLE_ID:
        leadership_role = discord.utils.get(guild.roles, id=int(ADMIN_ROLE_ID))
    if not leadership_role:
        leadership_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if leadership_role and leadership_role in member.roles:
        return True
    
    # Check for event coordinator role
    event_coordinator_role = None
    if EVENT_COORDINATOR_ROLE_ID:
        event_coordinator_role = discord.utils.get(guild.roles, id=int(EVENT_COORDINATOR_ROLE_ID))
    if not event_coordinator_role:
        event_coordinator_role = discord.utils.get(guild.roles, name=EVENT_COORDINATOR_ROLE)
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

def _get_member_from_interaction(interaction):
    member = getattr(interaction, 'user', None)
    if member and not isinstance(member, discord.Member) and interaction.guild:
        member = interaction.guild.get_member(member.id)
    return member

def bot_access_check(interaction: discord.Interaction) -> bool:
    """Custom check for bot access (leadership, event coordinator, or team member)"""
    member = _get_member_from_interaction(interaction)
    if not has_bot_access(member):
        raise app_commands.errors.MissingRole(f"{ADMIN_ROLE}, {EVENT_COORDINATOR_ROLE}, or team role")
    return True

def admin_access_check(interaction: discord.Interaction) -> bool:
    """Custom check for admin access (leadership only)"""
    member = _get_member_from_interaction(interaction)
    if not has_admin_access(member):
        raise app_commands.errors.MissingRole(ADMIN_ROLE)
    return True

def leadership_or_event_coordinator_check(interaction: discord.Interaction) -> bool:
    """Custom check for leadership or event coordinator access"""
    member = _get_member_from_interaction(interaction)
    if not has_leadership_or_event_coordinator_access(member):
        raise app_commands.errors.MissingRole(f"{ADMIN_ROLE} or {EVENT_COORDINATOR_ROLE}")
    return True

def team_member_access_check(interaction: discord.Interaction) -> bool:
    """Custom check for team member access (leadership, event coordinator, or team member)"""
    member = _get_member_from_interaction(interaction)
    if not has_team_member_access(member):
        raise app_commands.errors.MissingRole(f"{ADMIN_ROLE}, {EVENT_COORDINATOR_ROLE}, or team role")
    return True 

def admin_or_event_coordinator_id_check(interaction: discord.Interaction) -> bool:
    member = _get_member_from_interaction(interaction)
    user_role_ids = [r.id for r in member.roles] if member else []
    user_role_names = [r.name for r in member.roles] if member else []
    logger.info(f"[admin_or_event_coordinator_id_check] User: {member} | Role IDs: {user_role_ids} | Role Names: {user_role_names} | Expected ADMIN_ROLE_ID: {ADMIN_ROLE_ID}, EVENT_COORDINATOR_ROLE_ID: {EVENT_COORDINATOR_ROLE_ID} | ADMIN_ROLE: {ADMIN_ROLE}, EVENT_COORDINATOR_ROLE: {EVENT_COORDINATOR_ROLE}")
    if (ADMIN_ROLE_ID and int(ADMIN_ROLE_ID) in user_role_ids) or (EVENT_COORDINATOR_ROLE_ID and int(EVENT_COORDINATOR_ROLE_ID) in user_role_ids):
        return True
    if ADMIN_ROLE in user_role_names or EVENT_COORDINATOR_ROLE in user_role_names:
        return True
    raise app_commands.errors.MissingRole(f"{ADMIN_ROLE_ID or ADMIN_ROLE} or {EVENT_COORDINATOR_ROLE_ID or EVENT_COORDINATOR_ROLE}") 