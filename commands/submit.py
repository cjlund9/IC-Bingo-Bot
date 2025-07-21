import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot
import logging
import time
import asyncio
import sqlite3
from utils.access import team_member_access_check
from utils.rate_limiter import rate_limit

import config
from storage import mark_tile_submission
from board import generate_board_image, OUTPUT_FILE
from utils import get_user_team
from views.approval import ApprovalView

logger = logging.getLogger(__name__)

# Autocomplete for tile selection
async def tile_autocomplete(interaction: Interaction, current: str):
    try:
        conn = sqlite3.connect('leaderboard.db')
        cursor = conn.cursor()
        
        # Check if bingo_tiles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bingo_tiles'")
        if not cursor.fetchone():
            conn.close()
            return [app_commands.Choice(name="⚠️ Database not initialized", value="invalid")]
        
        cursor.execute('SELECT tile_index, name FROM bingo_tiles ORDER BY tile_index')
        tiles = cursor.fetchall()
        conn.close()
        
        choices = []
        for tile_index, tile_name in tiles:
            # Calculate tile coordinates (A1, A2, etc.)
            row = tile_index // 10  # 10x10 board
            col = tile_index % 10
            row_letter = chr(65 + row)  # A=65, B=66, etc.
            col_number = col + 1  # 1-based column numbers
            tile_indicator = f"{row_letter}{col_number}"
            
            # Create display name with indicator
            display_name = f"{tile_indicator}: {tile_name}"
            
            # Check if current input matches either the indicator or the tile name
            if (current.lower() in display_name.lower() or 
                current.lower() in tile_indicator.lower() or 
                current.lower() in tile_name.lower()):
                choices.append(app_commands.Choice(name=display_name, value=str(tile_index)))
        
        return choices[:25]
    except Exception as e:
        logger.error(f"Error in tile autocomplete: {e}")
        return [app_commands.Choice(name="⚠️ Error loading tiles", value="invalid")]

