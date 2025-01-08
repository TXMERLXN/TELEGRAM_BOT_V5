import json
import os
from typing import Optional
from aiogram.types import Message

def get_animation_data() -> Optional[str]:
    """Загружает данные анимации из JSON файла"""
    animation_path = os.path.join('assets', 'upload_animation.json')
    try:
        with open(animation_path, 'r') as f:
            return json.dumps(json.load(f))
    except Exception as e:
        print(f"Error loading animation: {e}")
        return None

async def send_upload_animation(message: Message, text: str) -> Optional[Message]:
    """Отправляет сообщение с анимацией загрузки"""
    animation_data = get_animation_data()
    if animation_data:
        return await message.answer_animation(
            animation=animation_data,
            caption=text
        )
    return await message.answer(text)
