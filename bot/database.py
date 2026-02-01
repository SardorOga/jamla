import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    mode TEXT DEFAULT 'realtime',
                    digest_time TEXT DEFAULT '09:00',
                    language TEXT DEFAULT 'uz',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Channels table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_username TEXT UNIQUE,
                    channel_id INTEGER,
                    title TEXT
                )
            """)

            # User-Channel relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_channels (
                    user_id INTEGER,
                    channel_id INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, channel_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (channel_id) REFERENCES channels(id)
                )
            """)

            # Posts table for digest
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    message_id INTEGER,
                    text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent INTEGER DEFAULT 0,
                    FOREIGN KEY (channel_id) REFERENCES channels(id),
                    UNIQUE(channel_id, message_id)
                )
            """)

            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_sent ON posts(sent)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_channels_user ON user_channels(user_id)")

            logger.info("Database initialized successfully")

    # User operations
    def get_or_create_user(self, user_id: int, username: Optional[str] = None) -> dict:
        """Get user or create if not exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)

            cursor.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            return {
                "user_id": user_id,
                "username": username,
                "mode": "realtime",
                "digest_time": "09:00",
                "language": "uz",
            }

    def update_user_mode(self, user_id: int, mode: str) -> None:
        """Update user notification mode."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET mode = ? WHERE user_id = ?",
                (mode, user_id)
            )

    def update_user_digest_time(self, user_id: int, digest_time: str) -> None:
        """Update user digest time."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET digest_time = ? WHERE user_id = ?",
                (digest_time, user_id)
            )

    def update_user_language(self, user_id: int, language: str) -> None:
        """Update user language preference."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET language = ? WHERE user_id = ?",
                (language, user_id)
            )

    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_users_by_mode(self, mode: str) -> list:
        """Get all users with a specific mode."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE mode = ?", (mode,))
            return [dict(row) for row in cursor.fetchall()]

    def get_users_for_digest(self, current_time: str) -> list:
        """Get users who should receive digest at current time."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE mode = 'digest' AND digest_time = ?",
                (current_time,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # Channel operations
    def add_channel(self, channel_username: str, channel_id: int, title: str) -> int:
        """Add a channel or get existing one."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if channel exists
            cursor.execute(
                "SELECT id FROM channels WHERE channel_username = ?",
                (channel_username.lower(),)
            )
            row = cursor.fetchone()

            if row:
                # Update channel info
                cursor.execute(
                    "UPDATE channels SET channel_id = ?, title = ? WHERE id = ?",
                    (channel_id, title, row["id"])
                )
                return row["id"]

            cursor.execute(
                "INSERT INTO channels (channel_username, channel_id, title) VALUES (?, ?, ?)",
                (channel_username.lower(), channel_id, title)
            )
            return cursor.lastrowid

    def get_channel_by_username(self, channel_username: str) -> Optional[dict]:
        """Get channel by username."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM channels WHERE channel_username = ?",
                (channel_username.lower(),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_channel_by_id(self, channel_id: int) -> Optional[dict]:
        """Get channel by Telegram ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM channels WHERE channel_id = ?",
                (channel_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_channels(self) -> list:
        """Get all channels being watched."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT c.* FROM channels c
                INNER JOIN user_channels uc ON c.id = uc.channel_id
            """)
            return [dict(row) for row in cursor.fetchall()]

    # User-Channel operations
    def add_user_channel(self, user_id: int, channel_id: int) -> bool:
        """Add channel to user's list. Returns False if already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO user_channels (user_id, channel_id) VALUES (?, ?)",
                    (user_id, channel_id)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_user_channel(self, user_id: int, channel_id: int) -> bool:
        """Remove channel from user's list."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_channels WHERE user_id = ? AND channel_id = ?",
                (user_id, channel_id)
            )
            return cursor.rowcount > 0

    def get_user_channels(self, user_id: int) -> list:
        """Get all channels for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.* FROM channels c
                INNER JOIN user_channels uc ON c.id = uc.channel_id
                WHERE uc.user_id = ?
                ORDER BY c.title
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_channel_users(self, channel_db_id: int) -> list:
        """Get all users subscribed to a channel."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.* FROM users u
                INNER JOIN user_channels uc ON u.user_id = uc.user_id
                WHERE uc.channel_id = ?
            """, (channel_db_id,))
            return [dict(row) for row in cursor.fetchall()]

    def user_has_channel(self, user_id: int, channel_id: int) -> bool:
        """Check if user has a specific channel."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_channels WHERE user_id = ? AND channel_id = ?",
                (user_id, channel_id)
            )
            return cursor.fetchone() is not None

    # Post operations
    def add_post(self, channel_id: int, message_id: int, text: str) -> Optional[int]:
        """Add a post for digest. Returns post ID or None if duplicate."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO posts (channel_id, message_id, text) VALUES (?, ?, ?)",
                    (channel_id, message_id, text[:500] if text else "")
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

    def get_unsent_posts_for_user(self, user_id: int) -> list:
        """Get unsent posts for user's channels from last 24 hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            yesterday = datetime.now() - timedelta(hours=24)
            cursor.execute("""
                SELECT p.*, c.title as channel_title, c.channel_username
                FROM posts p
                INNER JOIN channels c ON p.channel_id = c.id
                INNER JOIN user_channels uc ON c.id = uc.channel_id
                WHERE uc.user_id = ?
                AND p.created_at > ?
                AND p.sent = 0
                ORDER BY p.created_at DESC
            """, (user_id, yesterday))
            return [dict(row) for row in cursor.fetchall()]

    def mark_posts_sent(self, post_ids: list) -> None:
        """Mark posts as sent."""
        if not post_ids:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(post_ids))
            cursor.execute(
                f"UPDATE posts SET sent = 1 WHERE id IN ({placeholders})",
                post_ids
            )

    def cleanup_old_posts(self, days: int = 7) -> int:
        """Delete posts older than specified days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(days=days)
            cursor.execute("DELETE FROM posts WHERE created_at < ?", (cutoff,))
            return cursor.rowcount
