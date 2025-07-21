import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional, List, Dict, Any, Tuple
import requests
from datetime import datetime
from utils.access import admin_access_check
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class TeamBalancer:
    def __init__(self, players: List[Dict[str, Any]]):
        self.players = players
        self.stats_cache = {}
        
    async def fetch_player_stats(self, rsn: str) -> Dict[str, Any]:
        """Fetch player stats from Wise Old Man API asynchronously"""
        if rsn in self.stats_cache:
            return self.stats_cache[rsn]
        try:
            url = f"https://api.wiseoldman.net/v2/players/{rsn}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = {
                            'ehb': data.get('ehb', 0),
                            'ehp': data.get('ehp', 0),
                            'slayer_level': data.get('slayer', {}).get('level', 1),
                            'overall_level': data.get('overall', {}).get('level', 1)
                        }
                        self.stats_cache[rsn] = stats
                        return stats
                    else:
                        logger.warning(f"Failed to fetch stats for {rsn}: {response.status}")
                        return {'ehb': 0, 'ehp': 0, 'slayer_level': 1, 'overall_level': 1}
        except Exception as e:
            logger.error(f"Error fetching stats for {rsn}: {e}")
            return {'ehb': 0, 'ehp': 0, 'slayer_level': 1, 'overall_level': 1}
    
    def calculate_team_stats(self, team: List[Dict]) -> Dict[str, float]:
        """Calculate total stats for a team"""
        if not team:
            return {'ehb': 0, 'ehp': 0, 'slayer': 0}
            
        total_ehb = sum(player['ehb'] for player in team)
        total_ehp = sum(player['ehp'] for player in team)
        total_slayer = sum(player['slayer_level'] for player in team)
        
        return {
            'ehb': total_ehb,
            'ehp': total_ehp,
            'slayer': total_slayer
        }
    
    def calculate_balance_score(self, team1: List[Dict], team2: List[Dict]) -> Dict[str, float]:
        """Calculate balance metrics between teams"""
        team1_stats = self.calculate_team_stats(team1)
        team2_stats = self.calculate_team_stats(team2)
        
        return {
            'size_diff': abs(len(team1) - len(team2)),
            'ehb_diff': abs(team1_stats['ehb'] - team2_stats['ehb']),
            'ehp_diff': abs(team1_stats['ehp'] - team2_stats['ehp']),
            'slayer_diff': abs(team1_stats['slayer'] - team2_stats['slayer'])
        }
    
    def is_acceptable_balance(self, balance_scores: Dict[str, float]) -> bool:
        """Check if teams are acceptably balanced"""
        return (balance_scores['size_diff'] <= 1 and 
                balance_scores['ehb_diff'] <= 300 and 
                balance_scores['ehp_diff'] <= 300)
    
    async def generate_balanced_teams(self) -> Tuple[List[Dict], List[Dict]]:
        """Generate balanced teams using priority-based balancing"""
        import traceback
        try:
            for player in self.players:
                try:
                    stats = await self.fetch_player_stats(player['rsn'])
                    player.update(stats)
                    logger.debug(f"Fetched stats for {player['rsn']}: {stats}")
                except Exception as e:
                    logger.error(f"Error fetching stats for {player['rsn']}: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(10)
            sorted_players = sorted(self.players, key=lambda p: p['ehb'] + p['ehp'] + p['slayer_level'], reverse=True)
            best_balance = float('inf')
            best_teams = None
            for start_idx in range(min(3, len(sorted_players))):
                try:
                    team1, team2 = self._try_configuration(sorted_players, start_idx)
                    balance_scores = self.calculate_balance_score(team1, team2)
                    balance_score = (balance_scores['size_diff'] * 1000 + balance_scores['ehb_diff'] + balance_scores['ehp_diff'] + balance_scores['slayer_diff'])
                    logger.debug(f"Config {start_idx}: team1={len(team1)}, team2={len(team2)}, balance_scores={balance_scores}, balance_score={balance_score}")
                    if balance_score < best_balance:
                        best_balance = balance_score
                        best_teams = (team1, team2)
                except Exception as e:
                    logger.error(f"Error in team configuration {start_idx}: {e}\n{traceback.format_exc()}")
            logger.debug(f"Final teams: team1={len(best_teams[0]) if best_teams else 0}, team2={len(best_teams[1]) if best_teams else 0}")
            return best_teams or ([], [])
        except Exception as e:
            logger.error(f"Error generating balanced teams: {e}\n{traceback.format_exc()}")
            return [], []
    
    def _try_configuration(self, sorted_players: List[Dict], start_idx: int) -> Tuple[List[Dict], List[Dict]]:
        """Try a specific team configuration"""
        team1 = []
        team2 = []
        
        # Alternate between teams starting from start_idx
        for i, player in enumerate(sorted_players):
            if (i + start_idx) % 2 == 0:
                team1.append(player)
            else:
                team2.append(player)
        
        # Optimize the teams
        return self._optimize_teams(team1, team2)
    
    def _optimize_teams(self, team1: List[Dict], team2: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Optimize team balance by swapping players"""
        best_balance = self.calculate_balance_score(team1, team2)
        best_teams = (team1.copy(), team2.copy())
        
        # Try swapping players to improve balance
        for player1 in team1:
            for player2 in team2:
                # Create new teams with swapped players
                new_team1 = [p for p in team1 if p != player1] + [player2]
                new_team2 = [p for p in team2 if p != player2] + [player1]
                
                new_balance = self.calculate_balance_score(new_team1, new_team2)
                
                # Check if this swap improves balance
                balance_score = (new_balance['size_diff'] * 1000 + 
                               new_balance['ehb_diff'] + 
                               new_balance['ehp_diff'] + 
                               new_balance['slayer_diff'])
                
                best_score = (best_balance['size_diff'] * 1000 + 
                            best_balance['ehb_diff'] + 
                            best_balance['ehp_diff'] + 
                            best_balance['slayer_diff'])
                
                if balance_score < best_score:
                    best_balance = new_balance
                    best_teams = (new_team1, new_team2)
        
        return best_teams

class TeamRoleView(discord.ui.View):
    def __init__(self, team1, team2):
        super().__init__(timeout=300)
        self.team1 = team1
        self.team2 = team2
    
    @discord.ui.button(label="Assign Team Roles", style=discord.ButtonStyle.green)
    async def assign_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            guild = interaction.guild
            team1_role = discord.utils.get(guild.roles, name="Moles")
            team2_role = discord.utils.get(guild.roles, name="Obor")
            
            if not team1_role or not team2_role:
                await interaction.followup.send("❌ Team roles (Moles/Obor) not found.")
                return
            
            # Remove existing team roles from all members
            for member in guild.members:
                if team1_role in member.roles:
                    await member.remove_roles(team1_role)
                if team2_role in member.roles:
                    await member.remove_roles(team2_role)
            
            # Assign team roles
            assigned_count = 0
            
            for player in self.team1:
                try:
                    member = player['member']
                    await member.add_roles(team1_role)
                    assigned_count += 1
                except Exception as e:
                    logger.error(f"Error assigning role to {player['rsn']}: {e}")
            
            for player in self.team2:
                try:
                    member = player['member']
                    await member.add_roles(team2_role)
                    assigned_count += 1
                except Exception as e:
                    logger.error(f"Error assigning role to {player['rsn']}: {e}")
            
            embed = discord.Embed(
                title="✅ Team Roles Assigned",
                description=f"Successfully assigned team roles to {assigned_count} members",
                color=0x00FF00
            )
            
            embed.add_field(
                name="🦫 Moles",
                value=f"{len(self.team1)} members assigned",
                inline=True
            )
            
            embed.add_field(
                name="👹 Obor", 
                value=f"{len(self.team2)} members assigned",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error assigning team roles: {e}")
            await interaction.followup.send("❌ An error occurred while assigning team roles.")
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Team role assignment cancelled.", ephemeral=True)

def setup_teams_consolidated_command(bot: Bot):
    @bot.tree.command(
        name="teams",
        description="Team management and generation",
        guild=discord.Object(id=1344457562535497779)
    )
    @app_commands.describe(
        action="What you want to do",
        channel="Channel to post rosters in (for post action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Generate Teams", value="generate"),
        app_commands.Choice(name="Post Rosters", value="post")
    ])
    async def teams_cmd(interaction: Interaction, action: str, channel: discord.TextChannel = None):
        await interaction.response.defer()
        
        try:
            if action == "generate":
                await teams_generate(interaction)
            elif action == "post":
                await teams_post(interaction, channel)
            else:
                await interaction.followup.send("❌ Invalid action. Please choose generate or post.")
                
        except Exception as e:
            logger.error(f"Error in teams command: {e}")
            await interaction.followup.send("❌ An error occurred while processing your request.")

async def teams_generate(interaction: Interaction):
    """Generate balanced teams"""
    try:
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name='Summer 2025 Bingo')
        
        if not role:
            await interaction.followup.send("❌ Role 'Summer 2025 Bingo' not found.")
            return
            
        # Get members with bingo role
        members = []
        for m in role.members:
            if not m.bot:
                members.append(m)
        
        if len(members) < 2:
            await interaction.followup.send("❌ Not enough participants to form teams (need at least 2).")
            return
            
        await interaction.followup.send("🔄 Fetching player stats from Wise Old Man...")
        
        # Prepare player data
        player_stats = []
        for member in members:
            rsn = member.nick or member.name
            player_stats.append({
                'member': member,
                'rsn': rsn
            })
        
        # Use the team balancer
        balancer = TeamBalancer(player_stats)
        team1, team2 = await balancer.generate_balanced_teams()
        
        # Calculate team statistics
        team1_stats = balancer.calculate_team_stats(team1)
        team2_stats = balancer.calculate_team_stats(team2)
        balance_scores = balancer.calculate_balance_score(team1, team2)
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Balanced Teams Generated",
            description=f"Generated from {len(members)} participants using priority-based balancing",
            color=0x00ff00
        )
        
        # Team 1
        team1_text = ""
        for player in team1:
            team1_text += f"• **{player['rsn']}** (EHB: {player['ehb']:.1f}, EHP: {player['ehp']:.1f}, Slayer: {player['slayer_level']})\n"
        
        embed.add_field(
            name=f"🦫 Moles ({len(team1)} players)",
            value=team1_text or "No members",
            inline=False
        )
        
        # Team 2
        team2_text = ""
        for player in team2:
            team2_text += f"• **{player['rsn']}** (EHB: {player['ehb']:.1f}, EHP: {player['ehp']:.1f}, Slayer: {player['slayer_level']})\n"
        
        embed.add_field(
            name=f"👹 Obor ({len(team2)} players)",
            value=team2_text or "No members",
            inline=False
        )
        
        # Balance analysis
        balance_info = f"**Team Size Difference:** {balance_scores['size_diff']} player(s)\n\n"
        
        balance_info += f"**🦫 Moles Totals:**\n"
        balance_info += f"• EHB: {team1_stats['ehb']:.1f}\n"
        balance_info += f"• EHP: {team1_stats['ehp']:.1f}\n"
        balance_info += f"• Slayer: {team1_stats['slayer']:.0f}\n\n"
        
        balance_info += f"**👹 Obor Totals:**\n"
        balance_info += f"• EHB: {team2_stats['ehb']:.1f}\n"
        balance_info += f"• EHP: {team2_stats['ehp']:.1f}\n"
        balance_info += f"• Slayer: {team2_stats['slayer']:.0f}\n\n"
        
        balance_info += f"**Differences:**\n"
        balance_info += f"• EHB Diff: {balance_scores['ehb_diff']:.1f}\n"
        balance_info += f"• EHP Diff: {balance_scores['ehp_diff']:.1f}\n"
        balance_info += f"• Slayer Diff: {balance_scores['slayer_diff']:.0f}\n\n"
        
        # Balance assessment
        if balancer.is_acceptable_balance(balance_scores):
            balance_assessment = "🟢 **Excellent Balance** - All criteria met!"
        elif balance_scores['size_diff'] <= 1 and balance_scores['ehb_diff'] <= 500 and balance_scores['ehp_diff'] <= 500:
            balance_assessment = "🟡 **Good Balance** - Close to targets"
        elif balance_scores['size_diff'] <= 1:
            balance_assessment = "🟠 **Fair Balance** - Team sizes equal, stats could be better"
        else:
            balance_assessment = "🔴 **Poor Balance** - Needs improvement"
        
        balance_info += f"**Assessment:** {balance_assessment}"
        
        embed.add_field(
            name="📊 Balance Analysis",
            value=balance_info,
            inline=False
        )
        
        embed.set_footer(text="Priority: Team Size → EHB → EHP → Slayer Level")
        
        # Ask user if they want to assign roles
        embed.add_field(
            name="🎭 Role Assignment",
            value="Would you like to assign team roles to the members?",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, view=TeamRoleView(team1, team2))
        
    except Exception as e:
        logger.error(f"Error generating teams: {e}")
        await interaction.followup.send("❌ An error occurred while generating teams. Please try again.")

async def teams_post(interaction: Interaction, channel: discord.TextChannel = None):
    """Post team rosters"""
    try:
        # Use specified channel or current channel
        target_channel = channel or interaction.channel
        
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name='Summer 2025 Bingo')
        
        if not role:
            await interaction.followup.send("❌ Role 'Summer 2025 Bingo' not found.")
            return
            
        # Get members with bingo role
        members = []
        for m in role.members:
            if not m.bot:
                members.append(m)
        
        if len(members) < 2:
            await interaction.followup.send("❌ Not enough participants to form teams (need at least 2).")
            return
            
        await interaction.followup.send("🔄 Generating team rosters...")
        
        # Prepare player data
        player_stats = []
        for member in members:
            rsn = member.nick or member.name
            player_stats.append({
                'member': member,
                'rsn': rsn
            })
        
        # Use the team balancer
        balancer = TeamBalancer(player_stats)
        team1, team2 = await balancer.generate_balanced_teams()
        
        # Calculate team statistics
        team1_stats = balancer.calculate_team_stats(team1)
        team2_stats = balancer.calculate_team_stats(team2)
        balance_scores = balancer.calculate_balance_score(team1, team2)
        
        # Create roster embed
        embed = discord.Embed(
            title="🏆 Team Rosters",
            description=f"**Generated on:** <t:{int(datetime.now().timestamp())}:F>\n**Total Participants:** {len(members)}",
            color=0x0099FF
        )
        
        # Team 1 Roster
        team1_text = ""
        for i, player in enumerate(team1, 1):
            team1_text += f"{i}. **{player['rsn']}**\n"
            team1_text += f"   EHB: {player['ehb']:.1f} | EHP: {player['ehp']:.1f} | Slayer: {player['slayer_level']}\n"
        
        embed.add_field(
            name=f"🦫 Moles ({len(team1)} players)",
            value=team1_text or "No members",
            inline=False
        )
        
        # Team 2 Roster
        team2_text = ""
        for i, player in enumerate(team2, 1):
            team2_text += f"{i}. **{player['rsn']}**\n"
            team2_text += f"   EHB: {player['ehb']:.1f} | EHP: {player['ehp']:.1f} | Slayer: {player['slayer_level']}\n"
        
        embed.add_field(
            name=f"👹 Obor ({len(team2)} players)",
            value=team2_text or "No members",
            inline=False
        )
        
        # Team Statistics
        stats_text = f"**🦫 Moles Totals:**\n"
        stats_text += f"• EHB: {team1_stats['ehb']:.1f}\n"
        stats_text += f"• EHP: {team1_stats['ehp']:.1f}\n"
        stats_text += f"• Slayer: {team1_stats['slayer']:.0f}\n\n"
        
        stats_text += f"**👹 Obor Totals:**\n"
        stats_text += f"• EHB: {team2_stats['ehb']:.1f}\n"
        stats_text += f"• EHP: {team2_stats['ehp']:.1f}\n"
        stats_text += f"• Slayer: {team2_stats['slayer']:.0f}\n\n"
        
        stats_text += f"**Balance:**\n"
        stats_text += f"• Size Diff: {balance_scores['size_diff']} player(s)\n"
        stats_text += f"• EHB Diff: {balance_scores['ehb_diff']:.1f}\n"
        stats_text += f"• EHP Diff: {balance_scores['ehp_diff']:.1f}\n"
        stats_text += f"• Slayer Diff: {balance_scores['slayer_diff']:.0f}"
        
        embed.add_field(
            name="📊 Team Statistics",
            value=stats_text,
            inline=False
        )
        
        embed.set_footer(text="Teams generated using Wise Old Man stats")
        
        # Post to target channel
        await target_channel.send(embed=embed)
        await interaction.followup.send(f"✅ Team rosters posted in {target_channel.mention}")
        
    except Exception as e:
        logger.error(f"Error posting rosters: {e}")
        await interaction.followup.send("❌ An error occurred while posting rosters. Please try again.") 