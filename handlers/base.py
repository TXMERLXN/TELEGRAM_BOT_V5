import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from messages import WELCOME_MESSAGE, HELP_MESSAGE
from keyboards import get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        WELCOME_MESSAGE(message.from_user.first_name),
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    logger.info(f"User {message.from_user.id} requested help")
    await message.answer(
        HELP_MESSAGE(),
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    logger.info(f"User {callback.from_user.id} clicked help button")
    await callback.message.answer(
        HELP_MESSAGE(),
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
