from app.database.connection import get_db
from typing import Dict, Any, Optional
import aiosqlite

async def insert_file(data: Dict[str, Any]) -> int:
    """Inserts a new file record and returns its ID."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO files (
                telegram_file_id, telegram_file_unique_id, telegram_message_id, 
                chat_id, original_name, file_size, mime_type, sender_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['telegram_file_id'],
            data['telegram_file_unique_id'],
            data['telegram_message_id'],
            data['chat_id'],
            data.get('original_name'),
            data.get('file_size'),
            data.get('mime_type'),
            data['sender_id'],
            'RECEIVED'
        ))
        await db.commit()
        return cursor.lastrowid

async def get_file_by_unique_id(unique_id: str) -> Optional[Dict]:
    """Check if a file was already received to prevent duplicates."""
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM files WHERE telegram_file_unique_id = ?", (unique_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_file_status(file_id: int, status: str, **kwargs):
    """Updates file status and optionally other fields."""
    set_clause = "status = ?"
    values = [status]
    
    for key, val in kwargs.items():
        set_clause += f", {key} = ?"
        values.append(val)
        
    values.append(file_id)
    
    async with await get_db() as db:
        await db.execute(f"UPDATE files SET {set_clause} WHERE id = ?", tuple(values))
        await db.commit()
