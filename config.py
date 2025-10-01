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
STARTING_CREDITS = 10000
MIN_BET = 10
MAX_BET = 1000000000000000000000
BLACKJACK_PAYOUT = 1.5  # 3:2


# Sistema de Rangos
RANGOS = {
    0: {"nombre": "🎯 Novato", "min_creditos": 0, "color": 0x808080},
    1: {"nombre": "💰 Apostador", "min_creditos": 10_000, "color": 0x00ff00},
    2: {"nombre": "🎲 Jugador", "min_creditos": 50_000, "color": 0x0099ff},
    3: {"nombre": "♠️ High Roller", "min_creditos": 150_000, "color": 0xff9900},
    4: {"nombre": "🏆 Leyenda", "min_creditos": 300_000, "color": 0xff0000},
    5: {"nombre": "💎 Diamante", "min_creditos": 500_000, "color": 0x00ffff},
    6: {"nombre": "👑 Emperador", "min_creditos": 1_000_000, "color": 0xff00ff}
}

# Bonificaciones por rango
BONOS_RANGO = {
    1: {"bono_daily": 500, "multiplicador_ganancias": 1.0},
    2: {"bono_daily": 600, "multiplicador_ganancias": 1.05},
    3: {"bono_daily": 700, "multiplicador_ganancias": 1.10},
    4: {"bono_daily": 800, "multiplicador_ganancias": 1.15},
    5: {"bono_daily": 900, "multiplicador_ganancias": 1.20},
    6: {"bono_daily": 1000, "multiplicador_ganancias": 1.25}
}