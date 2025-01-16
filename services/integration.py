import asyncio
from typing import Dict, Any
from .account_manager import AccountManager
from .task_queue import TaskQueue
from .runninghub import RunningHubAPI
from config import config

class IntegrationService:
    def __init__(self, accounts: Dict[str, Dict[str, Any]]):
        self.runninghub_api = RunningHubAPI(api_url=config.runninghub.api_url)
        self.account_manager = AccountManager()
        self.task_queue = TaskQueue(self.account_manager)
        self.accounts = accounts

    async def initialize(self) -> None:
        """Инициализирует все компоненты"""
        # Преобразуем аккаунты в формат RunningHubAccount
        runninghub_accounts = {
            account['api_key']: RunningHubAccount(
                api_key=account['api_key'],
                workflow_id=account['workflow_id'],
                max_tasks=account['max_tasks']
            )
            for account in self.accounts.values()
        }
        
        await self.account_manager.initialize(runninghub_accounts)
        await self.task_queue.start()

    async def shutdown(self) -> None:
        """Завершает работу всех компонентов"""
        await self.task_queue.stop()
        await self.runninghub_api.close()

    async def add_generation_task(
        self,
        product_image_url: str,
        background_image_url: str,
        callback: Any
    ) -> None:
        """Добавляет задачу генерации в очередь"""
        await self.task_queue.add_task(
            product_image_url=product_image_url,
            background_image_url=background_image_url,
            callback=callback
        )

# Создаем и экспортируем экземпляр сервиса
integration_service = IntegrationService(config.runninghub.accounts)
