#!/usr/bin/env python3
"""
Script to fix database tile names and drops_needed values to match tiles.json
"""

import json
import sqlite3

def fix_database_tiles():
    """Fix database tile names and drops_needed values"""
    
    # Load tiles from JSON
    with open('data/tiles.json', 'r') as f:
        json_tiles = json.load(f)
    
    # Connect to database
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    
    # Fix tile names and drops_needed values
    fixes = [
        (13, '3x Malediction Ward Pieces', 3),
        (23, '10x Metal Boots', 10),
        (28, '10x Steel Rings', 10),
        (52, 'Any Rev Weapon', 1)
    ]
    
    print("Fixing database tiles...")
    for tile_index, name, drops_needed in fixes:
        cursor.execute('UPDATE bingo_tiles SET name = ?, drops_needed = ? WHERE tile_index = ?', 
                      (name, drops_needed, tile_index))
        print(f'  Updated tile {tile_index}: {name} (drops_needed: {drops_needed})')
    
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    fix_database_tiles() 