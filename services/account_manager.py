import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .runninghub import RunningHubAccount, RunningHubAPI

@dataclass
class AccountStatus:
    active_tasks: int = 0
    max_tasks: int = 5

class AccountManager:
    def __init__(self):
        from .runninghub import RunningHubAPI
        self.runninghub_api = RunningHubAPI()
        self.accounts: Dict[str, RunningHubAccount] = {}
        self.account_status: Dict[str, AccountStatus] = {}
        self.lock = asyncio.Lock()

    def add_account(self, api_key: str, workflow_id: str, max_tasks: int = 5) -> None:
        """Добавляет аккаунт в пул"""
        account = RunningHubAccount(
            api_key=api_key,
            workflow_id=workflow_id,
            max_tasks=max_tasks
        )
        self.accounts[api_key] = account
        self.account_status[api_key] = AccountStatus(max_tasks=max_tasks)

    async def get_available_account(self) -> Optional[str]:
        """Возвращает доступный аккаунт"""
        async with self.lock:
            for api_key, status in self.account_status.items():
                if status.active_tasks < status.max_tasks:
                    status.active_tasks += 1
                    return api_key
            return None

    async def release_account(self, api_key: str) -> None:
        """Освобождает аккаунт"""
        async with self.lock:
            if api_key in self.account_status:
                self.account_status[api_key].active_tasks -= 1

    async def check_accounts_status(self) -> Dict[str, Dict[str, Any]]:
        """Проверяет статус всех аккаунтов"""
        results = {}
        for api_key in self.accounts:
            status = await self.runninghub_api.check_account_status(api_key)
            if status:
                results[api_key] = {
                    "status": status,
                    "local_status": self.account_status[api_key]
                }
        return results

    async def close(self) -> None:
        """Закрывает все аккаунты"""
        await self.runninghub_api.close()

    async def initialize(self, accounts: Dict[str, RunningHubAccount]) -> None:
        """Инициализирует аккаунты"""
        for account in accounts.values():
            self.add_account(
                api_key=account.api_key,
                workflow_id=account.workflows['product'],
                max_tasks=account.max_jobs
            )

    def has_available_accounts(self) -> bool:
        """Проверяет наличие доступных аккаунтов"""
        async with self.lock:
            for status in self.account_status.values():
                if status.active_tasks < status.max_tasks:
                    return True
            return False

account_manager = AccountManager()
