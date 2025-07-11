import json
import os
from config import COMPLETED_FILE, DEFAULT_TEAM

# Structure: completed_dict = {team: [tile_indices]}
COMPLETED_FILE = "completed.json"

if os.path.exists(COMPLETED_FILE):
    with open(COMPLETED_FILE, "r", encoding="utf-8") as f:
        completed_dict = json.load(f)
else:
    completed_dict = {}

def save_completed():
    with open(COMPLETED_FILE, "w", encoding="utf-8") as f:
        json.dump(completed_dict, f, indent=2)

def get_completed():
    return completed_dict

def mark_tile_complete(team: str, tile_index: int):
    if team not in completed_dict:
        completed_dict[team] = []
    if tile_index not in completed_dict[team]:
        completed_dict[team].append(tile_index)
        save_completed()
