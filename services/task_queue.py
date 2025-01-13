import asyncio
import logging
import os
from typing import Dict, List, Optional, Tuple
from services.runninghub import RunningHubAPI
from aiogram import Bot

logger = logging.getLogger(__name__)

class RunningHubAccount:
    """Класс для хранения информации об аккаунте RunningHub"""
    def __init__(self, api: RunningHubAPI, max_tasks: int = 1):
        self.api = api
        self.max_tasks = max_tasks
        self.current_tasks = 0
        
    @property
    def is_available(self) -> bool:
        """Проверяет, доступен ли аккаунт для новых задач"""
        return self.current_tasks < self.max_tasks
        
    def increment_tasks(self):
        """Увеличивает счетчик текущих задач"""
        self.current_tasks += 1
        
    def decrement_tasks(self):
        """Уменьшает счетчик текущих задач"""
        if self.current_tasks > 0:
            self.current_tasks -= 1

class TaskQueue:
    """Класс для управления очередью задач и аккаунтами RunningHub"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.accounts: List[RunningHubAccount] = []
        self.active_tasks: Dict[str, RunningHubAccount] = {}  # user_id -> account
        self.task_queue: List[Tuple[str, str, str]] = []  # [(user_id, product_path, background_path)]
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    def add_account(self, api: RunningHubAPI, max_tasks: int = 5) -> None:
        """Добавление нового аккаунта"""
        account = RunningHubAccount(api=api, max_tasks=max_tasks)
        self.accounts.append(account)
        self.logger.info(f"Added new RunningHub account with max tasks: {max_tasks}")

    async def process_photos(self, user_id: str, product_photo_path: str, background_photo_path: str) -> Optional[str]:
        """Обработка фотографий с учетом очереди и распределения задач"""
        async with self._lock:
            self.logger.info(f"Starting photo processing. Total accounts available: {len(self.accounts)}")
            
            # Если пользователь уже имеет активную задачу
            if user_id in self.active_tasks:
                self.logger.info(f"User {user_id} already has an active task")
                return None

            # Поиск свободного аккаунта
            available_account = None
            for account in self.accounts:
                if account.current_tasks < account.max_tasks:
                    if len(self.active_tasks) == 0:  # Если нет активных задач, используем первый свободный аккаунт
                        available_account = account
                        break
                    elif account.current_tasks == 0:  # Если есть активные задачи, ищем полностью свободный аккаунт
                        available_account = account
                        break

            if available_account is None:
                # Если нет свободных аккаунтов, добавляем задачу в очередь
                self.task_queue.append((user_id, product_photo_path, background_photo_path))
                self.logger.info(f"No available accounts. Added task to queue. Queue size: {len(self.task_queue)}")
                return None

            # Запускаем обработку фотографий
            self.logger.info(f"Processing photos with account {available_account.api.api_key[:8]}... (tasks: {available_account.current_tasks + 1})")
            available_account.increment_tasks()
            self.active_tasks[user_id] = available_account

            try:
                # Получаем URL файлов
                product_file = await Bot(token=os.environ['BOT_TOKEN']).get_file(product_photo_path)
                background_file = await Bot(token=os.environ['BOT_TOKEN']).get_file(background_photo_path)
                
                product_url = f"https://api.telegram.org/file/bot{os.environ['BOT_TOKEN']}/{product_file.file_path}"
                background_url = f"https://api.telegram.org/file/bot{os.environ['BOT_TOKEN']}/{background_file.file_path}"
                
                result_url = await available_account.api.process_photos(
                    product_photo=product_url,
                    background_photo=background_url,
                    user_id=user_id
                )
                
                self.logger.info(f"Successfully processed photos with account {available_account.api.api_key[:8]}...")
                return result_url
            except Exception as e:
                self.logger.error(f"Error processing photos: {str(e)}")
                return None
            finally:
                available_account.decrement_tasks()
                self.active_tasks.pop(user_id, None)
                
                # Проверяем очередь после завершения задачи
                if self.task_queue and available_account.current_tasks < available_account.max_tasks:
                    next_task = self.task_queue.pop(0)
                    next_user_id, next_product, next_background = next_task
                    self.logger.info(f"Processing next task from queue for user {next_user_id}")
                    asyncio.create_task(self.process_photos(next_user_id, next_product, next_background))

    def initialize_clients(self) -> None:
        """Инициализация API клиентов"""
        for account in self.accounts:
            if account.api is not None:
                asyncio.create_task(account.api._get_session())
        self.logger.info(f"Initialized {len(self.accounts)} API clients")

    def close_clients(self) -> None:
        """Закрытие всех клиентов"""
        for account in self.accounts:
            if hasattr(account, 'api') and account.api is not None:
                try:
                    account.api.close_client()
                except Exception as e:
                    self.logger.error(f"Error closing client: {e}")
        self.logger.info("Closed all API clients")

    async def cancel_all_tasks(self) -> None:
        """Отмена всех активных задач"""
        self.logger.info("Cancelling all active tasks")
        for user_id, task in self.active_tasks.items():
            self.logger.info(f"Cancelling task for user {user_id}")
            account = task
            if account:
                account.current_tasks -= 1
        self.active_tasks.clear()
        self.task_queue.clear()
        
        # Закрываем все клиенты
        for account in self.accounts:
            if hasattr(account, 'api') and account.api is not None:
                try:
                    await account.api.close_client()
                except Exception as e:
                    self.logger.error(f"Error closing client: {e}")
        
        self.logger.info("All tasks cancelled and clients closed")

# Глобальный экземпляр очереди задач
task_queue = TaskQueue(api_url='https://api.runninghub.com')
