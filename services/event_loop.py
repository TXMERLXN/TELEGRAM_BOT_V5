import asyncio
import threading

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
        """Инициализация event loop с учетом многопоточности"""
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            # Если текущий event loop не существует, создаем новый
            self._loop = asyncio.new_event_loop()
        
        # Устанавливаем event loop для текущего потока
        asyncio.set_event_loop(self._loop)

    @property
    def loop(self):
        """Возвращает текущий event loop"""
        return self._loop

    def run(self, coro):
        """Запускает корутину в текущем event loop"""
        try:
            return self._loop.run_until_complete(coro)
        except RuntimeError:
            # Если loop закрыт, пересоздаем его
            self._initialize_loop()
            return self._loop.run_until_complete(coro)

    def close(self):
        """Закрывает event loop"""
        if self._loop and not self._loop.is_closed():
            self._loop.close()

# Создаем единственный экземпляр менеджера event loop
event_loop_manager = EventLoopManager()
