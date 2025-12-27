"""
Database utilities for storing violation data
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH


class ViolationDatabase:
    """
    SQLite database for storing violation records
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                frame_number INTEGER NOT NULL,
                frame_path TEXT,
                violation_type TEXT NOT NULL,
                roi_name TEXT,
                hand_bbox TEXT,
                pizza_bbox TEXT,
                scooper_detected INTEGER DEFAULT 0,
                confidence REAL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_violations INTEGER DEFAULT 0,
                total_frames INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def insert_violation(self, violation_data):
        """
        Insert a violation record
        
        Args:
            violation_data: dict containing violation information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO violations (
                timestamp, frame_number, frame_path, violation_type,
                roi_name, hand_bbox, pizza_bbox, scooper_detected,
                confidence, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            violation_data.get('timestamp', datetime.now().isoformat()),
            violation_data.get('frame_number', 0),
            violation_data.get('frame_path', ''),
            violation_data.get('violation_type', 'no_scooper'),
            violation_data.get('roi_name', ''),
            json.dumps(violation_data.get('hand_bbox', [])),
            json.dumps(violation_data.get('pizza_bbox', [])),
            violation_data.get('scooper_detected', 0),
            violation_data.get('confidence', 0.0),
            json.dumps(violation_data.get('metadata', {}))
        ))
        
        conn.commit()
        violation_id = cursor.lastrowid
        conn.close()
        
        return violation_id
    
    def get_violations(self, limit=None):
        """Get all violations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM violations ORDER BY timestamp DESC'
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        violations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return violations
    
    def get_violation_count(self):
        """Get total count of violations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM violations')
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def clear_violations(self):
        """Clear all violation records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM violations')
        conn.commit()
        conn.close()




