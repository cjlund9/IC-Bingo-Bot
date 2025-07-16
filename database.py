import sqlite3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "leaderboard.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with schema"""
        try:
            # Check if database already exists and has tables
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if cursor.fetchone():
                    logger.info("Database already exists, checking for bingo tables...")
                    # Check if bingo tables exist
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bingo_tiles'")
                    if not cursor.fetchone():
                        logger.info("Bingo tables not found, adding them...")
                        self._add_bingo_tables(conn)
                    return
            
            # Database doesn't exist, create it
            with open('database/database_schema.sql', 'r') as f:
                schema = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema)
                conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _add_bingo_tables(self, conn):
        """Add bingo tables to existing database"""
        try:
            bingo_schema = """
            -- Bingo tiles table - stores tile definitions
            CREATE TABLE bingo_tiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tile_index INTEGER NOT NULL, -- 0-99 for 10x10 board
                name TEXT NOT NULL,
                drops_needed INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tile_index)
            );

            -- Bingo tile drops table - stores required drops for each tile
            CREATE TABLE bingo_tile_drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tile_id INTEGER NOT NULL,
                drop_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
                UNIQUE(tile_id, drop_name)
            );

            -- Bingo team progress table - tracks team progress on tiles
            CREATE TABLE bingo_team_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                tile_id INTEGER NOT NULL,
                total_required INTEGER NOT NULL,
                completed_count INTEGER NOT NULL DEFAULT 0,
                is_complete BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
                UNIQUE(team_name, tile_id)
            );

            -- Bingo submissions table - stores individual drop submissions
            CREATE TABLE bingo_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                tile_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL, -- Discord user ID
                drop_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'denied', 'hold'
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by INTEGER, -- Discord user ID of approver
                denied_at TIMESTAMP,
                denied_by INTEGER, -- Discord user ID of denier
                denial_reason TEXT,
                hold_at TIMESTAMP,
                hold_by INTEGER, -- Discord user ID who put on hold
                hold_reason TEXT,
                FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(discord_id),
                FOREIGN KEY (approved_by) REFERENCES users(discord_id),
                FOREIGN KEY (denied_by) REFERENCES users(discord_id),
                FOREIGN KEY (hold_by) REFERENCES users(discord_id)
            );

            -- Bingo-specific indexes
            CREATE INDEX idx_bingo_tiles_index ON bingo_tiles(tile_index);
            CREATE INDEX idx_bingo_team_progress_team ON bingo_team_progress(team_name);
            CREATE INDEX idx_bingo_team_progress_tile ON bingo_team_progress(tile_id);
            CREATE INDEX idx_bingo_team_progress_complete ON bingo_team_progress(is_complete);
            CREATE INDEX idx_bingo_submissions_team ON bingo_submissions(team_name);
            CREATE INDEX idx_bingo_submissions_tile ON bingo_submissions(tile_id);
            CREATE INDEX idx_bingo_submissions_user ON bingo_submissions(user_id);
            CREATE INDEX idx_bingo_submissions_status ON bingo_submissions(status);
            CREATE INDEX idx_bingo_submissions_submitted ON bingo_submissions(submitted_at);
            CREATE INDEX idx_bingo_tile_drops_tile ON bingo_tile_drops(tile_id);
            """
            conn.executescript(bingo_schema)
            conn.commit()
            logger.info("Bingo tables added successfully")
        except Exception as e:
            logger.error(f"Error adding bingo tables: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    # ===== BINGO SYSTEM METHODS =====
    
    def sync_bingo_tiles_from_json(self, tiles_data: List[Dict]) -> bool:
        """Sync bingo tiles from tiles.json to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear existing tiles and drops
                cursor.execute("DELETE FROM bingo_tile_drops")
                cursor.execute("DELETE FROM bingo_tiles")
                
                # Insert new tiles
                for tile_data in tiles_data:
                    tile_index = tiles_data.index(tile_data)
                    name = tile_data.get('name', f'Tile {tile_index}')
                    drops_needed = tile_data.get('drops_needed', 1)
                    
                    cursor.execute(
                        "INSERT INTO bingo_tiles (tile_index, name, drops_needed) VALUES (?, ?, ?)",
                        (tile_index, name, drops_needed)
                    )
                    tile_id = cursor.lastrowid
                    
                    # Insert drops
                    drops_required = tile_data.get('drops_required', [])
                    for drop in drops_required:
                        cursor.execute(
                            "INSERT INTO bingo_tile_drops (tile_id, drop_name) VALUES (?, ?)",
                            (tile_id, drop)
                        )
                
                conn.commit()
                logger.info(f"Synced {len(tiles_data)} bingo tiles to database")
                return True
        except Exception as e:
            logger.error(f"Error syncing bingo tiles: {e}")
            return False
    
    def get_bingo_tiles(self) -> List[Dict]:
        """Get all bingo tiles with their drops"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT bt.*, GROUP_CONCAT(btd.drop_name) as drops_required
                    FROM bingo_tiles bt
                    LEFT JOIN bingo_tile_drops btd ON bt.id = btd.tile_id
                    GROUP BY bt.id
                    ORDER BY bt.tile_index
                """)
                tiles = []
                for row in cursor.fetchall():
                    tile = dict(row)
                    tile['drops_required'] = tile['drops_required'].split(',') if tile['drops_required'] else []
                    tiles.append(tile)
                return tiles
        except Exception as e:
            logger.error(f"Error getting bingo tiles: {e}")
            return []
    
    def get_team_progress(self, team_name: str) -> Dict[str, Any]:
        """Get team progress for all tiles"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT bt.tile_index, bt.name, btp.total_required, btp.completed_count, btp.is_complete
                    FROM bingo_tiles bt
                    LEFT JOIN bingo_team_progress btp ON bt.id = btp.tile_id AND btp.team_name = ?
                    ORDER BY bt.tile_index
                """, (team_name,))
                
                progress = {}
                for row in cursor.fetchall():
                    tile_index = row['tile_index']
                    progress[str(tile_index)] = {
                        'tile_name': row['name'],
                        'total_required': row['total_required'] or 1,
                        'completed_count': row['completed_count'] or 0,
                        'is_complete': bool(row['is_complete'])
                    }
                return progress
        except Exception as e:
            logger.error(f"Error getting team progress: {e}")
            return {}
    
    def get_tile_submissions(self, team_name: str, tile_index: int) -> List[Dict]:
        """Get all submissions for a specific tile and team"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT bs.*, u.username, u.display_name
                    FROM bingo_submissions bs
                    LEFT JOIN users u ON bs.user_id = u.discord_id
                    WHERE bs.team_name = ? AND bs.tile_id = (
                        SELECT id FROM bingo_tiles WHERE tile_index = ?
                    )
                    ORDER BY bs.submitted_at DESC
                """, (team_name, tile_index))
                
                submissions = []
                for row in cursor.fetchall():
                    submissions.append(dict(row))
                return submissions
        except Exception as e:
            logger.error(f"Error getting tile submissions: {e}")
            return []
    
    def add_bingo_submission(self, team_name: str, tile_index: int, user_id: int, 
                           drop_name: str, quantity: int = 1) -> bool:
        """Add a new bingo submission"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get tile ID
                cursor.execute("SELECT id FROM bingo_tiles WHERE tile_index = ?", (tile_index,))
                tile = cursor.fetchone()
                if not tile:
                    logger.error(f"Tile {tile_index} not found")
                    return False
                
                tile_id = tile['id']
                
                # Insert submission
                cursor.execute("""
                    INSERT INTO bingo_submissions (team_name, tile_id, user_id, drop_name, quantity)
                    VALUES (?, ?, ?, ?, ?)
                """, (team_name, tile_id, user_id, drop_name, quantity))
                
                conn.commit()
                logger.info(f"Added bingo submission: Team={team_name}, Tile={tile_index}, Drop={drop_name}")
                return True
        except Exception as e:
            logger.error(f"Error adding bingo submission: {e}")
            return False
    
    def approve_bingo_submission(self, submission_id: int, approved_by: int) -> bool:
        """Approve a bingo submission and update team progress"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get submission details
                cursor.execute("""
                    SELECT bs.*, bt.tile_index, bt.drops_needed
                    FROM bingo_submissions bs
                    JOIN bingo_tiles bt ON bs.tile_id = bt.id
                    WHERE bs.id = ?
                """, (submission_id,))
                
                submission = cursor.fetchone()
                if not submission:
                    logger.error(f"Submission {submission_id} not found")
                    return False
                
                # Update submission status
                cursor.execute("""
                    UPDATE bingo_submissions 
                    SET status = 'approved', approved_at = ?, approved_by = ?
                    WHERE id = ?
                """, (datetime.now(), approved_by, submission_id))
                
                # Update or create team progress
                cursor.execute("""
                    INSERT OR REPLACE INTO bingo_team_progress 
                    (team_name, tile_id, total_required, completed_count, is_complete, updated_at)
                    VALUES (
                        ?, ?, ?, 
                        COALESCE((SELECT completed_count FROM bingo_team_progress 
                                 WHERE team_name = ? AND tile_id = ?), 0) + ?,
                        CASE WHEN COALESCE((SELECT completed_count FROM bingo_team_progress 
                                           WHERE team_name = ? AND tile_id = ?), 0) + ? >= ? 
                             THEN 1 ELSE 0 END,
                        ?
                    )
                """, (
                    submission['team_name'], submission['tile_id'], submission['drops_needed'],
                    submission['team_name'], submission['tile_id'], submission['quantity'],
                    submission['team_name'], submission['tile_id'], submission['quantity'], submission['drops_needed'],
                    datetime.now()
                ))
                
                conn.commit()
                logger.info(f"Approved bingo submission {submission_id}")
                return True
        except Exception as e:
            logger.error(f"Error approving bingo submission: {e}")
            return False
    
    def deny_bingo_submission(self, submission_id: int, denied_by: int, reason: str = None) -> bool:
        """Deny a bingo submission"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bingo_submissions 
                    SET status = 'denied', denied_at = ?, denied_by = ?, denial_reason = ?
                    WHERE id = ?
                """, (datetime.now(), denied_by, reason, submission_id))
                conn.commit()
                logger.info(f"Denied bingo submission {submission_id}")
                return True
        except Exception as e:
            logger.error(f"Error denying bingo submission: {e}")
            return False
    
    def hold_bingo_submission(self, submission_id: int, hold_by: int, reason: str = None) -> bool:
        """Put a bingo submission on hold"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bingo_submissions 
                    SET status = 'hold', hold_at = ?, hold_by = ?, hold_reason = ?
                    WHERE id = ?
                """, (datetime.now(), hold_by, reason, submission_id))
                conn.commit()
                logger.info(f"Put bingo submission {submission_id} on hold")
                return True
        except Exception as e:
            logger.error(f"Error putting bingo submission on hold: {e}")
            return False
    
    def remove_bingo_submission(self, submission_id: int) -> bool:
        """Remove a bingo submission and update team progress"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get submission details before deletion
                cursor.execute("""
                    SELECT bs.*, bt.tile_index, bt.drops_needed
                    FROM bingo_submissions bs
                    JOIN bingo_tiles bt ON bs.tile_id = bt.id
                    WHERE bs.id = ?
                """, (submission_id,))
                
                submission = cursor.fetchone()
                if not submission:
                    logger.error(f"Submission {submission_id} not found")
                    return False
                
                # Delete submission
                cursor.execute("DELETE FROM bingo_submissions WHERE id = ?", (submission_id,))
                
                # Update team progress
                cursor.execute("""
                    UPDATE bingo_team_progress 
                    SET completed_count = completed_count - ?, 
                        is_complete = CASE WHEN completed_count - ? >= total_required THEN 1 ELSE 0 END,
                        updated_at = ?
                    WHERE team_name = ? AND tile_id = ?
                """, (submission['quantity'], submission['quantity'], datetime.now(), 
                     submission['team_name'], submission['tile_id']))
                
                conn.commit()
                logger.info(f"Removed bingo submission {submission_id}")
                return True
        except Exception as e:
            logger.error(f"Error removing bingo submission: {e}")
            return False
    
    def clear_all_progress(self) -> bool:
        """Clear all team progress and submissions from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear bingo submissions
                cursor.execute("DELETE FROM bingo_submissions")
                submissions_cleared = cursor.rowcount
                
                # Clear bingo team progress
                cursor.execute("DELETE FROM bingo_team_progress")
                progress_cleared = cursor.rowcount
                
                conn.commit()
                
            logger.info(f"Cleared {submissions_cleared} submissions and {progress_cleared} progress records")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing progress: {e}")
            return False
    
    # User Management
    def get_or_create_user(self, discord_id: int, username: str, display_name: str = None, team: str = None) -> Dict:
        """Get or create a user in the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute(
                "SELECT * FROM users WHERE discord_id = ?",
                (discord_id,)
            )
            user = cursor.fetchone()
            
            if user:
                # Update last active and return existing user
                cursor.execute(
                    "UPDATE users SET last_active = ?, username = ?, display_name = ? WHERE discord_id = ?",
                    (datetime.now(), username, display_name or username, discord_id)
                )
                conn.commit()
                return dict(user)
            else:
                # Create new user
                cursor.execute(
                    "INSERT INTO users (discord_id, username, display_name, team) VALUES (?, ?, ?, ?)",
                    (discord_id, username, display_name or username, team)
                )
                conn.commit()
                
                # Return the new user
                cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
                return dict(cursor.fetchone())
    
    def get_user(self, discord_id: int) -> Optional[Dict]:
        """Get user by Discord ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    
    def update_user_points(self, discord_id: int, points_change: int, reason: str, 
                          transaction_type: str, reference_id: int = None, 
                          awarded_by: int = None) -> bool:
        """Update user points and create transaction record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update user points
                cursor.execute(
                    "UPDATE users SET total_points = total_points + ? WHERE discord_id = ?",
                    (points_change, discord_id)
                )
                
                # Create transaction record
                cursor.execute(
                    """INSERT INTO point_transactions 
                       (user_id, amount, transaction_type, reference_id, reason, awarded_by)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (discord_id, points_change, transaction_type, reference_id, reason, awarded_by)
                )
                
                conn.commit()
                logger.info(f"Updated points for user {discord_id}: {points_change} ({reason})")
                return True
        except Exception as e:
            logger.error(f"Error updating user points: {e}")
            return False
    
    # Competition Management
    def create_competition(self, competition_type: str, name: str, 
                          start_date: datetime = None, end_date: datetime = None) -> int:
        """Create a new competition"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO competitions (competition_type_id, name, start_date, end_date)
                   SELECT id, ?, ?, ? FROM competition_types WHERE name = ?""",
                (name, start_date, end_date, competition_type)
            )
            conn.commit()
            return cursor.lastrowid
    
    def award_competition_points(self, competition_id: int, user_id: int, 
                                placement: int, awarded_by: int, notes: str = None) -> bool:
        """Award points for competition placement"""
        # Get points for placement based on competition type
        points_map = {
            'Skill of the Week': {1: 20, 2: 10, 3: 5},
            'Clue of the Month': {1: 20, 2: 10, 3: 5},
            'Boss of the Week': {1: 20, 2: 10, 3: 5},
            'General Bingo': {1: 20, 2: 5},
            'Battleship Bingo': {1: 30, 2: 10},
            'Mania': {1: 20, 2: 10, 3: 5},
            'Bounty': {1: 10, 2: 5}
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get competition type
            cursor.execute(
                """SELECT ct.name FROM competitions c
                   JOIN competition_types ct ON c.competition_type_id = ct.id
                   WHERE c.id = ?""",
                (competition_id,)
            )
            result = cursor.fetchone()
            if not result:
                logger.error(f"Competition {competition_id} not found")
                return False
            
            competition_type = result['name']
            points = points_map.get(competition_type, {}).get(placement, 0)
            
            if points == 0:
                logger.error(f"Invalid placement {placement} for {competition_type}")
                return False
            
            # Insert competition result
            cursor.execute(
                """INSERT INTO competition_results 
                   (competition_id, user_id, placement, points_awarded, awarded_by, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (competition_id, user_id, placement, points, awarded_by, notes)
            )
            
            result_id = cursor.lastrowid
            
            # Update user points
            success = self.update_user_points(
                user_id, points, 
                f"{competition_type} - {placement}{self._get_ordinal_suffix(placement)} place",
                'competition', result_id, awarded_by
            )
            
            conn.commit()
            return success
    
    def _get_ordinal_suffix(self, n: int) -> str:
        """Get ordinal suffix for numbers (1st, 2nd, 3rd, etc.)"""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return suffix
    
    def submit_clog(self, user_id: int, current_count: int, verified_by: int, notes: str = None) -> bool:
        """Submit a collection log count for points"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find the highest tier the user qualifies for
                cursor.execute("""
                    SELECT * FROM clog_tiers 
                    WHERE requirement <= ? AND active = 1
                    ORDER BY requirement DESC 
                    LIMIT 1
                """, (current_count,))
                
                tier = cursor.fetchone()
                if not tier:
                    logger.error(f"No CLOG tier found for count {current_count}")
                    return False
                
                # Check if user already has this tier
                cursor.execute("""
                    SELECT * FROM clog_submissions 
                    WHERE user_id = ? AND tier_id = ?
                """, (user_id, tier['id']))
                
                if cursor.fetchone():
                    logger.warning(f"User {user_id} already has CLOG tier {tier['name']}")
                    return False
                
                # Insert submission
                cursor.execute("""
                    INSERT INTO clog_submissions 
                    (user_id, tier_id, current_count, points_awarded, verified_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, tier['id'], current_count, tier['points'], verified_by, notes))
                
                submission_id = cursor.lastrowid
                
                # Award points
                success = self.update_user_points(
                    user_id, tier['points'], 
                    f"Collection Log {tier['name']} ({current_count} items)",
                    'clog', submission_id, verified_by
                )
                
                conn.commit()
                return success
        except Exception as e:
            logger.error(f"Error submitting CLOG: {e}")
            return False
    
    def submit_ca(self, user_id: int, tier_name: str, verified_by: int, notes: str = None) -> bool:
        """Submit a combat achievement tier for points"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get CA tier
                cursor.execute("SELECT * FROM ca_tiers WHERE name = ? AND active = 1", (tier_name,))
                tier = cursor.fetchone()
                if not tier:
                    logger.error(f"CA tier '{tier_name}' not found")
                    return False
                
                # Check if user already has this tier
                cursor.execute("""
                    SELECT * FROM ca_submissions 
                    WHERE user_id = ? AND tier_id = ?
                """, (user_id, tier['id']))
                
                if cursor.fetchone():
                    logger.warning(f"User {user_id} already has CA tier {tier_name}")
                    return False
                
                # Insert submission
                cursor.execute("""
                    INSERT INTO ca_submissions 
                    (user_id, tier_id, points_awarded, verified_by, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, tier['id'], tier['points'], verified_by, notes))
                
                submission_id = cursor.lastrowid
                
                # Award points
                success = self.update_user_points(
                    user_id, tier['points'], 
                    f"Combat Achievement {tier_name}",
                    'ca', submission_id, verified_by
                )
                
                conn.commit()
                return success
        except Exception as e:
            logger.error(f"Error submitting CA: {e}")
            return False
    
    def get_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get the leaderboard"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT discord_id, username, display_name, team, total_points, last_active
                FROM users 
                ORDER BY total_points DESC, last_active DESC
                LIMIT ?
            """, (limit,))
            
            leaderboard = []
            for row in cursor.fetchall():
                leaderboard.append(dict(row))
            return leaderboard
    
    def get_user_stats(self, discord_id: int) -> Dict:
        """Get detailed stats for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
            user = cursor.fetchone()
            if not user:
                return {}
            
            # Get competition results
            cursor.execute("""
                SELECT cr.*, c.name as competition_name, ct.name as competition_type
                FROM competition_results cr
                JOIN competitions c ON cr.competition_id = c.id
                JOIN competition_types ct ON c.competition_type_id = ct.id
                WHERE cr.user_id = ?
                ORDER BY cr.awarded_at DESC
            """, (discord_id,))
            competitions = [dict(row) for row in cursor.fetchall()]
            
            # Get CLOG submissions
            cursor.execute("""
                SELECT cs.*, ct.name as tier_name
                FROM clog_submissions cs
                JOIN clog_tiers ct ON cs.tier_id = ct.id
                WHERE cs.user_id = ?
                ORDER BY cs.submitted_at DESC
            """, (discord_id,))
            clogs = [dict(row) for row in cursor.fetchall()]
            
            # Get CA submissions
            cursor.execute("""
                SELECT cas.*, cat.name as tier_name
                FROM ca_submissions cas
                JOIN ca_tiers cat ON cas.tier_id = cat.id
                WHERE cas.user_id = ?
                ORDER BY cas.submitted_at DESC
            """, (discord_id,))
            cas = [dict(row) for row in cursor.fetchall()]
            
            # Get recent transactions
            cursor.execute("""
                SELECT * FROM point_transactions 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (discord_id,))
            transactions = [dict(row) for row in cursor.fetchall()]
            
            return {
                'user': dict(user),
                'competitions': competitions,
                'clogs': clogs,
                'cas': cas,
                'transactions': transactions
            }
    
    def get_shop_items(self) -> List[Dict]:
        """Get available shop items"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shop_items WHERE active = 1 ORDER BY cost")
            return [dict(row) for row in cursor.fetchall()]
    
    def purchase_item(self, user_id: int, item_id: int, quantity: int = 1) -> bool:
        """Purchase an item from the shop"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get item details
                cursor.execute("SELECT * FROM shop_items WHERE id = ? AND active = 1", (item_id,))
                item = cursor.fetchone()
                if not item:
                    logger.error(f"Shop item {item_id} not found or inactive")
                    return False
                
                # Check if user has enough points
                cursor.execute("SELECT total_points FROM users WHERE discord_id = ?", (user_id,))
                user = cursor.fetchone()
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                total_cost = item['cost'] * quantity
                if user['total_points'] < total_cost:
                    logger.error(f"User {user_id} doesn't have enough points")
                    return False
                
                # Check availability
                if item['available_quantity'] != -1 and item['available_quantity'] < quantity:
                    logger.error(f"Not enough items available")
                    return False
                
                # Create purchase record
                cursor.execute("""
                    INSERT INTO purchases (user_id, item_id, quantity, total_cost)
                    VALUES (?, ?, ?, ?)
                """, (user_id, item_id, quantity, total_cost))
                
                # Update user points
                cursor.execute(
                    "UPDATE users SET total_points = total_points - ? WHERE discord_id = ?",
                    (total_cost, user_id)
                )
                
                # Update item quantity if not unlimited
                if item['available_quantity'] != -1:
                    cursor.execute(
                        "UPDATE shop_items SET available_quantity = available_quantity - ? WHERE id = ?",
                        (quantity, item_id)
                    )
                
                # Create transaction record
                cursor.execute("""
                    INSERT INTO point_transactions 
                    (user_id, amount, transaction_type, reason)
                    VALUES (?, ?, 'shop_purchase', ?)
                """, (user_id, -total_cost, f"Purchased {quantity}x {item['name']}"))
                
                conn.commit()
                logger.info(f"User {user_id} purchased {quantity}x {item['name']} for {total_cost} points")
                return True
        except Exception as e:
            logger.error(f"Error processing purchase: {e}")
            return False
    
    def create_user_thread(self, user_id: int, thread_id: int, channel_id: int, thread_name: str = None) -> bool:
        """Create a new user thread record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_threads (user_id, thread_id, channel_id, thread_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, thread_id, channel_id, thread_name))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating user thread: {e}")
            return False
    
    def archive_user_thread(self, thread_id: int) -> bool:
        """Archive a user thread"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_threads 
                    SET archived = 1, archived_at = ? 
                    WHERE thread_id = ?
                """, (datetime.now(), thread_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error archiving user thread: {e}")
            return False
    
    def get_user_threads(self, user_id: int, archived: bool = False) -> List[Dict]:
        """Get user threads"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM user_threads 
                WHERE user_id = ? AND archived = ?
                ORDER BY created_at DESC
            """, (user_id, archived))
            return [dict(row) for row in cursor.fetchall()] 