#!/usr/bin/env python3
"""
Create a fresh bingo board with no completion data
"""

import os
import sys
from board import generate_board_image, load_placeholders

def main():
    print("🎯 Creating Fresh Bingo Board")
    print("=" * 40)
    
    try:
        # Load placeholders
        placeholders = load_placeholders()
        if not placeholders:
            print("❌ Failed to load placeholders")
            return False
            
        print(f"✅ Loaded {len(placeholders)} tiles")
        
        # Generate fresh board image
        success = generate_board_image(placeholders, None, team="all")
        
        if success:
            print("✅ Fresh board image generated successfully!")
            print("📁 Board saved as: board.png")
            return True
        else:
            print("❌ Failed to generate board image")
            return False
            
    except Exception as e:
        print(f"❌ Error creating fresh board: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 