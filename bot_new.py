import asyncio
import logging
import os
import sys
from typing import Optional

import uvloop
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
from aiogram.utils.executor import Executor

from services.event_loop import event_loop_manager
from services.task_queue import task_queue
from services.integration import IntegrationService
from states.generation import GenerationState
from utils.single_instance import ensure_single_instance

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None
integration_service: Optional[IntegrationService] = None

def global_error_handler(update, exception):
    """Глобальный обработчик необработанных исключений"""
    logger.error(f"Unhandled exception: {exception}")
    logger.error(f"Update: {update}")
    return True

async def on_startup(dp: Dispatcher):
    """Действия при старте бота"""
    global bot, integration_service
    
    # Инициализация сервисов
    integration_service = IntegrationService()
    await integration_service.initialize()
    
    # Регистрация обработчиков
    dp.register_errors_handler(global_error_handler)
    
    # Настройка состояний
    GenerationState.setup(dp)
    
    logger.info("Bot startup completed successfully")

async def on_shutdown(dp: Dispatcher):
    """Действия при остановке бота"""
    global bot, dp, integration_service
    
    logger.info("====== Shutting down bot ======")
    
    # Остановка сервисов
    if integration_service:
        await integration_service.shutdown()
        logger.info("Successfully shut down integration service")
    
    # Остановка очереди задач
    await task_queue.stop()
    
    # Закрытие соединений бота
    if bot:
        await bot.close()
    
    logger.info("Bot shutdown completed")

def main():
    """Основная функция запуска бота"""
    # Проверка единственного экземпляра
    ensure_single_instance()
    
    # Установка политики event loop
    uvloop.install()
    
    # Инициализация бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN не установлен!")
        sys.exit(1)
    
    global bot, dp
    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    
    # Настройка webhook или long polling
    use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
    
    try:
        if use_webhook:
            # Webhook-режим
            webhook_host = os.getenv('WEBHOOK_HOST', 'localhost')
            webhook_port = int(os.getenv('WEBHOOK_PORT', 8080))
            
            executor = Executor(dp)
            executor.on_startup(on_startup)
            executor.on_shutdown(on_shutdown)
            
            executor.start_webhook(
                webhook_host=webhook_host,
                webhook_port=webhook_port,
                skip_updates=True
            )
        else:
            # Long polling режим
            event_loop_manager.run(on_startup(dp))
            
            # Запуск polling
            event_loop_manager.run(dp.start_polling(
                skip_updates=True,
                on_startup=on_startup,
                on_shutdown=on_shutdown
            ))
    
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        # Финальная остановка
        event_loop_manager.close()
        logger.info("Bot polling cancelled")

if __name__ == '__main__':
    main()
