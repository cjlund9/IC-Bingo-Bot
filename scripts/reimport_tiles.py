import json
import sqlite3

TILES_JSON = 'data/tiles.json'
DB_FILE = 'leaderboard.db'

def main():
    with open(TILES_JSON, 'r', encoding='utf-8') as f:
        tiles = json.load(f)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Clear existing tiles and drops
    c.execute('DELETE FROM bingo_tile_drops')
    c.execute('DELETE FROM bingo_tiles')
    conn.commit()
    # Insert tiles and drops
    for i, tile in enumerate(tiles):
        c.execute('INSERT INTO bingo_tiles (tile_index, name, drops_needed) VALUES (?, ?, ?)', (i, tile['name'], tile['drops_needed']))
        tile_id = c.lastrowid
        for drop in tile['drops_required']:
            c.execute('INSERT INTO bingo_tile_drops (tile_id, drop_name) VALUES (?, ?)', (tile_id, drop))
    conn.commit()
    conn.close()
    print(f"Imported {len(tiles)} tiles and their drops.")

if __name__ == '__main__':
    main() 