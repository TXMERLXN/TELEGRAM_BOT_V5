import os
import sys
import logging
import asyncio
import tempfile
import fcntl
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

def ensure_single_instance():
    try:
        lock_file = open(os.path.join(tempfile.gettempdir(), 'telegram_bot.lock'), 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, BlockingIOError):
        logger.error("Another instance of the bot is already running.")
        sys.exit(1)

async def global_error_handler(update, exception):
    """Централизованная обработка необработанных исключений"""
    logger.error(f"Unhandled error: {exception}")
    # TODO: Реализовать отправку уведомления администратору
    # await send_error_notification(exception)

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    """Действия при запуске бота"""
    logger.info("====== Starting bot ======")
    
    try:
        await integration_service.initialize()
        logger.info("Successfully initialized integration service")
        
        # Запуск обработчика очереди с глобальным event loop
        await task_queue.start()
        
        # Настройка webhook
        await setup_webhook(bot)
    except Exception as e:
        logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("==========================")
    logger.info("Starting bot")

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Действия при завершении работы бота"""
    logger.info("====== Shutting down bot ======")
    
    try:
        await task_queue.stop()
        await integration_service.shutdown()
        logger.info("Successfully shut down services")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
    
    # Закрываем сессию бота
    await bot.session.close()

async def setup_webhook(bot: Bot):
    WEBHOOK_URL = f"https://{config.WEBHOOK_HOST}/webhook/{config.BOT_TOKEN}"
    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True,
        max_connections=100
    )

def setup_bot():
    # Создание бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(base_router)
    dp.include_router(generation_router)

    # Регистрация глобального обработчика ошибок
    dp.errors.register(global_error_handler)

    # Настройка событий запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return bot, dp

def main():
    # Обеспечение единственного экземпляра
    ensure_single_instance()

    # Загрузка переменных окружения
    load_dotenv()

    # Настройка бота
    bot, dp = setup_bot()

    # Запуск бота
    try:
        # Выбор режима запуска в зависимости от конфигурации
        if config.USE_WEBHOOK:
            app = web.Application()
            SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=f"/webhook/{config.BOT_TOKEN}")
            setup_application(app, dp, bot=bot)
            web.run_app(app, host=config.WEBHOOK_HOST, port=config.WEBHOOK_PORT)
        else:
            # Классический режим long polling
            asyncio.run(dp.start_polling(bot))
    except Exception as e:
        logger.error(f"Bot startup failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
