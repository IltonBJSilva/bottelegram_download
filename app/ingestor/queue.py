import asyncio
from typing import Optional
from app.database.connection import get_db
from app.core.logger import logger
import aiosqlite

# Global queue
download_queue: Optional[asyncio.Queue] = None

def init_queue():
    global download_queue
    if download_queue is None:
        download_queue = asyncio.Queue()
    return download_queue

async def recover_queue(queue: asyncio.Queue):
    """
    Recupera os downloads não concluídos caso o bot tenha caído.
    """
    logger.info("Recovering pending downloads from database...")
    
    count = 0
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        # Files that were received, queued or interrupted during download
        cursor = await db.execute(
            "SELECT id FROM files WHERE status IN ('RECEIVED', 'QUEUED', 'DOWNLOADING')"
        )
        rows = await cursor.fetchall()
        
        for row in rows:
            # Change status back to QUEUED
            await db.execute(
                "UPDATE files SET status = 'QUEUED' WHERE id = ?", (row['id'],)
            )
            await queue.put(row['id'])
            count += 1
            
        await db.commit()
        
    if count > 0:
        logger.info(f"Recovered {count} pending files to the queue.")
    else:
        logger.info("No pending downloads to recover.")
