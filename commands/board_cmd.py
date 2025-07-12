import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.commands import Bot

from config import GUILD_ID, TEAM_ROLES, DEFAULT_TEAM, BOARD_CHANNEL_NAME, ADMIN_ROLE
from storage import get_completed

class BoardCommand(app_commands.Group):
    def __init__(self):
        super().__init__(name="board", description="Bingo board commands")

    @app_commands.command(name="show", description="Display the current bingo board")
    @app_commands.describe(team="Team to display board for (optional, admin only)")
    @app_commands.checks.has_role(ADMIN_ROLE)
    async def show(self, interaction: Interaction, team: str = None):
        team = team.lower() if team else DEFAULT_TEAM

        if team != DEFAULT_TEAM and team.capitalize() not in TEAM_ROLES:
            await interaction.response.send_message(
                f"❌ Invalid team '{team}'. Valid teams: {', '.join(TEAM_ROLES)} or 'all'.",
                ephemeral=True
            )
            return

        completed_dict = get_completed()
        from board import generate_board_image, OUTPUT_FILE
        generate_board_image(placeholders=None, completed_dict=completed_dict, team=team)

        file = discord.File(OUTPUT_FILE)
        await interaction.response.send_message(file=file)

async def update_board_message(guild: discord.Guild, bot_user: discord.User, team: str = DEFAULT_TEAM):
    from core.update_board import update_board_message as update_board
    await update_board(guild, bot_user, team)

def setup_board_command(bot: Bot):
    board_cmd = BoardCommand()
    bot.tree.add_command(board_cmd)
