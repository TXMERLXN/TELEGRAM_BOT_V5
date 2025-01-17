import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация Sentry до импорта других модулей
from utils.sentry_utils import init_sentry
init_sentry(
    environment=os.getenv('SENTRY_ENVIRONMENT', 'development')
)

import httpx
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import config
from handlers.base import router as base_router
from handlers.generation import router as generation_router
from handlers.admin import router as admin_router
from services.integration import IntegrationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем параметры из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'https://example.com')

# Инициализация сервисов
integration_service = IntegrationService(config.runninghub.accounts)

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    """Действия при запуске бота"""
    logger.info("====== Starting bot ======")
    try:
        await integration_service.initialize()
        logger.info("Successfully initialized integration service")
    except Exception as e:
        logger.error(f"Failed to initialize integration service: {str(e)}", exc_info=True)
        # Используем sys.exit для корректного завершения
        sys.exit(1)
    
    # Настройка вебхука
    await bot.set_webhook(
        f"{WEBHOOK_HOST}/webhook", 
        drop_pending_updates=True
    )

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Действия при завершении работы бота"""
    logger.info("====== Shutting down bot ======")
    await integration_service.close()

def setup_bot():
    """Настройка бота и диспетчера"""
    # Параметры бота по умолчанию
    bot_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    
    # Создание бота
    bot = Bot(token=BOT_TOKEN, default=bot_properties)
    
    # Создание диспетчера
    dispatcher = Dispatcher()
    
    # Регистрация роутеров
    dispatcher.include_routers(base_router, generation_router, admin_router)
    
    # Регистрация обработчиков событий
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    
    return bot, dispatcher

async def main():
    """Основная функция запуска"""
    # Создание бота и диспетчера
    bot, dispatcher = setup_bot()
    
    # Настройка приложения
    app = web.Application()
    
    # Настройка вебхука
    SimpleRequestHandler(
        dispatcher=dispatcher, 
        bot=bot
    ).register(app, path="/webhook")
    
    setup_application(app, dispatcher, bot=bot)
    
    # Запуск приложения
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    
    # Ожидание остановки
    await asyncio.Event().wait()

# ASGI-приложение для Gunicorn
app = web.Application()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        # Автоматическая отправка критической ошибки в Sentry
        from utils.sentry_utils import capture_exception
        capture_exception(e)
        sys.exit(1)
