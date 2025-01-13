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

    async def _check_task_status(self, task_id: str) -> Optional[str]:
        """Проверка статуса задачи"""
        try:
            data = {
                "taskId": task_id,
                "apiKey": self.api_key
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            async with self.get_session().post(
                f"{self.api_url}/task/openapi/status",
                json=data,
                headers=headers,
                timeout=30
            ) as response:
                result = await response.json()
                logger.debug(f"Task status response: {result}")
                
                if response.status == 200 and result.get('code') == 0:
                    return result.get('data', {}).get('taskStatus')
                return None
                
        except Exception as e:
            logger.error(f"Error checking task status: {str(e)}")
            return None

    async def _check_account_status(self) -> Optional[bool]:
        """Проверка статуса аккаунта"""
        try:
            data = {
                "apikey": self.api_key
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            async with self.get_session().post(
                f"{self.api_url}/uc/openapi/accountStatus",
                json=data,
                headers=headers,
                timeout=30
            ) as response:
                result = await response.json()
                logger.debug(f"Account status response: {result}")
                
                if response.status == 200 and result.get('code') == 0:
                    task_count = int(result.get('data', {}).get('currentTaskCounts', '0'))
                    return task_count > 0
                return None
                
        except Exception as e:
            logger.error(f"Error checking account status: {str(e)}")
            return None

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
            last_url = None  # Для отслеживания изменений URL
            
            for attempt in range(max_attempts):
                try:
                    # Проверяем статус аккаунта
                    is_busy = await self._check_account_status()
                    if is_busy:
                        logger.debug(f"Account is busy, waiting... [{attempt+1}/{max_attempts}]")
                        await asyncio.sleep(5)
                        continue
                    
                    # Пробуем получить результат
                    async with self.get_session().post(
                        f"{self.api_url}/task/openapi/outputs",
                        json=data,
                        headers=headers,
                        timeout=30
                    ) as response:
                        response_text = await response.text()
                        logger.debug(f"Get result response [{attempt+1}/{max_attempts}]: {response_text}")
                        
                        if response.status != 200:
                            logger.error(f"Error response from API: Status {response.status}, Body: {response_text}")
                            await asyncio.sleep(5)
                            continue
                            
                        try:
                            result = await response.json()
                        except Exception as e:
                            logger.error(f"Failed to parse JSON response: {response_text}")
                            await asyncio.sleep(5)
                            continue
                            
                        if result.get('code') != 0:
                            error_msg = result.get('msg', 'Unknown error')
                            if error_msg == 'APIKEY_TASK_IS_RUNNING':
                                logger.debug(f"Task is still running, waiting... [{attempt+1}/{max_attempts}]")
                            else:
                                logger.error(f"API error: {error_msg}")
                            await asyncio.sleep(5)
                            continue
                            
                        if not result.get('data'):
                            logger.debug(f"No data in response yet, waiting... [{attempt+1}/{max_attempts}]")
                            await asyncio.sleep(5)
                            continue
                            
                        file_url = result['data'][0].get('fileUrl')
                        if not file_url:
                            logger.error(f"No fileUrl in response data: {result}")
                            await asyncio.sleep(5)
                            continue
                            
                        # Проверяем, изменился ли URL
                        if file_url == last_url:
                            logger.debug(f"URL hasn't changed, waiting for new result... [{attempt+1}/{max_attempts}]")
                            await asyncio.sleep(5)
                            continue
                            
                        # Проверяем, что URL содержит ID задачи
                        if task_id not in file_url:
                            logger.debug(f"URL doesn't match task ID, waiting... [{attempt+1}/{max_attempts}]")
                            await asyncio.sleep(5)
                            continue
                            
                        last_url = file_url
                        logger.info(f"Task completed successfully: {file_url}")
                        return file_url
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout on attempt {attempt+1}/{max_attempts}, retrying...")
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    logger.error(f"Error on attempt {attempt+1}/{max_attempts}: {str(e)}")
                    await asyncio.sleep(5)
                    continue
                    
            raise RuntimeError(f"Timeout waiting for task result after {max_attempts} attempts")
            
        except Exception as e:
            logger.error(f"Error getting task result: {str(e)}")
            raise

    async def process_photos(self, product_photo_id: str, background_photo_id: str, user_id: int) -> Optional[str]:
        """Обработка фотографий"""
        try:
            logger.info(f"Starting photo processing for user {user_id}")
            
            # Создаем директорию temp если её нет
            os.makedirs("temp", exist_ok=True)
            
            # Скачиваем фотографии
            product_path = f"temp/product_{user_id}.jpg"
            background_path = f"temp/background_{user_id}.jpg"
            
            # Получаем информацию о файлах
            product_file = await self.bot.get_file(product_photo_id)
            background_file = await self.bot.get_file(background_photo_id)
            
            # Скачиваем файлы
            await self.bot.download_file(product_file.file_path, product_path)
            logger.info(f"Successfully downloaded product photo to {product_path}")
            
            await self.bot.download_file(background_file.file_path, background_path)
            logger.info(f"Successfully downloaded background photo to {background_path}")
            
            try:
                # Создаем задачу
                task_id = await self.create_task(product_path, background_path)
                if not task_id:
                    raise RuntimeError("Failed to create task")
                    
                # Ждем результат
                result_url = await self._wait_for_result(task_id)
                if not result_url:
                    raise RuntimeError("Failed to get task result")
                    
                return result_url
                
            finally:
                # Удаляем временные файлы
                try:
                    if os.path.exists(product_path):
                        os.remove(product_path)
                    if os.path.exists(background_path):
                        os.remove(background_path)
                except Exception as e:
                    logger.error(f"Error removing temp files: {e}")
            
        except Exception as e:
            logger.error(f"Error processing photos: {str(e)}")
            raise
