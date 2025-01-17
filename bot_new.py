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

# Инициализация сервисов
integration_service = IntegrationService(config.runninghub.accounts)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Получаем порт из переменных окружения
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'https://example.com')

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    """Действия при запуске бота"""
    logger.info("====== Starting bot ======")
    try:
        await integration_service.initialize()
        logger.info("Successfully initialized integration service")
    except Exception as e:
        logger.error(f"Failed to initialize integration service: {str(e)}", exc_info=True)
        sys.exit(1)
    
    await bot.set_webhook(
        f"{WEBHOOK_HOST}/webhook", 
        drop_pending_updates=True
    )

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Действия при завершении работы бота"""
    logger.info("====== Stopping bot ======")
    try:
        await integration_service.shutdown()
        logger.info("Successfully shut down integration service")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
    
    await bot.delete_webhook()
    await bot.session.close()

def setup_bot():
    """Настройка бота и диспетчера"""
    bot = Bot(
        token=config.tg_bot.token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dispatcher = Dispatcher()
    dispatcher.include_routers(base_router, generation_router)
    
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    
    return bot, dispatcher

async def main():
    """Основная функция запуска"""
    load_dotenv()
    
    bot, dispatcher = setup_bot()
    
    app = web.Application()
    SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path="/webhook")
    setup_application(app, dispatcher, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    
    logger.info(f"Bot started on port {WEBHOOK_PORT}")
    
    # Бесконечный цикл для работы сервера
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
