from aiogram import Router, F
from aiogram.types import Message
from app.database.queries import insert_file, get_file_by_unique_id
from app.core.logger import logger
from app.ingestor import queue as ingestor_queue
import asyncio

router = Router(name="receiver_router")

def get_media_data(message: Message) -> dict:
    if message.video:
        return {
            'file_id': message.video.file_id,
            'file_unique_id': message.video.file_unique_id,
            'file_name': message.video.file_name or "video.mp4",
            'file_size': message.video.file_size,
            'mime_type': message.video.mime_type
        }
    elif message.document:
        return {
            'file_id': message.document.file_id,
            'file_unique_id': message.document.file_unique_id,
            'file_name': message.document.file_name or "document",
            'file_size': message.document.file_size,
            'mime_type': message.document.mime_type
        }
    elif message.photo:
        # Get the largest photo
        photo = message.photo[-1]
        return {
            'file_id': photo.file_id,
            'file_unique_id': photo.file_unique_id,
            'file_name': f"photo_{photo.file_unique_id}.jpg",
            'file_size': photo.file_size,
            'mime_type': 'image/jpeg'
        }
    return None

@router.message(F.video | F.document | F.photo)
async def handle_media(message: Message):
    media_data = get_media_data(message)
    if not media_data:
        return
        
    # Check deduplication
    existing = await get_file_by_unique_id(media_data['file_unique_id'])
    if existing:
        logger.info(f"Duplicate file ignored: {media_data['file_unique_id']}")
        return

    # Insert into DB
    data_to_insert = {
        'telegram_file_id': media_data['file_id'],
        'telegram_file_unique_id': media_data['file_unique_id'],
        'telegram_message_id': message.message_id,
        'chat_id': message.chat.id,
        'original_name': media_data['file_name'],
        'file_size': media_data['file_size'],
        'mime_type': media_data['mime_type'],
        'sender_id': message.from_user.id
    }
    
    try:
        db_id = await insert_file(data_to_insert)
        logger.info(f"File queued in DB [ID: {db_id}] - {media_data['file_name']}")
        
        # Put in asyncio queue
        if ingestor_queue.download_queue:
            await ingestor_queue.download_queue.put(db_id)
            
    except Exception as e:
        logger.error(f"Error saving file to DB: {e}", exc_info=True)
