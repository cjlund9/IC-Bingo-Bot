import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
import psutil
import time
from utils.access import admin_access_check
from utils.rate_limiter import get_rate_limit_stats

logger = logging.getLogger(__name__)

def setup_monitor_command(bot: Bot):
    @bot.tree.command(
        name="monitor",
        description="Monitor system performance and rate limiting (Admin only)",
        guild=discord.Object(id=1344457562535497779)
    )
    @app_commands.check(admin_access_check)
    async def monitor_cmd(interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get system performance stats
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            # Get rate limiting stats
            rate_stats = get_rate_limit_stats()
            
            # Create performance report
            embed = discord.Embed(
                title="🤖 Bot Performance Monitor",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # System stats
            embed.add_field(
                name="💾 Memory Usage",
                value=f"RSS: {memory_info.rss / 1024 / 1024:.1f}MB\n"
                      f"VMS: {memory_info.vms / 1024 / 1024:.1f}MB\n"
                      f"CPU: {cpu_percent:.1f}%",
                inline=True
            )
            
            # Rate limiting stats
            embed.add_field(
                name="⏰ Rate Limiting",
                value=f"Active Commands: {len(rate_stats['commands'])}\n"
                      f"Total Users: {rate_stats['total_users']}\n"
                      f"Total Requests: {rate_stats['total_requests']}",
                inline=True
            )
            
            # Command breakdown
            if rate_stats['commands']:
                command_details = []
                for cmd, stats in rate_stats['commands'].items():
                    command_details.append(
                        f"**{cmd}**: {stats['active_users']} users, {stats['requests_last_hour']} requests"
                    )
                
                embed.add_field(
                    name="📊 Command Usage (Last Hour)",
                    value="\n".join(command_details[:5]),  # Show top 5
                    inline=False
                )
            
            # System uptime
            uptime = time.time() - process.create_time()
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            embed.add_field(
                name="⏱️ Uptime",
                value=f"{hours}h {minutes}m",
                inline=True
            )
            
            # Disk usage
            try:
                disk_usage = psutil.disk_usage('.')
                embed.add_field(
                    name="💿 Disk Usage",
                    value=f"Used: {disk_usage.used / 1024 / 1024 / 1024:.1f}GB\n"
                          f"Free: {disk_usage.free / 1024 / 1024 / 1024:.1f}GB\n"
                          f"Total: {disk_usage.total / 1024 / 1024 / 1024:.1f}GB",
                    inline=True
                )
            except Exception as e:
                logger.warning(f"Could not get disk usage: {e}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in monitor command: {e}")
            await interaction.followup.send("❌ Error getting performance data.", ephemeral=True) 