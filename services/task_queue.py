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
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.account_manager = account_manager
        self.runninghub_api = RunningHubAPI()
        self._running = False
        self._task = None
        self._lock = asyncio.Lock(loop=self.loop)
        self._tasks = set()  # Хранение всех активных задач
        
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

        self._running = True
        self._task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Улучшенная остановка обработчика очереди"""
        logger.info("Останавливаем обработчик очереди...")
        
        try:
            # Устанавливаем флаг остановки
            self._running = False
            
            # Защищаем основную задачу от отмены
            if self._task and not self._task.done():
                try:
                    await asyncio.shield(self._task)
                except asyncio.CancelledError:
                    pass
            
            # Корректно завершаем все активные задачи
            pending_tasks = [
                task for task in self._tasks 
                if not task.done()
            ]
            
            if pending_tasks:
                # Собираем результаты с обработкой исключений
                results = await asyncio.gather(
                    *pending_tasks, 
                    return_exceptions=True
                )
                
                # Логируем любые исключения
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Ошибка в задаче: {result}")
            
            # Очищаем оставшиеся задачи
            self._tasks.clear()
            
            # Обработка оставшихся элементов в очереди
            while not self.queue.empty():
                try:
                    task = self.queue.get_nowait()
                    if task.callback:
                        try:
                            await task.callback(None)
                        except Exception as e:
                            logger.error(f"Ошибка в callback: {e}")
                except asyncio.QueueEmpty:
                    break
        
        except Exception as e:
            logger.error(f"Критическая ошибка при остановке: {e}", exc_info=True)
        finally:
            logger.info("Обработчик очереди остановлен")

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

    async def _process_queue(self) -> None:
        """Обрабатывает задачи из очереди"""
        while self._running:
            try:
                # Проверяем доступность аккаунтов
                if not self.account_manager.has_available_accounts():
                    await asyncio.sleep(1)
                    continue
                    
                task = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                api_key = await self.account_manager.get_available_account()
                
                if not api_key:
                    logger.warning("No available accounts, putting task back to queue")
                    await self.queue.put(task)
                    await asyncio.sleep(1)
                    continue
                    
                logger.info(f"Selected account {api_key} for task processing")

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

            except asyncio.TimeoutError:
                logger.warning("Queue processing timed out")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in queue processing: {e}", exc_info=True)
                await asyncio.sleep(1)

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
