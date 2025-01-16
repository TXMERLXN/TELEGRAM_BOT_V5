import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_ACCOUNT_LOAD = 5
RETRY_DELAY = 30  # Секунд между попытками
MAX_RETRY_ATTEMPTS = 50

@dataclass
class TaskQueueConfig:
    max_concurrent_tasks: int = 10
    retry_delay: int = RETRY_DELAY
    max_retry_attempts: int = MAX_RETRY_ATTEMPTS

class TaskQueue:
    def __init__(self, accounts: List[Dict], config: TaskQueueConfig = TaskQueueConfig()):
        self.accounts = accounts
        self.config = config
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.current_tasks: List[asyncio.Task] = []
        self._retry_count = 0

    async def start(self):
        """Запуск обработчика очереди задач"""
        if not self.running:
            self.running = True
            logger.info("Starting queue processing loop")
            await self._process_queue()

    async def stop(self):
        """Остановка обработчика очереди задач"""
        if self.running:
            self.running = False
            # Отмена всех текущих задач
            for task in self.current_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self.current_tasks, return_exceptions=True)
            logger.info("Queue processing stopped")

    async def add_task(self, task_data: Dict[str, Any]):
        """Добавление задачи в очередь"""
        await self.queue.put(task_data)
        logger.info(f"Task added to queue. Current queue size: {self.queue.qsize()}")

    async def _process_queue(self):
        """Основной цикл обработки задач"""
        while self.running:
            try:
                # Проверка статуса очереди
                logger.info(f"Queue status: size={self.queue.qsize()}, running={self.running}")

                # Ожидание задачи с таймаутом
                try:
                    task_data = await asyncio.wait_for(self.queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    continue

                # Поиск доступного аккаунта
                account = await self._find_available_account()
                if not account:
                    # Возврат задачи в очередь, если нет доступных аккаунтов
                    await self.queue.put(task_data)
                    await self._handle_no_available_accounts()
                    continue

                # Создание и запуск задачи
                task = asyncio.create_task(self._execute_task(account, task_data))
                self.current_tasks.append(task)
                task.add_done_callback(self.current_tasks.remove)

                # Освобождение слота в очереди
                self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processing: {e}")
                await asyncio.sleep(5)

    async def _find_available_account(self) -> Optional[Dict]:
        """Поиск свободного аккаунта для выполнения задачи"""
        available_accounts = [
            account for account in self.accounts 
            if account.get('current_load', 0) < MAX_ACCOUNT_LOAD
        ]
        return available_accounts[0] if available_accounts else None

    async def _execute_task(self, account: Dict, task_data: Dict):
        """Выполнение задачи с использованием выбранного аккаунта"""
        try:
            # Увеличение нагрузки на аккаунт
            account['current_load'] = account.get('current_load', 0) + 1
            
            # Выполнение задачи
            result = await self._process_task(account, task_data)
            
            return result
        except Exception as e:
            logger.error(f"Task execution error: {e}")
        finally:
            # Уменьшение нагрузки на аккаунт
            account['current_load'] = max(0, account.get('current_load', 0) - 1)

    async def _process_task(self, account: Dict, task_data: Dict):
        """Абстрактный метод обработки задачи"""
        # Здесь должна быть реализация обработки конкретной задачи
        logger.info(f"Processing task with account {account.get('id')}")
        await asyncio.sleep(1)  # Имитация работы

    async def _handle_no_available_accounts(self):
        """Обработка ситуации отсутствия доступных аккаунтов"""
        self._retry_count += 1
        
        if self._retry_count > self.config.max_retry_attempts:
            logger.critical("Max retry attempts reached. Stopping queue processing.")
            await self.stop()
            return

        logger.warning(f"No available accounts for {self._retry_count} attempts")
        
        # Экспоненциальная задержка
        delay = min(
            self.config.retry_delay * (2 ** self._retry_count), 
            300  # Максимальная задержка 5 минут
        )
        
        await asyncio.sleep(delay)

# Глобальный экземпляр TaskQueue
task_queue = TaskQueue([])