# Autocomplete for drop item based on selected tile
async def item_autocomplete(interaction: Interaction, current: str):
    tile_value = None
    if interaction.data and "options" in interaction.data:
        for option in interaction.data["options"]:
            if option["name"] == "tile":
                tile_value = option.get("value")
                break

    try:
        if not tile_value or tile_value == "invalid":
            return [app_commands.Choice(name="⚠️ Select a tile first", value="invalid")]
        
        tile_index = int(tile_value)
        conn = sqlite3.connect('leaderboard.db')
        cursor = conn.cursor()
        
        # Check if bingo_tiles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bingo_tiles'")
        if not cursor.fetchone():
            conn.close()
            return [app_commands.Choice(name="⚠️ Database not initialized", value="invalid")]
        
        # Get tile info and drops from database
        cursor.execute('''
            SELECT bt.name, bt.drops_needed, btd.drop_name 
            FROM bingo_tiles bt 
            LEFT JOIN bingo_tile_drops btd ON bt.id = btd.tile_id 
            WHERE bt.tile_index = ?
        ''', (tile_index,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return [app_commands.Choice(name="⚠️ Invalid tile", value="invalid")]
        
        tile_name = rows[0][0]
        drops_needed = rows[0][1]
        drops = [row[2] for row in rows if row[2] is not None]  # Filter out None values
        
        # Check if this is a points-based tile
        if "points" in drops and drops_needed > 1:
            # For points-based tiles, show a special option that will trigger the modal
            if not current:
                return [
                    app_commands.Choice(
                        name="📝 Use Points Input Form (Recommended)", 
                        value="points_modal"
                    ),
                    app_commands.Choice(
                        name="💡 Or type points directly (e.g., 1500)", 
                        value="points_direct"
                    )
                ]
            elif current == "points_modal":
                return [
                    app_commands.Choice(
                        name="📝 Use Points Input Form (Recommended)", 
                        value="points_modal"
                    )
                ]
            elif current.isdigit():
                # If user typed a number directly, allow it
                points = int(current)
                return [
                    app_commands.Choice(
                        name=f"📝 Submit {points:,} points", 
                        value=str(points)
                    )
                ]
            else:
                return [
                    app_commands.Choice(
                        name="💡 Type points earned (e.g., 1500)", 
                        value="points_direct"
                    )
                ]
        
        # Check if this is the Chugging Barrel tile (special resin points)
        if tile_name == "Chugging Barrel":
            resin_options = [
                ("Mox resin", 17250),
                ("Aga resin", 14000), 
                ("Lye resin", 18600)
            ]
            
            choices = []
            for resin_name, points in resin_options:
                if current.lower() in resin_name.lower():
                    choices.append(app_commands.Choice(
                        name=f"{resin_name} ({points:,} points)", 
                        value=f"{resin_name}:{points}"
                    ))
            
            # Also allow quantity input like "1000 Lye resin"
            if current and any(resin.lower() in current.lower() for resin, _ in resin_options):
                # Check if user is typing a quantity
                parts = current.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    quantity = int(parts[0])
                    resin_name = " ".join(parts[1:])
                    for resin, points in resin_options:
                        if resin.lower() in resin_name.lower():
                            choices.append(app_commands.Choice(
                                name=f"{quantity:,} {resin}", 
                                value=f"{resin}:{quantity}"
                            ))
                            break
            
            return choices[:25]
        
        # For regular tiles, show available drops
        choices = []
        for drop in drops:
            if current.lower() in drop.lower():
                choices.append(app_commands.Choice(name=drop, value=drop))
        
        return choices[:25]
        
    except (TypeError, ValueError) as e:
        return [app_commands.Choice(name="⚠️ Select a tile first", value="invalid")]
    except Exception as e:
        logger.error(f"Error in item autocomplete: {e}")
        return [app_commands.Choice(name="⚠️ Error loading drops", value="invalid")]


def setup_submit_command(bot: Bot):
    @bot.tree.command(
        name="submit",
        description="Submit a completed bingo tile with screenshot",
        guild=discord.Object(id=config.GUILD_ID)
    )
    @app_commands.check(team_member_access_check)
    @app_commands.describe(
        tile="Select the tile you completed",
        item="Which item did you get?",
        attachment="Upload screenshot"
    )
    @app_commands.autocomplete(tile=tile_autocomplete, item=item_autocomplete)
    @rate_limit(cooldown_seconds=5.0, max_requests_per_hour=50)  # Rate limit submissions
    async def submit(interaction: Interaction, tile: str, item: str, attachment: discord.Attachment = None):
        start_time = time.time()
        member = interaction.user

        try:
            # ✅ Defer immediately to avoid "Unknown Interaction" errors
            await interaction.response.defer(ephemeral=True)

            # All submissions require a screenshot
            if not attachment:
                await interaction.followup.send("❌ You must upload a screenshot for all submissions.", ephemeral=True)
                return

            # Validate file size (max 25MB) if attachment is provided
            if attachment and attachment.size > 25 * 1024 * 1024:
                await interaction.followup.send("❌ File too large. Please upload a smaller screenshot (max 25MB).", ephemeral=True)
                return

            try:
                tile_index = int(tile)
                # Get tile data from database
                conn = sqlite3.connect('leaderboard.db')
                cursor = conn.cursor()
                cursor.execute('SELECT id, name FROM bingo_tiles WHERE tile_index = ?', (tile_index,))
                tile_row = cursor.fetchone()
                conn.close()
                
                if not tile_row:
                    await interaction.followup.send("❌ Invalid tile selection.", ephemeral=True)
                    return
                
                tile_id, tile_name = tile_row
            except (ValueError, IndexError):
                await interaction.followup.send("❌ Invalid tile selection.", ephemeral=True)
                return

            team = get_user_team(member)

            # Check if this is a points-based tile that needs points input
            is_points_tile = False
            target_points = 0
            
            # Check if the tile is points-based
            conn = sqlite3.connect('leaderboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bt.drops_needed, btd.drop_name 
                FROM bingo_tiles bt 
                LEFT JOIN bingo_tile_drops btd ON bt.id = btd.tile_id 
                WHERE bt.tile_index = ?
            ''', (tile_index,))
            
            rows = cursor.fetchall()
            conn.close()
            
            drops_needed = rows[0][0] if rows else 1
            drops = [row[1] for row in rows if row[1] is not None]
            
            if "points" in drops and drops_needed > 1:
                is_points_tile = True
                target_points = drops_needed

            # Check if this is a points-based submission
            is_points_submission = False
            points_value = 0
            
            # Check if the tile is points-based and the item is numeric
            conn = sqlite3.connect('leaderboard.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bt.drops_needed, btd.drop_name 
                FROM bingo_tiles bt 
                LEFT JOIN bingo_tile_drops btd ON bt.id = btd.tile_id 
                WHERE bt.tile_index = ?
            ''', (tile_index,))
            
            rows = cursor.fetchall()
            conn.close()
            
            drops_needed = rows[0][0] if rows else 1
            drops = [row[1] for row in rows if row[1] is not None]
            
            if "points" in drops and drops_needed > 1 and item.isdigit():
                is_points_submission = True
                points_value = int(item)
                if points_value <= 0:
                    await interaction.followup.send("❌ Points must be greater than 0.", ephemeral=True)
                    return
            
            # Check if this is a resin submission for Chugging Barrel
            if tile_name == "Chugging Barrel" and ":" in item:
                try:
                    resin_name, value_str = item.split(":", 1)
                    if value_str.isdigit():
                        # This is a quantity submission (e.g., "Lye resin:1000")
                        quantity = int(value_str)
                        points_value = quantity  # Store the quantity, not points
                        is_points_submission = True
                        item = resin_name  # Use the resin name for display
                    else:
                        # This is a points submission (legacy format)
                        points_value = int(value_str)
                        is_points_submission = True
                        item = resin_name
                except (ValueError, IndexError):
                    await interaction.followup.send("❌ Invalid resin submission format.", ephemeral=True)
                    return

            review_channel = discord.utils.get(interaction.guild.text_channels, name=config.REVIEW_CHANNEL_NAME)
            if not review_channel:
                await interaction.followup.send(
                    f"❌ Review channel #{config.REVIEW_CHANNEL_NAME} not found.",
                    ephemeral=True
                )
                return

            # Convert attachment to file with timeout
            try:
                file = await asyncio.wait_for(attachment.to_file(), timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.followup.send("❌ Failed to process attachment. Please try again.", ephemeral=True)
                return

            # Create the submission in the database first
            conn = sqlite3.connect('leaderboard.db')
            cursor = conn.cursor()
            
            # For points-based tiles, create a placeholder submission that will be updated by the modal
            if is_points_tile:
                drop_name = "points_placeholder"
                quantity = 0  # Will be updated by modal
            elif is_points_submission:
                drop_name = "points" if tile_name != "Chugging Barrel" else item
                quantity = points_value
            else:
                drop_name = item
                quantity = 1
                
            cursor.execute('''
                INSERT INTO bingo_submissions (team_name, tile_id, user_id, drop_name, quantity, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (team, tile_id, member.id, drop_name, quantity))
            
            submission_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # For points-based tiles, show points input modal after submission
            if is_points_tile:
                from views.points_button import PointsTileButtonView
                
                embed = discord.Embed(
                    title="📝 Points Input Required",
                    description=f"**Tile:** {tile_name}\n**Target:** {target_points:,} points\n\nYour submission has been created. Please click the button below to enter your points.",
                    color=0x0099FF
                )
                
                view = PointsTileButtonView(tile_name, tile_id, target_points, submission_id)
                
                await interaction.followup.send(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
                return
            else:
                view = ApprovalView(member, tile_id, team, drop=item, submission_id=submission_id)

            # Create submission message
            if is_points_submission:
                if tile_name == "Chugging Barrel" and ":" in item:
                    # This was a resin submission, show both resin and points
                    submission_content = (
                        f"📥 Submission from {member.mention} for **{tile_name}** (Team: {team})\n"
                        f"Resin: **{item}** ({points_value:,} points)"
                    )
                else:
                    submission_content = (
                        f"📥 Submission from {member.mention} for **{tile_name}** (Team: {team})\n"
                        f"Points: **{points_value:,}**"
                    )
            else:
                submission_content = (
                    f"📥 Submission from {member.mention} for **{tile_name}** (Team: {team})\n"
                    f"Drop: **{item}**"
                )

            await review_channel.send(
                content=submission_content,
                file=file,
                view=view
            )

            await interaction.followup.send("✅ Submission sent for review!", ephemeral=True)
            
            # Log performance
            execution_time = time.time() - start_time
            logger.info(f"Submit command completed in {execution_time:.3f}s for user {member.id}")
        except Exception as e:
            logger.error(f"Error in submit command: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while processing your submission. Please try again.", ephemeral=True)
            except:
                pass  # Interaction might already be responded to
