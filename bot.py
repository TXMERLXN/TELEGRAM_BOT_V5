import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import config
from handlers import base, generation
from services.task_queue import task_queue

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    """Действия при запуске бота"""
    logger.info("====== Starting bot ======")
    
    # Логируем длину токена для проверки
    logger.info(f"Bot token length: {len(bot.token)}")
    
    # Инициализация RunningHub аккаунтов
    accounts_data = config.runninghub.accounts
    for account_data in accounts_data:
        api = RunningHubAPI(
            api_url=os.getenv('RUNNINGHUB_API_URL'),
            api_key=account_data['api_key'],
            workflow_id=account_data['workflow_id']
        )
        task_queue.add_account(api, account_data.get('max_tasks', 5))
    logger.info(f"Initialized {len(accounts_data)} RunningHub accounts")
    
    # Инициализация API клиентов
    task_queue.initialize_clients()
    
    logger.info("==========================")
    logger.info("Starting bot")

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Действия при завершении работы бота"""
    logger.info("====== Shutting down bot ======")
    
    # Отменяем все активные задачи
    await task_queue.cancel_all_tasks()
    
    # Закрываем все API клиенты
    task_queue.close_clients()
    
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
