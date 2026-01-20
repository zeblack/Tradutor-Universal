import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Room history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                room_id TEXT NOT NULL,
                room_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Room sessions table (Detailed History)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                room_id TEXT NOT NULL,
                room_name TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                left_at TIMESTAMP,
                duration_minutes INTEGER,
                role TEXT DEFAULT 'speaker',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # User profile migrations (safe add columns)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        except sqlite3.OperationalError:
            pass # Column likely exists
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'en-US'")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()
        print("✅ Database initialized (Schema Updated)")
    
    def create_user(self, email: str, username: str, password_hash: str) -> Optional[int]:
        """Create new user, return user_id or None if failed"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (email, username, password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            return None
    
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check available columns to avoid errors if schema not yet updated in runtime?
        # Assuming schema is updated.
        try:
             cursor.execute(
                "SELECT id, email, username, password_hash, created_at, last_login, avatar_url, bio, preferred_language FROM users WHERE email = ?",
                (email,)
            )
        except sqlite3.OperationalError:
             # Fallback for old schema
             cursor.execute(
                "SELECT id, email, username, password_hash, created_at, last_login, NULL, NULL, NULL FROM users WHERE email = ?",
                (email,)
            )

        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "username": row[2],
                "password_hash": row[3],
                "created_at": row[4],
                "last_login": row[5],
                "avatar_url": row[6],
                "bio": row[7],
                "preferred_language": row[8] or "en-US"
            }
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, email, username, created_at, last_login, avatar_url, bio, preferred_language FROM users WHERE id = ?",
                (user_id,)
            )
        except sqlite3.OperationalError:
            cursor.execute(
                "SELECT id, email, username, created_at, last_login, NULL, NULL, NULL FROM users WHERE id = ?",
                (user_id,)
            )
            
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "username": row[2],
                "created_at": row[3],
                "last_login": row[4],
                "avatar_url": row[5],
                "bio": row[6],
                "preferred_language": row[7] or "en-US"
            }
        return None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        conn.commit()
        conn.close()
    
    def add_room_history(self, user_id: int, room_id: str, room_name: str):
        """Add room to user's history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO room_history (user_id, room_id, room_name) VALUES (?, ?, ?)",
            (user_id, room_id, room_name)
        )
        conn.commit()
        conn.close()
    
    def get_room_history(self, user_id: int, limit: int = 10):
        """Get user's room history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT room_id, room_name, joined_at 
               FROM room_history 
               WHERE user_id = ? 
               ORDER BY joined_at DESC 
               LIMIT ?""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        

        return [
            {"room_id": row[0], "room_name": row[1], "joined_at": row[2]}
            for row in rows
        ]

    # --- New Methods for Auth System ---

    def create_room_session(self, user_id: int, room_id: str, room_name: str, role: str):
        """Record when a user joins a room"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO room_sessions (user_id, room_id, room_name, role)
            VALUES (?, ?, ?, ?)
        """, (user_id, room_id, room_name, role))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def end_room_session(self, session_id: int):
        """Record when a user leaves a room"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE room_sessions 
            SET left_at = CURRENT_TIMESTAMP,
            duration_minutes = CAST((julianday(CURRENT_TIMESTAMP) - julianday(joined_at)) * 24 * 60 AS INTEGER)
            WHERE id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    def get_user_room_history(self, user_id: int, limit: int = 10):
        """Get detailed room history from sessions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT room_id, room_name, joined_at, left_at, duration_minutes, role
            FROM room_sessions
            WHERE user_id = ?
            ORDER BY joined_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(['room_id', 'room_name', 'joined_at', 'left_at', 'duration_minutes', 'role'], row)) for row in rows]

    def update_user_avatar(self, user_id: int, avatar_url: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
        conn.commit()
        conn.close()

    def update_user_profile(self, user_id: int, bio: str = None, preferred_language: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if bio:
            cursor.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
        if preferred_language:
            cursor.execute("UPDATE users SET preferred_language = ? WHERE id = ?", (preferred_language, user_id))
        conn.commit()
        conn.close()
