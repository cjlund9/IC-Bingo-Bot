import sqlite3

DB_FILE = 'leaderboard.db'

def rebuild_team_progress():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Clear the progress table
    cursor.execute('DELETE FROM bingo_team_progress')

    # Get all approved submissions
    cursor.execute('''
        SELECT team_name, tile_id, SUM(quantity) as total_approved
        FROM bingo_submissions
        WHERE status = 'approved'
        GROUP BY team_name, tile_id
    ''')
    progress_rows = cursor.fetchall()

    # For each (team, tile), get total_required from bingo_tiles
    for team_name, tile_id, completed_count in progress_rows:
        cursor.execute('SELECT drops_needed FROM bingo_tiles WHERE id = ?', (tile_id,))
        row = cursor.fetchone()
        total_required = row[0] if row else 1
        cursor.execute('''
            INSERT INTO bingo_team_progress (team_name, tile_id, completed_count, total_required)
            VALUES (?, ?, ?, ?)
        ''', (team_name, tile_id, completed_count, total_required))

    conn.commit()
    conn.close()
    print('bingo_team_progress rebuilt from approved submissions.')

if __name__ == '__main__':
    rebuild_team_progress() 