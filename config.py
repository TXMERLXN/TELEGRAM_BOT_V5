from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

@dataclass
class TgBot:
    token: str

@dataclass
class RunningHubAccount:
    api_key: str
    workflows: dict[str, str]
    max_jobs: int = 5

@dataclass
class RunningHub:
    accounts: list[RunningHubAccount]
    api_url: str = "https://www.runninghub.ai"  # URL API RunningHub
    task_timeout: int = 600  # Таймаут задачи в секундах (10 минут)
    retry_delay: int = 5  # Задержка между попытками в секундах
    max_retries: int = 3  # Максимальное количество попыток для HTTP запросов
    max_tasks: int = 5  # Максимальное количество одновременных задач на аккаунт
    polling_interval: int = 5  # Интервал проверки статуса задачи в секундах

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

    # Load RunningHub accounts
    accounts = []
    account_index = 1
    
    while True:
        api_key = getenv(f"RUNNINGHUB_API_KEY_{account_index}")
        if not api_key:
            break
            
        workflow_id = getenv(f"RUNNINGHUB_WORKFLOW_ID_{account_index}")
        if not workflow_id:
            logger.error(f"RUNNINGHUB_WORKFLOW_ID_{account_index} is not set")
            break

        try:
            max_jobs = int(getenv(f"RUNNINGHUB_MAX_JOBS_{account_index}", "5"))
            if max_jobs <= 0 or max_jobs > 5:
                logger.warning(f"Invalid max_jobs value for account {account_index}, using default: 5")
                max_jobs = 5
        except ValueError:
            logger.warning(f"Invalid max_jobs value for account {account_index}, using default: 5")
            max_jobs = 5

        account = RunningHubAccount(
            api_key=api_key,
            workflows={"product": workflow_id},
            max_jobs=max_jobs
        )
        accounts.append(account)
        account_index += 1

    if not accounts:
        logger.error("No RunningHub accounts configured")
        raise ValueError("No RunningHub accounts configured")

    return Config(
        tg_bot=TgBot(token=bot_token),
        runninghub=RunningHub(accounts=accounts)
    )

config = load_config()