from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

@dataclass
class TgBot:
    token: str
    webhook_host: str = None

@dataclass
class RunningHubAccount:
    api_key: str
    workflows: dict[str, str]
    max_jobs: int = 5

@dataclass
class RunningHub:
    accounts: list[RunningHubAccount]
    api_url: str = "https://www.runninghub.ai/"  # URL API RunningHub
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

    # Проверяем наличие всех обязательных переменных окружения
    required_vars = {
        "BOT_TOKEN": "Telegram Bot Token",
        "WEBHOOK_HOST": "Webhook host URL",
        "RUNNINGHUB_API_KEY_1": "RunningHub API Key",
        "RUNNINGHUB_WORKFLOW_ID_1": "RunningHub Workflow ID"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        error_msg = "Missing required environment variables:\n" + "\n".join(missing_vars)
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Load RunningHub accounts
    accounts = []
    account_index = 1
    
    while True:
        api_key = getenv(f"RUNNINGHUB_API_KEY_{account_index}")
        workflow_id = getenv(f"RUNNINGHUB_WORKFLOW_ID_{account_index}")
        
        # Если не найден API ключ, значит больше нет аккаунтов
        if not api_key:
            break
            
        # Проверяем наличие workflow_id для этого аккаунта
        if not workflow_id:
            logger.error(
                f"RUNNINGHUB_WORKFLOW_ID_{account_index} is not set for API key "
                f"{api_key[:5]}...{api_key[-5:]}"
            )
            raise ValueError(
                f"RUNNINGHUB_WORKFLOW_ID_{account_index} is required for account {account_index}"
            )

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
        logger.info(
            f"Loaded RunningHub account {account_index} "
            f"(API key: {api_key[:5]}...{api_key[-5:]}, "
            f"workflow: {workflow_id})"
        )
        account_index += 1

    if not accounts:
        error_msg = (
            "No RunningHub accounts configured. Please set RUNNINGHUB_API_KEY_1 and "
            "RUNNINGHUB_WORKFLOW_ID_1 environment variables"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"Successfully loaded {len(accounts)} RunningHub account(s)")
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN"),
            webhook_host=getenv("WEBHOOK_HOST")
        ),
        runninghub=RunningHub(accounts=accounts)
    )

config = load_config()
