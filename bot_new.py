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
from typing import Dict
from pydantic import BaseModel, Field

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

# Импортируем os для работы с переменными окружения
import os

# Определяем WEBHOOK_HOST с резервным значением
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 
    os.getenv('RAILWAY_STATIC_URL', 
    os.getenv('RAILWAY_WEB_URL', 
    'https://default-fallback-url.com')))

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

# Создаем экземпляр FastAPI
app = FastAPI()

bot, dispatcher = setup_bot()

# Создаем модель для webhook
class WebhookUpdate(BaseModel):
    update: Dict = Field(..., description="Telegram webhook update")

# Регистрируем webhook-обработчик
@app.on_event("startup")
async def on_startup():
    # Настройка вебхука при старте
    await bot.set_webhook(
        url=f"{WEBHOOK_HOST}/webhook", 
        secret_token=BOT_TOKEN
    )

# Основной обработчик вебхука
@app.post("/webhook")
async def webhook(update: WebhookUpdate):
    # Обработка входящих обновлений от Telegram
    return await dispatcher.feed_webhook_update(bot, update.update)

# Healthcheck эндпоинт
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Telegram Bot is running",
        "webhook_host": WEBHOOK_HOST
    }

# Запуск мониторинга ресурсов
resource_monitor.start()

# Если файл запускается напрямую
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=WEBHOOK_PORT)
