import json
import os
import logging
import time
from typing import Dict, Any, Optional, List
from config import COMPLETED_FILE

# Memory optimization: cache for frequently accessed data
_cache = {}
_cache_timestamps = {}
_CACHE_TTL = 300  # 5 minutes cache TTL

logger = logging.getLogger(__name__)

# Initialize completed_dict
completed_dict: Dict[str, Any] = {}

def load_completed_data() -> Dict[str, Any]:
    """Load completed data from file with error handling"""
    global completed_dict
    try:
        if os.path.exists(COMPLETED_FILE):
            with open(COMPLETED_FILE, "r", encoding="utf-8") as f:
                completed_dict = json.load(f)
                logger.info(f"Loaded completed data from {COMPLETED_FILE}")
        else:
            completed_dict = {}
            logger.info(f"Created new completed data file: {COMPLETED_FILE}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {COMPLETED_FILE}: {e}")
        completed_dict = {}
    except Exception as e:
        logger.error(f"Error loading completed data: {e}")
        completed_dict = {}
    return completed_dict

def save_completed() -> bool:
    """Save completed data to file with error handling and cache invalidation"""
    try:
        # Create backup of existing file
        if os.path.exists(COMPLETED_FILE):
            backup_file = f"{COMPLETED_FILE}.backup"
            os.rename(COMPLETED_FILE, backup_file)
            logger.info(f"Created backup: {backup_file}")
        
        with open(COMPLETED_FILE, "w", encoding="utf-8") as f:
            json.dump(completed_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved completed data to {COMPLETED_FILE}")
        
        # Invalidate cache after save
        _cache.clear()
        _cache_timestamps.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error saving completed data: {e}")
        # Restore backup if save failed
        backup_file = f"{COMPLETED_FILE}.backup"
        if os.path.exists(backup_file):
            try:
                os.rename(backup_file, COMPLETED_FILE)
                logger.info("Restored backup after save failure")
            except Exception as restore_error:
                logger.error(f"Failed to restore backup: {restore_error}")
        return False

def get_completed() -> Dict[str, Any]:
    """Get completed data, loading if necessary with caching"""
    global completed_dict
    
    # Check cache first
    cache_key = "completed_data"
    current_time = time.time()
    
    if (cache_key in _cache and 
        cache_key in _cache_timestamps and 
        current_time - _cache_timestamps[cache_key] < _CACHE_TTL):
        return _cache[cache_key]
    
    # Load from memory or file
    if not completed_dict:
        load_completed_data()
    
    # Update cache
    _cache[cache_key] = completed_dict.copy()
    _cache_timestamps[cache_key] = current_time
    
    return completed_dict

def cleanup_cache():
    """Clean up expired cache entries to prevent memory leaks"""
    current_time = time.time()
    expired_keys = []
    
    for key, timestamp in _cache_timestamps.items():
        if current_time - timestamp > _CACHE_TTL:
            expired_keys.append(key)
    
    for key in expired_keys:
        if key in _cache:
            del _cache[key]
        if key in _cache_timestamps:
            del _cache_timestamps[key]
    
    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

def validate_team(team: str) -> bool:
    """Validate team name"""
    from config import TEAM_ROLES
    return team.lower() in {role.lower() for role in TEAM_ROLES}

def validate_tile_index(tile_index: int) -> bool:
    """Validate tile index"""
    try:
        from config import load_placeholders
        placeholders = load_placeholders()
        return 0 <= tile_index < len(placeholders)
    except Exception:
        return False

def sync_completed_data_with_tiles() -> Dict[str, Any]:
    """
    Sync completed.json data with current tiles.json values.
    Updates total_required to match drops_needed from tiles.json.
    
    Returns:
        Dict with sync results: {"updated_tiles": int, "errors": List[str]}
    """
    global completed_dict
    
    try:
        from config import load_placeholders
        placeholders = load_placeholders()
        
        if not placeholders:
            logger.error("No placeholders found, cannot sync data")
            return {"updated_tiles": 0, "errors": ["No placeholders found"]}
        
        sync_results = {"updated_tiles": 0, "errors": []}
        
        # Check each team's data
        for team_name, team_data in completed_dict.items():
            if not isinstance(team_data, dict):
                continue
                
            for tile_key, tile_data in team_data.items():
                try:
                    tile_index = int(tile_key)
                    
                    # Validate tile index
                    if tile_index >= len(placeholders):
                        sync_results["errors"].append(f"Invalid tile index {tile_index} for team {team_name}")
                        continue
                    
                    # Get current tile info
                    tile_info = placeholders[tile_index]
                    current_drops_needed = tile_info.get("drops_needed", 1)
                    
                    # Check if total_required needs updating
                    stored_total_required = tile_data.get("total_required", 1)
                    
                    if stored_total_required != current_drops_needed:
                        old_value = stored_total_required
                        tile_data["total_required"] = current_drops_needed
                        
                        # Adjust completed_count if it exceeds new total
                        completed_count = tile_data.get("completed_count", 0)
                        if completed_count > current_drops_needed:
                            tile_data["completed_count"] = current_drops_needed
                            logger.warning(f"Adjusted completed_count for team {team_name}, tile {tile_index}: {completed_count} -> {current_drops_needed}")
                        
                        sync_results["updated_tiles"] += 1
                        logger.info(f"Updated team {team_name}, tile {tile_index}: total_required {old_value} -> {current_drops_needed}")
                        
                except (ValueError, KeyError) as e:
                    sync_results["errors"].append(f"Error processing tile {tile_key} for team {team_name}: {e}")
        
        # Save updated data
        if sync_results["updated_tiles"] > 0:
            if save_completed():
                logger.info(f"Successfully synced {sync_results['updated_tiles']} tiles")
            else:
                sync_results["errors"].append("Failed to save synced data")
        
        return sync_results
        
    except Exception as e:
        logger.error(f"Error syncing completed data: {e}")
        return {"updated_tiles": 0, "errors": [str(e)]}

def get_tile_progress(team: str, tile_index: int) -> Dict[str, Any]:
    """
    Get detailed progress information for a specific tile and team
    
    Returns:
        Dict with progress information including:
        - total_required: Total drops needed
        - completed_count: Current progress
        - submissions: List of submissions
        - progress_percentage: Percentage complete
        - is_complete: Whether tile is fully completed
        - missing_drops: List of drops still needed
    """
    try:
        from config import load_placeholders
        placeholders = load_placeholders()
        
        if not validate_tile_index(tile_index):
            return {}
            
        tile_info = placeholders[tile_index]
        required_drops = tile_info.get("drops_required", [])
        total_required = tile_info.get("drops_needed", 1)
        
        # Get current progress
        team_data = completed_dict.get(team, {})
        tile_key = str(tile_index)
        tile_data = team_data.get(tile_key, {
            "total_required": total_required,
            "completed_count": 0,
            "submissions": []
        })
        
        # Ensure total_required matches current tiles.json
        if tile_data.get("total_required", 1) != total_required:
            tile_data["total_required"] = total_required
            # Adjust completed_count if needed
            completed_count = tile_data.get("completed_count", 0)
            if completed_count > total_required:
                tile_data["completed_count"] = total_required
        
        completed_count = tile_data.get("completed_count", 0)
        submissions = tile_data.get("submissions", [])
        
        # Calculate progress percentage
        progress_percentage = min(100, (completed_count / total_required) * 100) if total_required > 0 else 0
        
        # Determine missing drops
        submitted_drops = [sub["drop"] for sub in submissions]
        missing_drops = [drop for drop in required_drops if drop not in submitted_drops]
        
        return {
            "total_required": total_required,
            "completed_count": completed_count,
            "submissions": submissions,
            "progress_percentage": progress_percentage,
            "is_complete": completed_count >= total_required,
            "missing_drops": missing_drops,
            "tile_name": tile_info.get("name", f"Tile {tile_index}")
        }
        
    except Exception as e:
        logger.error(f"Error getting tile progress: {e}")
        return {}

def get_team_progress(team: str) -> Dict[str, Any]:
    """
    Get overall progress for a team
    
    Returns:
        Dict with team progress information
    """
    try:
        from config import load_placeholders
        placeholders = load_placeholders()
        
        team_data = completed_dict.get(team, {})
        total_tiles = len(placeholders)
        completed_tiles = 0
        in_progress_tiles = 0
        
        tile_progress = {}
        
        for i in range(total_tiles):
            progress = get_tile_progress(team, i)
            tile_progress[str(i)] = progress
            
            if progress.get("is_complete", False):
                completed_tiles += 1
            elif progress.get("completed_count", 0) > 0:
                in_progress_tiles += 1
        
        return {
            "total_tiles": total_tiles,
            "completed_tiles": completed_tiles,
            "in_progress_tiles": in_progress_tiles,
            "not_started_tiles": total_tiles - completed_tiles - in_progress_tiles,
            "completion_percentage": (completed_tiles / total_tiles * 100) if total_tiles > 0 else 0,
            "tile_progress": tile_progress
        }
        
    except Exception as e:
        logger.error(f"Error getting team progress: {e}")
        return {}

def mark_tile_submission(team: str, tile_index: int, user_id: int, drop: str, quantity: int = 1) -> bool:
    """
    Records a submission for a given team, tile, user, drop, and quantity.
    Handles partial completions and multiple users.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global completed_dict
    
    # Validate inputs
    if not validate_team(team):
        logger.error(f"Invalid team: {team}")
        return False
    
    if not validate_tile_index(tile_index):
        logger.error(f"Invalid tile index: {tile_index}")
        return False
    
    if quantity <= 0:
        logger.error(f"Invalid quantity: {quantity}")
        return False
    
    if not drop or not drop.strip():
        logger.error("Drop name cannot be empty")
        return False

    try:
        # Load placeholders to get required drops
        from config import load_placeholders
        placeholders = load_placeholders()
        
        team_data = completed_dict.setdefault(team, {})
        tile_key = str(tile_index)
        
        # Initialize tile if needed
        if tile_key not in team_data:
            tile_info = placeholders[tile_index]
            drops_needed = tile_info.get("drops_needed", 1)
            team_data[tile_key] = {
                "total_required": drops_needed,
                "completed_count": 0,
                "submissions": []
            }

        tile_data = team_data[tile_key]
        
        # Ensure total_required is current
        tile_info = placeholders[tile_index]
        current_drops_needed = tile_info.get("drops_needed", 1)
        if tile_data.get("total_required", 1) != current_drops_needed:
            tile_data["total_required"] = current_drops_needed
            logger.info(f"Updated total_required for team {team}, tile {tile_index}: {tile_data.get('total_required', 1)} -> {current_drops_needed}")

        # Update count without exceeding total required
        remaining = tile_data["total_required"] - tile_data["completed_count"]
        actual_quantity = min(quantity, remaining)
        tile_data["completed_count"] += actual_quantity

        # Log submission
        tile_data["submissions"].append({
            "user_id": str(user_id),
            "drop": drop.strip(),
            "quantity": actual_quantity
        })

        # Save to file
        if save_completed():
            logger.info(f"Marked submission: Team={team}, Tile={tile_index}, Drop={drop}, Quantity={actual_quantity}")
            return True
        else:
            logger.error("Failed to save submission")
            return False
            
    except Exception as e:
        logger.error(f"Error marking tile submission: {e}")
        return False

def remove_tile_submission(team: str, tile_index: int, submission_index: int) -> bool:
    """
    Remove a specific submission from a tile
    
    Returns:
        bool: True if successful, False otherwise
    """
    global completed_dict
    
    try:
        team_data = completed_dict.get(team, {})
        tile_key = str(tile_index)
        
        if tile_key not in team_data:
            logger.error(f"No tile data found for team {team}, tile {tile_index}")
            return False
            
        tile_data = team_data[tile_key]
        submissions = tile_data.get("submissions", [])
        
        if submission_index >= len(submissions):
            logger.error(f"Invalid submission index: {submission_index}")
            return False
            
        # Remove the submission and update count
        removed_submission = submissions.pop(submission_index)
        tile_data["completed_count"] = max(0, tile_data["completed_count"] - removed_submission["quantity"])
        
        # Save to file
        if save_completed():
            logger.info(f"Removed submission: Team={team}, Tile={tile_index}, Submission={submission_index}")
            return True
        else:
            logger.error("Failed to save after removing submission")
            return False
            
    except Exception as e:
        logger.error(f"Error removing tile submission: {e}")
        return False

# Initialize data on module load
load_completed_data()
