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
        # Инициализируем бота
        bot = Bot(
            token=config.tg_bot.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Настраиваем TaskQueue
        task_queue.setup(bot, config.runninghub.api_url)
        
        # Создаем диспетчер
        dp = Dispatcher(storage=MemoryStorage())
        
        # Регистрация хендлеров
        dp.include_router(base.router)
        dp.include_router(generation.router)
        
        # Инициализация RunningHub API
        await generation.init_runninghub(bot)
        
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

async def handle_sigterm(signum, frame):
    """Обработчик сигнала SIGTERM"""
    logger.info("Received SIGTERM signal")
    try:
        # Отменяем все активные задачи
        await task_queue.cancel_all_tasks()
        # Освобождаем все аккаунты
        await account_manager.release_all_accounts()
        # Закрываем сессии
        if generation.runninghub:
            await generation.runninghub.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    finally:
        sys.exit(0)

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
