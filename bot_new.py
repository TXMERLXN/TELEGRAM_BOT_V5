import os
import sys

# Добавляем корневую директорию в путь импорта
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

import logging
import asyncio
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Явное добавление пути к utils
sys.path.insert(0, os.path.join(project_root, 'utils'))

import httpx
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import config
from handlers.base import router as base_router
from handlers.generation import router as generation_router
from handlers.admin import router as admin_router
from services.integration import IntegrationService
from utils.monitoring import resource_monitor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем параметры из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_PORT = int(os.getenv('PORT', 8443))

# Автоматическое определение WEBHOOK_HOST
RAILWAY_STATIC_URL = os.getenv('RAILWAY_STATIC_URL', '')
RAILWAY_WEB_URL = os.getenv('RAILWAY_WEB_URL', '')

WEBHOOK_HOST = RAILWAY_STATIC_URL or RAILWAY_WEB_URL or os.getenv('WEBHOOK_HOST', 'https://example.com')

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
    
    # Добавляем FastAPI для healthcheck
    health_app = FastAPI()

    @health_app.get("/health")
    async def health_check():
        return JSONResponse(
            status_code=200, 
            content={
                "status": "healthy", 
                "message": "Telegram Bot is running"
            }
        )
    
    # Добавляем healthcheck в основное приложение
    app.add_subapp('/healthcheck', health_app)
    
    # Запуск мониторинга ресурсов
    resource_monitor.start()
    
    # Запуск приложения
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    
    # Ожидание остановки
    await asyncio.Event().wait()

async def asgi_app(scope, receive, send):
    """
    Корректная ASGI-обертка для приложения
    """
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ]
        })
        await send({
            'type': 'http.response.body',
            'body': b'Telegram Bot is running'
        })
    return

# ASGI-приложение для Gunicorn
app = web.Application()
setup_application(app, dispatcher, bot=bot)

# Добавляем healthcheck в основное приложение
app.add_subapp('/healthcheck', health_app)

# Если файл запускается напрямую
if __name__ == '__main__':
    web.run_app(app, port=WEBHOOK_PORT)
