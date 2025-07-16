import sqlite3
import shutil
import os
import json

DB_FILE = 'leaderboard.db'
BACKUP_FILE = f'leaderboard.db.backup'
TILES_JSON = 'data/tiles.json'


def backup_db():
    if os.path.exists(DB_FILE):
        shutil.copy(DB_FILE, f'{BACKUP_FILE}')
        print(f"Database backed up to {BACKUP_FILE}")
    else:
        print("No database file found to backup.")

def table_exists(conn, table_name):
    c = conn.cursor()
    c.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name=?
    """, (table_name,))
    return c.fetchone() is not None

def column_exists(conn, table_name, column_name):
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in c.fetchall()]
    return column_name in columns

def add_tile_index_column(conn):
    print("Adding missing 'tile_index' column to bingo_tiles ...")
    c = conn.cursor()
    c.execute("ALTER TABLE bingo_tiles ADD COLUMN tile_index INTEGER;")
    conn.commit()
    print("'tile_index' column added.")

def recreate_bingo_tile_drops(conn):
    print("Recreating missing table: bingo_tile_drops ...")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bingo_tile_drops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tile_id INTEGER NOT NULL,
            drop_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
            UNIQUE(tile_id, drop_name)
        )
    ''')
    conn.commit()
    print("bingo_tile_drops table created.")

def recreate_bingo_tables(conn):
    print("Dropping and recreating bingo_tiles and bingo_tile_drops tables ...")
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS bingo_tile_drops;")
    c.execute("DROP TABLE IF EXISTS bingo_tiles;")
    c.execute('''
        CREATE TABLE IF NOT EXISTS bingo_tiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tile_index INTEGER NOT NULL,
            name TEXT NOT NULL,
            drops_needed INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tile_index),
            UNIQUE(name)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bingo_tile_drops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tile_id INTEGER NOT NULL,
            drop_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
            UNIQUE(tile_id, drop_name)
        )
    ''')
    conn.commit()
    print("bingo_tiles and bingo_tile_drops tables recreated.")

def remove_duplicates():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Remove duplicate bingo_tiles by name (keep first occurrence)
    if table_exists(conn, 'bingo_tiles'):
        c.execute('''DELETE FROM bingo_tiles WHERE rowid NOT IN (SELECT MIN(rowid) FROM bingo_tiles GROUP BY name)''')
        print(f"Removed duplicate rows from bingo_tiles.")
    else:
        print("Table bingo_tiles does not exist. Skipping.")
    # Remove duplicate bingo_tile_drops by (tile_id, drop_name)
    if not table_exists(conn, 'bingo_tile_drops'):
        recreate_bingo_tile_drops(conn)
    if table_exists(conn, 'bingo_tile_drops'):
        c.execute('''DELETE FROM bingo_tile_drops WHERE rowid NOT IN (SELECT MIN(rowid) FROM bingo_tile_drops GROUP BY tile_id, drop_name)''')
        print(f"Removed duplicate rows from bingo_tile_drops.")
    else:
        print("Table bingo_tile_drops does not exist and could not be created. Skipping.")
    conn.commit()
    conn.close()

def reimport_tiles():
    if not os.path.exists(TILES_JSON):
        print(f"tiles.json not found at {TILES_JSON}")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Drop and recreate tables for a clean slate
    recreate_bingo_tables(conn)
    # Insert new tiles
    with open(TILES_JSON, 'r', encoding='utf-8') as f:
        tiles_data = json.load(f)
    for tile_index, tile_data in enumerate(tiles_data):
        name = tile_data.get('name', f'Tile {tile_index}')
        drops_needed = tile_data.get('drops_needed', 1)
        c.execute(
            "INSERT INTO bingo_tiles (tile_index, name, drops_needed) VALUES (?, ?, ?)",
            (tile_index, name, drops_needed)
        )
        tile_id = c.lastrowid
        drops_required = tile_data.get('drops_required', [])
        for drop in drops_required:
            c.execute(
                "INSERT INTO bingo_tile_drops (tile_id, drop_name) VALUES (?, ?)",
                (tile_id, drop)
            )
    conn.commit()
    conn.close()
    print(f"Re-imported tiles from {TILES_JSON}.")

def vacuum_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("VACUUM;")
    conn.close()
    print("Database vacuumed.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clean up bingo database duplicates and optionally re-import tiles.")
    parser.add_argument('--reimport', action='store_true', help='Re-import tiles from tiles.json after cleaning')
    args = parser.parse_args()

    backup_db()
    remove_duplicates()
    if args.reimport:
        reimport_tiles()
    vacuum_db()
    print("Cleanup complete.")

if __name__ == '__main__':
    main() 