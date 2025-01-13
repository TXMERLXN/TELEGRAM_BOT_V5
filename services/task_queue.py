import asyncio
import logging
from typing import Dict, Optional, Any, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from config import load_config

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
    callback: Optional[Callable] = None
    args: Optional[tuple] = None

class TaskQueue:
    def __init__(self):
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(config.runninghub.max_concurrent_tasks)
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()
        
    async def add_task(self, callback: Callable[..., Awaitable[Any]], *args) -> Any:
        """
        Добавляет задачу в очередь
        
        Args:
            callback: Функция для выполнения
            *args: Аргументы для функции
            
        Returns:
            Результат выполнения функции
        """
        task_id = f"{len(self.active_tasks) + 1}"
        user_id = args[-1] if args else 0  # Последний аргумент - user_id
        
        task_info = TaskInfo(
            user_id=user_id,
            task_id=task_id,
            start_time=datetime.now(),
            status="queued",
            callback=callback,
            args=args
        )
        
        self.active_tasks[task_id] = task_info
        logger.info(f"Task {task_id} added to queue for user {user_id}")
        
        # Выполняем функцию
        try:
            result = await callback(*args)
            task_info.status = "completed"
            task_info.result_url = result
            return result
        except Exception as e:
            task_info.status = "failed"
            task_info.error_message = str(e)
            raise

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
        """Удаляет задачу"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            logger.info(f"Task {task_id} removed")

    async def process_task(self, task_id: str) -> None:
        """Обрабатывает задачу"""
        if task_id not in self.active_tasks:
            return

        task_info = self.active_tasks[task_id]
        if not task_info.callback:
            return

        try:
            async with self.semaphore:
                result = await task_info.callback(*task_info.args)
                self.update_task_status(task_id, "completed", result_url=result)
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            self.update_task_status(task_id, "failed", error_message=str(e))
        finally:
            if task_id in self.processing_tasks:
                del self.processing_tasks[task_id]

    def get_active_tasks_count(self) -> int:
        """Возвращает количество активных задач"""
        return len(self.active_tasks)

    def get_user_tasks(self, user_id: int) -> Dict[str, TaskInfo]:
        """Получает все задачи пользователя"""
        return {
            task_id: task_info
            for task_id, task_info in self.active_tasks.items()
            if task_info.user_id == user_id
        }

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
