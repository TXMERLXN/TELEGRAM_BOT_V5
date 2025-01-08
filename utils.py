import os
import logging
import time
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup, FSInputFile, BufferedInputFile

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования DEBUG

def get_animation_file() -> Optional[Union[FSInputFile, BufferedInputFile]]:
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
        try:
            # Читаем файл в память
            with open(animation_path, 'rb') as file:
                content = file.read()
                logger.debug(f"Прочитан GIF файл размером {len(content)} байт")
                # Создаем BufferedInputFile с уникальным именем
                return BufferedInputFile(content, filename=f"upload_{int(time.time())}.gif")
        except Exception as e:
            logger.error(f"Ошибка при чтении GIF файла: {e}")
    else:
        logger.error(f"GIF файл не найден по пути: {animation_path}")
        # Проверяем содержимое директории
        if os.path.exists(assets_dir):
            files = os.listdir(assets_dir)
            logger.debug(f"Файлы в директории {assets_dir}: {files}")
        else:
            logger.error(f"Директория {assets_dir} не существует")
    
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
            logger.debug("Отправляем GIF анимацию")
            return await message.answer_animation(
                animation=animation,
                caption=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки анимации: {e}")
            return await message.answer(text, reply_markup=reply_markup)
    
    logger.warning("Анимация не найдена, отправляем сообщение без анимации")
    return await message.answer(text, reply_markup=reply_markup)
