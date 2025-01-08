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