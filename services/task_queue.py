import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from config import load_config
from typing import Optional

config = load_config()
logger = logging.getLogger(__name__)

@dataclass
class TaskInfo:
    user_id: int
    task_id: str
    start_time: datetime
    status: str
    result_url: Optional[str] = None
    retries: int = 0
    error_message: Optional[str] = None

class TaskQueue:
    def __init__(self):
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(config.runninghub.max_concurrent_tasks)
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()
        
    async def add_task(self, user_id: int, task_id: str) -> None:
        """Добавляет задачу в очередь"""
        task_info = TaskInfo(
            user_id=user_id,
            task_id=task_id,
            start_time=datetime.now(),
            status="queued"
        )
        self.active_tasks[task_id] = task_info
        await self.queue.put(task_id)
        logger.info(f"Task {task_id} added to queue for user {user_id}")

    async def get_next_task(self) -> Optional[str]:
        """Получает следующую задачу из очереди"""
        try:
            return await self.queue.get()
        except asyncio.QueueEmpty:
            return None

    def update_task_status(self, task_id: str, status: str, result_url: Optional[str] = None, error_message: Optional[str] = None) -> None:
        """Обновляет статус задачи"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id]
            task_info.status = status
            if result_url:
                task_info.result_url = result_url
            if error_message:
                task_info.error_message = error_message
            logger.info(f"Task {task_id} status updated to {status}")

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Получает информацию о задаче"""
        return self.active_tasks.get(task_id)

    def remove_task(self, task_id: str) -> None:
        """Удаляет задачу из очереди"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            # Отменяем выполняющуюся задачу, если она есть
            if task_id in self.processing_tasks:
                self.processing_tasks[task_id].cancel()
                del self.processing_tasks[task_id]
            logger.info(f"Task {task_id} removed from queue")

    async def process_task(self, task_id: str, process_func) -> None:
        """Обрабатывает задачу с использованием семафора"""
        async with self.semaphore:
            try:
                self.update_task_status(task_id, "processing")
                # Сохраняем задачу для возможности отмены
                processing_task = asyncio.create_task(process_func(task_id))
                self.processing_tasks[task_id] = processing_task
                
                try:
                    result = await processing_task
                    if result:
                        self.update_task_status(task_id, "completed", result)
                    else:
                        self.update_task_status(task_id, "failed", error_message="Task failed to complete")
                except asyncio.CancelledError:
                    self.update_task_status(task_id, "cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Error processing task {task_id}: {str(e)}")
                    self.update_task_status(task_id, "failed", error_message=str(e))
            finally:
                self.processing_tasks.pop(task_id, None)
                self.queue.task_done()

    def cancel_user_tasks(self, user_id: int) -> None:
        """Отменяет все задачи пользователя"""
        for task_id, task_info in list(self.active_tasks.items()):
            if task_info.user_id == user_id:
                self.remove_task(task_id)

    async def cleanup_old_tasks(self, max_age_seconds: int = 3600) -> None:
        """Очищает старые задачи"""
        now = datetime.now()
        for task_id, task_info in list(self.active_tasks.items()):
            age = (now - task_info.start_time).total_seconds()
            if age > max_age_seconds:
                self.remove_task(task_id)

    async def cancel_all_tasks(self):
        """Отменяет все активные задачи"""
        logger.info("Cancelling all active tasks")
        async with self.lock:
            for task_id in list(self.active_tasks.keys()):
                task = self.active_tasks[task_id]
                if task.status == "processing":
                    logger.info(f"Cancelling task {task_id}")
                    self.remove_task(task_id)
            self.active_tasks.clear()

# Глобальный экземпляр очереди задач
task_queue = TaskQueue()
