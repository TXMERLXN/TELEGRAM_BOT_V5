import asyncio

class EventLoopManager:
    _instance = None
    _loop = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._loop = asyncio.get_event_loop()
        return cls._instance

    @property
    def loop(self):
        return self._loop

    def run(self, coro):
        """Запускает корутину в текущем event loop"""
        return asyncio.run(coro, loop=self._loop)

# Создаем единственный экземпляр менеджера event loop
event_loop_manager = EventLoopManager()
