import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        """Initialize the database manager"""
        self._thread_local = threading.local()
        
        # Set database path
        root_dir = Path(__file__).parent.parent
        data_dir = root_dir / 'data'
        if not data_dir.exists():
            data_dir.mkdir(exist_ok=True)
        self.db_path = str(data_dir / 'followers.db')
        
        # Initialize database schema
        self.setup_database()
        
    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._thread_local, "connection"):
            self._thread_local.connection = sqlite3.connect(self.db_path)
            self._thread_local.connection.row_factory = sqlite3.Row
        return self._thread_local.connection
        
    def setup_database(self):
        """Create database tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create followers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_username TEXT NOT NULL,
                display_name TEXT NOT NULL,
                username TEXT NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                api_synced BOOLEAN NOT NULL DEFAULT 0,
                UNIQUE(target_username, username)
            )
        """)
        
        # Create scans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_username TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                total_followers INTEGER NOT NULL,
                new_followers INTEGER NOT NULL,
                batch_number INTEGER NOT NULL
            )
        """)
        
        conn.commit()
        
    def add_followers(self, target_username: str, followers: List[Dict[str, str]], batch_num: int) -> int:
        """Add new followers to database
        
        Args:
            target_username: Twitter username being tracked
            followers: List of follower dictionaries with display_name and username
            batch_num: Batch number for this group of followers
            
        Returns:
            int: Number of new followers added
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get existing followers
            cursor.execute("""
                SELECT username FROM followers
                WHERE target_username = ?
            """, (target_username,))
            existing = {row['username'] for row in cursor.fetchall()}
            
            # Add new followers
            now = datetime.now().isoformat()
            new_count = 0
            
            for follower in followers:
                if follower['username'] not in existing:
                    cursor.execute("""
                        INSERT INTO followers (
                            target_username, display_name, username,
                            first_seen, last_seen, is_active, api_synced
                        ) VALUES (?, ?, ?, ?, ?, 1, 0)
                    """, (
                        target_username,
                        follower['display_name'],
                        follower['username'],
                        now,
                        now
                    ))
                    new_count += 1
                else:
                    # Update last_seen for existing followers
                    cursor.execute("""
                        UPDATE followers
                        SET last_seen = ?, is_active = 1
                        WHERE target_username = ? AND username = ?
                    """, (now, target_username, follower['username']))
            
            # Record scan
            if followers:
                cursor.execute("""
                    INSERT INTO scans (
                        target_username, timestamp,
                        total_followers, new_followers, batch_number
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    target_username,
                    now,
                    len(followers),
                    new_count,
                    batch_num
                ))
            
            conn.commit()
            return new_count
            
        except Exception as e:
            print(f"Error adding followers to database: {str(e)}")
            return 0
            
    def mark_unfollowers(self, target_username: str):
        """Mark followers not seen in latest scan as inactive
        
        Args:
            target_username: Twitter username being tracked
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get timestamp of latest scan
            cursor.execute("""
                SELECT MAX(timestamp) as last_scan
                FROM scans
                WHERE target_username = ?
            """, (target_username,))
            result = cursor.fetchone()
            
            if result and result['last_scan']:
                # Mark followers not seen in latest scan as inactive
                cursor.execute("""
                    UPDATE followers
                    SET is_active = 0
                    WHERE target_username = ?
                    AND last_seen < ?
                    AND is_active = 1
                """, (target_username, result['last_scan']))
                
                conn.commit()
                
        except Exception as e:
            print(f"Error marking unfollowers: {str(e)}")
            
    def get_all_followers(self, target_username: str) -> List[Dict[str, Any]]:
        """Get all followers for a target username
        
        Args:
            target_username: Twitter username being tracked
            
        Returns:
            List of follower dictionaries
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, display_name, username, first_seen, last_seen, is_active, api_synced
                FROM followers
                WHERE target_username = ?
                ORDER BY last_seen DESC
            """, (target_username,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"Error getting followers from database: {str(e)}")
            return []
            
    def get_unsynced_followers(self, target_username: str) -> List[Dict[str, Any]]:
        """Get followers that haven't been synced to API
        
        Args:
            target_username: Twitter username being tracked
            
        Returns:
            List of unsynced follower dictionaries
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, display_name, username, first_seen
                FROM followers
                WHERE target_username = ?
                AND api_synced = 0
                AND is_active = 1
            """, (target_username,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"Error getting unsynced followers: {str(e)}")
            return []
            
    def mark_follower_synced(self, follower_id: int) -> bool:
        """Mark a follower as synced in database
        
        Args:
            follower_id: ID of the follower to mark as synced
            
        Returns:
            bool: True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE followers
                SET api_synced = 1
                WHERE id = ?
            """, (follower_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error marking follower as synced: {str(e)}")
            return False 