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
        
        # Закрытие event loop
        event_loop_manager.close()
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
        event_loop_manager.run(
            dispatcher.start_polling(
                bot, 
                skip_updates=True
            )
        )
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled")
    except KeyboardInterrupt:
        logger.info("Bot polling interrupted by user")
    except Exception as e:
        logger.error(f"Error during bot polling: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Гарантированная остановка всех компонентов
        try:
            # Остановка интеграционного сервиса
            event_loop_manager.run(integration_service.shutdown())
            
            # Остановка обработчика очереди
            event_loop_manager.run(task_queue.stop())
            
            # Закрытие event loop
            event_loop_manager.close()
        except Exception as shutdown_error:
            logger.error(f"Error during final shutdown: {shutdown_error}", exc_info=True)

if __name__ == "__main__":
    main()
