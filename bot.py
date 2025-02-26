import os
import sys
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import config
from handlers import base, generation
from services.integration import IntegrationService

# Инициализация сервисов
integration_service = IntegrationService(config.runninghub.accounts)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    """Действия при запуске бота"""
    logger.info("====== Starting bot ======")
    
    try:
        await integration_service.initialize()
        logger.info("Successfully initialized integration service")
    except Exception as e:
        logger.error(f"Failed to initialize integration service: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("==========================")
    logger.info("Starting bot")

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Действия при завершении работы бота"""
    logger.info("====== Shutting down bot ======")
    
    try:
        await integration_service.shutdown()
        logger.info("Successfully shut down integration service")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
    
    # Закрываем сессию бота
    await bot.session.close()
    
    logger.info("==========================")

def main():
    # Инициализация бота
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация хэндлеров
    dp.include_router(base.router)  # Базовые команды
    dp.include_router(generation.router)  # Генерация изображений
    
    # Регистрация обработчиков запуска и завершения
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск бота
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()
