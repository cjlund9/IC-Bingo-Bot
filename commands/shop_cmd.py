# Entire file commented out for minimal bingo bot
import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
from typing import Optional
from database import DatabaseManager
from config import GUILD_ID, ADMIN_ROLE, EVENT_COORDINATOR_ROLE
from utils.access import leadership_or_event_coordinator_check

logger = logging.getLogger(__name__)

def setup_shop_commands(bot: Bot):
    
    # @bot.tree.command(
    #     name="shop",
    #     description="Shop and points management",
    #     guild=discord.Object(id=GUILD_ID)
    # )
    @app_commands.describe(
        action="What you want to do",
        item_id="ID of the item (for buy/remove)",
        quantity="Quantity to purchase (for buy)",
        name="Item name (for add)",
        description="Item description (for add)",
        cost="Points cost (for add)",
        category="Item category (for add)",
        item_quantity="Available quantity, -1 for unlimited (for add)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View Shop", value="view"),
        app_commands.Choice(name="Buy Item", value="buy"),
        app_commands.Choice(name="Check Balance", value="balance"),
        app_commands.Choice(name="Add Item", value="add"),
        app_commands.Choice(name="Remove Item", value="remove")
    ])
    async def shop_cmd(interaction: Interaction, action: str, item_id: int = None, quantity: int = 1, 
                      name: str = None, description: str = None, cost: int = None, 
                      category: str = "General", item_quantity: int = -1):
        await interaction.response.defer()
        
        try:
            if action == "view":
                await shop_view(interaction)
            elif action == "buy":
                if item_id is None:
                    await interaction.followup.send("❌ Please specify an item ID to purchase.")
                    return
                await shop_buy(interaction, item_id, quantity)
            elif action == "balance":
                await shop_balance(interaction)
            elif action == "add":
                if not all([name, description, cost]):
                    await interaction.followup.send("❌ Please provide name, description, and cost for the item.")
                    return
                await shop_add(interaction, name, description, cost, category, item_quantity)
            elif action == "remove":
                if item_id is None:
                    await interaction.followup.send("❌ Please specify an item ID to remove.")
                    return
                await shop_remove(interaction, item_id)
            else:
                await interaction.followup.send("❌ Invalid action. Please choose view, buy, balance, add, or remove.")
                
        except Exception as e:
            logger.error(f"Error in shop command: {e}")
            await interaction.followup.send("❌ An error occurred while processing your request.")

async def shop_view(interaction: Interaction):
    """View the shop items"""
    try:
        # Get shop items
        db = DatabaseManager()
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
                category_text += f"• **{item['name']}** (ID: {item['id']}) - {item['cost']} pts{quantity_text}\n"
                if item['description']:
                    category_text += f"  *{item['description']}*\n"
            
            embed.add_field(
                name=f"📦 {category}",
                value=category_text,
                inline=False
            )
        
        embed.set_footer(text="Use /shop buy <item_id> to purchase items")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Shop viewed by {interaction.user.display_name}")
        
    except Exception as e:
        logger.error(f"Error in shop_view: {e}")
        await interaction.followup.send("❌ An error occurred while loading the shop.")

async def shop_buy(interaction: Interaction, item_id: int, quantity: int):
    """Purchase an item from the shop"""
    try:
        # Get or create user
        db = DatabaseManager()
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
        logger.error(f"Error in shop_buy: {e}")
        await interaction.followup.send("❌ An error occurred while processing your purchase.")

async def shop_balance(interaction: Interaction):
    """Check user's points balance"""
    try:
        # Get or create user
        db = DatabaseManager()
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
        logger.error(f"Error in shop_balance: {e}")
        await interaction.followup.send("❌ An error occurred while checking your points.")

async def shop_add(interaction: Interaction, name: str, description: str, cost: int, category: str, item_quantity: int):
    """Add a new item to the shop (admin only)"""
    # Check permissions
    if not leadership_or_event_coordinator_check(interaction):
        await interaction.followup.send("❌ You do not have permission to add shop items.")
        return
    
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO shop_items (name, description, cost, category, available_quantity)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, description, cost, category, item_quantity)
            )
            conn.commit()
            
            embed = discord.Embed(
                title="✅ Shop Item Added",
                description=f"Successfully added **{name}** to the shop",
                color=0x00FF00
            )
            embed.add_field(name="Cost", value=f"{cost} points", inline=True)
            embed.add_field(name="Category", value=category, inline=True)
            embed.add_field(name="Quantity", value="Unlimited" if item_quantity == -1 else str(item_quantity), inline=True)
            embed.add_field(name="Description", value=description, inline=False)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Shop item added: {name} by {interaction.user.display_name}")
            
    except Exception as e:
        logger.error(f"Error in shop_add: {e}")
        await interaction.followup.send("❌ An error occurred while adding the shop item.")

async def shop_remove(interaction: Interaction, item_id: int):
    """Remove an item from the shop (admin only)"""
    # Check permissions
    if not leadership_or_event_coordinator_check(interaction):
        await interaction.followup.send("❌ You do not have permission to remove shop items.")
        return
    
    try:
        db = DatabaseManager()
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
        logger.error(f"Error in shop_remove: {e}")
        await interaction.followup.send("❌ An error occurred while removing the shop item.") 