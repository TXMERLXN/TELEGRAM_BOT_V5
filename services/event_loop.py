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
            return self._loop.run_until_complete(coro)
        except RuntimeError:
            # Пересоздание event loop при ошибке
            logger.warning("RuntimeError in event loop, reinitializing")
            self._initialize_loop()
            return self._loop.run_until_complete(coro)

    def create_task(self, coro):
        """Создание задачи в текущем event loop с логированием"""
        try:
            task = asyncio.ensure_future(coro, loop=self.loop)
            logger.debug(f"Task created: {task}")
            return task
        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            raise

    def close(self):
        """Безопасное закрытие event loop"""
        if self._loop and not self._loop.is_closed():
            try:
                logger.info("Closing event loop")
                self._loop.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии event loop: {e}", exc_info=True)

# Создаем единственный экземпляр менеджера event loop
event_loop_manager = EventLoopManager()
