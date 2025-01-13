import asyncio
import logging
import os
from typing import Dict, List, Optional
from services.runninghub import RunningHubAPI
from aiogram import Bot

logger = logging.getLogger(__name__)

class RunningHubAccount:
    """Класс для хранения информации об аккаунте RunningHub"""
    def __init__(self, api_key: str, workflow_id: str, max_concurrent_tasks: int = 1):
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.max_concurrent_tasks = max_concurrent_tasks
        self.current_tasks = 0
        self.api: Optional[RunningHubAPI] = None
        
    @property
    def is_available(self) -> bool:
        """Проверяет, доступен ли аккаунт для новых задач"""
        return self.current_tasks < self.max_concurrent_tasks
        
    def increment_tasks(self):
        """Увеличивает счетчик текущих задач"""
        self.current_tasks += 1
        
    def decrement_tasks(self):
        """Уменьшает счетчик текущих задач"""
        if self.current_tasks > 0:
            self.current_tasks -= 1

class TaskQueue:
    """Класс для управления очередью задач и аккаунтами RunningHub"""
    
    def __init__(self):
        self.bot = None
        self.api_url = None
        self.accounts: List[RunningHubAccount] = []
        self.apis: Dict[str, RunningHubAPI] = {}
        
    def setup(self, bot: Bot, api_url: str):
        """Настройка TaskQueue с ботом и URL API"""
        self.bot = bot
        self.api_url = api_url
        logger.info(f"TaskQueue setup with API URL: {api_url}")
        
    def add_account(self, api_key: str, workflow_id: str, max_concurrent_tasks: int = 1):
        """Добавляет новый аккаунт в пул"""
        if not self.bot:
            raise RuntimeError("TaskQueue not initialized. Call setup() first")
            
        account = RunningHubAccount(api_key, workflow_id, max_concurrent_tasks)
        self.accounts.append(account)
        
        # Создаем API клиент для аккаунта
        api = RunningHubAPI(
            bot=self.bot,
            api_url=self.api_url,
            api_key=api_key,
            workflow_id=workflow_id
        )
        account.api = api
        logger.info(f"Added new RunningHub account with max tasks: {max_concurrent_tasks}")
        
    async def initialize(self):
        """Инициализация всех API клиентов"""
        if not self.bot:
            raise RuntimeError("TaskQueue not initialized. Call setup() first")
            
        for account in self.accounts:
            if account.api:
                await account.api.initialize()
        logger.info(f"Initialized {len(self.accounts)} API clients")
            
    async def close(self):
        """Закрытие всех API клиентов"""
        for account in self.accounts:
            if account.api:
                await account.api.close()
        logger.info("Closed all API clients")
            
    def get_available_account(self) -> Optional[RunningHubAccount]:
        """Возвращает доступный аккаунт с наименьшим количеством задач"""
        available_accounts = [acc for acc in self.accounts if acc.is_available]
        if not available_accounts:
            logger.warning(f"No available accounts. Total accounts: {len(self.accounts)}")
            return None
            
        selected_account = min(available_accounts, key=lambda x: x.current_tasks)
        logger.info(f"Selected account {selected_account.api_key[:8]}... (current tasks: {selected_account.current_tasks})")
        return selected_account

    async def process_photos(self, product_photo_id: str, background_photo_id: str, user_id: int) -> Optional[str]:
        """Обработка фотографий через доступный аккаунт"""
        if not self.bot:
            raise RuntimeError("TaskQueue not initialized. Call setup() first")
            
        # Пробуем все доступные аккаунты
        tried_accounts = set()
        logger.info(f"Starting photo processing. Total accounts available: {len(self.accounts)}")
        
        # Создаем список всех аккаунтов в порядке возрастания текущих задач
        available_accounts = sorted(self.accounts, key=lambda x: x.current_tasks)
        
        for account in available_accounts:
            if not account.api:
                continue
                
            if account.api_key in tried_accounts:
                continue
                
            tried_accounts.add(account.api_key)
            logger.info(f"Attempting account {account.api_key[:8]}... (tried accounts: {len(tried_accounts)}/{len(self.accounts)})")
            
            try:
                account.increment_tasks()
                logger.info(f"Processing photos with account {account.api_key[:8]}... (tasks: {account.current_tasks})")
                
                result = await account.api.process_photos(
                    product_photo_id=product_photo_id,
                    background_photo_id=background_photo_id,
                    user_id=user_id
                )
                
                if result:
                    logger.info(f"Successfully processed photos with account {account.api_key[:8]}...")
                    return result
                    
                logger.warning(f"Failed to process with account {account.api_key[:8]}..., trying next account")
                
            except Exception as e:
                logger.error(f"Error with account {account.api_key[:8]}...: {str(e)}")
            finally:
                account.decrement_tasks()
                logger.info(f"Finished processing with account {account.api_key[:8]}... (tasks: {account.current_tasks})")
        
        logger.error(f"All {len(self.accounts)} accounts failed to process photos")
        return None
            
    async def cancel_all_tasks(self):
        """Отмена всех активных задач"""
        logger.info("Canceling all active tasks")
        for account in self.accounts:
            account.current_tasks = 0
            
    @property
    def total_accounts(self) -> int:
        """Возвращает общее количество аккаунтов"""
        return len(self.accounts)
        
    @property
    def available_accounts(self) -> int:
        """Возвращает количество доступных аккаунтов"""
        return len([acc for acc in self.accounts if acc.is_available])
        
    @property
    def total_active_tasks(self) -> int:
        """Возвращает общее количество активных задач"""
        return sum(acc.current_tasks for acc in self.accounts)

# Глобальный экземпляр очереди задач
task_queue = TaskQueue()
task_queue.setup(Bot(token=os.environ['BOT_TOKEN']), api_url='https://api.runninghub.com')
