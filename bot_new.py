import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import config
from handlers.base import router as base_router
from handlers.new_generation import router as generation_router
from services.integration import IntegrationService
from services.task_queue import task_queue
from services.event_loop import event_loop_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Инициализация сервисов
integration_service = IntegrationService(config.runninghub.accounts)

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    """Действия при запуске бота"""
    logger.info("====== Starting bot ======")
    
    try:
        await integration_service.initialize()
        logger.info("Successfully initialized integration service")
        
        # Запуск обработчика очереди с глобальным event loop
        await task_queue.start()
    except Exception as e:
        logger.error(f"Failed to initialize integration service: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("==========================")
    logger.info("Starting bot")

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Действия при завершении работы бота"""
    logger.info("====== Shutting down bot ======")
    
    try:
        # Остановка обработчика очереди
        await task_queue.stop()
        
        await integration_service.shutdown()
        logger.info("Successfully shut down integration service")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

def setup_bot():
    """Настройка бота и диспетчера"""
    load_dotenv()

    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("Bot token not found in environment variables")
        sys.exit(1)

    bot = Bot(
        token=bot_token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dispatcher = Dispatcher()
    
    # Регистрация роутеров
    dispatcher.include_routers(
        base_router, 
        generation_router
    )

    # Регистрация обработчиков событий
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)

    return bot, dispatcher

def main():
    """Основная функция запуска"""
    bot, dispatcher = setup_bot()
    
    try:
        # Запуск polling с использованием глобального event loop
        dispatcher.run_polling(
            bot, 
            skip_updates=True,
            loop=event_loop_manager.loop
        )
    except Exception as e:
        logger.error(f"Error during bot polling: {str(e)}", exc_info=True)

if __name__ == "__main__":
    event_loop_manager.run(main())
