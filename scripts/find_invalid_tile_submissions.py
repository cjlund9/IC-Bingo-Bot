import sqlite3

DB_FILE = 'leaderboard.db'

def find_invalid_submissions():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM bingo_tiles')
    num_tiles = cursor.fetchone()[0]
    cursor.execute('SELECT id, team_name, tile_id, user_id, drop_name FROM bingo_submissions WHERE tile_id >= ? OR tile_id < 0', (num_tiles,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        print('No invalid submissions found.')
    else:
        print('Invalid submissions:')
        for row in rows:
            print(row)

if __name__ == '__main__':
    find_invalid_submissions() 