"""
IC-Bingo-Bot - Discord bot for managing RuneScape bingo games
Main entry point with performance monitoring and rate limiting
"""

import os
import asyncio
import time
import logging
import logging.handlers
from collections import defaultdict

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import psutil

# Load environment variables
load_dotenv()

# Import command modules
from commands.submit import setup_submit_command
from commands.board_cmd import setup_board_command
from commands.progress import setup_progress_command
from commands.manage import setup_manage_command
from commands.sync import setup_sync_command
from commands.teams_consolidated import setup_teams_consolidated_command
from commands.stats import setup_stats_command
# from commands.leaderboard_cmd import setup_leaderboard_commands  # Removed - leaderboard command is in progress.py
# from commands.shop_cmd import setup_shop_commands  # Temporarily disabled
from commands.monitor import setup_monitor_command
from commands.total_leaderboard import setup_total_leaderboard_command

# Import utilities
from utils.rate_limiter import cleanup_old_rate_limits, get_rate_limit_stats

# Configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
LEADERSHIP_ROLE = os.getenv('LEADERSHIP_ROLE', 'leadership')

# Configure logging with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            'logs/bot.log', 
            maxBytes=10*1024*1024,  # 10MB max file size
            backupCount=5  # Keep 5 backup files
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor bot performance and resource usage"""
    
    def __init__(self):
        self.command_times = defaultdict(list)
        self.memory_usage = []
        self.start_time = time.time()
    
    def log_command_time(self, command_name: str, execution_time: float):
        """Log command execution time for performance monitoring"""
        self.command_times[command_name].append(execution_time)
        # Keep only last 100 entries per command
        if len(self.command_times[command_name]) > 100:
            self.command_times[command_name] = self.command_times[command_name][-100:]
    
    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            'percent': process.memory_percent()
        }
    
    def log_memory_usage(self):
        """Log current memory usage"""
        memory_stats = self.get_memory_usage()
        self.memory_usage.append(memory_stats)
        # Keep only last 1000 entries
        if len(self.memory_usage) > 1000:
            self.memory_usage = self.memory_usage[-1000:]
        
        # Log if memory usage is high
        if memory_stats['rss_mb'] > 500:  # 500MB threshold
            logger.warning(f"High memory usage: {memory_stats['rss_mb']:.1f}MB ({memory_stats['percent']:.1f}%)")
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        stats = {}
        for command, times in self.command_times.items():
            if times:
                stats[command] = {
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times),
                    'count': len(times)
                }
        return stats


# Global performance monitor
performance_monitor = PerformanceMonitor()

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.leadership_role = LEADERSHIP_ROLE


def cleanup_temp_files():
    """Clean up temporary files to prevent disk space issues"""
    import glob
    
    try:
        # Clean up temporary board files older than 1 hour
        current_time = time.time()
        temp_patterns = [
            "board_*.png",
            "bingo_board_*.png",
            "temp_*.png"
        ]
        
        for pattern in temp_patterns:
            for file_path in glob.glob(pattern):
                try:
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        logger.debug(f"Cleaned up temp file: {file_path}")
                except OSError:
                    pass  # File might be in use or already deleted
                    
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")


async def background_maintenance():
    """Background task for maintenance operations"""
    while True:
        try:
            # Clean up old rate limits
            cleanup_old_rate_limits()
            
            # Clean up temporary files
            cleanup_temp_files()
            
            # Log performance stats every 10 minutes
            if int(time.time()) % 600 < 30:  # Every 10 minutes
                stats = performance_monitor.get_performance_stats()
                if stats:
                    logger.info(f"Performance stats: {len(stats)} commands tracked")
                    for cmd, cmd_stats in stats.items():
                        if cmd_stats['count'] > 10:  # Only log if we have enough data
                            logger.info(f"  {cmd}: avg={cmd_stats['avg_time']:.3f}s, max={cmd_stats['max_time']:.3f}s, count={cmd_stats['count']}")
            
            await asyncio.sleep(300)  # Run every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in background maintenance: {e}")
            await asyncio.sleep(300)


@bot.event
async def on_ready():
    """Bot startup event"""
    await bot.wait_until_ready()
    try:
        # Wait a moment for all cogs to be fully loaded
        await asyncio.sleep(2)
        
        # Sync commands after cogs are loaded
        import config
        synced = await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
        logger.info(f"✅ Bot online as {bot.user}")
        logger.info(f"✅ Synced {len(synced)} commands for guild {config.GUILD_ID}")
        
        # Log all synced commands for debugging
        for cmd in synced:
            logger.info(f"  - /{cmd.name}")
        
        # Start background tasks
        bot.loop.create_task(background_maintenance())
            
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle application command errors"""
    logger.error(f"Command error: {error}")
    
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command. Admins only.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
            ephemeral=True
        )
    else:
        # For unexpected errors, log them and show a generic message
        logger.error(f"Unexpected error in command {interaction.command.name}: {error}")
        await interaction.response.send_message(
            "❌ An unexpected error occurred. Please try again later.",
            ephemeral=True
        )


async def main():
    """Main bot startup function"""
    # Register application commands
    try:
        setup_submit_command(bot)
        setup_board_command(bot)
        setup_progress_command(bot)
        setup_manage_command(bot)
        setup_sync_command(bot)
        setup_teams_consolidated_command(bot)
        setup_stats_command(bot)
        # setup_leaderboard_commands(bot)  # Removed - leaderboard command is in progress.py
        # setup_shop_commands(bot)  # Temporarily disabled
        setup_monitor_command(bot)
        setup_total_leaderboard_command(bot)
        
        logger.info("✅ Application commands registered successfully")
    except Exception as e:
        logger.error(f"❌ Failed to register application commands: {e}")

    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())