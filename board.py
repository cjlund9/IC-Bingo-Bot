import os
import json
import textwrap
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOARD_SIZE = 10
TILE_SIZE = 80
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "runescape_uf.ttf")
FONT_SIZE = 12
OUTPUT_FILE = os.path.join(BASE_DIR, "board.png")
GENERATED_BOARD_PATH = os.path.join(BASE_DIR, "tiles.json")

COLOR_TILE = (70, 50, 20, 255)
COLOR_TEXT = (255, 255, 204, 255)
COLOR_TEXT_COMPLETED = (230, 230, 230, 255)
COLOR_COMPLETED_TILE = (0, 153, 76, 255)
COLOR_IN_PROGRESS_TILE = (255, 165, 0, 255)  # Orange
COLOR_TEXT_IN_PROGRESS = (255, 255, 255, 255)  # White

def load_placeholders():
    try:
        with open(GENERATED_BOARD_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load placeholders: {e}")
        return []

def generate_board_image(placeholders, completed_dict, team="all"):
    if placeholders is None:
        placeholders = load_placeholders()
    if completed_dict is None:
        completed_dict = {}

    img_width = BOARD_SIZE * TILE_SIZE
    img_height = BOARD_SIZE * TILE_SIZE
    image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception as e:
        print(f"❌ Failed to load font: {e}")
        font = ImageFont.load_default()

    # Track tile statuses
    tile_status = {}  # tile_index -> status: 'not_started', 'in_progress', 'complete'

    # Calculate drop progress
    drop_progress = completed_dict.get("drops", {})  # {team: {tile_index: [drops...]}}
    
    if team == "all":
        for team_drops in drop_progress.values():
            for tile_idx, drops in team_drops.items():
                tile_status[tile_idx] = tile_status.get(tile_idx, 0) + len(drops)
    else:
        for tile_idx, drops in drop_progress.get(team, {}).items():
            tile_status[tile_idx] = len(drops)

    for i, tile in enumerate(placeholders):
        tile_name = tile["name"] if isinstance(tile, dict) else tile
        required = tile.get("required", 1) if isinstance(tile, dict) else 1
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
        if required > 1:
            progress_text = f"{progress}/{required}"
            pt_width = draw.textlength(progress_text, font=font)
            draw.text((x + TILE_SIZE - pt_width - 4, y + TILE_SIZE - line_height), progress_text, font=font, fill=text_color)

    draw.rectangle([0, 0, img_width - 1, img_height - 1], outline=(200, 200, 200, 255), width=2)

    image.save(OUTPUT_FILE)
    print(f"✅ Board image saved to {OUTPUT_FILE}")
