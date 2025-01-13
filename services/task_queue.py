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
    
    def __init__(self, bot: Bot, api_url: str):
        self.bot = bot
        self.api_url = api_url
        self.accounts: List[RunningHubAccount] = []
        self.apis: Dict[str, RunningHubAPI] = {}
        
    def add_account(self, api_key: str, workflow_id: str, max_concurrent_tasks: int = 1):
        """Добавляет новый аккаунт в пул"""
        account = RunningHubAccount(api_key, workflow_id, max_concurrent_tasks)
        self.accounts.append(account)
        # Создаем API клиент для аккаунта
        api = RunningHubAPI(
            bot=self.bot,
            api_url=self.api_url,
            api_key=api_key,
            workflow_id=workflow_id
        )
        self.apis[api_key] = api
        logger.info(f"Added new RunningHub account with max tasks: {max_concurrent_tasks}")
        
    async def initialize(self):
        """Инициализация всех API клиентов"""
        for api in self.apis.values():
            await api.initialize()
            
    async def close(self):
        """Закрытие всех API клиентов"""
        for api in self.apis.values():
            await api.close()
            
    def get_available_account(self) -> Optional[RunningHubAccount]:
        """Возвращает доступный аккаунт с наименьшим количеством задач"""
        available_accounts = [acc for acc in self.accounts if acc.is_available]
        if not available_accounts:
            return None
        return min(available_accounts, key=lambda x: x.current_tasks)
        
    async def process_photos(self, product_photo_id: str, background_photo_id: str, user_id: int) -> Optional[str]:
        """Обработка фотографий через доступный аккаунт"""
        account = self.get_available_account()
        if not account:
            logger.warning("No available accounts for processing")
            return None
            
        try:
            account.increment_tasks()
            api = self.apis[account.api_key]
            result = await api.process_photos(product_photo_id, background_photo_id, user_id)
            return result
        finally:
            account.decrement_tasks()
            
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
task_queue = TaskQueue(Bot(token=os.environ['BOT_TOKEN']), api_url='https://api.runninghub.com')
