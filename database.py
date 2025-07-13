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
                    logger.info("Database already exists, skipping initialization")
                    return
            
            # Database doesn't exist, create it
            with open('database_schema.sql', 'r') as f:
                schema = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema)
                conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
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
    
    # Collection Log Management
    def submit_clog(self, user_id: int, current_count: int, verified_by: int, notes: str = None) -> bool:
        """Submit collection log progress and award points for new tiers"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all CLOG tiers
            cursor.execute("SELECT * FROM clog_tiers WHERE active = 1 ORDER BY requirement DESC")
            tiers = cursor.fetchall()
            
            # Get user's previous submissions
            cursor.execute(
                "SELECT tier_id FROM clog_submissions WHERE user_id = ?",
                (user_id,)
            )
            previous_tiers = {row['tier_id'] for row in cursor.fetchall()}
            
            # Check for new tiers achieved
            new_tiers = []
            for tier in tiers:
                if current_count >= tier['requirement'] and tier['id'] not in previous_tiers:
                    new_tiers.append(tier)
            
            if not new_tiers:
                logger.info(f"No new CLOG tiers for user {user_id} with count {current_count}")
                return True
            
            # Award points for new tiers
            total_points = 0
            for tier in new_tiers:
                cursor.execute(
                    """INSERT INTO clog_submissions 
                       (user_id, tier_id, current_count, points_awarded, verified_by, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, tier['id'], current_count, tier['points'], verified_by, notes)
                )
                total_points += tier['points']
            
            # Update user points
            success = self.update_user_points(
                user_id, total_points,
                f"Collection Log: {', '.join(t['name'] for t in new_tiers)}",
                'clog', None, verified_by
            )
            
            conn.commit()
            return success
    
    # Combat Achievement Management
    def submit_ca(self, user_id: int, tier_name: str, verified_by: int, notes: str = None) -> bool:
        """Submit combat achievement tier and award points"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get CA tier
            cursor.execute("SELECT * FROM ca_tiers WHERE name = ? AND active = 1", (tier_name,))
            tier = cursor.fetchone()
            
            if not tier:
                logger.error(f"Invalid CA tier: {tier_name}")
                return False
            
            # Check if already submitted
            cursor.execute(
                "SELECT id FROM ca_submissions WHERE user_id = ? AND tier_id = ?",
                (user_id, tier['id'])
            )
            if cursor.fetchone():
                logger.warning(f"User {user_id} already submitted CA tier {tier_name}")
                return False
            
            # Insert submission
            cursor.execute(
                """INSERT INTO ca_submissions 
                   (user_id, tier_id, points_awarded, verified_by, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, tier['id'], tier['points'], verified_by, notes)
            )
            
            submission_id = cursor.lastrowid
            
            # Update user points
            success = self.update_user_points(
                user_id, tier['points'],
                f"Combat Achievement: {tier_name}",
                'ca', submission_id, verified_by
            )
            
            conn.commit()
            return success
    
    # Leaderboard Management
    def get_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get the current leaderboard"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT discord_id, username, display_name, team, total_points
                   FROM users 
                   ORDER BY total_points DESC 
                   LIMIT ?""",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
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
            cursor.execute(
                """SELECT c.name, cr.placement, cr.points_awarded, cr.awarded_at
                   FROM competition_results cr
                   JOIN competitions c ON cr.competition_id = c.id
                   WHERE cr.user_id = ?
                   ORDER BY cr.awarded_at DESC""",
                (discord_id,)
            )
            competitions = [dict(row) for row in cursor.fetchall()]
            
            # Get CLOG submissions
            cursor.execute(
                """SELECT ct.name, cs.current_count, cs.points_awarded, cs.submitted_at
                   FROM clog_submissions cs
                   JOIN clog_tiers ct ON cs.tier_id = ct.id
                   WHERE cs.user_id = ?
                   ORDER BY cs.submitted_at DESC""",
                (discord_id,)
            )
            clogs = [dict(row) for row in cursor.fetchall()]
            
            # Get CA submissions
            cursor.execute(
                """SELECT cat.name, cas.points_awarded, cas.submitted_at
                   FROM ca_submissions cas
                   JOIN ca_tiers cat ON cas.tier_id = cat.id
                   WHERE cas.user_id = ?
                   ORDER BY cas.submitted_at DESC""",
                (discord_id,)
            )
            cas = [dict(row) for row in cursor.fetchall()]
            
            return {
                'user': dict(user),
                'competitions': competitions,
                'clogs': clogs,
                'cas': cas
            }
    
    # Shop Management
    def get_shop_items(self) -> List[Dict]:
        """Get all active shop items"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shop_items WHERE active = 1 ORDER BY cost ASC")
            return [dict(row) for row in cursor.fetchall()]
    
    def purchase_item(self, user_id: int, item_id: int, quantity: int = 1) -> bool:
        """Purchase an item from the shop"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get item info
            cursor.execute("SELECT * FROM shop_items WHERE id = ? AND active = 1", (item_id,))
            item = cursor.fetchone()
            if not item:
                logger.error(f"Item {item_id} not found or inactive")
                return False
            
            # Check user points
            cursor.execute("SELECT total_points FROM users WHERE discord_id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            total_cost = item['cost'] * quantity
            if user['total_points'] < total_cost:
                logger.error(f"User {user_id} insufficient points: {user['total_points']} < {total_cost}")
                return False
            
            # Check availability
            if item['available_quantity'] != -1 and item['available_quantity'] < quantity:
                logger.error(f"Item {item_id} insufficient quantity")
                return False
            
            # Process purchase
            cursor.execute(
                """INSERT INTO purchases (user_id, item_id, quantity, total_cost)
                   VALUES (?, ?, ?, ?)""",
                (user_id, item_id, quantity, total_cost)
            )
            
            # Update item quantity if limited
            if item['available_quantity'] != -1:
                cursor.execute(
                    "UPDATE shop_items SET available_quantity = available_quantity - ? WHERE id = ?",
                    (quantity, item_id)
                )
            
            # Deduct points from user
            success = self.update_user_points(
                user_id, -total_cost,
                f"Shop purchase: {item['name']} x{quantity}",
                'shop_purchase', cursor.lastrowid
            )
            
            conn.commit()
            return success
    
    # Thread Management
    def create_user_thread(self, user_id: int, thread_id: int, channel_id: int, thread_name: str = None) -> bool:
        """Create a new user thread record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO user_threads (user_id, thread_id, channel_id, thread_name)
                   VALUES (?, ?, ?, ?)""",
                (user_id, thread_id, channel_id, thread_name)
            )
            conn.commit()
            return True
    
    def archive_user_thread(self, thread_id: int) -> bool:
        """Archive a user thread"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_threads SET archived = 1, archived_at = ? WHERE thread_id = ?",
                (datetime.now(), thread_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_threads(self, user_id: int, archived: bool = False) -> List[Dict]:
        """Get threads for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_threads WHERE user_id = ? AND archived = ? ORDER BY created_at DESC",
                (user_id, archived)
            )
            return [dict(row) for row in cursor.fetchall()]

# Global database instance
db = DatabaseManager() 