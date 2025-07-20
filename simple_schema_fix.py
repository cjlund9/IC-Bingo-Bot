#!/usr/bin/env python3
"""
Simple schema fix to add team_name column
"""

import sqlite3

def fix_schema():
    """Fix database schema by adding team_name column"""
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
        
        # Add team_name column if it doesn't exist
        if 'team_name' not in columns:
            print("Adding team_name column to bingo_submissions...")
            cursor.execute("ALTER TABLE bingo_submissions ADD COLUMN team_name TEXT")
            print("✅ Added team_name column")
            
            # Copy data from team to team_name
            cursor.execute("UPDATE bingo_submissions SET team_name = team")
            print("✅ Copied data from team to team_name")
        
        # Check bingo_team_progress table
        cursor.execute("PRAGMA table_info(bingo_team_progress)")
        progress_columns = [row[1] for row in cursor.fetchall()]
        print(f"Current bingo_team_progress columns: {progress_columns}")
        
        # Add team_name column if it doesn't exist
        if 'team_name' not in progress_columns:
            print("Adding team_name column to bingo_team_progress...")
            cursor.execute("ALTER TABLE bingo_team_progress ADD COLUMN team_name TEXT")
            print("✅ Added team_name column")
            
            # Copy data from team to team_name
            cursor.execute("UPDATE bingo_team_progress SET team_name = team")
            print("✅ Copied data from team to team_name")
        
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