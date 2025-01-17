import asyncio
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .account_manager import AccountManager
from .runninghub_api import RunningHubAPI
from .account_manager import account_manager

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
        self._lock = asyncio.Lock()
        self.loop = None  

    async def add_task(
        self,
        product_image_url: str,
        background_image_url: str,
        callback: Any
    ) -> bool:
        """Добавляет задачу в очередь"""
        if not self.account_manager.has_available_accounts():
            logger.warning("No available accounts to process new task")
            return False
            
        task = Task(
            product_image_url=product_image_url,
            background_image_url=background_image_url,
            callback=callback
        )
        await self.queue.put(task)
        logger.info(f"Added new task to queue (queue size: {self.queue.qsize()})")
        return True

    async def start(self) -> None:
        """Запускает обработчик очереди"""
        if self._running:
            return

        # Инициализируем loop при старте, если он не установлен
        if self.loop is None:
            self.loop = asyncio.get_event_loop()

        self._running = True
        self._task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Останавливает обработчик очереди"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _cancel_task(self, task: asyncio.Task) -> None:
        """Корректно отменяет задачу"""
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _process_queue(self) -> None:
        """Обрабатывает задачи из очереди"""
        while self._running:
            try:
                task = await self.queue.get()
                async with self._lock:
                    # Логика обработки задачи
                    logger.info(f"Processing task: {task}")
                    # Здесь будет ваша основная логика обработки задачи
                    self.queue.task_done()
            except Exception as e:
                logger.error(f"Error processing task: {e}")

    async def _wait_for_task_completion(
        self,
        api_key: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Ожидает завершения задачи"""
        try:
            result = await self.runninghub_api.wait_for_task(
                api_key=api_key,
                task_id=task_id
            )
            return result
        except Exception as e:
            logger.error(f"Error waiting for task completion: {e}")
            return {}

# Создаем экземпляр TaskQueue
task_queue = TaskQueue(account_manager)
