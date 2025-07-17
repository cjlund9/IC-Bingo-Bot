import sqlite3

def check_tiles():
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    
    # Check total tiles
    cursor.execute('SELECT COUNT(*) FROM bingo_tiles')
    total = cursor.fetchone()[0]
    print(f"Total tiles in database: {total}")
    
    # Check tile indices
    cursor.execute('SELECT tile_index FROM bingo_tiles ORDER BY tile_index')
    indices = [row[0] for row in cursor.fetchall()]
    print(f"Tile indices: {indices[:10]}...")  # Show first 10   
    # Check if we have 0-99 tiles
    expected = list(range(100))
    missing = set(expected) - set(indices)
    if missing:
        print(f"Missing tile indices: {missing}")
    
    conn.close()

if __name__ == "__main__":
    check_tiles() 