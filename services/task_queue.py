import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .account_manager import AccountManager
from .runninghub import RunningHubAPI

@dataclass
class Task:
    product_image_url: str
    background_image_url: str
    callback: Any
    retries: int = 0

class TaskQueue:
    def __init__(self, account_manager: AccountManager):
        self.queue = asyncio.Queue()
        self.account_manager = account_manager
        self.runninghub_api = RunningHubAPI()
        self._running = False
        self._task = None

    async def add_task(
        self,
        product_image_url: str,
        background_image_url: str,
        callback: Any
    ) -> None:
        """Добавляет задачу в очередь"""
        task = Task(
            product_image_url=product_image_url,
            background_image_url=background_image_url,
            callback=callback
        )
        await self.queue.put(task)

    async def start(self) -> None:
        """Запускает обработчик очереди"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Останавливает обработчик очереди"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_queue(self) -> None:
        """Обрабатывает задачи из очереди"""
        while self._running:
            task = await self.queue.get()

            api_key = await self.account_manager.get_available_account()
            if not api_key:
                await asyncio.sleep(1)
                continue

            try:
                account = self.account_manager.accounts[api_key]
                task_id = await self.runninghub_api.create_task(
                    api_key=api_key,
                    workflow_id=account.workflow_id,
                    product_image_url=task.product_image_url,
                    background_image_url=task.background_image_url
                )

                if task_id:
                    results = await self._wait_for_task_completion(
                        api_key=api_key,
                        task_id=task_id
                    )
                    await task.callback(results)
                else:
                    await task.callback(None)

            except Exception as e:
                if task.retries < 3:
                    task.retries += 1
                    await self.queue.put(task)
                else:
                    await task.callback(None)
            finally:
                await self.account_manager.release_account(api_key)
                self.queue.task_done()

    async def _wait_for_task_completion(
        self,
        api_key: str,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Ожидает завершения задачи"""
        while True:
            await asyncio.sleep(5)
            results = await self.runninghub_api.get_task_outputs(
                api_key=api_key,
                task_id=task_id
            )
            if results:
                return results
