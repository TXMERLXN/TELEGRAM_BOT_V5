import os
import sys
import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import ParseMode
from aiogram.dispatcher.fsm.storage.memory import MemoryStorage
from aiogram.dispatcher.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import uvloop

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot = None
dp = None

async def on_startup(dispatcher):
    """Действия при старте бота"""
    logger.info("Бот запускается...")
    # Здесь можно добавить регистрацию хэндлеров
    # Например: await register_user_commands(bot)

async def on_shutdown(dispatcher):
    """Действия при остановке бота"""
    logger.info("Бот останавливается...")
    await bot.session.close()

def main():
    """Основная функция запуска бота"""
    try:
        # Установка политики event loop
        uvloop.install()
        
        # Получение токена
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN не установлен!")
            sys.exit(1)
        
        # Инициализация бота и диспетчера
        global bot, dp
        bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Регистрация обработчиков событий
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Получение параметров webhook
        webhook_host = os.getenv('WEBHOOK_HOST', 'localhost')
        webhook_port = int(os.getenv('WEBHOOK_PORT', 8080))
        
        # Настройка и запуск webhook
        app = setup_application(dp, bot)
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            webhook_path='/webhook'
        ).register(app, path='/webhook')
        
        # Возвращаем приложение для gunicorn
        return app
    
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
