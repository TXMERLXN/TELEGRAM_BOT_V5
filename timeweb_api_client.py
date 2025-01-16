import requests
import os
import json
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv('timeweb.env')

class TimewebCloudAPI:
    def __init__(self, api_key=None):
        """
        Инициализация клиента API Timeweb Cloud
        
        :param api_key: API-ключ из личного кабинета
        """
        self.api_key = api_key or os.getenv('TIMEWEB_API_KEY')
        if not self.api_key:
            raise ValueError("API-ключ не найден. Установите в timeweb.env файле TIMEWEB_API_KEY")
        
        self.base_url = "https://api.timeweb.cloud/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method, endpoint, data=None):
        """
        Выполнение HTTP-запроса с обработкой ошибок
        
        :param method: HTTP-метод (get, post, put, delete)
        :param endpoint: URL эндпоинта
        :param data: Данные для запроса
        :return: Ответ от API
        """
        try:
            full_url = f"{self.base_url}/{endpoint}"
            logger.info(f"Запрос {method.upper()} {full_url}")
            
            response_method = getattr(requests, method)
            response = response_method(full_url, headers=self.headers, json=data)
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            raise

    def create_server(self, server_config):
        """
        Создание нового сервера
        
        :param server_config: Словарь с конфигурацией сервера
        :return: Информация о созданном сервере
        """
        return self._make_request('post', 'servers', server_config)

    def list_servers(self):
        """
        Получение списка серверов
        
        :return: Список серверов
        """
        return self._make_request('get', 'servers')

    def get_server_details(self, server_id):
        """
        Получение детальной информации о сервере
        
        :param server_id: ID сервера
        :return: Детали сервера
        """
        return self._make_request('get', f'servers/{server_id}')

    def deploy_telegram_bot_server(self):
        """
        Автоматизированное создание сервера для Telegram бота
        
        :return: Информация о созданном сервере
        """
        server_config = {
            "name": "telegram-bot-v5",
            "os": "ubuntu-22.04",
            "configuration": {
                "cpu": 2,
                "ram": 4,
                "disk": 50
            },
            "network": {
                "bandwidth": 100,
                "firewall": {
                    "rules": [
                        {
                            "port": 8080,
                            "protocol": "tcp",
                            "direction": "in"
                        }
                    ]
                }
            },
            "additional_software": [
                "docker",
                "docker-compose"
            ]
        }
        
        return self.create_server(server_config)

def main():
    try:
        api_client = TimewebCloudAPI()
        
        # Создание сервера
        new_server = api_client.deploy_telegram_bot_server()
        print(json.dumps(new_server, indent=2))
        
        # Получение списка серверов
        servers = api_client.list_servers()
        print(json.dumps(servers, indent=2))
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
