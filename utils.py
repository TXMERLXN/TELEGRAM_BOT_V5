import os
import logging
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования DEBUG
