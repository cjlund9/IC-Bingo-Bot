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
def get_tile_by_name(tile_name: str) -> Optional[int]:
    """Get tile index by searching for tile name (case-insensitive partial match)."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        # Search for tile by name (case-insensitive, partial match)
        cursor.execute('SELECT id FROM bingo_tiles WHERE LOWER(name) LIKE LOWER(?)', (f'%{tile_name}%',))
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            # Return the first match
            return rows[0][0]
        return None
    except Exception as e:
        logger.error(f"Error searching for tile by name: {e}")
        return None

def get_tile_progress_by_name(team: str, tile_name: str) -> Dict[str, Any]:
    """Get progress for a specific tile by name and team from the database."""
    tile_index = get_tile_by_name(tile_name)
    if tile_index is None:
        return {}
    
    return get_tile_progress(team, tile_index)

def get_tile_progress(team: str, tile_index: int) -> Dict[str, Any]:
    """Get progress for a specific tile and team from the database."""
    try:
        conn = sqlite3.connect('leaderboard.db')
        cursor = conn.cursor()
        
        # Get tile name and team progress
        cursor.execute('''
            SELECT t.name, t.drops_needed, p.completed_count, p.total_required 
            FROM bingo_tiles t 
            LEFT JOIN bingo_team_progress p ON t.id = p.tile_id AND p.team_name = ?
            WHERE t.id = ?
        ''', (team, tile_index))
        tile_row = cursor.fetchone()
        
        # Get approved submissions only
        cursor.execute('''SELECT user_id, drop_name, quantity FROM bingo_submissions WHERE team_name = ? AND tile_id = ? AND status = 'approved' ''', (team, tile_index))
        submissions = cursor.fetchall()
        
        conn.close()
        
        if tile_row:
            tile_name, drops_needed, completed_count, total_required = tile_row
            completed_count = completed_count or 0
            total_required = total_required or drops_needed or 1
            
            # Calculate progress percentage and completion status
            progress_percentage = (completed_count / total_required * 100) if total_required > 0 else 0
            is_complete = completed_count >= total_required
            
            return {
                'tile_name': tile_name,
                'completed_count': completed_count,
                'total_required': total_required,
                'progress_percentage': progress_percentage,
                'is_complete': is_complete,
                'submissions': [
                    {
                        'user_id': sub[0],
                        'drop_name': sub[1],
                        'quantity': sub[2]
                    } for sub in submissions
                ]
            }
        else:
            return {
                'tile_name': f"Tile {tile_index}",
                'completed_count': 0,
                'total_required': 1,
                'progress_percentage': 0.0,
                'is_complete': False,
                'submissions': []
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
        
        # Check if this is a points-based tile
        cursor.execute('SELECT drops_needed FROM bingo_tiles WHERE id = ?', (tile_index,))
        tile_row = cursor.fetchone()
        if not tile_row:
            conn.close()
            return False
            
        # Insert submission
        cursor.execute('''INSERT INTO bingo_submissions (team_name, tile_id, user_id, drop_name, quantity) VALUES (?, ?, ?, ?, ?)''', (team, tile_index, user_id, drop, quantity))
        
        # Update team progress
        cursor.execute('''SELECT completed_count, total_required FROM bingo_team_progress WHERE team_name = ? AND tile_id = ?''', (team, tile_index))
        progress_row = cursor.fetchone()
        
        if progress_row:
            current_count = progress_row[0]
            total_required = progress_row[1]
            
            # For points-based tiles, add the quantity as points
            if drop == "points":
                new_count = current_count + quantity
            else:
                new_count = current_count + quantity
                
            cursor.execute('''UPDATE bingo_team_progress SET completed_count = ? WHERE team_name = ? AND tile_id = ?''', (new_count, team, tile_index))
        else:
            # Get total_required from tiles
            total_required = tile_row[0]
            cursor.execute('''INSERT INTO bingo_team_progress (team_name, tile_id, completed_count, total_required) VALUES (?, ?, ?, ?)''', (team, tile_index, quantity, total_required))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error marking tile submission: {e}")
        return False

def mark_points_submission(team: str, tile_index: int, user_id: int, points: int) -> bool:
    """Record a points submission for a points-based tile."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # Check if this is a points-based tile
        cursor.execute('SELECT drops_needed FROM bingo_tiles WHERE id = ?', (tile_index,))
        tile_row = cursor.fetchone()
        if not tile_row:
            conn.close()
            return False
            
        # Insert submission with "points" as the drop name
        cursor.execute('''INSERT INTO bingo_submissions (team_name, tile_id, user_id, drop_name, quantity) VALUES (?, ?, ?, ?, ?)''', (team, tile_index, user_id, "points", points))
        
        # Update team progress
        cursor.execute('''SELECT completed_count, total_required FROM bingo_team_progress WHERE team_name = ? AND tile_id = ?''', (team, tile_index))
        progress_row = cursor.fetchone()
        
        if progress_row:
            current_count = progress_row[0]
            total_required = progress_row[1]
            new_count = current_count + points
            cursor.execute('''UPDATE bingo_team_progress SET completed_count = ? WHERE team_name = ? AND tile_id = ?''', (new_count, team, tile_index))
        else:
            # Get total_required from tiles
            total_required = tile_row[0]
            cursor.execute('''INSERT INTO bingo_team_progress (team_name, tile_id, completed_count, total_required) VALUES (?, ?, ?, ?)''', (team, tile_index, points, total_required))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error marking points submission: {e}")
        return False

