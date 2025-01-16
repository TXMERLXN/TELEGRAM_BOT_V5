import asyncio
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .account_manager import AccountManager
from .runninghub import RunningHubAPI
from .event_loop import event_loop_manager
import time
import threading

logger = logging.getLogger(__name__)

@dataclass
class Task:
    product_image_url: str
    background_image_url: str
    callback: Any
    retries: int = 0

class TaskQueue:
    def __init__(self, account_manager: AccountManager):
        # Используем глобальный event loop с дополнительной защитой
        self.loop = event_loop_manager.loop
        
        # Создаем очередь с использованием глобального event loop
        self.queue = asyncio.Queue(loop=self.loop)
        
        self.account_manager = account_manager
        self.runninghub_api = RunningHubAPI()
        
        # Потокобезопасный флаг состояния
        self._running = threading.Event()
        
        self._task = None
        self._lock = asyncio.Lock(loop=self.loop)
        self._tasks = set()  # Хранение всех активных задач
        
        # Добавляем логирование состояния очереди
        self._last_queue_log_time = time.time()

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

    async def start(self):
        """Запуск обработчика очереди с использованием глобального event loop"""
        # Проверяем, что обработчик еще не запущен
        if not self._running.is_set():
            async with self._lock:
                # Двойная проверка для потокобезопасности
                if not self._running.is_set():
                    self._running.set()
                    # Создаем задачу с использованием глобального event loop
                    self._task = event_loop_manager.create_task(
                        self._process_queue(), 
                        name="TaskQueue_Processing"
                    )
                    self._tasks.add(self._task)
                    logger.info("Task queue processing started")
                    return True
        
        logger.warning("Task queue is already running")
        return False

    async def stop(self) -> None:
        """Улучшенная остановка обработчика очереди"""
        logger.info("Останавливаем обработчик очереди...")
        try:
            # Сбрасываем флаг работы
            self._running.clear()

            # Отмена всех активных задач
            if self._task:
                try:
                    # Используем глобальный event loop для отмены задачи
                    self._task.cancel()
                    await asyncio.wait([self._task], timeout=5.0)
                except asyncio.CancelledError:
                    logger.info("Задача обработчика очереди успешно отменена")
                except Exception as cancel_error:
                    logger.error(f"Ошибка при отмене задачи обработчика: {cancel_error}", exc_info=True)

            # Очистка множества задач
            for task in list(self._tasks):
                try:
                    task.cancel()
                except Exception as task_error:
                    logger.error(f"Ошибка при отмене задачи: {task_error}", exc_info=True)
            
            # Ожидание завершения всех задач
            if self._tasks:
                try:
                    await asyncio.wait(list(self._tasks), timeout=10.0)
                except asyncio.TimeoutError:
                    logger.warning("Тайм-аут при ожидании завершения задач")

            # Очистка очереди
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty:
                    break

        except Exception as e:
            logger.error(f"Критическая ошибка при остановке: {e}", exc_info=True)
        finally:
            logger.info("Обработчик очереди остановлен")
            # Сброс состояния
            self._task = None
            self._tasks.clear()

    async def _cancel_task(self, task: asyncio.Task) -> None:
        """Корректно отменяет задачу"""
        if task.done():
            return
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи: {e}", exc_info=True)

    async def _process_queue(self):
        """Обработка задач из очереди с расширенной диагностикой"""
        logger.info("Starting queue processing loop")
        
        # Счетчик для ограничения логирования отсутствия аккаунтов
        no_accounts_log_counter = 0
        
        # Используем флаг для контроля цикла
        while self._running.is_set():
            try:
                # Периодическое логирование состояния очереди
                current_time = time.time()
                if current_time - self._last_queue_log_time > 60:  # Логируем каждую минуту
                    logger.info(f"Queue status: size={self.queue.qsize()}, running={self._running.is_set()}")
                    self._last_queue_log_time = current_time

                # Проверка доступности аккаунтов перед ожиданием задачи
                if not self.account_manager.has_available_accounts():
                    # Логируем каждые 5 попыток, чтобы не засорять логи
                    no_accounts_log_counter += 1
                    if no_accounts_log_counter % 5 == 0:
                        logger.warning(f"No available accounts for {no_accounts_log_counter} attempts")
                    
                    await asyncio.sleep(5)
                    continue

                # Сбрасываем счетчик при появлении аккаунтов
                no_accounts_log_counter = 0

                # Ожидание задачи с таймаутом и логированием
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.debug("Queue wait timeout, continuing...")
                    continue

                # Получение API ключа
                api_key = await self.account_manager.get_available_account()
                
                if not api_key:
                    logger.warning("No API key available, returning task to queue")
                    await self.queue.put(task)
                    await asyncio.sleep(1)
                    continue

                try:
                    # Выполнение задачи с логированием
                    logger.info(f"Processing task from queue. Current queue size: {self.queue.qsize()}")
                    await self._execute_task(task, api_key)
                except Exception as task_error:
                    logger.error(f"Error executing task: {task_error}", exc_info=True)
                finally:
                    await self.account_manager.release_account(api_key)
                    self.queue.task_done()

            except Exception as e:
                logger.error(f"Unexpected error in queue processing: {e}", exc_info=True)
                
                # Попытка восстановления
                try:
                    # Пересоздаем очередь с использованием глобального event loop
                    self.queue = asyncio.Queue(loop=self.loop)
                    logger.warning("Queue recreated after error")
                except Exception as recovery_error:
                    logger.error(f"Failed to recover queue: {recovery_error}", exc_info=True)
                    break

        logger.info("Queue processing loop ended")

    async def _execute_task(self, task: Task, api_key: str) -> None:
        """Выполнение задачи"""
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
