import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
from discord.ui import Modal, TextInput
import requests
import logging

logger = logging.getLogger(__name__)

WOM_API_BASE = "https://api.wiseoldman.net/v2/competitions/leaderboard"

class LeaderboardSearchModal(Modal, title="Search WOM Leaderboard"):
    username = TextInput(label="Username (optional)", required=False, max_length=12)
    metric = TextInput(label="Metric (e.g., overall, attack, ehp)", required=False, placeholder="overall", max_length=20)
    period = TextInput(label="Period (e.g., day, week, month)", required=False, placeholder="week", max_length=10)

    def __init__(self, interaction: Interaction):
        super().__init__()
        self.interaction = interaction

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        username = self.username.value.strip()
        metric = self.metric.value.strip() or "overall"
        period = self.period.value.strip() or "week"

        params = {"metric": metric, "period": period}
        if username:
            params["username"] = username

        try:
            response = requests.get(WOM_API_BASE, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if not data or not data.get("players"):
                    await interaction.followup.send("❌ No leaderboard data found for your query.", ephemeral=True)
                    return
                players = data["players"]
                embed = discord.Embed(
                    title=f"WOM Leaderboard: {metric.capitalize()} ({period})",
                    description=f"Top results for your query.",
                    color=0xFFD700
                )
                for i, player in enumerate(players[:10], 1):
                    name = player.get("displayName", "Unknown")
                    value = player.get("value", "N/A")
                    embed.add_field(
                        name=f"#{i}: {name}",
                        value=f"Value: {value}",
                        inline=False
                    )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ WOM API error: {response.status_code}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error querying WOM API: {e}")
            await interaction.followup.send(f"❌ Error querying WOM API: {e}", ephemeral=True)

def setup_total_leaderboard_command(bot: Bot):
    @bot.tree.command(
        name="totalleaderboard",
        description="Search the Wise Old Man leaderboard dynamically.",
        guild=None  # Set to your guild if you want to restrict
    )
    async def total_leaderboard_cmd(interaction: Interaction):
        modal = LeaderboardSearchModal(interaction)
        await interaction.response.send_modal(modal) 