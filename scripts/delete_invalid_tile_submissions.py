import sqlite3

DB_FILE = 'leaderboard.db'

def delete_invalid_submissions():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM bingo_tiles')
    num_tiles = cursor.fetchone()[0]
    cursor.execute('DELETE FROM bingo_submissions WHERE tile_id >= ? OR tile_id < 0', (num_tiles,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    print(f'Deleted {deleted} invalid submissions.')

if __name__ == '__main__':
    delete_invalid_submissions() 