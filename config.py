from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

@dataclass
class TgBot:
    token: str

@dataclass
class RunningHub:
    api_key: str
    max_concurrent_tasks: int = 10  # Увеличиваем количество параллельных задач
    task_timeout: int = 600  # Таймаут задачи в секундах (10 минут)
    retry_delay: int = 5  # Задержка между попытками в секундах
    max_retries: int = 3  # Максимальное количество попыток для HTTP запросов

@dataclass
class Config:
    tg_bot: TgBot
    runninghub: RunningHub

def load_config() -> Config:
    # Load .env file
    load_dotenv()

    bot_token = getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set")
        raise ValueError("BOT_TOKEN environment variable is not set")

    api_key = getenv("RUNNINGHUB_API_KEY")
    if not api_key:
        logger.error("RUNNINGHUB_API_KEY environment variable is not set")
        raise ValueError("RUNNINGHUB_API_KEY environment variable is not set")

    return Config(
        tg_bot=TgBot(
            token=bot_token
        ),
        runninghub=RunningHub(
            api_key=api_key
        )
    )

config = load_config()