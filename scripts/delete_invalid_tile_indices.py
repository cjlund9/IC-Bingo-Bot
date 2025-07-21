import sqlite3
import json

# Load the current board placeholders
with open("data/tiles.json") as f:
    tiles = json.load(f)
num_tiles = len(tiles)

conn = sqlite3.connect("leaderboard.db")
cursor = conn.cursor()

cursor.execute("SELECT id, tile_id FROM bingo_submissions")
to_delete = []
for row in cursor.fetchall():
    submission_id, tile_index = row
    if not (0 <= tile_index < num_tiles):
        to_delete.append(submission_id)

if to_delete:
    print(f"Deleting {len(to_delete)} invalid submissions: {to_delete}")
    cursor.executemany("DELETE FROM bingo_submissions WHERE id = ?", [(sid,) for sid in to_delete])
    conn.commit()
    print("Done.")
else:
    print("No invalid submissions to delete.")

conn.close() 