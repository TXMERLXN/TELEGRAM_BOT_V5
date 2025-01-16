import asyncio
import logging
from typing import List, Dict, Optional

from .runninghub import RunningHubAPI
from .task_queue import task_queue

logger = logging.getLogger(__name__)

class IntegrationService:
    def __init__(self, accounts: List[Dict]):
        self.accounts = accounts
        self.runninghub_api = RunningHubAPI()
        self._initialized = False

    async def initialize(self):
        """Инициализация сервиса интеграции"""
        if self._initialized:
            return

        try:
            # Проверка доступности всех аккаунтов
            await self._validate_accounts()
            
            # Настройка глобальной очереди задач
            task_queue.accounts = self.accounts
            
            self._initialized = True
            logger.info("Integration service initialized successfully")
        except Exception as e:
            logger.error(f"Integration service initialization failed: {e}")
            raise

    async def _validate_accounts(self):
        """Проверка подключения к RunningHub для каждого аккаунта"""
        validated_accounts = []
        for account in self.accounts:
            try:
                # Проверка доступности аккаунта
                is_valid = await self._check_account_availability(account)
                if is_valid:
                    validated_accounts.append(account)
                    logger.info(f"Account {account.get('id')} validated successfully")
                else:
                    logger.warning(f"Account {account.get('id')} validation failed")
            except Exception as e:
                logger.error(f"Error validating account {account.get('id')}: {e}")

        if not validated_accounts:
            raise RuntimeError("No valid RunningHub accounts found")
        
        self.accounts = validated_accounts

    async def _check_account_availability(self, account: Dict) -> bool:
        """Проверка доступности конкретного аккаунта"""
        try:
            # Тестовый запрос к RunningHub API
            test_result = await self.runninghub_api.test_connection(
                api_key=account.get('api_key'),
                workflow_id=account.get('workflow_id')
            )
            return test_result
        except Exception as e:
            logger.error(f"Account connection test failed: {e}")
            return False

    async def process_task(self, task_data: Dict):
        """Обработка задачи через RunningHub"""
        try:
            # Получение свободного аккаунта
            account = await self._get_available_account()
            if not account:
                logger.warning("No available accounts to process task")
                return None

            # Выполнение задачи
            result = await self._execute_task(account, task_data)
            return result
        except Exception as e:
            logger.error(f"Task processing error: {e}")
            return None

    async def _get_available_account(self) -> Optional[Dict]:
        """Получение доступного аккаунта"""
        available_accounts = [
            account for account in self.accounts 
            if account.get('current_load', 0) < 5  # Максимальная нагрузка 5 задач
        ]
        return available_accounts[0] if available_accounts else None

    async def _execute_task(self, account: Dict, task_data: Dict):
        """Выполнение задачи с использованием аккаунта"""
        try:
            # Увеличение нагрузки на аккаунт
            account['current_load'] = account.get('current_load', 0) + 1

            # Создание задачи в RunningHub
            task_id = await self.runninghub_api.create_task(
                api_key=account.get('api_key'),
                workflow_id=account.get('workflow_id'),
                **task_data
            )

            if not task_id:
                raise ValueError("Failed to create task in RunningHub")

            # Ожидание результата
            result = await self._wait_for_task_completion(account, task_id)
            return result
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            raise
        finally:
            # Уменьшение нагрузки на аккаунт
            account['current_load'] = max(0, account.get('current_load', 0) - 1)

    async def _wait_for_task_completion(self, account: Dict, task_id: str):
        """Ожидание завершения задачи"""
        max_attempts = 60  # 5 минут с интервалом в 5 секунд
        for _ in range(max_attempts):
            await asyncio.sleep(5)
            results = await self.runninghub_api.get_task_outputs(
                api_key=account.get('api_key'),
                task_id=task_id
            )
            if results:
                return results
        
        logger.warning(f"Task {task_id} timed out")
        return None

    async def shutdown(self):
        """Корректное завершение сервиса"""
        logger.info("Shutting down integration service")
        try:
            # Остановка всех активных задач
            await task_queue.stop()
        except Exception as e:
            logger.error(f"Error during integration service shutdown: {e}")
        finally:
            self._initialized = False

# Создаем и экспортируем экземпляр сервиса
integration_service = IntegrationService(config.runninghub.accounts)
