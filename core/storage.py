"""
SQLite storage module for the Focus Timer application.
Handles database initialization, CRUD operations, and queries.
"""

import sqlite3
import os
import time
import csv
from pathlib import Path
from typing import List, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta

from .models import Group, Session, SessionStatus, AppSettings


def get_app_data_dir() -> Path:
    """
    Get the appropriate application data directory based on OS.
    Creates the directory if it doesn't exist.
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif os.name == 'posix':
        # macOS uses ~/Library/Application Support, Linux uses ~/.local/share
        if os.uname().sysname == 'Darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    else:
        base = Path.home()

    app_dir = base / 'FocusTimer'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


class Storage:
    """
    Database storage manager.
    Handles all SQLite operations for groups and sessions.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize storage with database path.
        
        Args:
            db_path: Optional custom path for database file.
                    If None, uses default app data directory.
        """
        if db_path is None:
            db_path = str(get_app_data_dir() / 'focus_timer.db')
        
        self.db_path = db_path
        self._init_database()

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
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema if tables don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create groups table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    default_focus INTEGER NOT NULL DEFAULT 25,
                    default_break INTEGER NOT NULL DEFAULT 5,
                    color TEXT DEFAULT '#4CAF50',
                    created_at INTEGER NOT NULL
                )
            ''')

            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    start_ts INTEGER NOT NULL,
                    end_ts INTEGER NOT NULL,
                    planned_sec INTEGER NOT NULL,
                    actual_sec INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT,
                    is_break INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            ''')

            # Create settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Create indexes for common queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_group 
                ON sessions(group_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_start 
                ON sessions(start_ts)
            ''')

            # Insert default groups if none exist
            cursor.execute('SELECT COUNT(*) FROM groups')
            if cursor.fetchone()[0] == 0:
                default_groups = [
                    ('Study', 25, 5, '#4CAF50'),
                    ('Work', 50, 10, '#2196F3'),
                    ('Coding', 45, 10, '#9C27B0'),
                    ('Reading', 30, 5, '#FF9800'),
                ]
                now = int(time.time())
                for name, focus, break_min, color in default_groups:
                    cursor.execute('''
                        INSERT INTO groups (name, default_focus, default_break, color, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (name, focus, break_min, color, now))

    # ==================== Group CRUD ====================

    def create_group(self, group: Group) -> int:
        """
        Create a new group.
        
        Args:
            group: Group object to create.
            
        Returns:
            ID of the created group.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO groups (name, default_focus, default_break, color, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                group.name,
                group.default_focus_minutes,
                group.default_break_minutes,
                group.color,
                group.created_at
            ))
            return cursor.lastrowid

    def get_group(self, group_id: int) -> Optional[Group]:
        """Get a group by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_group(row)
            return None

    def get_all_groups(self) -> List[Group]:
        """Get all groups ordered by name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM groups ORDER BY name')
            return [self._row_to_group(row) for row in cursor.fetchall()]

    def update_group(self, group: Group) -> bool:
        """
        Update an existing group.
        
        Returns:
            True if update was successful.
        """
        if group.id is None:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE groups 
                SET name = ?, default_focus = ?, default_break = ?, color = ?
                WHERE id = ?
            ''', (
                group.name,
                group.default_focus_minutes,
                group.default_break_minutes,
                group.color,
                group.id
            ))
            return cursor.rowcount > 0

    def delete_group(self, group_id: int) -> bool:
        """
        Delete a group by ID.
        Note: This will also delete all sessions associated with this group.
        
        Returns:
            True if deletion was successful.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # First delete associated sessions
            cursor.execute('DELETE FROM sessions WHERE group_id = ?', (group_id,))
            # Then delete the group
            cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
            return cursor.rowcount > 0

    def _row_to_group(self, row: sqlite3.Row) -> Group:
        """Convert a database row to a Group object."""
        return Group(
            id=row['id'],
            name=row['name'],
            default_focus_minutes=row['default_focus'],
            default_break_minutes=row['default_break'],
            color=row['color'],
            created_at=row['created_at']
        )

    # ==================== Session CRUD ====================

    def create_session(self, session: Session) -> int:
        """
        Create a new session record.
        
        Args:
            session: Session object to create.
            
        Returns:
            ID of the created session.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions 
                (group_id, start_ts, end_ts, planned_sec, actual_sec, status, note, is_break, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.group_id,
                session.start_ts,
                session.end_ts,
                session.planned_seconds,
                session.actual_seconds,
                session.status,
                session.note,
                1 if session.is_break else 0,
                session.created_at
            ))
            return cursor.lastrowid

    def get_session(self, session_id: int) -> Optional[Session]:
        """Get a session by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_session(row)
            return None

    def get_sessions(
        self,
        group_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_breaks: bool = False,
        limit: int = 100
    ) -> List[Session]:
        """
        Get sessions with optional filters.
        
        Args:
            group_id: Filter by group ID.
            start_date: Filter sessions starting from this date.
            end_date: Filter sessions up to this date.
            include_breaks: Include break sessions in results.
            limit: Maximum number of results.
            
        Returns:
            List of matching sessions.
        """
        query = 'SELECT * FROM sessions WHERE 1=1'
        params = []

        if not include_breaks:
            query += ' AND is_break = 0'

        if group_id is not None:
            query += ' AND group_id = ?'
            params.append(group_id)

        if start_date is not None:
            start_ts = int(start_date.timestamp())
            query += ' AND start_ts >= ?'
            params.append(start_ts)

        if end_date is not None:
            end_ts = int(end_date.timestamp())
            query += ' AND start_ts <= ?'
            params.append(end_ts)

        query += ' ORDER BY start_ts DESC LIMIT ?'
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_session(row) for row in cursor.fetchall()]

    def update_session_note(self, session_id: int, note: str) -> bool:
        """Update the note for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE sessions SET note = ? WHERE id = ?',
                (note, session_id)
            )
            return cursor.rowcount > 0

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert a database row to a Session object."""
        return Session(
            id=row['id'],
            group_id=row['group_id'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            planned_seconds=row['planned_sec'],
            actual_seconds=row['actual_sec'],
            status=row['status'],
            note=row['note'],
            is_break=bool(row['is_break']),
            created_at=row['created_at']
        )

    # ==================== Statistics Queries ====================

    def get_today_total_seconds(self, group_id: Optional[int] = None) -> int:
        """Get total focused seconds for today."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self._get_total_seconds_since(today, group_id)

    def get_week_total_seconds(self, group_id: Optional[int] = None) -> int:
        """Get total focused seconds for this week (Monday start)."""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        return self._get_total_seconds_since(start_of_week, group_id)

    def _get_total_seconds_since(
        self, 
        since: datetime, 
        group_id: Optional[int] = None
    ) -> int:
        """Helper to get total seconds since a given datetime."""
        query = '''
            SELECT COALESCE(SUM(actual_sec), 0) as total
            FROM sessions
            WHERE start_ts >= ? AND is_break = 0
        '''
        params = [int(since.timestamp())]

        if group_id is not None:
            query += ' AND group_id = ?'
            params.append(group_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_group_totals(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Tuple[Group, int, int]]:
        """
        Get total seconds and session count per group.
        
        Returns:
            List of tuples: (Group, total_seconds, session_count)
        """
        query = '''
            SELECT 
                g.id, g.name, g.default_focus, g.default_break, g.color, g.created_at,
                COALESCE(SUM(s.actual_sec), 0) as total_seconds,
                COUNT(s.id) as session_count
            FROM groups g
            LEFT JOIN sessions s ON g.id = s.group_id AND s.is_break = 0
        '''
        params = []

        where_clauses = []
        if start_date is not None:
            where_clauses.append('s.start_ts >= ?')
            params.append(int(start_date.timestamp()))
        if end_date is not None:
            where_clauses.append('s.start_ts <= ?')
            params.append(int(end_date.timestamp()))

        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)

        query += ' GROUP BY g.id ORDER BY total_seconds DESC'

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                group = Group(
                    id=row['id'],
                    name=row['name'],
                    default_focus_minutes=row['default_focus'],
                    default_break_minutes=row['default_break'],
                    color=row['color'],
                    created_at=row['created_at']
                )
                results.append((group, row['total_seconds'], row['session_count']))
            return results

    # ==================== Settings ====================

    def get_settings(self) -> AppSettings:
        """Get application settings."""
        settings = AppSettings()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM settings')
            for row in cursor.fetchall():
                key, value = row['key'], row['value']
                if hasattr(settings, key):
                    # Convert string to appropriate type
                    if value.lower() in ('true', 'false'):
                        setattr(settings, key, value.lower() == 'true')
                    else:
                        setattr(settings, key, value)
        return settings

    def save_settings(self, settings: AppSettings):
        """Save application settings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key in ['auto_start_break', 'auto_start_focus', 'keep_screen_awake',
                       'sound_enabled', 'notification_enabled', 'log_breaks']:
                value = str(getattr(settings, key))
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value)
                    VALUES (?, ?)
                ''', (key, value))

    # ==================== Export ====================

    def export_to_csv(
        self,
        filepath: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_id: Optional[int] = None
    ) -> int:
        """
        Export sessions to CSV file.
        
        Args:
            filepath: Path for the CSV file.
            start_date: Filter sessions from this date.
            end_date: Filter sessions to this date.
            group_id: Filter by group.
            
        Returns:
            Number of sessions exported.
        """
        # Build query
        query = '''
            SELECT 
                s.id, g.name as group_name, s.start_ts, s.end_ts,
                s.planned_sec, s.actual_sec, s.status, s.note, s.is_break
            FROM sessions s
            JOIN groups g ON s.group_id = g.id
            WHERE 1=1
        '''
        params = []

        if group_id is not None:
            query += ' AND s.group_id = ?'
            params.append(group_id)
        if start_date is not None:
            query += ' AND s.start_ts >= ?'
            params.append(int(start_date.timestamp()))
        if end_date is not None:
            query += ' AND s.start_ts <= ?'
            params.append(int(end_date.timestamp()))

        query += ' ORDER BY s.start_ts'

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Group', 'Start Time', 'End Time',
                'Planned (min)', 'Actual (min)', 'Status', 'Note', 'Is Break'
            ])
            for row in rows:
                writer.writerow([
                    row['id'],
                    row['group_name'],
                    datetime.fromtimestamp(row['start_ts']).strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.fromtimestamp(row['end_ts']).strftime('%Y-%m-%d %H:%M:%S'),
                    round(row['planned_sec'] / 60, 1),
                    round(row['actual_sec'] / 60, 1),
                    row['status'],
                    row['note'] or '',
                    'Yes' if row['is_break'] else 'No'
                ])

        return len(rows)
