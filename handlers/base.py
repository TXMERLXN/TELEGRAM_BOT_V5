from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_keyboard, get_back_keyboard
from messages import WELCOME_MESSAGE, HELP_MESSAGE

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start
    """
    # Сбрасываем состояние
    await state.clear()
    # Отправляем приветственное сообщение
    await message.answer(
        WELCOME_MESSAGE(message.from_user.first_name),
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """
    Возврат в главное меню
    """
    # Сбрасываем состояние
    await state.clear()
    # Отвечаем на callback
    await callback.answer()
    # Отправляем новое сообщение вместо редактирования
    await callback.message.answer(
        WELCOME_MESSAGE(callback.from_user.first_name),
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    """
    Обработчик кнопки помощи
    """
    # Отвечаем на callback
    await callback.answer()
    # Отправляем новое сообщение вместо редактирования
    await callback.message.answer(
        HELP_MESSAGE(),
        reply_markup=get_back_keyboard()
    )
