import asyncio
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .account_manager import AccountManager
from .runninghub import RunningHubAPI

logger = logging.getLogger(__name__)

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
        
        # Получаем текущий event loop
        loop = asyncio.get_running_loop()
        
        # Отменяем все задачи в очереди
        while not self.queue.empty():
            task = self.queue.get_nowait()
            if hasattr(task, 'callback'):
                try:
                    # Создаем новую задачу в текущем loop
                    callback_task = loop.create_task(task.callback(None))
                    await callback_task
                except Exception:
                    pass
            self.queue.task_done()

        # Отменяем основной обработчик
        if self._task:
            try:
                # Создаем новую задачу в текущем loop для отмены
                cancel_task = asyncio.create_task(self._task.cancel())
                await asyncio.wait_for(cancel_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.error(f"Error during task cancellation: {e}")
                # Принудительно завершаем задачу, если отмена не удалась
                if not self._task.done():
                    self._task.cancel()

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

# Создаем экземпляр TaskQueue
from .account_manager import account_manager
task_queue = TaskQueue(account_manager)
