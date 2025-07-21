import sqlite3
import json

# Load the current board placeholders
with open("data/tiles.json") as f:
    tiles = json.load(f)
num_tiles = len(tiles)

conn = sqlite3.connect("leaderboard.db")
cursor = conn.cursor()

cursor.execute("SELECT id, tile_id FROM bingo_submissions")
invalid = []
for row in cursor.fetchall():
    submission_id, tile_index = row
    if not (0 <= tile_index < num_tiles):
        invalid.append((submission_id, tile_index))

if invalid:
    print("Invalid tile indices found in submissions:")
    for sub_id, idx in invalid:
        print(f"Submission ID {sub_id}: tile_index={idx}")
else:
    print("No invalid tile indices found.")

conn.close() 