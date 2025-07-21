#!/usr/bin/env python3
"""
Fix points-based tile configuration on server
Updates drops_needed targets and removes unique constraint for multiple submissions
"""

import sys
import os
import sqlite3

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_points_tiles():
    """Fix points-based tile configuration"""
    print("🔧 Fixing points-based tile configuration...")
    
    db_path = "leaderboard.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Fix 5000 Pieces of Eight tile (ID 85)
        print("Fixing 5000 Pieces of Eight tile...")
        cursor.execute("UPDATE bingo_tiles SET drops_needed = 5000 WHERE id = 85")
        print("✅ Updated 5000 Pieces of Eight to require 5000 points")
        
        # Fix Chugging Barrel tile (ID 94)
        print("Fixing Chugging Barrel tile...")
        cursor.execute("UPDATE bingo_tiles SET drops_needed = 18600 WHERE id = 94")
        print("✅ Updated Chugging Barrel to require 18600 points")
        
        # Fix submissions table to allow multiple submissions for points-based tiles
        print("Fixing submissions table schema...")
        
        # Check current schema
        cursor.execute("PRAGMA table_info(bingo_submissions)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Check if unique constraint exists
        cursor.execute("PRAGMA index_list(bingo_submissions)")
        indexes = cursor.fetchall()
        has_unique_constraint = any('UNIQUE' in str(index) for index in indexes)
        
        if has_unique_constraint:
            print("Removing unique constraint from submissions table...")
            
            # Create new table without unique constraint
            cursor.execute("""
                CREATE TABLE bingo_submissions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT NOT NULL,
                    tile_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    drop_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id)
                )
            """)
            
            # Copy data
            cursor.execute("INSERT INTO bingo_submissions_new SELECT * FROM bingo_submissions")
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE bingo_submissions")
            cursor.execute("ALTER TABLE bingo_submissions_new RENAME TO bingo_submissions")
            
            print("✅ Removed unique constraint from submissions table")
        else:
            print("✅ Submissions table already has correct schema")
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_team ON bingo_submissions(team_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_tile ON bingo_submissions(tile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_user ON bingo_submissions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_status ON bingo_submissions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bingo_submissions_submitted ON bingo_submissions(submitted_at)")
        
        print("✅ Created indexes")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("✅ Points-based tile configuration fixed successfully!")
        
        # Verify the fixes
        print("\nVerifying fixes...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check 5000 Pieces of Eight
        cursor.execute("SELECT name, drops_needed FROM bingo_tiles WHERE id = 85")
        result = cursor.fetchone()
        print(f"5000 Pieces of Eight: {result[0]} - requires {result[1]} points")
        
        # Check Chugging Barrel
        cursor.execute("SELECT name, drops_needed FROM bingo_tiles WHERE id = 94")
        result = cursor.fetchone()
        print(f"Chugging Barrel: {result[0]} - requires {result[1]} points")
        
        # Check submissions table schema
        cursor.execute("PRAGMA table_info(bingo_submissions)")
        columns = cursor.fetchall()
        print(f"Submissions table columns: {[col[1] for col in columns]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error fixing points-based tiles: {e}")
        if 'conn' in locals():
            conn.close()
        return False
    
    return True

if __name__ == "__main__":
    fix_points_tiles() 