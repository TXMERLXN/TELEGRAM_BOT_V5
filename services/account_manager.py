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
        self._accounts: List[RunningHubAccount] = []
        self._lock = asyncio.Lock()
    
    def add_account(self, api_key: str, workflows: Dict[str, str], max_jobs: int = 5):
        """Add a new RunningHub account to the pool."""
        account = RunningHubAccount(
            api_key=api_key,
            workflows=workflows,
            max_jobs=max_jobs
        )
        self._accounts.append(account)
        logger.info(f"Added new RunningHub account with workflows: {list(workflows.keys())}")
    
    async def get_available_account(self, workflow_type: str) -> Optional[RunningHubAccount]:
        """Get the least loaded account that can handle the specified workflow type."""
        async with self._lock:
            available_accounts = [
                acc for acc in self._accounts 
                if acc.active_jobs < acc.max_jobs and workflow_type in acc.workflows
            ]
            
            if not available_accounts:
                logger.warning(f"No available accounts for workflow type: {workflow_type}")
                return None
            
            # Sort by number of active jobs and last used time
            available_accounts.sort(key=lambda x: (x.active_jobs, x.last_used or datetime.min))
            selected_account = available_accounts[0]
            
            selected_account.active_jobs += 1
            selected_account.last_used = datetime.now()
            
            logger.debug(f"Selected account with {selected_account.active_jobs}/{selected_account.max_jobs} active jobs")
            return selected_account
    
    async def release_account(self, account: RunningHubAccount):
        """Release the account after task completion."""
        async with self._lock:
            if account in self._accounts:
                account.active_jobs = max(0, account.active_jobs - 1)
                logger.debug(f"Released account. Now has {account.active_jobs} active jobs")

# Global instance
account_manager = AccountManager()
