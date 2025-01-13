import aiohttp
import json
import logging
import asyncio
from typing import Optional, Dict
from PIL import Image
import io
from config import load_config
from .task_queue import task_queue
from .account_manager import account_manager, RunningHubAccount

config = load_config()
logger = logging.getLogger(__name__)

class RunningHubAPI:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json"
        }
        self.api_url = "https://www.runninghub.ai"
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
        logger.info("Initialized RunningHubAPI")

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

    async def _make_request(self, method: str, url: str, return_bytes: bool = False, **kwargs) -> tuple:
        """
        Выполняет HTTP-запрос с повторными попытками
        """
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with getattr(session, method)(url, **kwargs) as response:
                        if return_bytes:
                            response_data = await response.read()
                        else:
                            response_data = await response.text()
                        return response.status, response_data
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
            except Exception as e:
                logger.error(f"Request failed on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
        raise Exception(f"Failed after {self.max_retries} attempts")

    async def upload_image(self, image_data: bytes, filename: str, account: RunningHubAccount) -> Optional[str]:
        """Загружает изображение на RunningHub"""
        url = f"{self.api_url}/task/openapi/upload"
        
        try:
            form = aiohttp.FormData()
            form.add_field('apiKey', account.api_key)
            form.add_field('file', image_data, filename=filename, content_type='image/jpeg')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form) as response:
                    response_text = await response.text()
                    logger.debug(f"Upload response: {response_text}")
                    
                    if response.status == 200:
                        try:
                            data = json.loads(response_text)
                            if data.get("code") == 0:
                                return data["data"]["fileName"]
                            else:
                                logger.error(f"Upload API error: {data.get('msg', 'Unknown error')}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse upload response: {e}")
                    else:
                        logger.error(f"Failed to upload image: {response.status} - {response_text}")
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
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
        """
        Скачивает файл из Telegram
        """
        file_path = await self._get_telegram_file_path(file_id)
        if not file_path:
            return None

        url = f"https://api.telegram.org/file/bot{config.tg_bot.token}/{file_path}"
        status, response = await self._make_request('get', url, return_bytes=True)
        if status == 200 and response:
            return response
        
        logger.error(f"Failed to download file from Telegram: {status}")
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
                
                payload = {
                    "taskId": task_id,
                    "apiKey": account.api_key
                }

                try:
                    status, response_text = await self._make_request('post', url, json=payload)
                    
                    if status == 504:  # Gateway Timeout
                        logger.warning("Got timeout, will retry...")
                        await asyncio.sleep(delay)
                        continue
                        
                    if status == 200 and response_text:
                        try:
                            data = json.loads(response_text)
                            if data.get("code") == 0 and data["data"]:
                                # Успешное завершение
                                result = data["data"][0]
                                if result.get("fileUrl"):
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
                        logger.error(f"Task result API error: {status} - {response_text}")
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
        
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Creating task with uploaded files (attempt {attempt}/{self.max_retries})")
            
            data = {
                "apiKey": account.api_key,
                "workflowId": workflow_id,
                "variables": {
                    "product_image": product_filename,
                    "background_image": background_filename
                }
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=data) as response:
                        response_text = await response.text()
                        if response.status == 200:
                            try:
                                data = json.loads(response_text)
                                if data.get("code") == 0:
                                    return data["data"]["taskId"]
                                else:
                                    error_msg = data.get("msg", "Unknown error")
                                    if error_msg == "TASK_QUEUE_MAXED":
                                        # Если очередь заполнена, ждем дольше перед следующей попыткой
                                        logger.warning("Task queue is maxed out, waiting before retry")
                                        await asyncio.sleep(self.retry_delay * 2)
                                    elif error_msg == "TASK_CREATE_TOO_FAST":
                                        logger.warning("Task creation too fast, waiting before retry")
                                        await asyncio.sleep(self.retry_delay)
                                    else:
                                        logger.error(f"Task creation API error: {error_msg}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse task creation response: {e}")
                        else:
                            logger.error(f"Task creation failed with status {response.status}")
                            
            except Exception as e:
                logger.error(f"Error creating task: {str(e)}")
            
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay)
                
        return None

    async def generate_product_photo(self, user_id: int, product_file_id: str, background_file_id: str) -> Optional[str]:
        """
        Генерирует фотографию продукта с фоном
        """
        account = None
        task_id = None
        try:
            # Получаем доступный аккаунт для генерации
            account = await account_manager.get_available_account("product")
            if not account:
                logger.error("No available RunningHub accounts")
                return None

            workflow_id = account.workflows["product"]
            logger.info(f"Using RunningHub account with workflow_id: {workflow_id}")

            # Скачиваем изображения из Telegram
            product_image = await self._download_telegram_file(product_file_id)
            if not product_image:
                logger.error("Failed to download product image")
                return None

            background_image = await self._download_telegram_file(background_file_id)
            if not background_image:
                logger.error("Failed to download background image")
                return None

            # Уменьшаем размер изображений
            product_image = self._resize_image(product_image)
            background_image = self._resize_image(background_image)

            # Загружаем изображения
            product_filename = await self.upload_image(product_image, "product.jpg", account)
            if not product_filename:
                logger.error("Failed to upload product image")
                return None

            background_filename = await self.upload_image(background_image, "background.jpg", account)
            if not background_filename:
                logger.error("Failed to upload background image")
                return None

            # Создаем задачу
            task_id = await self.create_task(product_filename, background_filename, workflow_id, account)
            if not task_id:
                logger.error("Failed to create task")
                return None

            # Сохраняем аккаунт для этой задачи
            self.task_accounts[task_id] = account

            logger.info(f"Created task {task_id} for user {user_id}")

            # Добавляем задачу в очередь
            await task_queue.add_task(user_id, task_id)

            # Ожидаем завершения задачи
            result_url = await self._wait_for_task_completion(task_id)
            if not result_url:
                logger.error(f"Task {task_id} failed or timed out")
                return None

            return result_url

        except Exception as e:
            logger.error(f"Error in generate_product_photo: {str(e)}")
            return None
        finally:
            # Освобождаем аккаунт в случае ошибки
            if account and (task_id is None or task_id not in self.task_accounts):
                await account_manager.release_account(account)

    async def get_generation_status(self, task_id: str) -> tuple[str, Optional[str]]:
        """
        Получает статус генерации и URL результата
        Возвращает: (status, result_url)
        """
        url = f"{self.api_url}/task/openapi/outputs"
        account = self.task_accounts.get(task_id)
        if not account:
            logger.error(f"No account found for task {task_id}")
            return None

        payload = {
            "taskId": task_id,
            "apiKey": account.api_key
        }

        status, response_text = await self._make_request('post', url, json=payload)
        if status == 200 and response_text:
            try:
                data = json.loads(response_text)
                if data.get("code") == 0 and data["data"]:
                    # Задача завершена успешно
                    result = data["data"][0]
                    if result.get("fileUrl"):
                        return "completed", result["fileUrl"]
                    elif result.get("text"):
                        return "completed", result["text"]
                    else:
                        logger.error("Task completed but no result found")
                        return None
                elif data.get("code") == 804:  # APIKEY_TASK_IS_RUNNING
                    return "processing", None
                elif data.get("code") == 805:  # APIKEY_TASK_QUEUE
                    return "queued", None
                else:
                    return "failed", None
            except json.JSONDecodeError:
                return "failed", None
        return "failed", None
