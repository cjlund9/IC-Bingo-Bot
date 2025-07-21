import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
from discord.ui import View, Button
import logging
import requests
import json
from utils.access import has_bot_access, bot_access_check, admin_access_check, admin_or_event_coordinator_id_check
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from config import ADMIN_ROLE

logger = logging.getLogger(__name__)

class TeamBalancer:
    """Team balancing with priority-based algorithm"""
    
    def __init__(self, players: List[Dict[str, Any]]):
        self.players = players
        self.n_players = len(players)
        self.n_teams = 2
        self.target_team_size = self.n_players // self.n_teams
        self.extra_players = self.n_players % self.n_teams
    
    def fetch_player_stats(self, rsn: str) -> Dict[str, Any]:
        """Fetch player stats from WiseOldMan API"""
        try:
            url = f'https://api.wiseoldman.net/v2/players/{rsn}'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ehb = data.get('ehb', 0)
                ehp = data.get('ehp', 0)
                slayer_level = data.get('latestSnapshot', {}).get('data', {}).get('skills', {}).get('slayer', {}).get('level', 1)
                
                return {
                    'ehb': ehb,
                    'ehp': ehp,
                    'slayer_level': slayer_level,
                    'total_score': ehb + ehp + (slayer_level * 0.1)  # Weighted score
                }
            else:
                logger.warning(f"Failed to fetch stats for {rsn}: {response.status_code}")
                return {
                    'ehb': 0,
                    'ehp': 0,
                    'slayer_level': 1,
                    'total_score': 0.1
                }
        except Exception as e:
            logger.warning(f"Failed to fetch stats for {rsn}: {e}")
            return {
                'ehb': 0,
                'ehp': 0,
                'slayer_level': 1,
                'total_score': 0.1
            }
    
    def calculate_team_stats(self, team: List[Dict]) -> Dict[str, float]:
        """Calculate total stats for a team"""
        if not team:
            return {'ehb': 0, 'ehp': 0, 'slayer': 0}
        
        total_ehb = sum(p['ehb'] for p in team)
        total_ehp = sum(p['ehp'] for p in team)
        total_slayer = sum(p['slayer_level'] for p in team)
        
        return {
            'ehb': total_ehb,
            'ehp': total_ehp,
            'slayer': total_slayer
        }
    
    def calculate_balance_score(self, team1: List[Dict], team2: List[Dict]) -> Dict[str, float]:
        """Calculate balance scores for all metrics (lower is better)"""
        stats1 = self.calculate_team_stats(team1)
        stats2 = self.calculate_team_stats(team2)
        
        size_diff = abs(len(team1) - len(team2))
        ehb_diff = abs(stats1['ehb'] - stats2['ehb'])
        ehp_diff = abs(stats1['ehp'] - stats2['ehp'])
        slayer_diff = abs(stats1['slayer'] - stats2['slayer'])
        
        return {
            'size_diff': size_diff,
            'ehb_diff': ehb_diff,
            'ehp_diff': ehp_diff,
            'slayer_diff': slayer_diff
        }
    
    def is_acceptable_balance(self, balance_scores: Dict[str, float]) -> bool:
        """Check if the balance meets our criteria"""
        return (
            balance_scores['size_diff'] <= 1 and  # Team sizes within 1
            balance_scores['ehb_diff'] <= 300 and  # EHB within 300
            balance_scores['ehp_diff'] <= 300      # EHP within 300
        )
    
    async def generate_balanced_teams(self) -> Tuple[List[Dict], List[Dict]]:
        """Generate optimally balanced teams using priority-based algorithm"""
        
        if self.n_players < 2:
            return [], []
        
        # Fetch stats for all players
        logger.info("Fetching player stats from WiseOldMan...")
        for player in self.players:
            stats = await self.fetch_player_stats(player['rsn'])
            player.update(stats)
            # Add a 5-second delay between requests
            await asyncio.sleep(5)
        
        # Sort players by total score for initial distribution
        sorted_players = sorted(self.players, key=lambda x: x['total_score'], reverse=True)
        
        best_team1 = []
        best_team2 = []
        best_overall_score = float('inf')
        
        # Try different starting configurations
        for start_idx in range(min(3, len(sorted_players))):
            team1, team2 = self._try_configuration(sorted_players, start_idx)
            balance_scores = self.calculate_balance_score(team1, team2)
            
            # Calculate weighted score based on priorities
            overall_score = (
                balance_scores['size_diff'] * 1000 +      # Priority 1: Team size
                balance_scores['ehb_diff'] * 100 +        # Priority 2: Overall EHB
                balance_scores['ehp_diff'] * 100 +        # Priority 3: Overall EHP
                balance_scores['slayer_diff'] * 10        # Priority 4: Slayer level
            )
            
            if overall_score < best_overall_score:
                best_overall_score = overall_score
                best_team1 = team1.copy()
                best_team2 = team2.copy()
        
        # Try to improve balance by swapping players
        improved_team1, improved_team2 = self._optimize_teams(best_team1, best_team2)
        
        return improved_team1, improved_team2
    
    def _try_configuration(self, sorted_players: List[Dict], start_idx: int) -> Tuple[List[Dict], List[Dict]]:
        """Try a specific team configuration"""
        team1 = []
        team2 = []
        
        # Start with the specified player
        start_player = sorted_players[start_idx]
        team1.append(start_player)
        
        # Remove starting player from list
        remaining_players = [p for i, p in enumerate(sorted_players) if i != start_idx]
        
        # Distribute remaining players with priority-based logic
        for player in remaining_players:
            # Try adding to each team and see which results in better balance
            temp_team1 = team1 + [player]
            temp_team2 = team2
            
            balance_with_team1 = self.calculate_balance_score(temp_team1, temp_team2)
            score_with_team1 = (
                balance_with_team1['size_diff'] * 1000 +
                balance_with_team1['ehb_diff'] * 100 +
                balance_with_team1['ehp_diff'] * 100 +
                balance_with_team1['slayer_diff'] * 10
            )
            
            temp_team1 = team1
            temp_team2 = team2 + [player]
            
            balance_with_team2 = self.calculate_balance_score(temp_team1, temp_team2)
            score_with_team2 = (
                balance_with_team2['size_diff'] * 1000 +
                balance_with_team2['ehb_diff'] * 100 +
                balance_with_team2['ehp_diff'] * 100 +
                balance_with_team2['slayer_diff'] * 10
            )
            
            # Add to team with better score
            if score_with_team1 <= score_with_team2:
                team1.append(player)
            else:
                team2.append(player)
        
        return team1, team2
    
    def _optimize_teams(self, team1: List[Dict], team2: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Try swapping players to improve balance"""
        current_balance = self.calculate_balance_score(team1, team2)
        current_score = (
            current_balance['size_diff'] * 1000 +
            current_balance['ehb_diff'] * 100 +
            current_balance['ehp_diff'] * 100 +
            current_balance['slayer_diff'] * 10
        )
        
        improved = True
        iterations = 0
        max_iterations = 10  # Prevent infinite loops
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            # Try swapping each player from team1 with each player from team2
            for i, player1 in enumerate(team1):
                for j, player2 in enumerate(team2):
                    # Create temporary teams with swapped players
                    temp_team1 = team1.copy()
                    temp_team2 = team2.copy()
                    temp_team1[i] = player2
                    temp_team2[j] = player1
                    
                    # Check if this swap improves balance
                    new_balance = self.calculate_balance_score(temp_team1, temp_team2)
                    new_score = (
                        new_balance['size_diff'] * 1000 +
                        new_balance['ehb_diff'] * 100 +
                        new_balance['ehp_diff'] * 100 +
                        new_balance['slayer_diff'] * 10
                    )
                    
                    if new_score < current_score:
                        team1 = temp_team1
                        team2 = temp_team2
                        current_balance = new_balance
                        current_score = new_score
                        improved = True
                        break
                
                if improved:
                    break
        
        return team1, team2

class TeamRoleView(View):
    def __init__(self, team1, team2):
        super().__init__(timeout=300)  # 5 minute timeout
        self.team1 = team1
        self.team2 = team2
    
    @discord.ui.button(label="Assign Team Roles", style=discord.ButtonStyle.green)
    async def assign_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Check permissions
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send("❌ You need 'Manage Roles' permission to assign team roles.", ephemeral=True)
                return
            
            guild = interaction.guild
            
            # Get existing team roles
            team1_role = discord.utils.get(guild.roles, name="Moles")
            team2_role = discord.utils.get(guild.roles, name="Obor")
            
            if not team1_role:
                await interaction.followup.send("❌ Role 'Moles' not found. Please create this role first.", ephemeral=True)
                return
                
            if not team2_role:
                await interaction.followup.send("❌ Role 'Obor' not found. Please create this role first.", ephemeral=True)
                return
            
            # Assign roles
            assigned_count = 0
            errors = []
            
            # Assign Team 1 roles
            for player in self.team1:
                try:
                    member = player['member']
                    # Remove other team roles first
                    if team2_role in member.roles:
                        await member.remove_roles(team2_role)
                    # Add Team 1 role
                    if team1_role not in member.roles:
                        await member.add_roles(team1_role)
                        assigned_count += 1
                except Exception as e:
                    errors.append(f"Failed to assign Team 1 role to {player['rsn']}: {e}")
            
            # Assign Team 2 roles
            for player in self.team2:
                try:
                    member = player['member']
                    # Remove other team roles first
                    if team1_role in member.roles:
                        await member.remove_roles(team1_role)
                    # Add Team 2 role
                    if team2_role not in member.roles:
                        await member.add_roles(team2_role)
                        assigned_count += 1
                except Exception as e:
                    errors.append(f"Failed to assign Team 2 role to {player['rsn']}: {e}")
            
            # Create result embed
            embed = discord.Embed(
                title="🎭 Team Roles Assigned",
                description=f"Successfully assigned roles to {assigned_count} members",
                color=0x00ff00
            )
            
            if errors:
                embed.add_field(
                    name="⚠️ Errors",
                    value="\n".join(errors[:5]) + ("..." if len(errors) > 5 else ""),
                    inline=False
                )
            
            embed.add_field(
                name="🔵 Team 1 Role",
                value=f"<@&{team1_role.id}>",
                inline=True
            )
            
            embed.add_field(
                name="🔴 Team 2 Role",
                value=f"<@&{team2_role.id}>",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error assigning team roles: {e}")
            await interaction.followup.send("❌ An error occurred while assigning team roles.", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Team role assignment cancelled.", ephemeral=True)

def setup_teams_command(bot: Bot):
    @bot.tree.command(
        name="generate_teams",
        description="Generate balanced teams from members with the event role using Wise Old Man stats",
        guild=discord.Object(id=721816434790891643)  # Replace with your guild ID
    )
    @app_commands.check(admin_or_event_coordinator_id_check)
    async def generate_teams(interaction: Interaction):
        await interaction.response.defer()
        
        try:
            guild = interaction.guild
            role = discord.utils.get(guild.roles, name='Summer 2025 Bingo')
            
            if not role:
                await interaction.followup.send("❌ Role 'Summer 2025 Bingo' not found.")
                return
                
            # Get members with bingo role (including leadership who also have the bingo role)
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
                # Try to get RSN from nickname or username
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

    @bot.tree.command(
        name="post_rosters",
        description="Generate and post team rosters as a message",
        guild=discord.Object(id=1344457562535497779)
    )
    @app_commands.check(admin_or_event_coordinator_id_check)
    @app_commands.describe(
        channel="Channel to post the rosters in (optional, defaults to current channel)"
    )
    async def post_rosters(interaction: Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer()
        
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
                name=f"🦫 Moles Team ({len(team1)} players)",
                value=team1_text or "No members",
                inline=False
            )
            
            # Team 2 Roster
            team2_text = ""
            for i, player in enumerate(team2, 1):
                team2_text += f"{i}. **{player['rsn']}**\n"
                team2_text += f"   EHB: {player['ehb']:.1f} | EHP: {player['ehp']:.1f} | Slayer: {player['slayer_level']}\n"
            
            embed.add_field(
                name=f"👹 Obor Team ({len(team2)} players)",
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
            
            embed.set_footer(text="Generated using WiseOldMan stats | Priority: Team Size → EHB → EHP → Slayer")
            
            # Post the roster message
            roster_message = await target_channel.send(embed=embed)
            
            # Confirm to the user
            await interaction.followup.send(
                f"✅ Team rosters posted in {target_channel.mention}!\n"
                f"Message: {roster_message.jump_url}"
            )
            
        except Exception as e:
            logger.error(f"Error posting rosters: {e}")
            await interaction.followup.send("❌ An error occurred while posting team rosters. Please try again.") 