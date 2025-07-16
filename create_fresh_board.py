#!/usr/bin/env python3
"""
Create a fresh bingo board with all tiles uncompleted
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from board import generate_board_image, load_placeholders
from storage import get_completed

def main():
    print("🎯 Creating fresh bingo board...")
    
    try:
        # Load tiles
        placeholders = load_placeholders()
        print(f"✅ Loaded {len(placeholders)} tiles")
        
        # Get completed data (should be empty)
        completed_dict = get_completed()
        print(f"✅ Loaded completed data: {len(completed_dict)} teams")
        
        # Generate fresh board image
        success = generate_board_image(placeholders, completed_dict, team="all")
        
        if success:
            print("✅ Fresh board created successfully!")
            print("📁 File: board.png")
        else:
            print("❌ Failed to create board")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 