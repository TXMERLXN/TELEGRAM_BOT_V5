import asyncio
import logging
import sys
import signal
from typing import Optional, Coroutine, Any

logger = logging.getLogger(__name__)

class EventLoopManager:
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: set = set()
        self._is_closing = False

    def initialize(self):
        """Инициализация event loop с расширенной обработкой"""
        try:
            # Используем uvloop для повышения производительности, если доступен
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            logger.warning("uvloop не установлен, используется стандартный event loop")

        # Создаем новый event loop
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Настройка обработчиков сигналов
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(
                sig, 
                lambda s=sig: asyncio.create_task(self.graceful_shutdown(s))
            )

        logger.info("Event loop initialized successfully")
        return self._loop

    def run(self, coro: Coroutine[Any, Any, Any]):
        """Безопасный запуск корутины"""
        if not self._loop:
            self.initialize()

        try:
            return self._loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Ошибка при выполнении корутины: {e}")
            raise
        finally:
            if not self._loop.is_closed():
                self.close()

    def create_task(self, coro: Coroutine[Any, Any, Any], name: Optional[str] = None):
        """Создание задачи с безопасным добавлением в список"""
        if not self._loop:
            self.initialize()

        task = self._loop.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def graceful_shutdown(self, sig=None):
        """Корректное завершение всех задач"""
        if self._is_closing:
            return

        self._is_closing = True
        logger.info(f"Получен сигнал завершения: {sig}")

        # Отмена всех активных задач
        for task in list(self._tasks):
            if not task.done():
                task.cancel()

        # Ожидание завершения задач с таймаутом
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка при завершении задач: {e}")

        # Остановка event loop
        if self._loop and not self._loop.is_closed():
            self._loop.stop()

    def close(self):
        """Безопасное закрытие event loop"""
        logger.info("Initiating event loop closure")

        if not self._loop:
            return

        try:
            # Отмена всех незавершенных задач
            if not self._loop.is_closed():
                logger.info(f"Cancelling {len(self._tasks)} pending tasks")
                for task in list(self._tasks):
                    if not task.done():
                        task.cancel()

                # Попытка корректного закрытия
                self._loop.run_until_complete(
                    asyncio.gather(*self._tasks, return_exceptions=True)
                )
                
                self._loop.close()
                logger.info("Event loop closed successfully")
        except Exception as e:
            logger.error(f"Unexpected error during event loop closure: {e}")
        finally:
            # Сброс глобального event loop
            asyncio.set_event_loop(None)
            self._loop = None
            self._tasks.clear()

# Глобальный менеджер event loop
event_loop_manager = EventLoopManager()
