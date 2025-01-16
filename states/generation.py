from aiogram.fsm.state import State, StatesGroup

class GenerationState(StatesGroup):
    """Состояния для процесса генерации изображений"""
    waiting_for_product = State()  # Ожидание фото продукта
    waiting_for_background = State()  # Ожидание фото фона
    processing = State()  # Обработка и генерация
