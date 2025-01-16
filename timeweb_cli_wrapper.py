import subprocess
import json
import logging
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TimewebCLIWrapper:
    @staticmethod
    def _run_command(command: List[str]) -> Dict:
        """
        Выполнение команды Timeweb CLI
        
        :param command: Список аргументов команды
        :return: Результат выполнения команды
        """
        try:
            result = subprocess.run(
                ['twc'] + command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return {
                'success': True,
                'output': json.loads(result.stdout) if result.stdout else {},
                'error': None
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка выполнения команды: {e}")
            return {
                'success': False,
                'output': {},
                'error': e.stderr
            }
        except json.JSONDecodeError:
            logger.warning("Не удалось распарсить JSON-ответ")
            return {
                'success': False,
                'output': {},
                'error': 'JSON parsing error'
            }

    @classmethod
    def create_server(cls, name: str, os: str = 'ubuntu-22.04', 
                      cpu: int = 2, ram: int = 4, disk: int = 50) -> Optional[Dict]:
        """
        Создание нового сервера
        
        :param name: Имя сервера
        :param os: Операционная система
        :param cpu: Количество ядер
        :param ram: Объем RAM в ГБ
        :param disk: Размер диска в ГБ
        :return: Информация о созданном сервере
        """
        command = [
            'server', 'create', 
            '--name', name,
            '--os', os,
            '--cpu', str(cpu),
            '--ram', str(ram),
            '--disk', str(disk),
            '--output', 'json'
        ]
        return cls._run_command(command)

    @classmethod
    def list_servers(cls) -> Optional[Dict]:
        """
        Получение списка серверов
        
        :return: Список серверов
        """
        return cls._run_command(['server', 'list', '--output', 'json'])

    @classmethod
    def deploy_telegram_bot(cls, server_id: str) -> Optional[Dict]:
        """
        Деплой Telegram бота на указанный сервер
        
        :param server_id: ID сервера
        :return: Результат деплоя
        """
        command = [
            'app', 'deploy',
            '--server-id', server_id,
            '--repository', 'https://github.com/TXMERLXN/TELEGRAM_BOT_V5.git',
            '--branch', 'master',
            '--output', 'json'
        ]
        return cls._run_command(command)

def main():
    cli = TimewebCLIWrapper()
    
    # Создание сервера
    server_result = cli.create_server(name='telegram-bot-v5')
    if server_result['success']:
        server_id = server_result['output'].get('id')
        
        # Деплой бота
        deploy_result = cli.deploy_telegram_bot(server_id)
        print(json.dumps(deploy_result, indent=2))
    else:
        logger.error("Не удалось создать сервер")

if __name__ == "__main__":
    main()
