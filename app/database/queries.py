from app.database.connection import get_db
from typing import Dict, Any, Optional
import aiosqlite

async def insert_file(data: Dict[str, Any]) -> int:
    """Inserts a new file record and returns its ID."""
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO files (
                telegram_file_id, telegram_file_unique_id, telegram_message_id, 
                chat_id, original_name, file_size, mime_type, sender_id, status, destination_folder
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', ?)
        """, (
            data['telegram_file_id'], data['telegram_file_unique_id'], 
            data['telegram_message_id'], data['chat_id'], data['original_name'], 
            data['file_size'], data['mime_type'], data['sender_id'], data.get('destination_folder')
        ))
        await db.commit()
        return cursor.lastrowid

async def get_file_by_unique_id(unique_id: str) -> Optional[Dict]:
    """Check if a file was already received to prevent duplicates."""
    async with get_db() as db:
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
    
    async with get_db() as db:
        await db.execute(f"UPDATE files SET {set_clause} WHERE id = ?", tuple(values))
        await db.commit()

async def get_user_folder(user_id: int) -> str:
    """Gets the currently selected folder for a user, or the default."""
    from app.core.config import settings
    async with get_db() as db:
        async with db.execute("SELECT current_folder FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else settings.DEFAULT_FOLDER

async def get_statistics() -> Dict[str, Any]:
    """Get system statistics for the /status command."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        
        stats = {
            'total_files': 0,
            'completed_files': 0,
            'pending_files': 0,
            'failed_files': 0,
            'total_bytes': 0
        }
        
        async with db.execute("SELECT status, COUNT(*) as count, SUM(file_size) as total_size FROM files GROUP BY status") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                status = row['status']
                count = row['count']
                size = row['total_size'] or 0
                
                stats['total_files'] += count
                
                if status == 'COMPLETED':
                    stats['completed_files'] += count
                    stats['total_bytes'] += size
                elif status == 'QUEUED' or status == 'DOWNLOADING':
                    stats['pending_files'] += count
                elif status == 'FAILED':
                    stats['failed_files'] += count
                    
        return stats
