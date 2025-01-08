from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

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

    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN")
        ),
        runninghub=RunningHub(
            api_key=getenv("RUNNINGHUB_API_KEY")
        )
    )

config = load_config()
