import os
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup, FSInputFile

def get_animation_file() -> Optional[FSInputFile]:
    """Загружает файл GIF анимации"""
    animation_path = os.path.join('assets', 'upload_animation.gif')
    if os.path.exists(animation_path):
        return FSInputFile(animation_path)
    return None

async def send_upload_animation(
    message: Message,
    text: str,
    reply_markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]] = None
) -> Optional[Message]:
    """Отправляет сообщение с GIF анимацией загрузки"""
    animation = get_animation_file()
    if animation:
        try:
            return await message.answer_animation(
                animation=animation,
                caption=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Ошибка отправки анимации: {e}")
            return await message.answer(text, reply_markup=reply_markup)
    return await message.answer(text, reply_markup=reply_markup)
