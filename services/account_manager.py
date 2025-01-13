from dataclasses import dataclass
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class RunningHubAccount:
    api_key: str
    workflows: Dict[str, str]  # type -> workflow_id mapping
    max_jobs: int
    active_jobs: int = 0
    last_used: datetime = None

class AccountManager:
    def __init__(self):
        self.accounts = []
        self.lock = asyncio.Lock()

    def add_account(self, api_key: str, workflows: Dict[str, str], max_jobs: int = 5) -> None:
        """Добавляет новый аккаунт RunningHub"""
        account = RunningHubAccount(api_key=api_key, workflows=workflows, max_jobs=max_jobs)
        self.accounts.append(account)
        logger.info(f"Added new RunningHub account with workflows: {list(workflows.keys())}")

    async def get_available_account(self, workflow_type: str) -> Optional[RunningHubAccount]:
        """Получает доступный аккаунт для указанного типа задачи"""
        async with self.lock:
            # Находим аккаунт с наименьшим количеством активных задач
            available_accounts = [acc for acc in self.accounts if workflow_type in acc.workflows]
            if not available_accounts:
                logger.error(f"No accounts available for workflow type: {workflow_type}")
                return None

            min_jobs_account = min(available_accounts, key=lambda x: x.active_jobs)
            if min_jobs_account.active_jobs >= min_jobs_account.max_jobs:
                logger.error("All accounts are at maximum capacity")
                return None

            min_jobs_account.active_jobs += 1
            logger.debug(f"Using account with {min_jobs_account.active_jobs} active jobs")
            return min_jobs_account

    async def release_account(self, account: Optional[RunningHubAccount]) -> None:
        """Освобождает аккаунт после завершения задачи"""
        if not account:
            return

        async with self.lock:
            if account.active_jobs > 0:
                account.active_jobs -= 1
                logger.debug(f"Released account. Now has {account.active_jobs} active jobs")

    async def release_all_accounts(self) -> None:
        """Освобождает все аккаунты"""
        async with self.lock:
            for account in self.accounts:
                account.active_jobs = 0
            logger.info("Released all accounts")

# Global instance
account_manager = AccountManager()
