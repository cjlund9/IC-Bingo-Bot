import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional
from database import db
from config import GUILD_ID, ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from utils.access import leadership_or_event_coordinator_check

logger = logging.getLogger(__name__)

def setup_shop_commands(bot: Bot):
    
    @bot.tree.command(
        name="shop",
        description="View the points shop",
        guild=discord.Object(id=GUILD_ID)
    )
    async def shop_cmd(interaction: Interaction):
        await interaction.response.defer()
        
        try:
            # Get shop items
            items = db.get_shop_items()
            
            if not items:
                await interaction.followup.send("❌ No items available in the shop.")
                return
            
            # Create embed
            embed = discord.Embed(
                title="🛒 Ironclad Events Shop",
                description="Spend your hard-earned points on exclusive items!",
                color=0x00FF00
            )
            
            # Group items by category
            categories = {}
            for item in items:
                category = item['category'] or 'General'
                if category not in categories:
                    categories[category] = []
                categories[category].append(item)
            
            # Add items by category
            for category, category_items in categories.items():
                category_text = ""
                for item in category_items:
                    quantity_text = f" (Stock: {item['available_quantity']})" if item['available_quantity'] != -1 else ""
                    category_text += f"• **{item['name']}** - {item['cost']} pts{quantity_text}\n"
                    if item['description']:
                        category_text += f"  *{item['description']}*\n"
                
                embed.add_field(
                    name=f"📦 {category}",
                    value=category_text,
                    inline=False
                )
            
            embed.set_footer(text="Use /buy to purchase items")
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Shop viewed by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error in shop command: {e}")
            await interaction.followup.send("❌ An error occurred while loading the shop.")
    
    @bot.tree.command(
        name="buy",
        description="Purchase an item from the shop",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.describe(
        item_id="ID of the item to purchase",
        quantity="Quantity to purchase (default: 1)"
    )
    async def buy_cmd(interaction: Interaction, item_id: int, quantity: int = 1):
        await interaction.response.defer()
        
        try:
            # Get or create user
            user = db.get_or_create_user(
                interaction.user.id,
                interaction.user.name,
                interaction.user.display_name
            )
            
            # Purchase item
            success = db.purchase_item(interaction.user.id, item_id, quantity)
            
            if success:
                # Get updated user info and item info
                user_info = db.get_user(interaction.user.id)
                items = db.get_shop_items()
                item = next((item for item in items if item['id'] == item_id), None)
                
                embed = discord.Embed(
                    title="✅ Purchase Successful",
                    description=f"Successfully purchased **{item['name']}** x{quantity}",
                    color=0x00FF00
                )
                embed.add_field(name="Cost", value=f"{item['cost'] * quantity} points", inline=True)
                embed.add_field(name="Remaining Points", value=f"{user_info['total_points']} points", inline=True)
                
                await interaction.followup.send(embed=embed)
                logger.info(f"Purchase: {interaction.user.display_name} bought {item['name']} x{quantity}")
            else:
                await interaction.followup.send("❌ Failed to purchase item. Check your points and item availability.")
                
        except Exception as e:
            logger.error(f"Error in buy command: {e}")
            await interaction.followup.send("❌ An error occurred while processing your purchase.")
    
    @bot.tree.command(
        name="add_shop_item",
        description="Add a new item to the shop (Leadership/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(
        name="Name of the item",
        description="Item description",
        cost="Points cost",
        category="Item category",
        quantity="Available quantity (-1 for unlimited)"
    )
    async def add_shop_item_cmd(interaction: Interaction, name: str, description: str, 
                               cost: int, category: str = "General", quantity: int = -1):
        await interaction.response.defer()
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO shop_items (name, description, cost, category, available_quantity)
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, description, cost, category, quantity)
                )
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Shop Item Added",
                    description=f"Successfully added **{name}** to the shop",
                    color=0x00FF00
                )
                embed.add_field(name="Cost", value=f"{cost} points", inline=True)
                embed.add_field(name="Category", value=category, inline=True)
                embed.add_field(name="Quantity", value="Unlimited" if quantity == -1 else str(quantity), inline=True)
                embed.add_field(name="Description", value=description, inline=False)
                
                await interaction.followup.send(embed=embed)
                logger.info(f"Shop item added: {name} by {interaction.user.display_name}")
                
        except Exception as e:
            logger.error(f"Error in add_shop_item command: {e}")
            await interaction.followup.send("❌ An error occurred while adding the shop item.")
    
    @bot.tree.command(
        name="remove_shop_item",
        description="Remove an item from the shop (Leadership/Event Coordinator only)",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.check(leadership_or_event_coordinator_check)
    @app_commands.describe(item_id="ID of the item to remove")
    async def remove_shop_item_cmd(interaction: Interaction, item_id: int):
        await interaction.response.defer()
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get item info first
                cursor.execute("SELECT * FROM shop_items WHERE id = ?", (item_id,))
                item = cursor.fetchone()
                
                if not item:
                    await interaction.followup.send("❌ Item not found.")
                    return
                
                # Deactivate item
                cursor.execute("UPDATE shop_items SET active = 0 WHERE id = ?", (item_id,))
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Shop Item Removed",
                    description=f"Successfully removed **{item['name']}** from the shop",
                    color=0xFF0000
                )
                
                await interaction.followup.send(embed=embed)
                logger.info(f"Shop item removed: {item['name']} by {interaction.user.display_name}")
                
        except Exception as e:
            logger.error(f"Error in remove_shop_item command: {e}")
            await interaction.followup.send("❌ An error occurred while removing the shop item.")
    
    @bot.tree.command(
        name="my_points",
        description="Check your current points balance",
        guild=discord.Object(id=GUILD_ID)
    )
    async def my_points_cmd(interaction: Interaction):
        await interaction.response.defer()
        
        try:
            # Get or create user
            user = db.get_or_create_user(
                interaction.user.id,
                interaction.user.name,
                interaction.user.display_name
            )
            
            embed = discord.Embed(
                title="💰 Your Points Balance",
                description=f"{interaction.user.mention}",
                color=0xFFD700
            )
            embed.add_field(
                name="Total Points",
                value=f"**{user['total_points']}** points",
                inline=False
            )
            
            # Show recent transactions
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT amount, reason, created_at 
                       FROM point_transactions 
                       WHERE user_id = ? 
                       ORDER BY created_at DESC 
                       LIMIT 5""",
                    (interaction.user.id,)
                )
                transactions = cursor.fetchall()
                
                if transactions:
                    transaction_text = ""
                    for tx in transactions:
                        sign = "+" if tx['amount'] > 0 else ""
                        date = tx['created_at'][:10]
                        transaction_text += f"• {sign}{tx['amount']} pts - {tx['reason']} ({date})\n"
                    
                    embed.add_field(
                        name="Recent Activity",
                        value=transaction_text,
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Points checked by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error in my_points command: {e}")
            await interaction.followup.send("❌ An error occurred while checking your points.") 