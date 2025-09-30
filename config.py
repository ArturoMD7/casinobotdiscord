import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "blackjackbot"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "blackjack"),
    "port": int(os.getenv("DB_PORT", 3306))
}

# Configuración del juego
STARTING_CREDITS = 1000
MIN_BET = 10
MAX_BET = 1000000000000000000000
BLACKJACK_PAYOUT = 1.5  # 3:2