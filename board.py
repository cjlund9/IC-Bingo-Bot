import os
import json
import textwrap
import logging
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOARD_SIZE = 10
TILE_SIZE = 80
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "runescape_uf.ttf")
FONT_SIZE = 12
OUTPUT_FILE = os.path.join(BASE_DIR, "board.png")
GENERATED_BOARD_PATH = os.path.join(BASE_DIR, "tiles.json")

COLOR_TILE = (70, 50, 20, 255)         # Original RuneScape brown
COLOR_TEXT = (255, 255, 204, 255)
COLOR_TEXT_COMPLETED = (230, 230, 230, 255)
COLOR_COMPLETED_TILE = (0, 153, 76, 255)
COLOR_IN_PROGRESS_TILE = (255, 224, 102, 255)  # Light yellow
COLOR_TEXT_IN_PROGRESS = (0, 0, 0, 255)  # Black text for better contrast

def load_placeholders() -> List[Dict[str, Any]]:
    """Load placeholders from JSON file with error handling"""
    try:
        if not os.path.exists(GENERATED_BOARD_PATH):
            logger.error(f"Board file not found: {GENERATED_BOARD_PATH}")
            return []
            
        with open(GENERATED_BOARD_PATH, "r", encoding="utf-8") as f:
            placeholders = json.load(f)
            logger.info(f"Loaded {len(placeholders)} placeholders from {GENERATED_BOARD_PATH}")
            return placeholders
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {GENERATED_BOARD_PATH}: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to load placeholders: {e}")
        return []

def validate_inputs(placeholders: List[Dict[str, Any]], completed_dict: Dict[str, Any], team: str) -> bool:
    """Validate input parameters"""
    if not placeholders:
        logger.error("No placeholders provided")
        return False
    
    if not isinstance(completed_dict, dict):
        logger.error("Completed dict must be a dictionary")
        return False
    
    if not team or not isinstance(team, str):
        logger.error("Team must be a non-empty string")
        return False
    
    return True

def get_font() -> ImageFont.FreeTypeFont:
    """Get font with fallback to default"""
    try:
        if os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
            logger.debug(f"Loaded custom font: {FONT_PATH}")
        else:
            logger.warning(f"Font file not found: {FONT_PATH}, using default")
            font = ImageFont.load_default()
    except Exception as e:
        logger.warning(f"Failed to load custom font: {e}, using default")
        font = ImageFont.load_default()
    return font

def calculate_tile_status(completed_dict: Dict[str, Any], team: str) -> Dict[int, int]:
    """Calculate tile status for the given team"""
    tile_status = {}
    
    try:
        if team == "all":
            # Sum up progress across all teams
            for team_name, team_data in completed_dict.items():
                if isinstance(team_data, dict):
                    for tile_idx, tile_data in team_data.items():
                        if isinstance(tile_data, dict) and "completed_count" in tile_data:
                            tile_status[int(tile_idx)] = tile_status.get(int(tile_idx), 0) + tile_data["completed_count"]
        else:
            # Get progress for specific team
            team_data = completed_dict.get(team, {})
            if isinstance(team_data, dict):
                for tile_idx, tile_data in team_data.items():
                    if isinstance(tile_data, dict) and "completed_count" in tile_data:
                        tile_status[int(tile_idx)] = tile_data["completed_count"]
                
    except Exception as e:
        logger.error(f"Error calculating tile status: {e}")
    
    return tile_status

def generate_board_image(placeholders: Optional[List[Dict[str, Any]]] = None, 
                        completed_dict: Optional[Dict[str, Any]] = None, 
                        team: str = "all") -> bool:
    """
    Generate bingo board image
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load defaults if not provided
        if placeholders is None:
            placeholders = load_placeholders()
        if completed_dict is None:
            completed_dict = {}

        # Validate inputs
        if not validate_inputs(placeholders, completed_dict, team):
            return False

        # Create image
        img_width = BOARD_SIZE * TILE_SIZE
        img_height = BOARD_SIZE * TILE_SIZE
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Get font
        font = get_font()

        # Calculate tile statuses
        tile_status = calculate_tile_status(completed_dict, team)

        # Draw tiles
        for i, tile in enumerate(placeholders):
            if i >= BOARD_SIZE * BOARD_SIZE:
                logger.warning(f"Tile index {i} exceeds board size, skipping")
                continue
                
            tile_name = tile["name"] if isinstance(tile, dict) else str(tile)
            required = tile.get("drops_needed", 1) if isinstance(tile, dict) else 1
            progress = tile_status.get(i, 0)

            row = i // BOARD_SIZE
            col = i % BOARD_SIZE
            x = col * TILE_SIZE
            y = row * TILE_SIZE

            # Determine visual status
            if progress >= required:
                tile_color = COLOR_COMPLETED_TILE
                text_color = COLOR_TEXT_COMPLETED
            elif progress > 0:
                tile_color = COLOR_IN_PROGRESS_TILE
                text_color = COLOR_TEXT_IN_PROGRESS
            else:
                tile_color = COLOR_TILE
                text_color = COLOR_TEXT

            # Draw tile background
            draw.rectangle(
                [x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1],
                fill=tile_color,
                outline=(0, 0, 0, 255)
            )

            # Add tile text (wrapped)
            max_chars_per_line = 12
            wrapped = textwrap.wrap(tile_name, width=max_chars_per_line)
            line_height = (font.getbbox("A")[3] - font.getbbox("A")[1]) + 4
            total_text_height = len(wrapped) * line_height
            text_y = y + (TILE_SIZE - total_text_height) / 2

            for line in wrapped:
                text_width = draw.textlength(line, font=font)
                text_x = x + (TILE_SIZE - text_width) / 2
                draw.text((text_x, text_y), line, font=font, fill=text_color)
                text_y += line_height

            # Draw progress indicator (e.g., "1/3") if needed
            if required > 1 or progress > 0:
                progress_text = f"{progress}/{required}"
                pt_width = draw.textlength(progress_text, font=font)
                draw.text((x + TILE_SIZE - pt_width - 4, y + TILE_SIZE - line_height), 
                         progress_text, font=font, fill=text_color)

        # Draw board border
        draw.rectangle([0, 0, img_width - 1, img_height - 1], 
                      outline=(200, 200, 200, 255), width=2)

        # Save image with timestamp to prevent caching
        import time
        timestamp = int(time.time())
        temp_filename = f"board_{team}_{timestamp}.png"
        image.save(temp_filename)
        
        # Copy to main output file
        import shutil
        shutil.copy2(temp_filename, OUTPUT_FILE)
        
        # Clean up temp file
        try:
            os.remove(temp_filename)
        except:
            pass
            
        logger.info(f"✅ Board image saved to {OUTPUT_FILE} for team: {team}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating board image: {e}")
        return False