def remove_tile_submission(team: str, tile_index: int, submission_index: int) -> bool:
    """Remove a submission by index for a given team and tile."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        # Get the submission id
        cursor.execute('''SELECT id FROM bingo_submissions WHERE team_name = ? AND tile_id = ? ORDER BY id LIMIT 1 OFFSET ?''', (team, tile_index, submission_index))
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

def approve_submission(submission_id: int, approver_id: int) -> bool:
    """Approve an existing submission by updating its status."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # Get the submission details
        cursor.execute('''
            SELECT team_name, tile_id, user_id, drop_name, quantity 
            FROM bingo_submissions 
            WHERE id = ?
        ''', (submission_id,))
        submission = cursor.fetchone()
        
        if not submission:
            conn.close()
            return False
            
        team_name, tile_id, user_id, drop_name, quantity = submission
        
        # Update the submission status to approved
        cursor.execute('''
            UPDATE bingo_submissions 
            SET status = 'approved', approved_at = CURRENT_TIMESTAMP, approved_by = ?
            WHERE id = ?
        ''', (approver_id, submission_id))
        
        # Update team progress
        cursor.execute('''SELECT completed_count, total_required FROM bingo_team_progress WHERE team_name = ? AND tile_id = ?''', (team_name, tile_id))
        progress_row = cursor.fetchone()
        
        if progress_row:
            current_count = progress_row[0]
            total_required = progress_row[1]
            
            # For points-based tiles, add the quantity as points
            if drop_name == "points":
                new_count = current_count + quantity
            else:
                new_count = current_count + quantity
                
            cursor.execute('''UPDATE bingo_team_progress SET completed_count = ? WHERE team_name = ? AND tile_id = ?''', (new_count, team_name, tile_id))
        else:
            # Get total_required from tiles
            cursor.execute('SELECT drops_needed FROM bingo_tiles WHERE id = ?', (tile_id,))
            tile_row = cursor.fetchone()
            if tile_row:
                total_required = tile_row[0]
                cursor.execute('''INSERT INTO bingo_team_progress (team_name, tile_id, completed_count, total_required) VALUES (?, ?, ?, ?)''', (team_name, tile_id, quantity, total_required))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error approving submission: {e}")
        return False

def deny_submission(submission_id: int, denier_id: int, reason: str = None) -> bool:
    """Deny an existing submission by updating its status."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bingo_submissions 
            SET status = 'denied', denied_at = CURRENT_TIMESTAMP, denied_by = ?, denial_reason = ?
            WHERE id = ?
        ''', (denier_id, reason, submission_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error denying submission: {e}")
        return False

def hold_submission(submission_id: int, holder_id: int, reason: str = None) -> bool:
    """Put an existing submission on hold by updating its status."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bingo_submissions 
            SET status = 'hold', hold_at = CURRENT_TIMESTAMP, hold_by = ?, hold_reason = ?
            WHERE id = ?
        ''', (holder_id, reason, submission_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error holding submission: {e}")
        return False
