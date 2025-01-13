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

    async def process_photos(self, user_id: int, product_photo: str, background_photo: str) -> Optional[str]:
        """Обработка фотографий"""
        try:
            logger.info(f"Starting photo processing for user {user_id}")
            
            # Скачиваем фотографии
            product_path = f"temp/product_{user_id}.jpg"
            background_path = f"temp/background_{user_id}.jpg"
            
            try:
                async with self.get_session().get(product_photo) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download product photo: {response.status}")
                        return None
                    with open(product_path, 'wb') as f:
                        f.write(await response.read())
                logger.info(f"Successfully downloaded product photo to {product_path}")
            except Exception as e:
                logger.error(f"Error downloading product photo: {str(e)}")
                return None
                
            try:
                async with self.get_session().get(background_photo) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download background photo: {response.status}")
                        return None
                    with open(background_path, 'wb') as f:
                        f.write(await response.read())
                logger.info(f"Successfully downloaded background photo to {background_path}")
            except Exception as e:
                logger.error(f"Error downloading background photo: {str(e)}")
                return None
            
            # Загружаем фотографии в RunningHub
            logger.info("Uploading product image...")
            try:
                # Создаем multipart form
                form = aiohttp.FormData()
                form.add_field('apiKey', self.api_key)
                form.add_field('fileType', 'image')
                form.add_field(
                    'file',
                    open(product_path, 'rb'),
                    filename=os.path.basename(product_path),
                    content_type='image/jpeg'
                )
                
                upload_url = f"{self.api_url}/task/openapi/upload"
                logger.info(f"Making request to {upload_url}")
                
                async with self.get_session().post(
                    upload_url,
                    data=form,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Product upload response: {response_text}")
                    if response.status != 200:
                        logger.error(f"Failed to upload product image: Status {response.status}, Response: {response_text}")
                        return None
                    product_result = await response.json()
                    if product_result.get('code') != 0:
                        logger.error(f"Failed to upload product image: {product_result.get('msg')}")
                        return None
                    product_url = product_result['data'].get('fileName')
                    if not product_url:
                        logger.error("No fileName in product upload response")
                        return None
                    logger.info(f"Successfully uploaded product image: {product_url}")
            except Exception as e:
                logger.error(f"Error uploading product image: {str(e)}")
                return None
            finally:
                if 'form' in locals() and hasattr(form, '_fields'):
                    for field in form._fields:
                        if hasattr(field[2], 'close'):
                            field[2].close()
                    
            logger.info("Uploading background image...")
            try:
                # Создаем multipart form
                form = aiohttp.FormData()
                form.add_field('apiKey', self.api_key)
                form.add_field('fileType', 'image')
                form.add_field(
                    'file',
                    open(background_path, 'rb'),
                    filename=os.path.basename(background_path),
                    content_type='image/jpeg'
                )
                
                upload_url = f"{self.api_url}/task/openapi/upload"
                logger.info(f"Making request to {upload_url}")
                
                async with self.get_session().post(
                    upload_url,
                    data=form,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Background upload response: {response_text}")
                    if response.status != 200:
                        logger.error(f"Failed to upload background image: Status {response.status}, Response: {response_text}")
                        return None
                    background_result = await response.json()
                    if background_result.get('code') != 0:
                        logger.error(f"Failed to upload background image: {background_result.get('msg')}")
                        return None
                    background_url = background_result['data'].get('fileName')
                    if not background_url:
                        logger.error("No fileName in background upload response")
                        return None
                    logger.info(f"Successfully uploaded background image: {background_url}")
            except Exception as e:
                logger.error(f"Error uploading background image: {str(e)}")
                return None
            finally:
                if 'form' in locals() and hasattr(form, '_fields'):
                    for field in form._fields:
                        if hasattr(field[2], 'close'):
                            field[2].close()
                            
            # Создаем задачу с загруженными изображениями
            logger.info(f"Creating task with workflow {self.workflow_id}")
            try:
                task_data = {
                    "workflowId": self.workflow_id,
                    "apiKey": self.api_key,
                    "nodeInfoList": [
                        {
                            "nodeId": "2",  # ID узла для продукта
                            "fieldName": "image",
                            "fieldValue": product_url
                        },
                        {
                            "nodeId": "32",  # ID узла для фона
                            "fieldName": "image",
                            "fieldValue": background_url
                        }
                    ]
                }
                
                async with self.get_session().post(
                    f"{self.api_url}/task/openapi/create",
                    json=task_data,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Task creation response: {response_text}")
                    if response.status != 200:
                        logger.error(f"Failed to create task: Status {response.status}")
                        return None
                        
                    task_result = await response.json()
                    if task_result.get('code') != 0:
                        logger.error(f"Failed to create task: {task_result.get('msg')}")
                        return None
                        
                    task_id = task_result['data'].get('taskId')
                    if not task_id:
                        logger.error("No taskId in response")
                        return None
                        
                    logger.info(f"Successfully created task: {task_id}")
                    return await self._wait_for_result(task_id)
                    
            except Exception as e:
                logger.error(f"Error creating task: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing photos: {str(e)}", exc_info=True)
            return None
        finally:
            # Удаляем временные файлы
            try:
                if os.path.exists(product_path):
                    os.remove(product_path)
                if os.path.exists(background_path):
                    os.remove(background_path)
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")

    async def _wait_for_result(self, task_id: str, max_attempts: int = 60, delay: int = 5) -> Optional[str]:
        """Ожидание результата задачи"""
        logger.info(f"Waiting for task {task_id} result")
        
        for attempt in range(max_attempts):
            try:
                # Проверяем статус задачи
                status_data = {
                    "taskId": task_id,
                    "apiKey": self.api_key
                }
                
                async with self.get_session().post(
                    f"{self.api_url}/task/openapi/outputs",
                    json=status_data,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Task status response: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Failed to get task status: Status {response.status}")
                        await asyncio.sleep(delay)
                        continue
                        
                    result = await response.json()
                    if result.get('code') != 0:
                        error_msg = result.get('msg', 'Unknown error')
                        logger.error(f"API error: {error_msg}")
                        if error_msg == 'TASK_NOT_FOUND':
                            return None
                        await asyncio.sleep(delay)
                        continue
                        
                    # Проверяем, есть ли результат
                    output_data = result.get('data', [])
                    if output_data and isinstance(output_data, list) and len(output_data) > 0:
                        output = output_data[0]
                        file_url = output.get('fileUrl')
                        task_cost_time = output.get('taskCostTime', '0')
                        
                        # Проверяем, что задача действительно выполнилась
                        if file_url and task_cost_time != '0':
                            logger.info(f"Task completed successfully in {task_cost_time}s, result URL: {file_url}")
                            return file_url
                        else:
                            logger.info(f"Task {task_id} is still processing (cost time: {task_cost_time}), waiting...")
                            
                    logger.info(f"Task {task_id} still processing, attempt {attempt + 1}/{max_attempts}")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error checking task status: {str(e)}")
                await asyncio.sleep(delay)
                
        logger.error(f"Timeout waiting for task result after {max_attempts} attempts")
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
            
            try:
                async with self.get_session().post(
                    f"{self.api_url}/uc/openapi/accountStatus",
                    json=data,
                    headers=headers,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Account status response: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Error response from account status API: Status {response.status}, Body: {response_text}")
                        return None
                        
                    try:
                        result = await response.json()
                    except Exception as e:
                        logger.error(f"Failed to parse account status JSON response: {response_text}, Error: {str(e)}")
                        return None
                    
                    if result.get('code') != 0:
                        error_msg = result.get('msg', 'Unknown error')
                        logger.error(f"Account status API error: {error_msg}")
                        return None
                    
                    task_count = int(result.get('data', {}).get('currentTaskCounts', '0'))
                    logger.debug(f"Current task count: {task_count}")
                    return task_count > 0
                    
            except asyncio.TimeoutError:
                logger.error("Timeout while checking account status")
                return None
            except Exception as e:
                logger.error(f"HTTP error while checking account status: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking account status: {str(e)}", exc_info=True)
            return None
