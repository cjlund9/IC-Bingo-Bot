import discord
from discord.ext import commands
from discord import app_commands
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', 'auto_voice_settings.json')
DEFAULT_TRIGGER = 'Join to Create'
DEFAULT_NAME_PATTERN = 'Party - {username}'
JOIN_TO_CREATE_TEXT = 'join-to-create'

# Helper to load/save settings
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {'trigger': DEFAULT_TRIGGER, 'category': None, 'name_pattern': DEFAULT_NAME_PATTERN, 'menu_message_id': None}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

class VoiceChannelMenu(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Create Default Voice Channel", style=discord.ButtonStyle.green)
    async def default_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        settings = self.cog.settings
        category = None
        cat_id = settings.get('category')
        if cat_id:
            category = discord.utils.get(interaction.guild.categories, id=cat_id)
        if not category:
            category = interaction.guild.categories[0] if interaction.guild.categories else None
        name_pattern = settings.get('name_pattern', DEFAULT_NAME_PATTERN)
        channel_name = name_pattern.format(username=member.display_name)
        temp_channel = await interaction.guild.create_voice_channel(channel_name, category=category)
        self.cog.temp_channels.add(temp_channel.id)
        await member.move_to(temp_channel)
        await interaction.response.send_message(f"Created and moved you to: {channel_name}", ephemeral=True)

    @discord.ui.button(label="Create Custom Voice Channel", style=discord.ButtonStyle.blurple)
    async def custom_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomVoiceModal(self.cog))

class CustomVoiceModal(discord.ui.Modal, title="Custom Voice Channel"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.channel_name = discord.ui.TextInput(label="Channel Name", placeholder="Enter your channel name", max_length=32)
        self.add_item(self.channel_name)

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.user
        settings = self.cog.settings
        category = None
        cat_id = settings.get('category')
        if cat_id:
            category = discord.utils.get(interaction.guild.categories, id=cat_id)
        if not category:
            category = interaction.guild.categories[0] if interaction.guild.categories else None
        channel_name = self.channel_name.value
        temp_channel = await interaction.guild.create_voice_channel(channel_name, category=category)
        self.cog.temp_channels.add(temp_channel.id)
        await member.move_to(temp_channel)
        await interaction.response.send_message(f"Created and moved you to: {channel_name}", ephemeral=True)

class AutoVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = set()
        self.settings = load_settings()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Clean up temp channels when empty
        for channel_id in list(self.temp_channels):
            channel = member.guild.get_channel(channel_id)
            if channel and isinstance(channel, discord.VoiceChannel) and len(channel.members) == 0:
                await channel.delete()
                self.temp_channels.remove(channel_id)

    @app_commands.command(name="voice_channel_menu", description="Show menu to create a temp voice channel")
    async def voice_channel_menu(self, interaction: discord.Interaction):
        view = VoiceChannelMenu(self)
        await interaction.response.send_message(
            "Click a button to create a temporary voice channel:", view=view, ephemeral=True
        )

    @commands.command(name='set_temp_voice')
    @commands.has_permissions(administrator=True)
    async def set_temp_voice(self, ctx, trigger: str = None, category: discord.CategoryChannel = None, name_pattern: str = None):
        """Set trigger channel, category, and name pattern for temp voice channels (admin only)."""
        if trigger:
            self.settings['trigger'] = trigger
        if category:
            self.settings['category'] = category.id
        if name_pattern:
            self.settings['name_pattern'] = name_pattern
        save_settings(self.settings)
        await ctx.send(f"Temp voice settings updated. Use !show_temp_voice_settings to view.")

    @commands.command(name='show_temp_voice_settings')
    async def show_temp_voice_settings(self, ctx):
        """Show current temp voice channel settings."""
        trigger = self.settings.get('trigger', DEFAULT_TRIGGER)
        cat_id = self.settings.get('category')
        name_pattern = self.settings.get('name_pattern', DEFAULT_NAME_PATTERN)
        category = discord.utils.get(ctx.guild.categories, id=cat_id) if cat_id else None
        msg = f"Trigger channel: {trigger}\nCategory: {category.name if category else 'Default'}\nName pattern: {name_pattern}"
        await ctx.send(msg)

def setup(bot):
    bot.add_cog(AutoVoice(bot)) 