import aiohttp
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

@dataclass
class RunningHubAccount:
    api_key: str
    workflow_id: str
    max_tasks: int = 5

class RunningHubAPI:
    BASE_URL = "https://api.runninghub.com"

    def __init__(self):
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def upload_image(self, api_key: str, image_url: str) -> Optional[str]:
        """Загружает изображение в RunningHub"""
        session = await self._get_session()
        async with session.post(
            f"{self.BASE_URL}/task/openapi/upload",
            headers={"Authorization": f"Bearer {api_key}"},
            data={
                "file": image_url,
                "fileType": "image"
            }
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {}).get("fileName")
            return None

    async def create_task(
        self,
        api_key: str,
        workflow_id: str,
        product_image_url: str,
        background_image_url: str
    ) -> Optional[str]:
        """Создает задачу в RunningHub"""
        session = await self._get_session()
        product_file = await self.upload_image(api_key, product_image_url)
        if not product_file:
            return None

        background_file = await self.upload_image(api_key, background_image_url)
        if not background_file:
            return None

        payload = {
            "workflowId": workflow_id,
            "apiKey": api_key,
            "nodeInfoList": [
                {
                    "nodeId": "2",
                    "fieldName": "image",
                    "fieldValue": product_file
                },
                {
                    "nodeId": "32",
                    "fieldName": "image",
                    "fieldValue": background_file
                }
            ]
        }

        async with session.post(
            f"{self.BASE_URL}/task/openapi/create",
            json=payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {}).get("taskId")
            return None

    async def get_task_outputs(self, api_key: str, task_id: str) -> Optional[List[Dict[str, Any]]]:
        """Получает результаты выполнения задачи"""
        session = await self._get_session()
        async with session.post(
            f"{self.BASE_URL}/task/openapi/outputs",
            json={
                "taskId": task_id,
                "apiKey": api_key
            }
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            return None

    async def check_account_status(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Проверяет статус аккаунта"""
        session = await self._get_session()
        async with session.post(
            f"{self.BASE_URL}/uc/openapi/accountStatus",
            json={"apikey": api_key}
        ) as response:
            if response.status == 200:
                return await response.json()
            return None

    async def close(self) -> None:
        """Закрывает сессию"""
        if self._session and not self._session.closed:
            await self._session.close()
