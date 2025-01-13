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
import json

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
        
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Создание SSL контекста с отключенной проверкой сертификата"""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
        
    def _create_connector(self) -> aiohttp.TCPConnector:
        """Создание TCP коннектора с настроенным SSL"""
        return aiohttp.TCPConnector(
            verify_ssl=False,
            force_close=True,
            enable_cleanup_closed=True,
            ttl_dns_cache=300
        )
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Создание или получение существующей сессии"""
        if not hasattr(self, '_session') or self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                connector=self._create_connector(),
                timeout=timeout,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'RunningHub-Client/1.0',
                    'Connection': 'keep-alive'
                }
            )
            self.logger.info("Created new aiohttp session")
        return self._session

    async def close_client(self) -> None:
        """Закрытие aiohttp сессии"""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.info("Closed aiohttp session")

    async def upload_image(self, file_path: str) -> str:
        """Загрузка изображения на сервер"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        self.logger.info(f"Uploading product image...")
        url = f"{self.api_url}/task/openapi/upload"
        self.logger.info(f"Making request to {url}")

        data = aiohttp.FormData()
        data.add_field('apiKey', self.api_key)
        data.add_field('fileType', 'image')
        data.add_field('file', 
                      open(file_path, 'rb'),
                      filename=os.path.basename(file_path),
                      content_type='image/jpeg')

        try:
            async with (await self._get_session()).post(url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Upload failed with status {response.status}: {error_text}")
                
                result = await response.json()
                if result.get('code') != 0:
                    raise Exception(f"Upload failed: {result.get('msg')}")
                
                return result['data']['fileName']
        except Exception as e:
            self.logger.error(f"Error uploading image: {e}")
            raise

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
            product_url = await self.upload_image(product_path)
            if not product_url:
                return None
            self.logger.info(f"Successfully uploaded product image: {product_url}")
            
            self.logger.info("Uploading background image...")
            background_url = await self.upload_image(background_path)
            if not background_url:
                return None
            self.logger.info(f"Successfully uploaded background image: {background_url}")
            
            # Создаем задачу с загруженными изображениями
            task_id = await self._create_task(product_url, background_url)
            if not task_id:
                return None
            
            # Ожидаем результат задачи
            return await self._wait_for_result(task_id)
                
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

    async def _create_task(self, product_url: str, background_url: str) -> Optional[str]:
        """Создание задачи в RunningHub"""
        self.logger.info(f"Creating task with workflow {self.workflow_id}")
        
        url = f"{self.api_url}/task/openapi/create"
        data = {
            "workflowId": self.workflow_id,
            "apiKey": self.api_key,
            "nodeInfoList": [
                {
                    "nodeId": "2",  # ID узла для загрузки изображения продукта
                    "fieldName": "image",
                    "fieldValue": product_url
                },
                {
                    "nodeId": "32",  # ID узла для загрузки фонового изображения
                    "fieldName": "image",
                    "fieldValue": background_url
                }
            ]
        }
        
        try:
            async with (await self._get_session()).post(url, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Task creation failed with status {response.status}: {error_text}")
                
                result = await response.json()
                if result.get('code') != 0:
                    raise Exception(f"Task creation failed: {result.get('msg')}")
                
                task_id = result['data']['taskId']
                self.logger.info(f"Successfully created task: {task_id}")
                return task_id
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            return None

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
