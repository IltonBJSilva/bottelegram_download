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

# Cache temporário para sincronizar pastas de um mesmo álbum (media_group)
# Formato: media_group_id: (folder_name, asyncio.Event)
media_group_cache = {}

@router.message(F.video | F.document | F.photo)
@router.channel_post(F.video | F.document | F.photo)
async def handle_media(message: Message):
    caption = message.caption or ""
    sender_id = message.from_user.id if message.from_user else 0
    group_id = message.media_group_id
    
    # Se tem comando na legenda, atualiza DB e salva no cache se for um grupo
    if caption.startswith("/pasta "):
        args = caption.split(maxsplit=1)
        if len(args) >= 2:
            folder_name = args[1].strip()
            from app.database.connection import get_db
            async with get_db() as db:
                await db.execute(
                    "INSERT OR REPLACE INTO user_settings (user_id, current_folder) VALUES (?, ?)",
                    (sender_id, folder_name)
                )
                await db.commit()
                
            if group_id:
                if group_id not in media_group_cache:
                    media_group_cache[group_id] = (folder_name, asyncio.Event())
                else:
                    media_group_cache[group_id] = (folder_name, media_group_cache[group_id][1])
                media_group_cache[group_id][1].set() # Avisa outras mensagens do grupo que a pasta foi definida!
                
    media_data = get_media_data(message)
    if not media_data:
        return
        
    from app.database.queries import get_user_folder
    
    # Lógica de pasta com sincronização de Álbum
    current_folder_for_this_file = None
    
    if group_id:
        if group_id in media_group_cache and media_group_cache[group_id][1].is_set():
            # A mensagem principal já processou a legenda e definiu a pasta
            current_folder_for_this_file = media_group_cache[group_id][0]
        elif not caption.startswith("/pasta "):
            # Não temos a pasta no cache ainda, e esta não é a mensagem com a legenda.
            # Vamos aguardar até 1 segundo para ver se a mensagem com legenda chega e atualiza o cache.
            if group_id not in media_group_cache:
                media_group_cache[group_id] = (None, asyncio.Event())
                
            try:
                await asyncio.wait_for(media_group_cache[group_id][1].wait(), timeout=1.0)
                current_folder_for_this_file = media_group_cache[group_id][0]
            except asyncio.TimeoutError:
                pass # Nenhuma legenda com /pasta chegou para esse álbum a tempo
                
    if not current_folder_for_this_file:
        # Fallback normal: Pega a última pasta do usuário salva no banco
        current_folder_for_this_file = await get_user_folder(sender_id)

    # Insert into DB
    data_to_insert = {
        'telegram_file_id': media_data['file_id'],
        'telegram_file_unique_id': media_data['file_unique_id'],
        'telegram_message_id': message.message_id,
        'chat_id': message.chat.id,
        'original_name': media_data['file_name'],
        'file_size': media_data['file_size'],
        'mime_type': media_data['mime_type'],
        'sender_id': sender_id,
        'destination_folder': current_folder_for_this_file
    }
    
    try:
        db_id = await insert_file(data_to_insert)
        logger.info(f"File queued in DB [ID: {db_id}] - {media_data['file_name']}")
        
        # Put in asyncio queue
        if ingestor_queue.download_queue:
            await ingestor_queue.download_queue.put(db_id)
            
    except Exception as e:
        logger.error(f"Error saving file to DB: {e}", exc_info=True)
