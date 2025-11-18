# config.py
# ======================================
# Ultra-Safe Hybrid Bot 2.1
# Final Config
# ======================================

# === API ===
REST_URL = "https://api.bitget.com"
WS_URL = "wss://ws.bitget.com/mix/v1/stream"

# === Trading Pairs ===
# Normal Mode → Stabil & besar
NORMAL_PAIRS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "LTCUSDT",
    "ASTRUSDT"
]

# Sniper Mode → Volatil & meme coins
SNIPER_PAIRS = [
    "PEPEUSDT",
    "SHIBUSDT",
    "FLOKIUSDT",
    "DASHUSDT",
    "XMRUSDT",
    "BONKUSDT",
    "WIFUSDT",
    "AVNTUSDT"
]

# === Leverage ===
LEVERAGE_NORMAL = 25    # Normal mode
LEVERAGE_SNIPER = 20    # Meme sniper mode

# === Trading Limits ===
MAX_ORDER_NORMAL = 3    # Maksimal order per running untuk normal
MAX_ORDER_SNIPER = 2    # Maksimal order per running untuk sniper

# === Modal & Risk Management ===
INITIAL_BALANCE = 3     # Modal awal $3
DAILY_STOPLOSS = 1      # Stoploss harian
DAILY_TARGET = 30       # Target harian base normal
TARGET_NORMAL = 30      # Base target per hari normal
TARGET_SNIPER = 40      # Base target per hari sniper

MODE_TARGET = {
    "normal": TARGET_NORMAL,
    "sniper": TARGET_SNIPER
}

MODE_STOPLOSS = {
    "normal": 1,
    "sniper": 1
}

# === Timing ===
AUTO_RESTART_HOURS = 6  # Bot restart otomatis setiap 6 jam

# === Scalp & Trendline Config ===
SCALP_MINUTES = 5
SCALP_MAX_MINUTES = 15
MULTI_TIMEFRAME = ["5m", "15m", "1h", "4h"]

# === Safety Features ===
ANTI_RUG = True
AUTO_SHORT_ON_DUMP = True
FLOATING_PROFIT_MANAGEMENT = True
PARALLEL_CHANNEL_SNR_SND = True
