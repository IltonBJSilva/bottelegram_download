import aiosqlite
import os
from pathlib import Path
from app.core.logger import logger

DB_PATH = Path("data/ingestor.db")

async def init_db():
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("Initializing database...")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_file_id TEXT NOT NULL,
                telegram_file_unique_id TEXT NOT NULL,
                telegram_message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                original_name TEXT,
                file_size INTEGER,
                mime_type TEXT,
                sender_id INTEGER,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                local_path TEXT,
                sha256 TEXT,
                download_started_at TIMESTAMP,
                download_completed_at TIMESTAMP,
                error TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)
        
        # Indexes for faster queries
        await db.execute("CREATE INDEX IF NOT EXISTS idx_status ON files(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_file_unique_id ON files(telegram_file_unique_id)")
        
        # Settings table for user-specific settings like current folder
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                current_folder TEXT NOT NULL
            )
        """)
        
        await db.commit()
    logger.info("Database initialized.")

async def get_db():
    return await aiosqlite.connect(DB_PATH)
