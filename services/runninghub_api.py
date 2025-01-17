import asyncio
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RunningHubAPI:
    def __init__(self, base_url: str = "https://api.runninghub.com"):
        """
        Инициализация API для RunningHub
        
        :param base_url: Базовый URL API
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def create_task(
        self, 
        api_key: str, 
        workflow_id: str, 
        product_image_url: str, 
        background_image_url: str
    ) -> Optional[str]:
        """
        Создание задачи в RunningHub
        
        :param api_key: API ключ
        :param workflow_id: ID workflow
        :param product_image_url: URL продукта
        :param background_image_url: URL фона
        :return: ID созданной задачи или None
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tasks",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "workflow_id": workflow_id,
                    "inputs": {
                        "product_image": product_image_url,
                        "background_image": background_image_url
                    }
                }
            )
            response.raise_for_status()
            return response.json().get("task_id")
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    async def get_task_outputs(
        self, 
        api_key: str, 
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получение результатов задачи
        
        :param api_key: API ключ
        :param task_id: ID задачи
        :return: Результаты задачи или None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers={
                    "Authorization": f"Bearer {api_key}"
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting task outputs: {e}")
            return None

    async def wait_for_task(
        self, 
        api_key: str, 
        task_id: str, 
        timeout: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Ожидание завершения задачи с таймаутом
        
        :param api_key: API ключ
        :param task_id: ID задачи
        :param timeout: Максимальное время ожидания в секундах
        :return: Результаты задачи или None
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                logger.warning(f"Task {task_id} timed out")
                return None

            result = await self.get_task_outputs(api_key, task_id)
            
            if result and result.get('status') == 'completed':
                return result
            
            await asyncio.sleep(5)  # Опрос каждые 5 секунд

    async def close(self):
        """
        Закрытие HTTP-клиента
        """
        await self.client.aclose()
