import asyncio
import threading
import sys
import logging

logger = logging.getLogger(__name__)

class EventLoopManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize_loop()
        return cls._instance

    def _initialize_loop(self):
        """Инициализация event loop с расширенной диагностикой"""
        try:
            # Попытка получить текущий event loop
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            # Создание нового event loop
            self._loop = asyncio.new_event_loop()
        
        # Безусловная установка event loop для текущего потока
        asyncio.set_event_loop(self._loop)

        # Добавление обработчика необработанных исключений
        self._loop.set_exception_handler(self._handle_exception)
        
        logger.info("Event loop initialized successfully")

    def _handle_exception(self, loop, context):
        """Расширенная обработка исключений в event loop"""
        exception = context.get('exception')
        message = context.get('message', 'Неизвестная ошибка')
        
        # Логирование полной информации об исключении
        logger.error(f"Event Loop Exception: {message}")
        if exception:
            logger.error(f"Exception details: {exception}", exc_info=True)
        
        # Попытка восстановления
        try:
            self._initialize_loop()
            logger.warning("Event loop reinitialized after exception")
        except Exception as e:
            logger.error(f"Ошибка восстановления event loop: {e}", exc_info=True)
            sys.exit(1)

    @property
    def loop(self):
        """Возвращает текущий event loop с дополнительной проверкой"""
        if not self._loop or self._loop.is_closed():
            logger.warning("Event loop is closed, reinitializing")
            self._initialize_loop()
        return self._loop

    def run(self, coro):
        """Запуск корутины с расширенной обработкой ошибок"""
        try:
            # Проверка, что передан корректный объект
            if not asyncio.iscoroutine(coro):
                coro = asyncio.create_task(coro)
            
            return self._loop.run_until_complete(coro)
        except RuntimeError as runtime_err:
            # Обработка ошибок, связанных с закрытием loop
            if "Event loop is closed" in str(runtime_err):
                logger.warning("Event loop was closed, reinitializing")
                self._initialize_loop()
                return self._loop.run_until_complete(coro)
            raise
        except Exception as e:
            logger.error(f"Ошибка при выполнении корутины: {e}", exc_info=True)
            raise

    def create_task(self, coro, name=None):
        """Создание задачи в текущем event loop с расширенной обработкой"""
        try:
            # Проверка, что передан корректный объект
            if not asyncio.iscoroutine(coro):
                logger.warning("Passed object is not a coroutine, converting")
                coro = asyncio.create_task(coro)
            
            # Создание задачи с именем
            task = self._loop.create_task(coro, name=name)
            
            # Добавление обработчика исключений
            def exception_handler(task):
                try:
                    task.result()
                except asyncio.CancelledError:
                    logger.info(f"Задача {name or 'unnamed'} отменена")
                except Exception as e:
                    logger.error(f"Необработанное исключение в задаче {name or 'unnamed'}: {e}", exc_info=True)
            
            task.add_done_callback(exception_handler)
            
            return task
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}", exc_info=True)
            raise

    def close(self):
        """Безопасное закрытие event loop с принудительной остановкой"""
        logger.info("Initiating event loop closure")
        try:
            # Проверяем, что loop существует и не закрыт
            if self._loop and not self._loop.is_closed():
                # Получаем все активные задачи
                pending_tasks = asyncio.all_tasks(loop=self._loop)
                
                if pending_tasks:
                    logger.info(f"Cancelling {len(pending_tasks)} pending tasks")
                    
                    # Отменяем все задачи
                    for task in pending_tasks:
                        if not task.done():
                            task.cancel()
                    
                    # Ожидаем завершения задач с таймаутом
                    try:
                        self._loop.run_until_complete(
                            asyncio.wait(pending_tasks, timeout=5.0)
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Timeout while waiting for tasks to complete")
                
                # Останавливаем асинхронные генераторы
                try:
                    self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                except Exception as gen_error:
                    logger.error(f"Error shutting down async generators: {gen_error}")
                
                # Принудительное закрытие loop
                try:
                    # Используем stop() для остановки loop
                    self._loop.stop()
                    
                    # Форсированное закрытие
                    self._loop.close()
                    logger.info("Event loop successfully closed")
                except Exception as close_error:
                    logger.error(f"Error during event loop closure: {close_error}")
            else:
                logger.warning("Event loop is already closed or not initialized")
        
        except Exception as e:
            logger.error(f"Unexpected error during event loop closure: {e}", exc_info=True)
        finally:
            # Пересоздаем loop на случай повторного использования
            self._initialize_loop()

# Создаем единственный экземпляр менеджера event loop
event_loop_manager = EventLoopManager()
