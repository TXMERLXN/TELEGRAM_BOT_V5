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
    max_concurrent_tasks: int = 15  # Максимальное количество одновременных задач (5 задач * 3 аккаунта)

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
            
        workflows = {}
        workflow_product = getenv(f"RUNNINGHUB_WORKFLOW_PRODUCT_{account_index}")
        if workflow_product:
            workflows["product"] = workflow_product
            
        if not workflows:
            logger.warning(f"No workflows found for account {account_index}")
            account_index += 1
            continue
            
        max_jobs = int(getenv(f"RUNNINGHUB_MAX_JOBS_{account_index}", "5"))
        
        accounts.append(RunningHubAccount(
            api_key=api_key,
            workflows=workflows,
            max_jobs=max_jobs
        ))
        account_index += 1
    
    if not accounts:
        logger.error("No RunningHub accounts configured")
        raise ValueError("No RunningHub accounts configured")

    return Config(
        tg_bot=TgBot(token=bot_token),
        runninghub=RunningHub(accounts=accounts)
    )

config = load_config()