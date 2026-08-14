import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from app.core.config import settings
from app.core.logger import logger
from app.database.connection import init_db

from app.bot.auth import AuthMiddleware
from app.bot.handlers import router as commands_router
from app.bot.receiver import router as receiver_router

from app.ingestor.queue import init_queue, recover_queue
from app.ingestor.worker import download_worker

async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        sys.exit(1)
        
    await init_db()
    
    # Initialize Queue and recover state
    queue = init_queue()
    await recover_queue(queue)
    
    # Configure Session for Local API Server if defined
    session = None
    if settings.TELEGRAM_API_SERVER:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(settings.TELEGRAM_API_SERVER)
        )
        logger.info(f"Using Local API Server: {settings.TELEGRAM_API_SERVER}")
        
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, session=session)
    dp = Dispatcher()
    
    # Register Middleware
    dp.update.outer_middleware(AuthMiddleware())
    
    # Register Routers
    dp.include_router(commands_router)
    dp.include_router(receiver_router)
    
    # Start Workers
    workers = []
    for i in range(settings.DOWNLOAD_WORKERS):
        task = asyncio.create_task(download_worker(i + 1, bot))
        workers.append(task)
    
    logger.info("Bot is starting...")
    
    try:
        await dp.start_polling(bot)
    finally:
        # Cancel workers
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
