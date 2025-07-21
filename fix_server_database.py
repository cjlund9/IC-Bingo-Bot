#!/usr/bin/env python3
"""
Fix server database schema issues
Updates column names from 'team' to 'team_name' to match the correct schema
"""

import sys
import os
import sqlite3
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_server_database():
    """Fix server database schema by updating column names"""
    print("🔧 Fixing server database schema...")
    
    db_path = "leaderboard.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        print("Checking current schema...")
        
        # Check bingo_team_progress table schema
        cursor.execute("PRAGMA table_info(bingo_team_progress)")
        team_progress_columns = cursor.fetchall()
        print(f"bingo_team_progress columns: {[col[1] for col in team_progress_columns]}")
        
        # Check bingo_submissions table schema
        cursor.execute("PRAGMA table_info(bingo_submissions)")
        submissions_columns = cursor.fetchall()
        print(f"bingo_submissions columns: {[col[1] for col in submissions_columns]}")
        
        # Check if we need to fix bingo_team_progress table
        has_team_column = any(col[1] == 'team' for col in team_progress_columns)
        has_team_name_column = any(col[1] == 'team_name' for col in team_progress_columns)
        
        if has_team_column and not has_team_name_column:
            print("Fixing bingo_team_progress table...")
            
            # Create new table with correct schema
            cursor.execute("""
                CREATE TABLE bingo_team_progress_new (
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
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO bingo_team_progress_new (id, team_name, tile_id, total_required, completed_count, is_complete, created_at, updated_at)
                SELECT id, team, tile_id, total_required, completed_count, is_complete, created_at, updated_at
                FROM bingo_team_progress
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE bingo_team_progress")
            cursor.execute("ALTER TABLE bingo_team_progress_new RENAME TO bingo_team_progress")
            
            print("✅ Fixed bingo_team_progress table")
        
        # Check if we need to fix bingo_submissions table
        has_team_column = any(col[1] == 'team' for col in submissions_columns)
        has_team_name_column = any(col[1] == 'team_name' for col in submissions_columns)
        
        if has_team_column and not has_team_name_column:
            print("Fixing bingo_submissions table...")
            
            # Create new table with correct schema
            cursor.execute("""
                CREATE TABLE bingo_submissions_new (
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
                    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(discord_id),
                    FOREIGN KEY (approved_by) REFERENCES users(discord_id),
                    FOREIGN KEY (denied_by) REFERENCES users(discord_id),
                    FOREIGN KEY (hold_by) REFERENCES users(discord_id)
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO bingo_submissions_new (id, team_name, tile_id, user_id, drop_name, quantity, status, submitted_at, approved_at, approved_by, denied_at, denied_by, denial_reason, hold_at, hold_by, hold_reason)
                SELECT id, team, tile_id, user_id, drop_name, quantity, status, submitted_at, approved_at, approved_by, denied_at, denied_by, denial_reason, hold_at, hold_by, hold_reason
                FROM bingo_submissions
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE bingo_submissions")
            cursor.execute("ALTER TABLE bingo_submissions_new RENAME TO bingo_submissions")
            
            print("✅ Fixed bingo_submissions table")
        
        # Create indexes if they don't exist
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_team ON bingo_team_progress(team_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_tile ON bingo_team_progress(tile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_complete ON bingo_team_progress(is_complete)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_team ON bingo_submissions(team_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_tile ON bingo_submissions(tile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_user ON bingo_submissions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_status ON bingo_submissions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_submitted ON bingo_submissions(submitted_at)")
        
        print("✅ Created indexes")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("✅ Server database schema fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        if 'conn' in locals():
            conn.close()
        return False
    
    return True

if __name__ == "__main__":
    fix_server_database() 