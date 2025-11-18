# config.py
# Ultra-Safe Hybrid Bot Final 2.1

REST_URL = "https://api.bitget.com"
WS_URL = "wss://ws.bitget.com/mix/v1/stream"

# Normal pairs
NORMAL_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LTCUSDT", "ASTERUSDT", "HYPEUSDT"]

# Sniper pairs
SNIPER_PAIRS = ["PEPEUSDT", "SHIBUSDT", "FLOKIUSDT", "DASHUSDT", "XMRUSDT", "BONKUSDT"]

# Leverage
LEVERAGE_NORMAL = 25
LEVERAGE_SNIPER = 20

# Modal & Target
INITIAL_BALANCE = 3
TARGET_NORMAL = 30
TARGET_SNIPER = 40

# Max order per running
MAX_ORDER_NORMAL = 3
MAX_ORDER_SNIPER = 2

# Safety & Strategy Flags
AUTO_SHORT_ON_DUMP = True
ANTI_RUG = True
PARALLEL_CHANNEL_SNR_SND = True
SCALP_MINUTES = 5
SCALP_MAX_MINUTES = 15
MULTI_TIMEFRAME = ["5m","15m","1h","4h"]

# Auto restart
AUTO_RESTART_HOURS = 6
