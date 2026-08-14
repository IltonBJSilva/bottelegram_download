import asyncio
import aiosqlite
import shutil
from pathlib import Path
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.core.config import settings
from app.core.logger import logger
from app.database.connection import get_db
from app.database.queries import update_file_status
from app.ingestor.queue import download_queue

async def get_file_record(file_id: int) -> Optional[dict]:
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM files WHERE id = ?", (file_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def download_worker(worker_id: int, bot: Bot):
    """
    Worker assíncrono que consome a fila e processa os downloads.
    """
    logger.info(f"Worker {worker_id} started.")
    
    while True:
        try:
            if download_queue is None:
                await asyncio.sleep(1)
                continue
                
            db_id = await download_queue.get()
            
            # Fetch record
            file_record = await get_file_record(db_id)
            if not file_record:
                logger.error(f"Worker {worker_id}: Record ID {db_id} not found in DB.")
                download_queue.task_done()
                continue
                
            telegram_file_id = file_record['telegram_file_id']
            retry_count = file_record['retry_count']
            file_name = file_record['original_name']
            
            logger.info(f"Worker {worker_id}: Processing '{file_name}' (DB ID: {db_id}, Retry: {retry_count})")
            
            await update_file_status(db_id, "DOWNLOADING")
            
            try:
                # 1. Ask Telegram for the file object
                tg_file = await bot.get_file(telegram_file_id)
                
                # We will just put them in the root download dir for now.
                # Phase 3 will handle correct dynamic sub-folders
                dest_dir = Path(settings.DOWNLOAD_DIR)
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                # Create a unique filename if it exists
                dest_path = dest_dir / f"{file_record['telegram_file_unique_id']}_{file_name}"
                
                # 2. Download the file
                logger.info(f"Worker {worker_id}: Downloading '{file_name}' to {dest_path}")
                
                # Bot.download handles the HTTP streaming (or local copy if local API is perfectly aligned)
                await bot.download_file(tg_file.file_path, dest_path)
                
                # 3. Mark as completed (Hash verification will be added in Phase 3)
                await update_file_status(
                    db_id, 
                    "COMPLETED", 
                    local_path=str(dest_path),
                    download_completed_at="CURRENT_TIMESTAMP" # Note: using string here might not work as SQLite func, need to fix
                )
                
                async with await get_db() as db:
                    await db.execute(
                        "UPDATE files SET local_path = ?, download_completed_at = CURRENT_TIMESTAMP, status = 'COMPLETED' WHERE id = ?",
                        (str(dest_path), db_id)
                    )
                    await db.commit()
                
                logger.info(f"Worker {worker_id}: Successfully completed '{file_name}'")
                
            except Exception as e:
                logger.error(f"Worker {worker_id}: Error downloading '{file_name}': {e}", exc_info=True)
                
                # Exponential Backoff logic
                new_retry = retry_count + 1
                if new_retry <= settings.MAX_RETRIES:
                    await update_file_status(db_id, "QUEUED", retry_count=new_retry, error=str(e))
                    delay = 2 ** new_retry # 2, 4, 8, 16, 32 seconds
                    logger.info(f"Worker {worker_id}: Re-queuing '{file_name}' for retry {new_retry} in {delay}s")
                    
                    async def delayed_requeue(id_to_queue, sleep_time):
                        await asyncio.sleep(sleep_time)
                        if download_queue:
                            await download_queue.put(id_to_queue)
                            
                    asyncio.create_task(delayed_requeue(db_id, delay))
                else:
                    logger.error(f"Worker {worker_id}: Max retries reached for '{file_name}'. Marking as FAILED.")
                    await update_file_status(db_id, "FAILED", error=f"Max retries reached: {e}")
                    
            finally:
                download_queue.task_done()
                
        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} stopping...")
            break
        except Exception as e:
            logger.error(f"Worker {worker_id} encountered an unexpected error: {e}", exc_info=True)
            await asyncio.sleep(5) # Prevent tight loop on critical error
