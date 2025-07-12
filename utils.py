import discord
import logging
from typing import Optional
from config import TEAM_ROLES, DEFAULT_TEAM

logger = logging.getLogger(__name__)

def get_user_team(member: discord.Member) -> str:
    """
    Get the team role for a Discord member.
    
    Args:
        member: Discord member object
        
    Returns:
        str: Team name in lowercase, or DEFAULT_TEAM if no team role found
    """
    if not member or not hasattr(member, 'roles'):
        logger.warning("Invalid member object provided")
        return DEFAULT_TEAM
    
    try:
        for role in member.roles:
            if role.name in TEAM_ROLES:
                return role.name.lower()
        return DEFAULT_TEAM
    except Exception as e:
        logger.error(f"Error getting user team: {e}")
        return DEFAULT_TEAM

def validate_drop_name(drop_name: str) -> bool:
    """
    Validate a drop name.
    
    Args:
        drop_name: Name of the drop to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not drop_name or not isinstance(drop_name, str):
        return False
    
    # Remove whitespace and check if empty
    drop_name = drop_name.strip()
    if not drop_name:
        return False
    
    # Check for reasonable length (1-100 characters)
    if len(drop_name) > 100:
        return False
    
    return True

def validate_quantity(quantity: int) -> bool:
    """
    Validate a quantity value.
    
    Args:
        quantity: Quantity to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(quantity, int):
        return False
    
    if quantity <= 0:
        return False
    
    # Reasonable upper limit
    if quantity > 1000:
        return False
    
    return True

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'", ';', '(', ')', '{', '}', '[', ']']
    sanitized = text
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized.strip()