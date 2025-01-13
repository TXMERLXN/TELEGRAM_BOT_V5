import aiohttp
import json
import logging
import asyncio
from typing import Optional, Dict, Union, Tuple
from PIL import Image
import io
from config import load_config
from .task_queue import task_queue
from .account_manager import account_manager, RunningHubAccount
import os
import aiofiles
import time
from tempfile import NamedTemporaryFile

config = load_config()
logger = logging.getLogger(__name__)

class RunningHubAPI:
    def __init__(self, bot=None):
        self.headers = {
            "Content-Type": "application/json"
        }
        self.api_url = config.runninghub.api_url
        self.bot_token = config.tg_bot.token
        self.session = None
        # Таймауты для HTTP-запросов
        self.timeout = aiohttp.ClientTimeout(
            total=config.runninghub.task_timeout,
            connect=60,  # Таймаут на подключение 1 минута
            sock_read=300  # Таймаут на чтение 5 минут
        )
        self.max_retries = config.runninghub.max_retries
        self.retry_delay = config.runninghub.retry_delay
        self.max_image_size = 1024  # Максимальный размер изображения
        # Словарь для хранения аккаунтов по task_id
        self.task_accounts = {}
        self.bot = bot
        logger.setLevel(logging.DEBUG)
        logger.info("Initialized RunningHubAPI")

    async def initialize(self):
        """Инициализация сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Закрытие сессии"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
                logger.info("RunningHub session closed")
        except Exception as e:
            logger.error(f"Error closing RunningHub session: {str(e)}")

    def _resize_image(self, image_data: bytes) -> bytes:
        """Уменьшает размер изображения, сохраняя пропорции"""
        try:
            # Открываем изображение из bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Получаем размеры
            width, height = image.size
            
            # Если изображение меньше максимального размера, возвращаем как есть
            if width <= self.max_image_size and height <= self.max_image_size:
                return image_data
            
            # Вычисляем новые размеры, сохраняя пропорции
            if width > height:
                new_width = self.max_image_size
                new_height = int(height * (self.max_image_size / width))
            else:
                new_height = self.max_image_size
                new_width = int(width * (self.max_image_size / height))
            
            # Изменяем размер
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Сохраняем в bytes
            output = io.BytesIO()
            resized_image.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            return image_data

    async def _make_request(self, method: str, url: str, **kwargs) -> Tuple[int, Optional[str]]:
        """Выполняет HTTP запрос с повторными попытками"""
        try:
            async with aiohttp.ClientSession() as session:
                async with getattr(session, method)(url, **kwargs) as response:
                    response_text = await response.text()
                    return response.status, response_text
        except Exception as e:
            logger.error(f"HTTP request error: {str(e)}")
            return 500, None

    async def upload_image(self, image_data: bytes, filename: str, account: RunningHubAccount) -> Optional[str]:
        """Загружает изображение в RunningHub"""
        url = f"{self.api_url}/task/openapi/upload"
        
        for attempt in range(self.max_retries):
            try:
                # Создаем форму для загрузки
                form = aiohttp.FormData()
                form.add_field('apiKey', account.api_key)
                form.add_field('file', image_data, filename=filename, content_type='image/png')
                
                # Отправляем запрос
                status, response_text = await self._make_request('post', url, data=form)
                logger.debug(f"Upload response: {response_text}")
                
                if status == 200:
                    response = json.loads(response_text)
                    if response.get('code') == 0 and response.get('data', {}).get('fileName'):
                        return response['data']['fileName']  # Возвращаем полный путь из ответа
                    
                logger.error(f"Failed to upload image (attempt {attempt + 1}): {response_text}")
                
            except Exception as e:
                logger.error(f"Error uploading image (attempt {attempt + 1}): {str(e)}")
                
            # Ждем перед следующей попыткой
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
        
        return None

    async def _get_telegram_file_path(self, file_id: str) -> str:
        """
        Получает путь к файлу в Telegram
        """
        url = f"https://api.telegram.org/bot{config.tg_bot.token}/getFile"
        params = {"file_id": file_id}
        
        status, response_text = await self._make_request('get', url, params=params)
        if status == 200 and response_text:
            try:
                data = json.loads(response_text)
                if data.get("ok"):
                    return data["result"]["file_path"]
            except json.JSONDecodeError:
                pass
        logger.error(f"Failed to get file path from Telegram: {status}")
        return None

    async def _download_telegram_file(self, file_id: str) -> Optional[bytes]:
        """Скачивает файл из Telegram"""
        try:
            file = await self.bot.get_file(file_id)
            if not file or not file.file_path:
                logger.error(f"Failed to get file info for {file_id}")
                return None

            url = f"https://api.telegram.org/file/bot{self.bot_token}/{file.file_path}"
            status, response = await self._make_request('get', url, return_bytes=True)
            
            if status == 200 and response:
                return response
            
            logger.error(f"Failed to download file from Telegram: {status}")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading Telegram file: {str(e)}")
            return None

    async def _wait_for_task_completion(self, task_id: str, max_attempts: int = 120, delay: int = 5) -> Optional[str]:
        """
        Ожидает завершения задачи и возвращает результат
        max_attempts: максимальное количество попыток (120 попыток * 5 секунд = 10 минут)
        delay: задержка между попытками в секундах
        """
        url = f"{self.api_url}/task/openapi/outputs"
        account = self.task_accounts.get(task_id)
        if not account:
            logger.error(f"No account found for task {task_id}")
            return None

        result_url = None
        task_completed = False
        try:
            for attempt in range(max_attempts):
                logger.info(f"Getting task result for task {task_id} (attempt {attempt + 1}/{max_attempts})")
                
                try:
                    payload = {
                        "taskId": task_id,
                        "apiKey": account.api_key
                    }

                    status, response_text = await self._make_request('post', url, json=payload)
                    
                    if status == 504:  # Gateway Timeout
                        logger.warning("Got timeout, will retry...")
                        await asyncio.sleep(delay)
                        continue
                        
                    if status == 200 and response_text:
                        try:
                            data = json.loads(response_text)
                            if data.get("code") == 0 and data.get("data"):
                                task_info = data["data"]
                                task_id = task_info.get("taskId")
                                if task_id:
                                    # Успешное завершение
                                    result = data["data"][0]
                                    if result.get("fileUrl"):  # API возвращает fileUrl
                                        logger.info(f"Task {task_id} completed successfully")
                                        result_url = result["fileUrl"]
                                        task_completed = True
                                        break
                                    elif result.get("text"):
                                        logger.info(f"Task {task_id} completed successfully")
                                        result_url = result["text"]
                                        task_completed = True
                                        break
                                    else:
                                        logger.error("Task completed but no result found")
                                        break
                                else:
                                    logger.error(f"No taskId in response: {task_info}")
                            elif data.get("code") == 804:  # APIKEY_TASK_IS_RUNNING
                                logger.info("Task is still running, waiting...")
                                await asyncio.sleep(delay)
                                continue
                            elif data.get("code") == 805:  # APIKEY_TASK_QUEUE
                                logger.info("Task is in queue, waiting...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                error_msg = data.get("msg", "Unknown error")
                                logger.error(f"Task result API error: {error_msg}")
                                break
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse task result JSON response: {e}")
                            break
                    else:
                        logger.error(f"Task result API error: {status}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error while waiting for task completion: {str(e)}")
                    break

            if not result_url:
                logger.error(f"Task {task_id} did not complete within {max_attempts * delay} seconds")
                return None

            return result_url
            
        finally:
            # Освобождаем аккаунт только если задача завершилась или произошла ошибка
            if task_id in self.task_accounts and (task_completed or not result_url):
                await account_manager.release_account(account)
                self.task_accounts.pop(task_id, None)
                logger.info(f"Released account for task {task_id}")

    async def create_task(self, product_filename: str, background_filename: str, workflow_id: str, account: RunningHubAccount) -> Optional[str]:
        """Создает задачу в RunningHub"""
        url = f"{self.api_url}/task/openapi/create"
        
        for attempt in range(self.max_retries):
            logger.info(f"Creating task with uploaded files (attempt {attempt + 1}/{self.max_retries})")
            
            try:
                # Убеждаемся что пути начинаются с api/
                if not product_filename.startswith('api/'):
                    product_filename = f'api/{product_filename}'
                if not background_filename.startswith('api/'):
                    background_filename = f'api/{background_filename}'

                # Создаем задачу
                payload = {
                    "apiKey": account.api_key,
                    "workflowId": workflow_id,
                    "inputs": {
                        "2": product_filename,  # Нода #2 для изображения товара
                        "32": background_filename  # Нода #32 для изображения фона
                    }
                }
                
                status, response_text = await self._make_request('post', url, json=payload)
                logger.debug(f"Create task response: {response_text}")
                
                if status == 200 and response_text:
                    try:
                        data = json.loads(response_text)
                        if data.get("code") == 0 and data.get("data"):
                            task_info = data["data"]
                            task_id = task_info.get("taskId")
                            if task_id:
                                # Сохраняем аккаунт для этой задачи
                                self.task_accounts[task_id] = account
                                logger.info(f"Created task {task_info}")
                                return task_id
                            else:
                                logger.error(f"No taskId in response: {task_info}")
                        else:
                            logger.error(f"API error: {data.get('msg', 'Unknown error')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse task creation response: {e}")
                        continue
                
                logger.error(f"Task creation API error: {status} - {response_text}")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                logger.error(f"Error creating task: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        
        logger.error("Failed to create task")
        return None

    async def get_generation_status(self, task_id: str) -> tuple[str, Optional[str]]:
        """
        Получает статус генерации и URL результата
        Возвращает: (status, result_url)
        """
        url = f"{self.api_url}/task/openapi/status"  # Исправляем endpoint для проверки статуса
        account = self.task_accounts.get(task_id)
        if not account:
            logger.error(f"No account found for task {task_id}")
            return "failed", None

        payload = {
            "taskId": task_id,
            "apiKey": account.api_key
        }

        status, response_text = await self._make_request('post', url, json=payload)
        logger.debug(f"Status check response: {response_text}")
        
        if status == 200 and response_text:
            try:
                data = json.loads(response_text)
                if data.get("code") == 0:
                    task_status = str(data.get("data", "")).upper()
                    logger.debug(f"Task status: {task_status}")
                    
                    # Нормализуем статусы
                    status_mapping = {
                        "SUCCESS": "SUCCEEDED",
                        "FAIL": "FAILED",
                        "FAILED": "FAILED"
                    }
                    task_status = status_mapping.get(task_status, task_status)
                    
                    if task_status == "SUCCEEDED":
                        # Получаем результат через отдельный endpoint
                        result_url = f"{self.api_url}/task/openapi/outputs"
                        result_payload = {
                            "taskId": task_id,
                            "apiKey": account.api_key
                        }
                        result_status, result_response = await self._make_request('post', result_url, json=result_payload)
                        logger.debug(f"Result response: {result_response}")
                        
                        if result_status == 200 and result_response:
                            try:
                                result_data = json.loads(result_response)
                                if result_data.get("code") == 0 and result_data.get("data"):
                                    outputs = result_data["data"]
                                    if isinstance(outputs, list) and outputs:
                                        for output in outputs:
                                            if output.get("fileUrl"):  # API возвращает fileUrl
                                                return "completed", output["fileUrl"]
                                    logger.error(f"No URL in outputs: {outputs}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse result response: {e}")
                        
                        return "failed", None
                    elif task_status == "FAILED":
                        logger.error(f"Task failed with status: {task_status}")
                        return "failed", None
                    elif task_status in ["RUNNING", "PENDING", "QUEUED"]:
                        return "processing", None
                    else:
                        logger.error(f"Unknown task status: {task_status}")
                        return "failed", None
                elif data.get("code") == 804:  # APIKEY_TASK_IS_RUNNING
                    return "processing", None
                elif data.get("code") == 805:  # APIKEY_TASK_QUEUE
                    return "queued", None
                else:
                    logger.error(f"API error: {data.get('msg', 'Unknown error')}")
                    return "failed", None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse task status response: {e}")
                return "failed", None
            except Exception as e:
                logger.error(f"Error checking task status: {str(e)}\nResponse: {response_text}")
                return "failed", None
        return "failed", None

    async def generate_product_photo(self, user_id: int, product_file_id: str, background_file_id: str) -> Optional[str]:
        """Генерирует фото продукта с новым фоном"""
        try:
            account = await account_manager.get_available_account('product')
            if not account:
                logger.error("No available accounts for product generation")
                return None

            # Получаем workflow_id для этого аккаунта
            workflow_id = account.workflows.get('product')
            if not workflow_id:
                logger.error("No workflow_id found for product generation")
                await account_manager.release_account(account)
                return None

            # Скачиваем файлы
            product_data = await self._download_telegram_file(product_file_id)
            if not product_data:
                logger.error("Failed to download product image")
                await account_manager.release_account(account)
                return None

            background_data = await self._download_telegram_file(background_file_id)
            if not background_data:
                logger.error("Failed to download background image")
                await account_manager.release_account(account)
                return None

            # Загружаем файлы на RunningHub
            product_filename = await self.upload_image(product_data, "product.png", account)
            if not product_filename:
                logger.error("Failed to upload product image")
                await account_manager.release_account(account)
                return None

            background_filename = await self.upload_image(background_data, "background.png", account)
            if not background_filename:
                logger.error("Failed to upload background image")
                await account_manager.release_account(account)
                return None

            try:
                # Создаем задачу
                task_id = await self.create_task(
                    product_filename,
                    background_filename,
                    workflow_id,
                    account
                )
                
                if not task_id:
                    logger.error("Failed to create task")
                    await account_manager.release_account(account)
                    return None

                # Ждем результат
                start_time = time.time()
                while time.time() - start_time < config.runninghub.task_timeout:
                    status, result_url = await self.get_generation_status(task_id)
                    
                    if status == "completed" and result_url:
                        logger.info(f"Task {task_id} completed successfully")
                        return result_url
                        
                    if status == "failed":
                        logger.error(f"Task {task_id} failed")
                        break
                        
                    # Продолжаем ждать, если задача в процессе
                    if status in ["processing", "queued"]:
                        await asyncio.sleep(config.runninghub.polling_interval)
                        continue
                        
                    # Неизвестный статус
                    logger.error(f"Unknown task status: {status}")
                    break
                
                logger.error(f"Task {task_id} timed out")
                return None
                
            finally:
                # Освобождаем аккаунт
                await account_manager.release_account(account)
                
        except Exception as e:
            logger.error(f"Error generating product photo: {str(e)}")
            if 'account' in locals():
                await account_manager.release_account(account)
            return None
