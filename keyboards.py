from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_keyboard():
    """
    Создает основную клавиатуру бота с функциями генерации
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки воркфлоу
    builder.button(text="📷 Сгенерировать фото продукта", callback_data="product")
    builder.button(text="❓ Помощь", callback_data="help")
    
    # Располагаем кнопки в одну колонку
    builder.adjust(1)
    
    return builder.as_markup()

def get_back_keyboard():
    """
    Создает клавиатуру с кнопкой возврата в главное меню
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Назад", callback_data="back_to_main")
    return builder.as_markup()

def get_result_keyboard():
    """
    Создает клавиатуру для результата генерации
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📷 Сгенерировать ещё", callback_data="product")
    builder.button(text="↩️ В главное меню", callback_data="back_to_main")
    
    # Располагаем кнопки в одну колонку
    builder.adjust(1)
    
    return builder.as_markup()

def get_cancel_keyboard():
    """
    Создает клавиатуру с кнопкой отмены генерации
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить генерацию", callback_data="cancel_generation")
    return builder.as_markup()
