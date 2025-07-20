#!/usr/bin/env python3
"""
Fix database issues on Ubuntu server
"""

import sys
import os
import sqlite3
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_database():
    """Fix database issues by creating missing tables"""
    print("🔧 Fixing database issues...")
    
    db_path = "leaderboard.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")
        
        # Create bingo_tiles table if it doesn't exist
        if 'bingo_tiles' not in existing_tables:
            print("Creating bingo_tiles table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bingo_tiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tile_index INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    drops_needed INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tile_index)
                )
            """)
            print("✅ Created bingo_tiles table")
        
        # Create bingo_tile_drops table if it doesn't exist
        if 'bingo_tile_drops' not in existing_tables:
            print("Creating bingo_tile_drops table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bingo_tile_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tile_id INTEGER NOT NULL,
                    drop_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
                    UNIQUE(tile_id, drop_name)
                )
            """)
            print("✅ Created bingo_tile_drops table")
        
        # Create bingo_team_progress table if it doesn't exist
        if 'bingo_team_progress' not in existing_tables:
            print("Creating bingo_team_progress table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bingo_team_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT NOT NULL,
                    tile_id INTEGER NOT NULL,
                    total_required INTEGER NOT NULL,
                    completed_count INTEGER NOT NULL DEFAULT 0,
                    is_complete BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
                    UNIQUE(team_name, tile_id)
                )
            """)
            print("✅ Created bingo_team_progress table")
        
        # Create bingo_submissions table if it doesn't exist
        if 'bingo_submissions' not in existing_tables:
            print("Creating bingo_submissions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bingo_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT NOT NULL,
                    tile_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    drop_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by INTEGER,
                    denied_at TIMESTAMP,
                    denied_by INTEGER,
                    denial_reason TEXT,
                    hold_at TIMESTAMP,
                    hold_by INTEGER,
                    hold_reason TEXT,
                    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE
                )
            """)
            print("✅ Created bingo_submissions table")
        
        # Create board_release_config table if it doesn't exist
        if 'board_release_config' not in existing_tables:
            print("Creating board_release_config table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS board_release_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    release_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            print("✅ Created board_release_config table")
        
        # Create other required tables if they don't exist
        if 'wom_player_data' not in existing_tables:
            print("Creating wom_player_data table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wom_player_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rsn TEXT NOT NULL UNIQUE,
                    data TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Created wom_player_data table")
        
        if 'wom_sync_config' not in existing_tables:
            print("Creating wom_sync_config table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wom_sync_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rsns TEXT,
                    auto_sync_enabled BOOLEAN DEFAULT FALSE,
                    last_sync TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Created wom_sync_config table")
        
        # Create indexes
        print("Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_bingo_tiles_index ON bingo_tiles(tile_index)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_team ON bingo_team_progress(team_name)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_tile ON bingo_team_progress(tile_id)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_complete ON bingo_team_progress(is_complete)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_team ON bingo_submissions(team_name)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_tile ON bingo_submissions(tile_id)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_user ON bingo_submissions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_status ON bingo_submissions(status)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_submitted ON bingo_submissions(submitted_at)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_tile_drops_tile ON bingo_tile_drops(tile_id)",
            "CREATE INDEX IF NOT EXISTS idx_wom_player_data_rsn ON wom_player_data(rsn)",
            "CREATE INDEX IF NOT EXISTS idx_wom_player_data_updated ON wom_player_data(last_updated)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("✅ Created all indexes")
        
        # Commit changes
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        final_tables = [row[0] for row in cursor.fetchall()]
        print(f"Final tables: {final_tables}")
        
        # Check if tiles.json exists and sync it manually
        if os.path.exists('data/tiles.json'):
            print("Syncing tiles from tiles.json...")
            
            with open('data/tiles.json', 'r') as f:
                tiles_data = json.load(f)
            
            # Check if tiles already exist
            cursor.execute("SELECT COUNT(*) FROM bingo_tiles")
            existing_count = cursor.fetchone()[0]
            
            if existing_count == 0:
                # Clear existing tiles and drops first
                cursor.execute("DELETE FROM bingo_tile_drops")
                cursor.execute("DELETE FROM bingo_tiles")
                
                # Insert new tiles
                for tile_data in tiles_data:
                    tile_index = tiles_data.index(tile_data)
                    name = tile_data.get('name', f'Tile {tile_index}')
                    drops_needed = tile_data.get('drops_needed', 1)
                    
                    cursor.execute(
                        "INSERT INTO bingo_tiles (tile_index, name, drops_needed) VALUES (?, ?, ?)",
                        (tile_index, name, drops_needed)
                    )
                    tile_id = cursor.lastrowid
                    
                    # Insert drops
                    drops_required = tile_data.get('drops_required', [])
                    for drop in drops_required:
                        cursor.execute(
                            "INSERT INTO bingo_tile_drops (tile_id, drop_name) VALUES (?, ?)",
                            (tile_id, drop)
                        )
                
                conn.commit()
                print(f"✅ Synced {len(tiles_data)} tiles from tiles.json")
            else:
                print(f"⚠️  {existing_count} tiles already exist in database, skipping sync")
        else:
            print("⚠️  tiles.json not found, skipping tile sync")
        
        print("✅ Database fix completed!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    fix_database() 