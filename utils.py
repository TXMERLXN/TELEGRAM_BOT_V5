import os
import logging
import time
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup, FSInputFile

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования DEBUG

def get_animation_file() -> Optional[FSInputFile]:
    """Загружает файл GIF анимации"""
    assets_dir = 'assets'
    animation_path = os.path.join(assets_dir, 'upload_animation.gif')
    json_path = os.path.join(assets_dir, 'upload_animation.json')
    
    # Логируем текущую директорию
    current_dir = os.getcwd()
    logger.debug(f"Текущая директория: {current_dir}")
    
    # Проверяем наличие обоих файлов
    if os.path.exists(json_path):
        logger.warning(f"JSON файл всё ещё существует: {json_path}")
        try:
            os.remove(json_path)
            logger.info("Удалили старый JSON файл")
        except Exception as e:
            logger.error(f"Ошибка при удалении JSON файла: {e}")
    
    # Логируем содержимое директории assets
    if os.path.exists(assets_dir):
        files = os.listdir(assets_dir)
        logger.debug(f"Файлы в директории {assets_dir}: {files}")
        
        # Проверяем размер GIF файла
        if os.path.exists(animation_path):
            size = os.path.getsize(animation_path)
            logger.debug(f"Размер GIF файла: {size} байт")
    else:
        logger.error(f"Директория {assets_dir} не существует")
        try:
            os.makedirs(assets_dir)
            logger.info(f"Создали директорию {assets_dir}")
        except Exception as e:
            logger.error(f"Ошибка при создании директории: {e}")
    
    logger.debug(f"Путь к файлу анимации: {animation_path}")
    logger.debug(f"Файл существует: {os.path.exists(animation_path)}")
    
    if os.path.exists(animation_path):
        # Добавляем timestamp к имени файла для избежания кэширования
        return FSInputFile(animation_path, filename=f"upload_animation_{int(time.time())}.gif")
    
    logger.error("GIF файл не найден")
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
            logger.debug("Пытаемся отправить GIF анимацию")
            return await message.answer_animation(
                animation=animation,
                caption=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки анимации: {e}")
            return await message.answer(text, reply_markup=reply_markup)
    return await message.answer(text, reply_markup=reply_markup)
