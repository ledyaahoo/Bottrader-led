import os

# =========================
# API Settings (Secret dari Environment)
# =========================
BITGET_API_KEY = os.getenv("BITGET_API_KEY")
BITGET_API_SECRET = os.getenv("BITGET_API_SECRET")
BITGET_API_PASSWORD = os.getenv("BITGET_API_PASSWORD")

# =========================
# General Settings
# =========================
MODE = "LIVE"  # LIVE / TEST
MARGIN_TYPE = "CROSS"
TIMEZONE = "Asia/Jakarta"

# =========================
# Pairs
NORMAL_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LTCUSDT", "UNIUSDT", "HYPEUSDT", "ASTERUSDT"]
MEME_PAIRS = ["PEPEUSDT", "SHIBUSDT", "FLOKIUSDT", "WIFUSDT", "BONKUSDT", "AVNTUSDT",
              "XPLUSDT", "MANTAUSDT", "WIFUUSDT", "DASHUSDT", "ZCASHUSDT", "BEATUSDT", "XMRUSDT"]

# =========================
# Leverage
LEVERAGE_NORMAL = 25
LEVERAGE_SNIPER_SMALL = 13
LEVERAGE_SNIPER_BIG = 20
LEVERAGE_SNIPER_BIG_MAX = 25

# =========================
# Target Profit
NORMAL_TARGET_INITIAL = 30
NORMAL_MULTIPLIER = 3
SNIPER_TARGET_INITIAL = 40
SNIPER_MULTIPLIER = 1.5
MAX_PROFIT = 3000  # setelah profit > 3000, target = x1

# =========================
# Orders
MAX_ORDER_INITIAL = 5  # 3 normal + 2 sniper
MAX_ORDER_TARGET2 = 6
DELTA_BUFFER = 0.03
FAST_MODE = 0.3  # 0.3 detik lebih cepat dari ritel

# =========================
# Margin Allocation
NORMAL_MARGIN_RATIO = 0.4
SNIPER_MARGIN_RATIO = 0.3
RESERVE_MARGIN_RATIO = 0.3
