import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands
import logging
import config
from commands.submit import setup_submit_command
from commands.board_cmd import setup_board_command
from commands.progress import setup_progress_command
from commands.manage import setup_manage_command
from commands.sync import setup_sync_command
from commands.teams import setup_teams_command
from commands.stats import setup_stats_command

from core.update_board import update_board_message
import asyncio

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
LEADERSHIP_ROLE = os.getenv('LEADERSHIP_ROLE', 'leadership')

# Enable all necessary intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = commands.Bot(command_prefix="!", intents=intents)

# Store leadership role in bot config for cogs to use
bot.leadership_role = LEADERSHIP_ROLE

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    try:
        # Wait a moment for all cogs to be fully loaded
        await asyncio.sleep(2)
        
        # Sync commands after cogs are loaded
        synced = await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
        logger.info(f"✅ Bot online as {bot.user}")
        logger.info(f"✅ Synced {len(synced)} commands for guild {config.GUILD_ID}")
        
        # Log all synced commands for debugging
        for cmd in synced:
            logger.info(f"  - /{cmd.name}")
        
        # Auto-sync data on startup
        from storage import sync_completed_data_with_tiles
        sync_results = sync_completed_data_with_tiles()
        if sync_results.get("updated_tiles", 0) > 0:
            logger.info(f"🔄 Auto-sync completed: {sync_results['updated_tiles']} tiles updated")
        if sync_results.get("errors"):
            logger.warning(f"⚠️ Auto-sync errors: {len(sync_results['errors'])} errors")
            
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
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
    # Register application commands
    try:
        setup_submit_command(bot)
        setup_board_command(bot)
        setup_progress_command(bot)
        setup_manage_command(bot)
        setup_sync_command(bot)
        setup_teams_command(bot)
        setup_stats_command(bot)

        
        logger.info("✅ Application commands registered successfully")
    except Exception as e:
        logger.error(f"❌ Failed to register application commands: {e}")

    await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())