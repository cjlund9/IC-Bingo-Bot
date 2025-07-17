"""
Storage module for managing bingo game progress data
Handles data persistence, caching, and validation
"""

import sqlite3
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DB_FILE = 'leaderboard.db'

# --- DB Utility ---
def get_db_conn():
    return sqlite3.connect(DB_FILE)

# --- Progress Functions ---
def get_tile_progress(team: str, tile_index: int) -> Dict[str, Any]:
    """Get progress for a specific tile and team from the database."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        # Get tile info
        cursor.execute('SELECT name, drops_needed FROM bingo_tiles WHERE id = ?', (tile_index,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {}
        tile_name, total_required = row
        
        # Get drops required from bingo_tile_drops table
        cursor.execute('SELECT drop_name FROM bingo_tile_drops WHERE tile_id = ?', (tile_index,))
        drops_required = [row[0] for row in cursor.fetchall()]
        
        # Get progress
        cursor.execute('''SELECT completed_count, total_required FROM bingo_team_progress WHERE team = ? AND tile_id = ?''', (team, tile_index))
        progress_row = cursor.fetchone()
        completed_count = progress_row[0] if progress_row else 0
        total_required = progress_row[1] if progress_row else total_required
        # Get submissions
        cursor.execute('''SELECT user_id, drop_name, quantity FROM bingo_submissions WHERE team = ? AND tile_id = ?''', (team, tile_index))
        submissions = [
            {"user_id": r[0], "drop": r[1], "quantity": r[2]} for r in cursor.fetchall()
        ]
        # Calculate progress
        is_complete = completed_count >= total_required
        missing_drops = []  # Optionally implement
        progress_percentage = min(100, (completed_count / total_required) * 100) if total_required > 0 else 0
        conn.close()
        return {
            "tile_name": tile_name,
            "total_required": total_required,
            "completed_count": completed_count,
            "submissions": submissions,
            "progress_percentage": progress_percentage,
            "is_complete": is_complete,
            "missing_drops": missing_drops,
            "drops_required": drops_required
        }
    except Exception as e:
        logger.error(f"Error getting tile progress: {e}")
        return {}

def get_team_progress(team: str) -> Dict[str, Any]:
    """Get overall progress for a team from the database."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        # Get all tiles
        cursor.execute('SELECT id FROM bingo_tiles')
        tile_ids = [row[0] for row in cursor.fetchall()]
        total_tiles = len(tile_ids)
        completed_tiles = 0
        in_progress_tiles = 0
        tile_progress = {}
        for tile_id in tile_ids:
            progress = get_tile_progress(team, tile_id)
            tile_progress[str(tile_id)] = progress
            if progress.get("is_complete", False):
                completed_tiles += 1
            elif progress.get("completed_count", 0) > 0:
                in_progress_tiles += 1
        not_started_tiles = total_tiles - completed_tiles - in_progress_tiles
        completion_percentage = (completed_tiles / total_tiles * 100) if total_tiles > 0 else 0
        conn.close()
        return {
            "total_tiles": total_tiles,
            "completed_tiles": completed_tiles,
            "in_progress_tiles": in_progress_tiles,
            "not_started_tiles": not_started_tiles,
            "completion_percentage": completion_percentage,
            "tile_progress": tile_progress
        }
    except Exception as e:
        logger.error(f"Error getting team progress: {e}")
        return {}

def mark_tile_submission(team: str, tile_index: int, user_id: int, drop: str, quantity: int = 1) -> bool:
    """Record a submission for a given team, tile, user, drop, and quantity in the database."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        # Insert submission
        cursor.execute('''INSERT INTO bingo_submissions (team, tile_id, user_id, drop_name, quantity) VALUES (?, ?, ?, ?, ?)''', (team, tile_index, user_id, drop, quantity))
        # Update team progress
        cursor.execute('''SELECT completed_count FROM bingo_team_progress WHERE team = ? AND tile_id = ?''', (team, tile_index))
        row = cursor.fetchone()
        if row:
            new_count = row[0] + quantity
            cursor.execute('''UPDATE bingo_team_progress SET completed_count = ? WHERE team = ? AND tile_id = ?''', (new_count, team, tile_index))
        else:
            # Get total_required from tiles
            cursor.execute('SELECT drops_needed FROM bingo_tiles WHERE id = ?', (tile_index,))
            tr_row = cursor.fetchone()
            total_required = tr_row[0] if tr_row else 1
            cursor.execute('''INSERT INTO bingo_team_progress (team, tile_id, completed_count, total_required) VALUES (?, ?, ?, ?)''', (team, tile_index, quantity, total_required))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error marking tile submission: {e}")
        return False

def remove_tile_submission(team: str, tile_index: int, submission_index: int) -> bool:
    """Remove a submission by index for a given team and tile."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        # Get the submission id
        cursor.execute('''SELECT id FROM bingo_submissions WHERE team = ? AND tile_id = ? ORDER BY id LIMIT 1 OFFSET ?''', (team, tile_index, submission_index))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        submission_id = row[0]
        # Delete the submission
        cursor.execute('DELETE FROM bingo_submissions WHERE id = ?', (submission_id,))
        # Optionally update progress (not strictly necessary if recalculated)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error removing tile submission: {e}")
        return False
