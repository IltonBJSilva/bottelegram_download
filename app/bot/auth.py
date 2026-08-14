from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from app.core.config import settings
from app.core.logger import logger

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = event.from_user.id if event.from_user else None
        chat_id = event.chat.id
        
        allowed_users = settings.allowed_users
        allowed_chats = settings.allowed_chats
        
        is_allowed = False
        
        # If no restrictions are set in .env, everyone is allowed (not recommended for production)
        if not allowed_users and not allowed_chats:
            is_allowed = True
        else:
            if allowed_users and user_id in allowed_users:
                is_allowed = True
            if allowed_chats and chat_id in allowed_chats:
                is_allowed = True
                
        if not is_allowed:
            logger.warning(f"Unauthorized access attempt by User: {user_id} in Chat: {chat_id}")
            # Optionally send a message or just ignore
            # await event.answer("Acesso não autorizado.")
            return
            
        return await handler(event, data)
