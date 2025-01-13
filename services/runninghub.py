import asyncio
import logging
import os
from pathlib import Path
import aiohttp
from typing import Optional, Dict, Any, Tuple

from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

class RunningHubAPI:
    """Класс для работы с API RunningHub"""
    
    def __init__(
        self,
        bot: Bot,
        api_url: str,
        task_timeout: int = 300,
        retry_delay: int = 5,
        max_retries: int = 3,
        polling_interval: int = 2
    ):
        self.bot = bot
        self.api_url = api_url.rstrip('/')
        self.task_timeout = task_timeout
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.polling_interval = polling_interval
        self.session = None
        
        # Создаем директорию для временных файлов
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        
    async def initialize(self):
        """Инициализация сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            self.session = None

    async def process_photos(
        self,
        product_photo_id: str,
        background_photo_id: str,
        user_id: int
    ) -> Optional[str]:
        """
        Обработка фотографий через RunningHub API
        
        Args:
            product_photo_id: ID фото продукта в Telegram
            background_photo_id: ID фото фона в Telegram
            user_id: ID пользователя
            
        Returns:
            str: Путь к сгенерированному изображению или None в случае ошибки
        """
        product_path = self.temp_dir / f"product_{user_id}.jpg"
        background_path = self.temp_dir / f"background_{user_id}.jpg"
        
        try:
            # Скачиваем фотографии
            await self._download_photo(product_photo_id, str(product_path))
            await self._download_photo(background_photo_id, str(background_path))
            
            # Создаем задачу
            task_id = await self.create_task(str(product_path), str(background_path))
            if not task_id:
                raise Exception("Failed to create task")
            
            # Ждем результат
            result = await self._wait_for_result(task_id)
            if not result:
                raise Exception("Failed to get result")
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing photos: {str(e)}")
            return None
        finally:
            # Удаляем временные файлы
            try:
                if product_path.exists():
                    product_path.unlink()
                if background_path.exists():
                    background_path.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up temp files: {str(e)}")
            
    async def _download_photo(self, file_id: str, save_path: str) -> None:
        """Скачивание фото из Telegram"""
        file = await self.bot.get_file(file_id)
        await self.bot.download_file(file.file_path, save_path)
        
    async def create_task(self, product_path: str, background_path: str) -> Optional[str]:
        """Создание задачи в RunningHub"""
        try:
            data = aiohttp.FormData()
            data.add_field('product_image',
                          open(product_path, 'rb'),
                          filename='product.jpg',
                          content_type='image/jpeg')
            data.add_field('background_image',
                          open(background_path, 'rb'),
                          filename='background.jpg',
                          content_type='image/jpeg')
            
            async with self.session.post(f"{self.api_url}/tasks", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('task_id')
                else:
                    logger.error(f"Error creating task: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return None
            
    async def _wait_for_result(self, task_id: str) -> Optional[str]:
        """Ожидание результата генерации"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > self.task_timeout:
                logger.error("Task timeout")
                return None
                
            try:
                async with self.session.get(f"{self.api_url}/tasks/{task_id}") as response:
                    if response.status != 200:
                        logger.error(f"Error checking task status: {response.status}")
                        return None
                        
                    result = await response.json()
                    status = result.get('status')
                    
                    if status == 'completed':
                        return result.get('result_url')
                    elif status == 'failed':
                        logger.error("Task failed")
                        return None
                        
                    # Ждем перед следующей проверкой
                    await asyncio.sleep(self.polling_interval)
                    
            except Exception as e:
                logger.error(f"Error checking task status: {str(e)}")
                return None
