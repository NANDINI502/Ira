"""
Database Module
SQLite setup for conversation persistence
"""

import aiosqlite
from pathlib import Path
from loguru import logger

from app.config import settings


class Database:
    """Async SQLite database connection"""
    
    def __init__(self):
        self.db_path = settings.DATABASE_PATH
        self._connection = None
    
    async def initialize(self):
        """Initialize database and create tables"""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        
        await self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")
    
    async def _create_tables(self):
        """Create required tables"""
        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id);
            
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await self._connection.commit()
    
    async def execute(self, query: str, params: tuple = ()):
        """Execute a query"""
        cursor = await self._connection.execute(query, params)
        await self._connection.commit()
        return cursor
    
    async def fetch_one(self, query: str, params: tuple = ()):
        """Fetch one result"""
        cursor = await self._connection.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all results"""
        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            logger.info("Database connection closed")
