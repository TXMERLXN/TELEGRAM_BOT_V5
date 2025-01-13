import asyncio
import logging
import os
from pathlib import Path
import aiohttp
from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile
import time
import random
import ssl

logger = logging.getLogger(__name__)

class RunningHubAPI:
    """Класс для работы с API RunningHub"""
    
    def __init__(self, api_url: str, api_key: str, workflow_id: str, max_tasks: int = 5):
        """Инициализация API клиента"""
        self.api_url = api_url
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.max_tasks = max_tasks
        self.current_tasks = 0
        self._session = None
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    def initialize_client(self) -> None:
        """Инициализация aiohttp сессии"""
        if self._session is None:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(connector=connector)
            self.logger.info("Created new aiohttp session")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание сессии"""
        if self._session is None or self._session.closed:
            self.initialize_client()
        return self._session

    async def close_client(self) -> None:
        """Закрытие aiohttp сессии"""
        if self._session is not None:
            if not self._session.closed:
                try:
                    if self._session._connector is not None and not self._session._connector.closed:
                        self._session._connector.close()
                    if self._session._connector_owner:
                        self._session._connector = None
                except Exception as e:
                    self.logger.error(f"Error closing session connector: {e}")
                
                try:
                    self._session.close()
                except Exception as e:
                    self.logger.error(f"Error closing session: {e}")
            
            self._session = None
            self.logger.info("Closed aiohttp session")

    async def _upload_image(self, image_path: str, file_type: str = "image") -> Optional[str]:
        """Загрузка изображения на сервер"""
        try:
            url = f"{self.api_url}/task/openapi/upload"
            self.logger.info(f"Making request to {url}")
            
            # Подготовка файла и данных
            with open(image_path, 'rb') as f:
                file_data = f.read()
            
            form = aiohttp.FormData()
            form.add_field('file', file_data, filename=os.path.basename(image_path))
            form.add_field('type', file_type)
            form.add_field('apiKey', self.api_key)
            
            headers = {
                'Accept': 'application/json'
            }
            
            session = await self._get_session()
            async with session.post(url, data=form, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('id')
                else:
                    error_text = await response.text()
                    self.logger.error(f"Error response: {error_text}")
                    return None
        except Exception as e:
            self.logger.error(f"Error uploading image: {e}")
            return None

    async def process_photos(self, user_id: int, product_photo: str, background_photo: str) -> Optional[str]:
        """Обработка фотографий"""
        try:
            self.logger.info(f"Starting photo processing for user {user_id}")
            
            # Скачиваем фотографии
            product_path = f"temp/product_{user_id}.jpg"
            background_path = f"temp/background_{user_id}.jpg"
            
            try:
                session = await self._get_session()
                async with session.get(product_photo) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to download product photo: {response.status}")
                        return None
                        
                    with open(product_path, 'wb') as f:
                        f.write(await response.read())
                    self.logger.info(f"Successfully downloaded product photo to {product_path}")
            except Exception as e:
                self.logger.error(f"Error downloading product photo: {e}")
                return None
                
            try:
                session = await self._get_session()
                async with session.get(background_photo) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to download background photo: {response.status}")
                        return None
                        
                    with open(background_path, 'wb') as f:
                        f.write(await response.read())
                    self.logger.info(f"Successfully downloaded background photo to {background_path}")
            except Exception as e:
                self.logger.error(f"Error downloading background photo: {e}")
                return None
            
            # Загружаем фотографии в RunningHub
            self.logger.info("Uploading product image...")
            product_url = await self._upload_image(product_path)
            if not product_url:
                return None
            self.logger.info(f"Successfully uploaded product image: {product_url}")
            
            self.logger.info("Uploading background image...")
            background_url = await self._upload_image(background_path)
            if not background_url:
                return None
            self.logger.info(f"Successfully uploaded background image: {background_url}")
            
            # Создаем задачу с загруженными изображениями
            self.logger.info(f"Creating task with workflow {self.workflow_id}")
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
                
                async with self._get_session() as session:
                    async with session.post(
                        f"{self.api_url}/task/openapi/create",
                        json=task_data,
                        timeout=30
                    ) as response:
                        response_text = await response.text()
                        self.logger.info(f"Task creation response: {response_text}")
                        if response.status != 200:
                            self.logger.error(f"Failed to create task: Status {response.status}")
                            return None
                        
                        task_result = await response.json()
                        if task_result.get('code') != 0:
                            self.logger.error(f"Failed to create task: {task_result.get('msg')}")
                            return None
                        
                        task_id = task_result['data'].get('taskId')
                        if not task_id:
                            self.logger.error("No taskId in response")
                            return None
                        
                        self.logger.info(f"Successfully created task: {task_id}")
                        return await self._wait_for_result(task_id)
                    
            except Exception as e:
                self.logger.error(f"Error creating task: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing photos: {str(e)}", exc_info=True)
            return None
        finally:
            # Удаляем временные файлы
            try:
                if os.path.exists(product_path):
                    os.remove(product_path)
                if os.path.exists(background_path):
                    os.remove(background_path)
            except Exception as e:
                self.logger.error(f"Error cleaning up temporary files: {str(e)}")

    async def _wait_for_result(self, task_id: str, max_attempts: int = 60, delay: int = 10) -> Optional[str]:
        """Ожидание результата задачи"""
        self.logger.info(f"Waiting for task {task_id} result")
        
        # Минимальное время ожидания перед первой проверкой (20 секунд)
        initial_wait = 20
        self.logger.info(f"Initial wait for {initial_wait} seconds...")
        await asyncio.sleep(initial_wait)
        
        # Сохраняем время начала задачи
        start_time = time.time()
        last_url = None
        consecutive_same_url = 0
        
        for attempt in range(max_attempts):
            try:
                elapsed_time = time.time() - start_time
                self.logger.info(f"Checking task status (attempt {attempt + 1}/{max_attempts}, elapsed time: {elapsed_time:.1f}s)")
                
                # Сначала проверяем статус задачи
                status_data = {
                    "taskId": task_id,
                    "apiKey": self.api_key
                }
                
                async with self._get_session() as session:
                    async with session.post(
                        f"{self.api_url}/task/openapi/status",
                        json=status_data,
                        timeout=30
                    ) as response:
                        response_text = await response.text()
                        self.logger.info(f"Task status response: {response_text}")
                        
                        if response.status != 200:
                            self.logger.error(f"Failed to get task status: Status {response.status}")
                            await asyncio.sleep(delay)
                            continue
                        
                        result = await response.json()
                        if result.get('code') != 0:
                            error_msg = result.get('msg', 'Unknown error')
                            self.logger.error(f"API error: {error_msg}")
                            if error_msg == 'TASK_NOT_FOUND':
                                return None
                            await asyncio.sleep(delay)
                            continue
                        
                        task_status = result.get('data')
                        self.logger.info(f"Current task status: {task_status}")
                        
                        # Если задача завершена успешно
                        if task_status == 'SUCCESS':
                            async with self._get_session() as session:
                                async with session.post(
                                    f"{self.api_url}/task/openapi/outputs",
                                    json=status_data,
                                    timeout=30
                                ) as output_response:
                                    output_text = await output_response.text()
                                    self.logger.info(f"Task output response: {output_text}")
                                    
                                    if output_response.status != 200:
                                        self.logger.error(f"Failed to get task output: Status {output_response.status}")
                                        await asyncio.sleep(delay)
                                        continue
                                        
                                    output_result = await output_response.json()
                                    if output_result.get('code') != 0:
                                        self.logger.error(f"API error in output: {output_result.get('msg', 'Unknown error')}")
                                        await asyncio.sleep(delay)
                                        continue
                                        
                                    output_data = output_result.get('data', [])
                                    if output_data and isinstance(output_data, list) and len(output_data) > 0:
                                        output = output_data[0]
                                        file_url = output.get('fileUrl')
                                        task_cost_time = output.get('taskCostTime', '0')
                                        
                                        # Проверяем признаки кэшированного результата
                                        elapsed_time = time.time() - start_time
                                        is_cached = False
                                        
                                        if task_cost_time == '0' or task_cost_time == '1':
                                            is_cached = True
                                            self.logger.warning(f"Suspicious taskCostTime: {task_cost_time}")
                                        
                                        if elapsed_time < 20 and attempt < 2:
                                            is_cached = True
                                            self.logger.warning(f"Task completed too quickly: {elapsed_time:.1f}s")
                                        
                                        if file_url == last_url:
                                            consecutive_same_url += 1
                                            if consecutive_same_url >= 2:
                                                is_cached = True
                                                self.logger.warning(f"Same URL returned {consecutive_same_url} times")
                                        else:
                                            consecutive_same_url = 0
                                            last_url = file_url
                                        
                                        if is_cached:
                                            self.logger.warning("Got cached result, waiting for actual task completion")
                                            await asyncio.sleep(delay)
                                            continue
                                        
                                        if file_url:
                                            self.logger.info(f"Task completed successfully in {task_cost_time}s (total time: {elapsed_time:.1f}s), result URL: {file_url}")
                                            return file_url
                    
                        elif task_status == 'FAILED':
                            self.logger.error(f"Task failed")
                            return None
                        elif task_status == 'RUNNING':
                            self.logger.info(f"Task {task_id} is still running")
                        else:
                            self.logger.warning(f"Unknown task status: {task_status}")
                        
                        self.logger.info(f"Task {task_id} still processing (status: {task_status}), attempt {attempt + 1}/{max_attempts}")
                        await asyncio.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"Error checking task status: {str(e)}")
                await asyncio.sleep(delay)
                
        self.logger.error(f"Timeout waiting for task result after {max_attempts} attempts (total time: {time.time() - start_time:.1f}s)")
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
                async with self._get_session() as session:
                    async with session.post(
                        f"{self.api_url}/uc/openapi/accountStatus",
                        json=data,
                        headers=headers,
                        timeout=30
                    ) as response:
                        response_text = await response.text()
                        self.logger.debug(f"Account status response: {response_text}")
                        
                        if response.status != 200:
                            self.logger.error(f"Error response from account status API: Status {response.status}, Body: {response_text}")
                            return None
                        
                        try:
                            result = await response.json()
                        except Exception as e:
                            self.logger.error(f"Failed to parse account status JSON response: {response_text}, Error: {str(e)}")
                            return None
                        
                        if result.get('code') != 0:
                            error_msg = result.get('msg', 'Unknown error')
                            self.logger.error(f"Account status API error: {error_msg}")
                            return None
                        
                        task_count = int(result.get('data', {}).get('currentTaskCounts', '0'))
                        self.logger.debug(f"Current task count: {task_count}")
                        return task_count > 0
                    
            except asyncio.TimeoutError:
                self.logger.error("Timeout while checking account status")
                return None
            except Exception as e:
                self.logger.error(f"HTTP error while checking account status: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking account status: {str(e)}", exc_info=True)
            return None
