import os
import logging
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup

logger = logging.getLogger(__name__)
# Устанавливаем уровень логирования в зависимости от окружения
if os.getenv('ENVIRONMENT') == 'production':
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.DEBUG)
