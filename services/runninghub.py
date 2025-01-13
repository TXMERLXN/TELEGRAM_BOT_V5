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
        
        logger.info(f"Initialized RunningHubAPI with URL: {self.api_url}")
        
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
            
            # Загружаем файлы на RunningHub
            logger.info("Uploading files to RunningHub")
            product_filename = await self._upload_file(str(product_path))
            background_filename = await self._upload_file(str(background_path))
            
            if not product_filename or not background_filename:
                raise Exception("Failed to upload files")
            
            # Создаем задачу
            logger.info("Creating task with uploaded files")
            task_id = await self.create_task(product_filename, background_filename)
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
            return None
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
            file = await self.bot.get_file(file_id)
            await self.bot.download_file(file.file_path, save_path)
            logger.debug(f"Successfully downloaded file {file_id} to {save_path}")
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            raise
            
    async def _upload_file(self, file_path: str) -> Optional[str]:
        """Загрузка файла на RunningHub"""
        try:
            data = aiohttp.FormData()
            data.add_field('apiKey', os.getenv('RUNNINGHUB_API_KEY', ''))
            data.add_field('fileType', 'image')
            data.add_field('file',
                          open(file_path, 'rb'),
                          filename=os.path.basename(file_path),
                          content_type='image/jpeg')
            
            logger.debug(f"Uploading file {file_path} to RunningHub")
            async with self.session.post(
                f"{self.api_url}/task/openapi/upload",
                data=data,
                timeout=30
            ) as response:
                response_text = await response.text()
                logger.debug(f"Upload response: {response.status} - {response_text}")
                
                if response.status == 200:
                    result = await response.json()
                    if result.get('code') == 0:
                        filename = result.get('data', {}).get('fileName')
                        if filename:
                            logger.debug(f"File uploaded successfully: {filename}")
                            return filename
                        else:
                            logger.error(f"No filename in upload response: {result}")
                            return None
                    else:
                        logger.error(f"Upload failed: {result.get('msg')}")
                        return None
                else:
                    logger.error(f"Error uploading file: {response.status} - {response_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return None
        
    async def create_task(self, product_filename: str, background_filename: str) -> Optional[str]:
        """Создание задачи в RunningHub"""
        try:
            # Формируем данные для создания задачи
            data = {
                'workflowId': os.getenv('RUNNINGHUB_WORKFLOW_PRODUCT', ''),
                'apiKey': os.getenv('RUNNINGHUB_API_KEY', ''),
                'nodeInfoList': [
                    {
                        'nodeId': '10',  # ID ноды для загрузки изображения продукта
                        'fieldName': 'image',
                        'fieldValue': product_filename
                    },
                    {
                        'nodeId': '20',  # ID ноды для загрузки изображения фона
                        'fieldName': 'image',
                        'fieldValue': background_filename
                    }
                ]
            }
            
            logger.debug(f"Creating task with data: {data}")
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            async with self.session.post(
                f"{self.api_url}/task/openapi/create",
                json=data,
                headers=headers,
                timeout=30
            ) as response:
                response_text = await response.text()
                logger.debug(f"Create task response: {response.status} - {response_text}")
                
                if response.status == 200:
                    result = await response.json()
                    if result.get('code') == 0:
                        task_id = result.get('data', {}).get('taskId')
                        if task_id:
                            return task_id
                        else:
                            logger.error(f"No taskId in response: {result}")
                            return None
                    else:
                        logger.error(f"Task creation failed: {result.get('msg')}")
                        return None
                else:
                    logger.error(f"Error creating task: {response.status} - {response_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return None
            
    async def _wait_for_result(self, task_id: str) -> Optional[str]:
        """Ожидание результата генерации"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > self.task_timeout:
                logger.error(f"Task {task_id} timeout after {self.task_timeout} seconds")
                return None
                
            try:
                logger.debug(f"Checking task status: {task_id}")
                data = {
                    'taskId': task_id,
                    'apiKey': os.getenv('RUNNINGHUB_API_KEY', '')
                }
                
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                async with self.session.post(
                    f"{self.api_url}/task/openapi/outputs",
                    json=data,
                    headers=headers,
                    timeout=10
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Status check response: {response.status} - {response_text}")
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get('code') == 0:
                            data = result.get('data', [])
                            if data and isinstance(data, list) and len(data) > 0:
                                file_url = data[0].get('fileUrl')
                                if file_url:
                                    return file_url
                                else:
                                    logger.error(f"No fileUrl in response data: {data}")
                                    return None
                            else:
                                # Задача еще выполняется
                                await asyncio.sleep(self.polling_interval)
                                continue
                        else:
                            logger.error(f"Task check failed: {result.get('msg')}")
                            return None
                    else:
                        logger.error(f"Error checking task status: {response.status} - {response_text}")
                        return None
                    
            except Exception as e:
                logger.error(f"Error checking task status: {str(e)}")
                return None
