import asyncio
import logging
import os
from pathlib import Path
import aiohttp
from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

class RunningHubAPI:
    """API клиент для RunningHub"""
    
    def __init__(self, bot: Bot, api_url: str, api_key: str, workflow_id: str):
        self.bot = bot
        self.api_url = api_url.rstrip('/')  # Убираем trailing slash
        self.api_key = api_key
        self.workflow_id = workflow_id
        self._session = None
        
    async def initialize(self):
        """Инициализация клиента"""
        if not self._session:
            self._session = aiohttp.ClientSession()
            logger.info("Created new aiohttp session")
            
    async def close(self):
        """Закрытие клиента"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Closed aiohttp session")
            
    def get_session(self) -> aiohttp.ClientSession:
        """Получение сессии"""
        if not self._session:
            raise RuntimeError("Session not initialized. Call initialize() first")
        return self._session

    async def upload_image(self, image_path: str) -> Optional[str]:
        """Загрузка изображения в RunningHub"""
        try:
            data = aiohttp.FormData()
            data.add_field('apiKey', self.api_key)
            data.add_field('fileType', 'image')
            data.add_field('file', 
                          open(image_path, 'rb'),
                          filename=os.path.basename(image_path),
                          content_type='image/jpeg')

            async with self.get_session().post(
                f"{self.api_url}/task/openapi/upload",
                data=data,
                timeout=30
            ) as response:
                result = await response.json()
                logger.debug(f"Upload response: {result}")
                
                if response.status == 200 and result.get('code') == 0:
                    return result['data']['fileName']
                else:
                    raise RuntimeError(f"Failed to upload image: {result}")
                    
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            raise

    async def create_task(self, product_path: str, background_path: str) -> Optional[str]:
        """Создание задачи в RunningHub"""
        try:
            # Сначала загружаем изображения
            logger.info("Uploading product image...")
            product_file = await self.upload_image(product_path)
            logger.info("Uploading background image...")
            background_file = await self.upload_image(background_path)
            
            # Создаем задачу с загруженными изображениями
            data = {
                "workflowId": self.workflow_id,
                "apiKey": self.api_key,
                "nodeInfoList": [
                    {
                        "nodeId": "2",  # ID ноды для продукта
                        "fieldName": "image",
                        "fieldValue": product_file
                    },
                    {
                        "nodeId": "32",  # ID ноды для фона
                        "fieldName": "image",
                        "fieldValue": background_file
                    }
                ]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"Creating task with workflow {self.workflow_id}")
            async with self.get_session().post(
                f"{self.api_url}/task/openapi/create",
                json=data,
                headers=headers,
                timeout=30
            ) as response:
                result = await response.json()
                logger.debug(f"Create task response: {result}")
                
                if response.status == 200 and result.get('code') == 0:
                    task_id = result['data']['taskId']
                    logger.info(f"Successfully created task: {task_id}")
                    return task_id
                else:
                    raise RuntimeError(f"Failed to create task: {result}")
                    
        except Exception as e:
            logger.error(f"Error in create_task: {str(e)}")
            raise

    async def _wait_for_result(self, task_id: str) -> Optional[str]:
        """Ожидание результата генерации"""
        try:
            data = {
                "taskId": task_id,
                "apiKey": self.api_key
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            max_attempts = 60  # Максимальное количество попыток (5 минут при задержке в 5 секунд)
            for attempt in range(max_attempts):
                async with self.get_session().post(
                    f"{self.api_url}/task/openapi/outputs",
                    json=data,
                    headers=headers,
                    timeout=30
                ) as response:
                    result = await response.json()
                    logger.debug(f"Get result response: {result}")
                    
                    if response.status == 200 and result.get('code') == 0:
                        if result['data']:  # Если есть результат
                            file_url = result['data'][0]['fileUrl']
                            logger.info(f"Task completed successfully: {file_url}")
                            return file_url
                            
                    # Если результат еще не готов, ждем и пробуем снова
                    await asyncio.sleep(5)
                    
            raise RuntimeError(f"Timeout waiting for task result after {max_attempts} attempts")
            
        except Exception as e:
            logger.error(f"Error getting task result: {str(e)}")
            raise

    async def process_photos(self, product_photo_id: str, background_photo_id: str, user_id: int) -> Optional[str]:
        """Обработка фотографий"""
        try:
            logger.info(f"Starting photo processing for user {user_id}")
            
            # Скачиваем фотографии
            product_path = f"temp/product_{user_id}.jpg"
            background_path = f"temp/background_{user_id}.jpg"
            
            await self.bot.download_file_by_id(product_photo_id, product_path)
            logger.info(f"Successfully downloaded photo to {product_path}")
            
            await self.bot.download_file_by_id(background_photo_id, background_path)
            logger.info(f"Successfully downloaded photo to {background_path}")
            
            # Создаем задачу
            task_id = await self.create_task(product_path, background_path)
            if not task_id:
                raise RuntimeError("Failed to create task")
                
            # Ждем результат
            result_url = await self._wait_for_result(task_id)
            if not result_url:
                raise RuntimeError("Failed to get task result")
                
            return result_url
            
        except Exception as e:
            logger.error(f"Error processing photos: {str(e)}")
            raise
