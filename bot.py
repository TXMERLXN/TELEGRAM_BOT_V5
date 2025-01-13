import asyncio
import logging
import signal
import sys
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import load_config
from handlers import base, generation
from services.task_queue import task_queue
from services.account_manager import account_manager

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def main():
    # Загрузка конфигурации
    config = load_config()
    
    # Проверка длины токена
    logger.info("====== Starting bot ======")
    logger.info(f"Bot token length: {len(config.tg_bot.token)}")
    
    try:
        # Инициализация бота и диспетчера с защитой от повторного запуска
        dp = Dispatcher(storage=MemoryStorage())
        bot = Bot(
            token=config.tg_bot.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # Регистрация хендлеров
        dp.include_router(base.router)
        dp.include_router(generation.router)
        
        # Инициализация RunningHub API
        generation.init_runninghub(bot)
        
        # Инициализация RunningHub аккаунтов
        for account in config.runninghub.accounts:
            account_manager.add_account(
                api_key=account.api_key,
                workflows=account.workflows,
                max_jobs=account.max_jobs
            )
        logger.info(f"Initialized {len(config.runninghub.accounts)} RunningHub accounts")
        
        logger.info("==========================")
        
        # Запуск бота
        logger.info("Starting bot")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        raise
    finally:
        # Освобождаем все аккаунты при остановке
        await account_manager.release_all_accounts()
        # Закрываем сессии
        if generation.runninghub:
            await generation.runninghub.close()
        if 'bot' in locals():
            await bot.session.close()

# Обработчик SIGTERM
async def handle_sigterm(signum, frame):
    """Обработчик сигнала SIGTERM"""
    logger.info("Received SIGTERM signal")
    # Отменяем все активные задачи
    await task_queue.cancel_all_tasks()
    # Освобождаем все аккаунты
    await account_manager.release_all_accounts()
    # Закрываем сессии
    if generation.runninghub:
        await generation.runninghub.close()
    if 'bot' in globals():
        await bot.session.close()
    # Останавливаем поллинг
    await dp.stop_polling()
    logger.info("Shutting down bot")

# Регистрируем обработчик SIGTERM
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGTERM, 
                      lambda: asyncio.create_task(handle_sigterm(signal.SIGTERM, None)))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
