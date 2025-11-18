# config.py

# API
REST_URL = "https://api.bitget.com"
WS_URL = "wss://ws.bitget.com/mix/v1/stream"

API_KEY = "YOUR_KEY"
API_SECRET = "YOUR_SECRET"
API_PASSPHRASE = "YOUR_PASSPHRASE"

# Trading Pairs
NORMAL_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LTCUSDT", "ASTERUSDT"]
SNIPER_PAIRS = ["PEPEUSDT", "SHIBUSDT", "FLOKIUSDT", "DASHUSDT", "XMRUSDT"]

# Leverage
LEVERAGE_NORMAL = 25
LEVERAGE_SNIPER = 20

# Mode Limits
MAX_ORDER_NORMAL = 3
MAX_ORDER_SNIPER = 2

# Risk
INITIAL_BALANCE = 3  # Starting with $3
DAILY_STOPLOSS = 1
DAILY_TARGET = 30  # base daily target for normal
TARGET_NORMAL = 30
TARGET_SNIPER = 40

MODE_TARGET = {"normal": TARGET_NORMAL, "sniper": TARGET_SNIPER}
MODE_STOPLOSS = {"normal": 1, "sniper": 1}
