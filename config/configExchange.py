import ccxt
import os
from dotenv import load_dotenv

env_file_name = "api/.envTest"


def load_config(env_file_name=".env"):
    try:
        load_dotenv(env_file_name)

        TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

        BITMEX_API_KEY = os.getenv("BITMEX_API_KEY")
        BITMEX_SECRET = os.getenv("BITMEX_SECRET")

        exchange = ccxt.bitmex({
            'apiKey': BITMEX_API_KEY,
            'secret': BITMEX_SECRET,
            'timeout': 30000,
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True},
        })

        return exchange, TELEGRAM_API_TOKEN, TELEGRAM_CHAT_ID
    except Exception as e:
        print(f"Error occurred while loading configuration: {str(e)}")


exchange, TELEGRAM_API_TOKEN, TELEGRAM_CHAT_ID = load_config(env_file_name)
