import json
from collections import Counter

TILES_JSON = 'data/tiles.json'

def find_duplicates():
    with open(TILES_JSON, 'r', encoding='utf-8') as f:
        tiles = json.load(f)
    names = [tile.get('name', f'Tile {i}') for i, tile in enumerate(tiles)]
    counts = Counter(names)
    duplicates = [name for name, count in counts.items() if count > 1]
    if duplicates:
        print("Duplicate tile names found:")
        for name in duplicates:
            print(f"  {name} (count: {counts[name]})")
    else:
        print("No duplicate tile names found.")

if __name__ == '__main__':
    find_duplicates() 