from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [
            InlineKeyboardButton(text="🖼 Сгенерировать", callback_data="generate"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата"""
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после генерации"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Сгенерировать ещё", callback_data="generate"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
