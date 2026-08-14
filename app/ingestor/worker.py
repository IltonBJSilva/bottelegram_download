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
from app.ingestor import queue as ingestor_queue

async def get_file_record(file_id: int) -> Optional[dict]:
    async with get_db() as db:
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
            if ingestor_queue.download_queue is None:
                await asyncio.sleep(1)
                continue
                
            db_id = await ingestor_queue.download_queue.get()
            
            # Fetch record
            file_record = await get_file_record(db_id)
            if not file_record:
                logger.error(f"Worker {worker_id}: Record ID {db_id} not found in DB.")
                ingestor_queue.download_queue.task_done()
                continue
                
            telegram_file_id = file_record['telegram_file_id']
            retry_count = file_record['retry_count']
            file_name = file_record['original_name']
            
            logger.info(f"Worker {worker_id}: Processing '{file_name}' (DB ID: {db_id}, Retry: {retry_count})")
            
            await update_file_status(db_id, "DOWNLOADING")
            
            try:
                # 1. Ask Telegram for the file object
                tg_file = await bot.get_file(telegram_file_id)
                
                # Fetch user's current folder preference
                current_folder = file_record.get('destination_folder')
                if not current_folder:
                    # Fallback para arquivos enfileirados antes da atualização
                    sender_id = file_record['sender_id']
                    from app.database.queries import get_user_folder
                    current_folder = await get_user_folder(sender_id)
                
                # 2. Get dynamic destination path
                from app.ingestor.organizer import get_destination_path, calculate_sha256
                dest_path = get_destination_path(current_folder, file_name, file_record['telegram_file_unique_id'])
                
                # 3. Download the file
                logger.info(f"Worker {worker_id}: Downloading '{file_name}' to {dest_path}")
                await bot.download_file(tg_file.file_path, dest_path)
                
                # 4. Calculate SHA256
                logger.info(f"Worker {worker_id}: Calculating SHA-256 for '{file_name}'")
                file_hash = await calculate_sha256(dest_path)
                
                # 5. Mark as completed
                async with get_db() as db:
                    await db.execute(
                        "UPDATE files SET local_path = ?, sha256 = ?, download_completed_at = CURRENT_TIMESTAMP, status = 'COMPLETED' WHERE id = ?",
                        (str(dest_path), file_hash, db_id)
                    )
                    await db.commit()
                
                logger.info(f"Worker {worker_id}: Successfully completed '{file_name}' [HASH: {file_hash[:8]}...]")
                
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
                        if ingestor_queue.download_queue:
                            await ingestor_queue.download_queue.put(id_to_queue)
                            
                    asyncio.create_task(delayed_requeue(db_id, delay))
                else:
                    logger.error(f"Worker {worker_id}: Max retries reached for '{file_name}'. Marking as FAILED.")
                    await update_file_status(db_id, "FAILED", error=f"Max retries reached: {e}")
                    
            finally:
                ingestor_queue.download_queue.task_done()
                
        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} stopping...")
            break
        except Exception as e:
            logger.error(f"Worker {worker_id} encountered an unexpected error: {e}", exc_info=True)
            await asyncio.sleep(5) # Prevent tight loop on critical error
