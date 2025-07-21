#!/usr/bin/env python3
"""
Script to fix the bingo_submissions table schema to include approval status columns
"""

import sqlite3

def fix_submissions_schema():
    """Fix the bingo_submissions table schema"""
    
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    
    print("Fixing bingo_submissions table schema...")
    
    # Check if status column exists
    cursor.execute("PRAGMA table_info(bingo_submissions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'status' not in columns:
        print("Adding missing columns to bingo_submissions table...")
        
        # Add the missing columns
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN status TEXT NOT NULL DEFAULT "pending"')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN approved_at TIMESTAMP')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN approved_by INTEGER')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN denied_at TIMESTAMP')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN denied_by INTEGER')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN denial_reason TEXT')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN hold_at TIMESTAMP')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN hold_by INTEGER')
        cursor.execute('ALTER TABLE bingo_submissions ADD COLUMN hold_reason TEXT')
        
        # Add foreign key constraints
        cursor.execute('''
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
        ''')
        
        # Copy data from old table to new table
        cursor.execute('''
            INSERT INTO bingo_submissions_new 
            (id, team_name, tile_id, user_id, drop_name, quantity, submitted_at)
            SELECT id, team_name, tile_id, user_id, drop_name, quantity, submitted_at
            FROM bingo_submissions
        ''')
        
        # Drop old table and rename new table
        cursor.execute('DROP TABLE bingo_submissions')
        cursor.execute('ALTER TABLE bingo_submissions_new RENAME TO bingo_submissions')
        
        # Recreate indexes
        cursor.execute('CREATE INDEX idx_bingo_submissions_team ON bingo_submissions(team_name)')
        cursor.execute('CREATE INDEX idx_bingo_submissions_tile ON bingo_submissions(tile_id)')
        cursor.execute('CREATE INDEX idx_bingo_submissions_user ON bingo_submissions(user_id)')
        cursor.execute('CREATE INDEX idx_bingo_submissions_status ON bingo_submissions(status)')
        cursor.execute('CREATE INDEX idx_bingo_submissions_submitted ON bingo_submissions(submitted_at)')
        
        print("✅ Schema updated successfully!")
    else:
        print("✅ Schema already up to date!")
    
    # Show current schema
    cursor.execute("PRAGMA table_info(bingo_submissions)")
    columns = cursor.fetchall()
    print("\nCurrent bingo_submissions table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_submissions_schema() 