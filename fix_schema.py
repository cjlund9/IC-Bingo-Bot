#!/usr/bin/env python3
"""
Fix database schema issues on Ubuntu server
"""

import sys
import os
import sqlite3

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_schema():
    """Fix database schema issues by adding missing columns"""
    print("🔧 Fixing database schema...")
    
    db_path = "leaderboard.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema of bingo_submissions table
        cursor.execute("PRAGMA table_info(bingo_submissions)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current bingo_submissions columns: {columns}")
        
        # Add missing columns if they don't exist
        if 'team_name' not in columns:
            print("Adding team_name column to bingo_submissions...")
            cursor.execute("ALTER TABLE bingo_submissions ADD COLUMN team_name TEXT")
            print("✅ Added team_name column")
        
        if 'team' in columns:
            print("Removing old 'team' column from bingo_submissions...")
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
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
                    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO bingo_submissions_new 
                (id, team_name, tile_id, user_id, drop_name, quantity, status, submitted_at, 
                 approved_at, approved_by, denied_at, denied_by, denial_reason, hold_at, hold_by, hold_reason)
                SELECT id, team, tile_id, user_id, drop_name, quantity, status, submitted_at,
                       approved_at, approved_by, denied_at, denied_by, denial_reason, hold_at, hold_by, hold_reason
                FROM bingo_submissions
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE bingo_submissions")
            cursor.execute("ALTER TABLE bingo_submissions_new RENAME TO bingo_submissions")
            print("✅ Recreated bingo_submissions table with correct schema")
        
        # Check bingo_team_progress table
        cursor.execute("PRAGMA table_info(bingo_team_progress)")
        progress_columns = [row[1] for row in cursor.fetchall()]
        print(f"Current bingo_team_progress columns: {progress_columns}")
        
        if 'team' in progress_columns and 'team_name' not in progress_columns:
            print("Fixing bingo_team_progress table...")
            cursor.execute("ALTER TABLE bingo_team_progress ADD COLUMN team_name TEXT")
            cursor.execute("UPDATE bingo_team_progress SET team_name = team")
            print("✅ Added team_name column to bingo_team_progress")
        
        # Recreate indexes
        print("Recreating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_team ON bingo_submissions(team_name)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_tile ON bingo_submissions(tile_id)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_user ON bingo_submissions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_status ON bingo_submissions(status)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_submissions_submitted ON bingo_submissions(submitted_at)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_team ON bingo_team_progress(team_name)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_tile ON bingo_team_progress(tile_id)",
            "CREATE INDEX IF NOT EXISTS idx_bingo_team_progress_complete ON bingo_team_progress(is_complete)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("✅ Recreated all indexes")
        
        # Commit changes
        conn.commit()
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(bingo_submissions)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"Final bingo_submissions columns: {final_columns}")
        
        print("✅ Database schema fix completed!")
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    fix_schema() 