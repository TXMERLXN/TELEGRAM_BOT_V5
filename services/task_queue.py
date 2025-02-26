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
        self._lock = asyncio.Lock()
        self.loop = asyncio.get_running_loop()

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
        self._task = self.loop.create_task(self._process_queue())

    async def stop(self) -> None:
        """Останавливает обработчик очереди"""
        async with self._lock:
            if not self._running:
                return
                
            self._running = False
            
            # Отменяем основной обработчик
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    logger.debug("Main task cancelled successfully")
                except Exception as e:
                    logger.error(f"Error during task execution: {e}")
                finally:
                    self._task = None

            # Обрабатываем оставшиеся задачи в очереди
            pending_tasks = []
            try:
                while not self.queue.empty():
                    task = self.queue.get_nowait()
                    if task.callback:
                        try:
                            # Создаем задачу для callback в текущем loop
                            if asyncio.iscoroutinefunction(task.callback):
                                callback_task = asyncio.create_task(
                                    task.callback(None),
                                    name=f"callback_task_{id(task)}"
                                )
                                pending_tasks.append(callback_task)
                            else:
                                # Для синхронных callback'ов используем run_in_executor
                                await asyncio.to_thread(task.callback, None)
                        except Exception as e:
                            logger.error(f"Error during callback execution: {e}", exc_info=True)
                    self.queue.task_done()
            except Exception as e:
                logger.error(f"Error while processing remaining tasks: {e}")

            # Ожидаем завершения всех callback задач
            if pending_tasks:
                try:
                    done, pending = await asyncio.wait(
                        pending_tasks,
                        timeout=5.0,
                        return_when=asyncio.ALL_COMPLETED
                    )
                    
                    if pending:
                        logger.warning(f"{len(pending)} callback tasks still pending")
                        for task in pending:
                            try:
                                # Проверяем что задача принадлежит текущему loop
                                if hasattr(task, '_loop'):
                                    if task._loop is not self.loop:
                                        logger.debug(f"Task {task.get_name()} belongs to different loop {task._loop}, current loop {self.loop}")
                                        # Создаем задачу в правильном loop
                                        if task._loop.is_running():
                                            task._loop.create_task(self._cancel_task(task))
                                        continue
                                    
                                # Убедимся что задача еще не завершена
                                if task.done():
                                    logger.debug(f"Task {task.get_name()} already done")
                                    continue
                                    
                                # Создаем новую задачу в текущем loop для отмены
                                cancel_task = self.loop.create_task(
                                    self._cancel_task(task),
                                    name=f"cancel_task_{id(task)}"
                                )
                                # Добавляем обратный вызов для обработки ошибок
                                cancel_task.add_done_callback(
                                    lambda t: logger.debug(f"Cancel task {id(t)} completed with status: {t.result()}")
                                )
                            except Exception as e:
                                logger.error(f"Error preparing task cancellation: {e}", exc_info=True)
                                continue
                            try:
                                await cancel_task
                            except Exception as e:
                                logger.error(f"Error during task cancellation: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error while waiting for tasks completion: {e}", exc_info=True)

            # Освобождаем все аккаунты
            await self.account_manager.release_all_accounts()

    async def _cancel_task(self, task: asyncio.Task) -> None:
        """Корректно отменяет задачу"""
        if task.done():
            return
            
        # Проверяем принадлежность задачи текущему loop
        if hasattr(task, '_loop') and task._loop is not self.loop:
            logger.debug(f"Task belongs to different loop {task._loop}, current loop {self.loop}")
            if task._loop.is_running():
                # Создаем задачу отмены в правильном loop
                cancel_task = task._loop.create_task(self._cancel_task(task))
                try:
                    await cancel_task
                except Exception as e:
                    logger.error(f"Error cancelling task in different loop: {e}", exc_info=True)
            return
            
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error during task execution: {e}", exc_info=True)

    async def _process_queue(self) -> None:
        """Обрабатывает задачи из очереди"""
        while self._running:
            async with self._lock:
                if not self._running:
                    break
                    
                # Проверяем доступность аккаунтов
                if not self.account_manager.has_available_accounts():
                    await asyncio.sleep(1)
                    continue
                    
                task = await self.queue.get()
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
