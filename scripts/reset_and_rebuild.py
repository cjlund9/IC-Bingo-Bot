import os
import shutil
import sqlite3
import json

DB_FILE = 'leaderboard.db'
BACKUP_FILE = 'leaderboard.db.backup'
TILES_JSON = 'data/tiles.json'

def backup_db():
    if os.path.exists(DB_FILE):
        shutil.copy(DB_FILE, BACKUP_FILE)
        print(f"Database backed up to {BACKUP_FILE}")
    else:
        print("No database file found to backup.")

def clear_progress_and_submissions(conn):
    c = conn.cursor()
    c.execute('DELETE FROM bingo_team_progress')
    c.execute('DELETE FROM bingo_submissions')
    conn.commit()
    print("Cleared all progress and submissions.")

def reimport_tiles(conn):
    if not os.path.exists(TILES_JSON):
        print(f"tiles.json not found at {TILES_JSON}")
        return
    c = conn.cursor()
    # Clear existing tiles and drops
    c.execute('DELETE FROM bingo_tile_drops')
    c.execute('DELETE FROM bingo_tiles')
    conn.commit()
    # Insert tiles and drops
    with open(TILES_JSON, 'r', encoding='utf-8') as f:
        tiles = json.load(f)
    for i, tile in enumerate(tiles):
        c.execute('INSERT INTO bingo_tiles (tile_index, name, drops_needed) VALUES (?, ?, ?)', (i, tile['name'], tile['drops_needed']))
        tile_id = c.lastrowid
        for drop in tile['drops_required']:
            c.execute('INSERT INTO bingo_tile_drops (tile_id, drop_name) VALUES (?, ?)', (tile_id, drop))
    conn.commit()
    print(f"Imported {len(tiles)} tiles and their drops.")

def rebuild_team_progress(conn):
    c = conn.cursor()
    c.execute('DELETE FROM bingo_team_progress')
    # Get all approved submissions
    c.execute('''
        SELECT team_name, tile_id, SUM(quantity) as total_approved
        FROM bingo_submissions
        WHERE status = 'approved'
        GROUP BY team_name, tile_id
    ''')
    progress_rows = c.fetchall()
    # For each (team_name, tile), get total_required from bingo_tiles
    for team_name, tile_id, completed_count in progress_rows:
        c.execute('SELECT drops_needed FROM bingo_tiles WHERE id = ?', (tile_id,))
        row = c.fetchone()
        total_required = row[0] if row else 1
        c.execute('''
            INSERT INTO bingo_team_progress (team, tile_id, completed_count, total_required)
            VALUES (?, ?, ?, ?)
        ''', (team_name, tile_id, completed_count, total_required))
    conn.commit()
    print('bingo_team_progress rebuilt from approved submissions.')

def main():
    backup_db()
    conn = sqlite3.connect(DB_FILE)
    clear_progress_and_submissions(conn)
    reimport_tiles(conn)
    rebuild_team_progress(conn)
    conn.close()
    print("Reset and rebuild complete.")

if __name__ == '__main__':
    main() 