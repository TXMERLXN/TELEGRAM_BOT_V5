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

# Настраиваем логирование
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Создаем форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Добавляем обработчик для вывода в stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# Добавляем обработчик для вывода в файл
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

async def main():
    # Загружаем конфиг
    config = load_config()
    logger.debug(f"Loaded config: {config}")
    logger.info("====== Starting bot ======")
    logger.info(f"Bot token length: {len(config.tg_bot.token)}")
    
    # Инициализируем аккаунты RunningHub
    from services.account_manager import account_manager
    for acc in config.runninghub.accounts:
        account_manager.add_account(
            api_key=acc.api_key,
            workflows=acc.workflows,
            max_jobs=acc.max_jobs
        )
    logger.info(f"Initialized {len(config.runninghub.accounts)} RunningHub accounts")
    logger.info("==========================")

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(base.router)
    dp.include_router(generation.router)

    # Обработчик SIGTERM
    async def handle_sigterm(signum, frame):
        logger.info("Received SIGTERM signal")
        # Отменяем все активные задачи
        await task_queue.cancel_all_tasks()
        # Закрываем соединения
        await bot.session.close()
        # Останавливаем поллинг
        await dp.stop_polling()
        logger.info("Shutting down bot")

    # Регистрируем обработчик SIGTERM
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, 
                          lambda: asyncio.create_task(handle_sigterm(signal.SIGTERM, None)))

    logger.info("Starting bot")
    try:
        # Запускаем бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Очистка при выходе
        await task_queue.cancel_all_tasks()
        await bot.session.close()
        logger.info("Shutting down bot")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
