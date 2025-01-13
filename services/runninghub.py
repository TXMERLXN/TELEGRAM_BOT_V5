import asyncio
import logging
import os
from pathlib import Path
import aiohttp
from typing import Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

class RunningHubAPI:
    """Класс для работы с API RunningHub"""
    
    def __init__(
        self,
        bot: Bot,
        api_url: str,
        api_key: str,
        workflow_id: str,
        task_timeout: int = 300,
        retry_delay: int = 5,
        max_retries: int = 3,
        polling_interval: int = 2
    ):
        self.bot = bot
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.task_timeout = task_timeout
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.polling_interval = polling_interval
        self.session = None
        
        # Создаем директорию для временных файлов
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized RunningHubAPI with URL: {self.api_url}")
        
    @asynccontextmanager
    async def get_session(self):
        """Получение сессии с автоматическим закрытием"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(
                total=60,  # Total timeout
                connect=10,  # Connection timeout
                sock_read=30  # Socket read timeout
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Accept': 'application/json',
                    'X-API-Key': self.api_key
                }
            )
            logger.info("Created new aiohttp session")
        try:
            yield self.session
        finally:
            if self.session:
                await self.session.close()
                self.session = None
                logger.info("Closed aiohttp session")
        
    async def initialize(self):
        """Инициализация сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Created new aiohttp session")
            
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Closed aiohttp session")

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
        logger.info(f"Starting photo processing for user {user_id}")
        product_path = self.temp_dir / f"product_{user_id}.jpg"
        background_path = self.temp_dir / f"background_{user_id}.jpg"
        
        try:
            # Скачиваем фотографии
            logger.info(f"Downloading product photo {product_photo_id} to {product_path}")
            await self._download_photo(product_photo_id, str(product_path))
            
            logger.info(f"Downloading background photo {background_photo_id} to {background_path}")
            await self._download_photo(background_photo_id, str(background_path))
            
            # Проверяем, что файлы существуют и не пустые
            if not product_path.exists() or product_path.stat().st_size == 0:
                raise Exception(f"Product file does not exist or is empty: {product_path}")
            if not background_path.exists() or background_path.stat().st_size == 0:
                raise Exception(f"Background file does not exist or is empty: {background_path}")
            
            # Создаем задачу
            logger.info("Creating task with downloaded photos")
            task_id = await self.create_task(str(product_path), str(background_path))
            if not task_id:
                raise Exception("Failed to create task: no task_id returned")
            
            logger.info(f"Task created with ID: {task_id}")
            
            # Ждем результат
            logger.info(f"Waiting for task {task_id} completion")
            result = await self._wait_for_result(task_id)
            if not result:
                raise Exception(f"Task {task_id} failed to complete")
                
            logger.info(f"Task {task_id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing photos: {str(e)}")
            # Не перехватываем исключение, чтобы TaskQueue мог попробовать другой аккаунт
            raise
        finally:
            # Удаляем временные файлы
            try:
                if product_path.exists():
                    product_path.unlink()
                    logger.debug(f"Removed temp file: {product_path}")
                if background_path.exists():
                    background_path.unlink()
                    logger.debug(f"Removed temp file: {background_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temp files: {str(e)}")
            
    async def _download_photo(self, file_id: str, save_path: str) -> None:
        """Скачивание фото из Telegram"""
        try:
            # Получаем информацию о файле
            file = await self.bot.get_file(file_id)
            if not file:
                raise Exception(f"Could not get file info for {file_id}")
                
            # Скачиваем файл напрямую через бота
            await self.bot.download(
                file=file,
                destination=save_path
            )
                        
            logger.info(f"Successfully downloaded photo to {save_path}")
            
        except Exception as e:
            logger.error(f"Error downloading photo: {str(e)}")
            raise
        
    async def create_task(self, product_path: str, background_path: str) -> Optional[str]:
        """Создание задачи в RunningHub"""
        for attempt in range(self.max_retries):
            try:
                # Проверяем размер файлов и логируем информацию
                product_size = os.path.getsize(product_path)
                background_size = os.path.getsize(background_path)
                logger.info(f"Attempting to create task (attempt {attempt + 1}/{self.max_retries})")
                logger.info(f"Product image: {product_path} ({product_size / 1024:.1f} KB)")
                logger.info(f"Background image: {background_path} ({background_size / 1024:.1f} KB)")

                # Создаем form-data с файлами
                data = aiohttp.FormData()
                data.add_field('product_image',
                            open(product_path, 'rb'),
                            filename='product.jpg',
                            content_type='image/jpeg')
                data.add_field('background_image',
                            open(background_path, 'rb'),
                            filename='background.jpg',
                            content_type='image/jpeg')
                data.add_field('workflow_id', self.workflow_id)

                async with self.get_session() as session:
                    async with session.post(
                        f"{self.api_url}/tasks",
                        data=data,
                        timeout=30
                    ) as response:
                        response_text = await response.text()
                        logger.debug(f"API response: {response.status} - {response_text}")
                        
                        try:
                            result = await response.json()
                        except Exception as e:
                            logger.error(f"Failed to parse JSON response: {response_text}")
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay)
                                continue
                            raise RuntimeError(f"Failed to parse API response: {str(e)}")

                        if response.status == 200:
                            task_id = result.get('task_id')
                            if not task_id:
                                raise RuntimeError(f"No task_id in successful response: {result}")
                            logger.info(f"Successfully created task: {task_id}")
                            return task_id
                        else:
                            error_code = result.get('code')
                            error_msg = result.get('msg')
                            error_data = result.get('data')
                            error_text = f"API Error - Status: {response.status}, Code: {error_code}, Message: {error_msg}, Data: {error_data}"
                            logger.error(error_text)
                            
                            if response.status == 500 and attempt < self.max_retries - 1:
                                logger.info(f"Retrying after server error (attempt {attempt + 1})")
                                await asyncio.sleep(self.retry_delay)
                                continue
                            raise RuntimeError(error_text)

            except Exception as e:
                logger.error(f"Error in create_task: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise  # Пробрасываем исключение наверх после всех попыток

        raise RuntimeError("All retry attempts failed")

    async def _wait_for_result(self, task_id: str) -> Optional[str]:
        """Ожидание результата генерации"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > self.task_timeout:
                logger.error(f"Task {task_id} timeout after {self.task_timeout} seconds")
                return None
                
            try:
                logger.debug(f"Checking status for task {task_id}")
                async with self.get_session() as session:
                    async with session.get(
                        f"{self.api_url}/tasks/{task_id}",
                        timeout=10
                    ) as response:
                        response_text = await response.text()
                        logger.debug(f"Status check response: {response.status} - {response_text}")
                        
                        if response.status != 200:
                            logger.error(f"Error checking task status: {response.status} - {response_text}")
                            return None
                            
                        result = await response.json()
                        status = result.get('status')
                        logger.debug(f"Task {task_id} status: {status}")
                        
                        if status == 'completed':
                            result_url = result.get('result_url')
                            if not result_url:
                                logger.error(f"No result_url in completed task response: {result}")
                                return None
                            return result_url
                        elif status == 'failed':
                            error = result.get('error', 'Unknown error')
                            logger.error(f"Task {task_id} failed: {error}")
                            return None
                            
                        # Ждем перед следующей проверкой
                        logger.debug(f"Task {task_id} still processing, waiting {self.polling_interval} seconds")
                        await asyncio.sleep(self.polling_interval)
                        
            except Exception as e:
                logger.error(f"Error checking task {task_id} status: {str(e)}")
                return None
