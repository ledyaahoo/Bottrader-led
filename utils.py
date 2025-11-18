# utils.py
import requests
from config import REST_URL, API_KEY, API_SECRET, API_PASSPHRASE

def fetch_candles(pair, tf="5m", limit=100):
    url = f"{REST_URL}/api/v2/market/candles?symbol={pair}&granularity={tf}&limit={limit}"
    try:
        return requests.get(url).json()
    except:
        return []

def fetch_orderbook(pair):
    url = f"{REST_URL}/api/v2/market/orderbook?symbol={pair}&limit=5"
    try:
        return requests.get(url).json()
    except:
        return {}

def api_place_order(pair, side, size, leverage):
    # Full signature/headers omitted for safety
    print(f"[API] ORDER SENT → {pair} | {side} | size={size} | lev={leverage}")
    # In real bot, return Bitget order ID
    return True
    
