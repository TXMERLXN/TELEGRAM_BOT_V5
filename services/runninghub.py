import aiohttp
import json
import logging
import asyncio
from config import load_config

config = load_config()
logger = logging.getLogger(__name__)

class RunningHubAPI:
    def __init__(self):
        self.api_key = config.runninghub.api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        self.workflow_id = "1871659613585305601"
        self.api_url = "https://www.runninghub.ai"
        # Таймауты для HTTP-запросов
        self.timeout = aiohttp.ClientTimeout(
            total=600,  # Общий таймаут 10 минут
            connect=60,  # Таймаут на подключение 1 минута
            sock_read=300  # Таймаут на чтение 5 минут
        )
        if not self.api_key:
            logger.error("RunningHubAPI initialization failed: API key is not set")
            raise ValueError("RUNNINGHUB_API_KEY environment variable is not set")
        logger.info(f"Initialized RunningHubAPI with API key: {self.api_key[:8]}...")

    async def _make_request(self, method: str, url: str, return_bytes: bool = False, **kwargs) -> tuple:
        """
        Выполняет HTTP-запрос с повторными попытками
        """
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with getattr(session, method)(url, **kwargs) as response:
                        if return_bytes:
                            response_data = await response.read()
                        else:
                            response_data = await response.text()
                        return response.status, response_data
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                continue
            except Exception as e:
                logger.error(f"Request error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                continue
        
        return None, None

    async def upload_image(self, image_data: bytes, filename: str) -> str:
        """
        Загружает изображение на сервер RunningHub
        """
        url = f"{self.api_url}/task/openapi/upload"
        
        # Создаем форму для загрузки файла
        form = aiohttp.FormData()
        form.add_field('apiKey', self.api_key)
        form.add_field('file', image_data, filename=filename, content_type='image/jpeg')
        form.add_field('fileType', 'image')

        logger.info(f"Uploading image to {url}")
        
        status, response_text = await self._make_request('post', url, data=form)
        if status == 200 and response_text:
            try:
                data = json.loads(response_text)
                if data.get("code") == 0:
                    return data["data"]["fileName"]
                else:
                    error_msg = data.get("msg")
                    logger.error(f"Upload API error: {error_msg}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse upload JSON response: {e}")
        else:
            logger.error(f"Upload API error: {status} - {response_text}")
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

    async def _download_telegram_file(self, file_id: str) -> bytes:
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

    async def _wait_for_task_completion(self, task_id: str, max_attempts: int = 120, delay: int = 5) -> str:
        """
        Ожидает завершения задачи и возвращает результат
        max_attempts: максимальное количество попыток (120 попыток * 5 секунд = 10 минут)
        delay: задержка между попытками в секундах
        """
        url = f"{self.api_url}/task/openapi/outputs"
        payload = {
            "taskId": task_id,
            "apiKey": self.api_key
        }

        for attempt in range(max_attempts):
            logger.info(f"Getting task result for task {task_id} (attempt {attempt + 1}/{max_attempts})")
            
            status, response_text = await self._make_request('post', url, json=payload)
            if status == 200 and response_text:
                try:
                    data = json.loads(response_text)
                    if data.get("code") == 0 and data["data"]:
                        return data["data"][0]["fileUrl"]
                    elif data.get("code") == 804:  # APIKEY_TASK_IS_RUNNING
                        logger.info("Task is still running, waiting...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        error_msg = data.get("msg")
                        logger.error(f"Task result API error: {error_msg}")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse task result JSON response: {e}")
                    return None
            else:
                logger.error(f"Task result API error: {status} - {response_text}")
                if status != 504:  # Если ошибка не таймаут, прекращаем попытки
                    return None
                logger.warning("Got timeout, will retry...")
                await asyncio.sleep(delay)
                continue
            
        logger.error(f"Task {task_id} did not complete within {max_attempts * delay} seconds")
        return None

    async def generate_product_photo(self, product_image: str, background_image: str) -> str:
        """
        Генерирует фотографию продукта с фоном
        """
        # Скачиваем файлы из Telegram
        product_data = await self._download_telegram_file(product_image)
        background_data = await self._download_telegram_file(background_image)
        
        if not product_data or not background_data:
            logger.error("Failed to download images from Telegram")
            return None

        # Загружаем файлы на RunningHub
        product_filename = await self.upload_image(product_data, "product.jpg")
        background_filename = await self.upload_image(background_data, "background.jpg")

        if not product_filename or not background_filename:
            logger.error("Failed to upload images to RunningHub")
            return None

        # Создаем задачу с загруженными файлами
        url = f"{self.api_url}/task/openapi/create"
        payload = {
            "workflowId": self.workflow_id,
            "apiKey": self.api_key,
            "nodeInfoList": [
                {
                    "nodeId": "2",  # ID ноды для загрузки изображения продукта
                    "fieldName": "image",
                    "fieldValue": product_filename
                },
                {
                    "nodeId": "32",  # ID ноды для загрузки фонового изображения
                    "fieldName": "image",
                    "fieldValue": background_filename
                }
            ]
        }

        logger.info("Creating task with uploaded files")
        status, response_text = await self._make_request('post', url, json=payload)
        if status == 200 and response_text:
            try:
                data = json.loads(response_text)
                if data.get("code") == 0:
                    task_id = data["data"]["taskId"]
                    logger.info(f"Task created successfully: {task_id}")
                    # Ждем завершения задачи
                    return await self._wait_for_task_completion(task_id)
                else:
                    error_msg = data.get("msg")
                    logger.error(f"Task creation API error: {error_msg}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse task creation JSON response: {e}")
        else:
            logger.error(f"Task creation API error: {status} - {response_text}")
        return None
