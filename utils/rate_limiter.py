"""
Rate limiting utilities for Discord commands
Provides decorators and functions for managing command cooldowns and usage limits
"""

import time
import functools
from collections import defaultdict
from typing import Callable, Any
import discord
from discord import app_commands, Interaction
import logging

logger = logging.getLogger(__name__)

# Global rate limiting storage
command_cooldowns = defaultdict(lambda: defaultdict(float))
user_command_counts = defaultdict(lambda: defaultdict(list))


def rate_limit(cooldown_seconds: float = 3.0, max_requests_per_hour: int = 100):
    """
    Decorator to add rate limiting to Discord commands
    
    Args:
        cooldown_seconds: Minimum time between command uses per user
        max_requests_per_hour: Maximum requests per hour per user
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs) -> Any:
            user_id = interaction.user.id
            command_name = func.__name__
            current_time = time.time()
            
            # Check cooldown
            last_used = command_cooldowns[command_name][user_id]
            if current_time - last_used < cooldown_seconds:
                remaining = cooldown_seconds - (current_time - last_used)
                try:
                    await interaction.response.send_message(
                        f"⏰ Please wait {remaining:.1f} seconds before using this command again.",
                        ephemeral=True
                    )
                except discord.errors.HTTPException as e:
                    if e.code == 40060:  # Interaction already acknowledged
                        await interaction.followup.send(
                            f"⏰ Please wait {remaining:.1f} seconds before using this command again.",
                            ephemeral=True
                        )
                    else:
                        raise
                return
            
            # Check hourly limit
            hour_ago = current_time - 3600
            user_counts = user_command_counts[command_name]
            
            # Clean old entries and count valid ones
            if user_id not in user_counts:
                user_counts[user_id] = []
            # Ensure the value is always a list (fix for possible int assignment bug)
            if not isinstance(user_counts[user_id], list):
                user_counts[user_id] = []
            
            # Filter out old timestamps and count remaining ones
            valid_timestamps = [ts for ts in user_counts[user_id] if ts > hour_ago]
            user_counts[user_id] = valid_timestamps
            
            if len(user_counts[user_id]) >= max_requests_per_hour:
                try:
                    await interaction.response.send_message(
                        f"⏰ You've used this command too many times in the last hour. Please wait before trying again.",
                        ephemeral=True
                    )
                except discord.errors.HTTPException as e:
                    if e.code == 40060:  # Interaction already acknowledged
                        await interaction.followup.send(
                            f"⏰ You've used this command too many times in the last hour. Please wait before trying again.",
                            ephemeral=True
                        )
                    else:
                        raise
                return
            
            # Update usage tracking
            command_cooldowns[command_name][user_id] = current_time
            user_counts[user_id].append(current_time)
            
            # Execute the command
            try:
                return await func(interaction, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in rate-limited command {command_name}: {e}")
                raise
        
        return wrapper
    return decorator


def check_rate_limit(user_id: int, command_name: str, cooldown_seconds: float = 3.0) -> bool:
    """
    Synchronous rate limit check for use in tests or non-Discord contexts.
    Returns True if allowed, False if on cooldown.
    """
    current_time = time.time()
    last_used = command_cooldowns[command_name][user_id]
    if current_time - last_used < cooldown_seconds:
        return False
    command_cooldowns[command_name][user_id] = current_time
    return True


def cleanup_old_rate_limits():
    """Clean up old rate limiting data to prevent memory leaks"""
    current_time = time.time()
    cutoff_time = current_time - 3600  # 1 hour
    
    # Clean up cooldowns
    for command_name in list(command_cooldowns.keys()):
        for user_id in list(command_cooldowns[command_name].keys()):
            if command_cooldowns[command_name][user_id] < cutoff_time:
                del command_cooldowns[command_name][user_id]
        
        # Remove empty command entries
        if not command_cooldowns[command_name]:
            del command_cooldowns[command_name]
    
    # Clean up command counts
    for command_name in list(user_command_counts.keys()):
        for user_id in list(user_command_counts[command_name].keys()):
            user_command_counts[command_name][user_id] = [
                ts for ts in user_command_counts[command_name][user_id] 
                if ts > cutoff_time
            ]
            
            # Remove empty user entries
            if not user_command_counts[command_name][user_id]:
                del user_command_counts[command_name][user_id]
        
        # Remove empty command entries
        if not user_command_counts[command_name]:
            del user_command_counts[command_name]


def get_rate_limit_stats() -> dict:
    """Get statistics about rate limiting usage"""
    stats = {
        'commands': {},
        'total_users': 0,
        'total_requests': 0
    }
    
    for command_name in command_cooldowns:
        user_count = len(command_cooldowns[command_name])
        request_count = sum(len(user_command_counts[command_name].get(user_id, [])) 
                           for user_id in command_cooldowns[command_name])
        
        stats['commands'][command_name] = {
            'active_users': user_count,
            'requests_last_hour': request_count
        }
        stats['total_users'] += user_count
        stats['total_requests'] += request_count
    
    return stats 