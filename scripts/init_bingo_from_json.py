import sqlite3
import json
import os

DB_FILE = 'leaderboard.db'
TILES_JSON = 'data/tiles.json'
TEAMS = ['Moles', 'Obor']

def wipe_bingo_tables(conn):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bingo_team_progress;')
    cursor.execute('DELETE FROM bingo_submissions;')
    cursor.execute('DELETE FROM bingo_tile_drops;')
    cursor.execute('DELETE FROM bingo_tiles;')
    conn.commit()
    print('Wiped bingo tables.')

def import_tiles_and_drops(conn, tiles_json):
    with open(tiles_json, 'r', encoding='utf-8') as f:
        tiles = json.load(f)
    cursor = conn.cursor()
    for idx, tile in enumerate(tiles):
        name = tile['name']
        drops_needed = tile.get('drops_needed', 1)
        cursor.execute('INSERT INTO bingo_tiles (tile_index, name, drops_needed) VALUES (?, ?, ?)', (idx, name, drops_needed))
        tile_id = cursor.lastrowid
        for drop in tile.get('drops_required', []):
            cursor.execute('INSERT INTO bingo_tile_drops (tile_id, drop_name) VALUES (?, ?)', (tile_id, drop))
    conn.commit()
    print(f'Imported {len(tiles)} tiles and their drops.')

def init_team_progress(conn, teams):
    cursor = conn.cursor()
    cursor.execute('SELECT id, drops_needed FROM bingo_tiles ORDER BY tile_index')
    tiles = cursor.fetchall()
    for team in teams:
        for tile_id, drops_needed in tiles:
            cursor.execute('INSERT INTO bingo_team_progress (team_name, tile_id, total_required, completed_count, is_complete) VALUES (?, ?, ?, 0, 0)', (team, tile_id, drops_needed))
    conn.commit()
    print(f'Initialized progress for teams: {", ".join(teams)}')

def main():
    if not os.path.exists(TILES_JSON):
        print(f'Error: {TILES_JSON} not found.')
        return
    conn = sqlite3.connect(DB_FILE)
    try:
        wipe_bingo_tables(conn)
        import_tiles_and_drops(conn, TILES_JSON)
        init_team_progress(conn, TEAMS)
        print('Bingo database initialized successfully!')
    finally:
        conn.close()

if __name__ == '__main__':
    main() 