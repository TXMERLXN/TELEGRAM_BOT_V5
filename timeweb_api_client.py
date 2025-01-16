import requests
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class TimewebCloudAPI:
    def __init__(self, api_key=None):
        """
        Инициализация клиента API Timeweb Cloud
        
        :param api_key: API-ключ из личного кабинета
        """
        self.api_key = api_key or os.getenv('TIMEWEB_API_KEY')
        if not self.api_key:
            raise ValueError("API-ключ не найден. Установите в .env файле TIMEWEB_API_KEY")
        
        self.base_url = "https://api.timeweb.cloud/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_server(self, server_config):
        """
        Создание нового сервера
        
        :param server_config: Словарь с конфигурацией сервера
        :return: Информация о созданном сервере
        """
        endpoint = f"{self.base_url}/servers"
        response = requests.post(endpoint, json=server_config, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_servers(self):
        """
        Получение списка серверов
        
        :return: Список серверов
        """
        endpoint = f"{self.base_url}/servers"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_server_details(self, server_id):
        """
        Получение детальной информации о сервере
        
        :param server_id: ID сервера
        :return: Детали сервера
        """
        endpoint = f"{self.base_url}/servers/{server_id}"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def deploy_telegram_bot(self):
        """
        Автоматизированное создание сервера для Telegram бота
        
        :return: Информация о созданном сервере
        """
        server_config = {
            "name": "telegram-bot-v5",
            "os": "ubuntu-22.04",
            "cpu": 2,
            "ram": 4,
            "disk": 50,
            "network": {
                "bandwidth": 100
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
        new_server = api_client.deploy_telegram_bot()
        print("Сервер создан:", new_server)
        
        # Получение списка серверов
        servers = api_client.list_servers()
        print("Список серверов:", servers)
    
    except Exception as e:
        print(f"Ошибка при работе с API: {e}")

if __name__ == "__main__":
    main()
