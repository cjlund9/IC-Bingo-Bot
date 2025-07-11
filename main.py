import discord
from discord.ext import commands
from discord import app_commands
import config
from commands.submit import setup_submit_command
from commands.board_cmd import setup_board_command
from core.update_board import update_board_message
from commands.board_cmd import BoardCommand

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
    print(f"\u2705 Bot online as {bot.user}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command. Admins only.",
            ephemeral=True
        )
    else:
        # For unexpected errors, log or display them
        await interaction.response.send_message(
            f"❌ An unexpected error occurred: {error}",
            ephemeral=True
        )

# Register application commands
setup_submit_command(bot)
setup_board_command(bot)

@bot.tree.command(name="board", description="Display the current bingo board", guild=discord.Object(id=config.GUILD_ID))
@app_commands.describe(team="Team to display board for (optional, admin only)")
@app_commands.checks.has_role(config.ADMIN_ROLE)
async def board_cmd(interaction: discord.Interaction, team: str = None):
    from board import generate_board_image, OUTPUT_FILE, load_placeholders
    from storage import get_completed

    team = team.lower() if team else config.DEFAULT_TEAM
    completed_dict = get_completed()
    placeholders = load_placeholders()

    if team != config.DEFAULT_TEAM and team.capitalize() not in config.TEAM_ROLES:
        await interaction.response.send_message(
            f"❌ Invalid team '{team}'. Valid teams: {', '.join(config.TEAM_ROLES)} or 'all'.",
            ephemeral=True
        )
        return

    generate_board_image(placeholders=placeholders, completed_dict=completed_dict, team=team)
    file = discord.File(OUTPUT_FILE)
    await interaction.response.send_message(file=file)


bot.run(config.TOKEN)