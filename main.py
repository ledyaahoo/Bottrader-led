# main.py
# Runner + Bitget REST + WebSocket manager + Target manager + Auto restart
# Requirements: websockets, requests
# Secrets (GitHub): BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE
# Optional: BITGET_ENABLE_TRADING="true" to enable real orders

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import asyncio
import threading
from datetime import datetime, timedelta

# ---- CONFIG (edit only non-secret values) ----
NORMAL_COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","LTCUSDT","UNIUSDT","HYPEUSDT","ASTRUSDT"]
MEME_COINS   = ["PEPEUSDT","SHIBUSDT","FLOKIUSDT","WIFUSDT","BONKUSDT","AVNTUSDT","XPLUSDT","MANTAUSDT","WIFUUSDT"]

INITIAL_BALANCE = 3.0

NORMAL_TARGET_DAY1 = 30.0
NORMAL_MULTIPLIER = 3.0
SNIPER_TARGET_DAY1 = 40.0
SNIPER_MULTIPLIER = 1.5
SWITCH_BALANCE = 3000.0

NORMAL_LEVERAGE_MIN = 20
NORMAL_LEVERAGE_MAX = 30
SNIPER_LEVERAGE_MIN = 10
SNIPER_LEVERAGE_MAX = 15

AUTO_RESTART_SECONDS = 6 * 3600  # 6 hours
WS_URL = "wss://ws.bitget.com/mix/v1/stream"
MIN_TRADE_USDT = 1.5  # minimal per trade

# ---- LOGGING ----
def log(msg):
    t = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] {msg}", flush=True)

# ---- Bitget REST client (minimal, using signature) ----
import requests
class BitgetClient:
    BASE = "https://api.bitget.com"

    def __init__(self):
        self.api_key = os.getenv("BITGET_API_KEY")
        self.api_secret = os.getenv("BITGET_API_SECRET")
        self.passphrase = os.getenv("BITGET_API_PASSPHRASE")
        self.enable_trading = os.getenv("BITGET_ENABLE_TRADING","false").lower() == "true"
        if not (self.api_key and self.api_secret and self.passphrase):
            log("⚠️ API keys missing in env. Set BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE in GitHub Secrets for live trading.")
        else:
            log("API keys loaded from environment.")
        self.session = requests.Session()

    def _sign(self, timestamp_ms: str, method: str, request_path: str, body: str=""):
        # Bitget signature (HMAC SHA256 hex); some implementations need base64 - adapt if API complains.
        to_sign = f"{timestamp_ms}{method}{request_path}{body}"
        sign = hmac.new(self.api_secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest()
        return sign

    def _headers(self, method: str, path: str, body_str: str=""):
        ts = str(int(time.time() * 1000))
        sign = ""
        if self.api_secret:
            sign = self._sign(ts, method, path, body_str)
        return {
            "ACCESS-KEY": self.api_key or "",
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self.passphrase or "",
            "Content-Type": "application/json"
        }

    # REST helpers (safe wrappers)
    def get_orderbook(self, symbol, limit=50):
        try:
            path = f"/api/mix/v1/market/depth?symbol={symbol}&limit={limit}"
            url = self.BASE + path
            r = self.session.get(url, timeout=8)
            return r.json()
        except Exception as e:
            log(f"get_orderbook error {e}")
            return None

    def get_ticker(self, symbol):
        try:
            path = f"/api/mix/v1/market/ticker?symbol={symbol}"
            url = self.BASE + path
            r = self.session.get(url, timeout=8)
            return r.json()
        except Exception as e:
            log(f"get_ticker error {e}")
            return None

    def place_market_order(self, symbol, side, size_usdt, leverage=10):
        """
        side: 'open_long' or 'open_short' (Bitget mix endpoints may need 'buy'/'sell' or specific values - check docs)
        size_usdt: USDT notional size (we pass directly as 'size' field)
        """
        if not self.enable_trading:
            log(f"[SIM] place_market_order {symbol} {side} {size_usdt} USDT lev={leverage}")
            return {"result": "simulated"}

        path = "/api/mix/v1/order/placeOrder"
        body = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "size": str(size_usdt),
            "side": side,
            "orderType": "market"
        }
        body_str = json.dumps(body)
        headers = self._headers("POST", path, body_str)
        try:
            r = self.session.post(self.BASE + path, headers=headers, data=body_str, timeout=10)
            log(f"[ORDER] {r.status_code} {r.text}")
            return r.json()
        except Exception as e:
            log(f"place_market_order error {e}")
            return {"error": str(e)}

    def get_account_balance(self):
        try:
            path = "/api/mix/v1/account/accounts?productType=USDT-FUTURES"
            r = self.session.get(self.BASE + path, timeout=8, headers=self._headers("GET", path))
            return r.json()
        except Exception as e:
            log(f"get_account_balance error {e}")
            return None

# ---- WebSocket manager (maintains latest orderbook/ticker snapshots) ----
import websockets

class WSManager:
    def __init__(self, symbols):
        self.url = WS_URL
        self.symbols = symbols
        self.book = {}   # symbol -> latest orderbook dict
        self.ticker = {} # symbol -> latest ticker dict
        self._ws = None
        self._task = None
        self._loop = None

    async def _connect_and_subscribe(self):
        try:
            self._ws = await websockets.connect(self.url, ping_interval=20, ping_timeout=20)
            # subscribe books and ticker for symbols
            for s in self.symbols:
                sub_books = {"op":"subscribe","args":[{"instType":"USDT-FUTURES","channel":"books","instId":s}]}
                sub_tick = {"op":"subscribe","args":[{"instType":"USDT-FUTURES","channel":"ticker","instId":s}]}
                await self._ws.send(json.dumps(sub_books))
                await self._ws.send(json.dumps(sub_tick))
            log(f"WS subscribed to {len(self.symbols)} symbols.")
            # listen loop
            async for msg in self._ws:
                try:
                    data = json.loads(msg)
                    # message parsing: bitget wraps messages with 'arg' or 'data'
                    if isinstance(data, dict):
                        if "arg" in data and "channel" in data["arg"]:
                            ch = data["arg"]["channel"]
                            # data['data'] often is a list
                            if "data" in data:
                                payload = data["data"]
                                if ch == "books":
                                    # store last snapshot keyed by instId
                                    # payload could be list of dicts
                                    for item in payload:
                                        inst = item.get("instId") or item.get("symbol") or data["arg"].get("instId")
                                        if inst:
                                            self.book[inst] = item
                                elif ch == "ticker":
                                    for item in payload:
                                        inst = item.get("instId") or item.get("symbol")
                                        if inst:
                                            self.ticker[inst] = item
                        # sometimes 'topic' style messages exist; best-effort parse
                        elif "topic" in data and "data" in data:
                            topic = data["topic"]
                            payload = data["data"]
                            # best effort: if 'books' in topic
                            if "books" in topic:
                                # topic like books:BTCUSDT
                                try:
                                    inst = topic.split(":")[-1]
                                    self.book[inst] = payload
                                except:
                                    pass
                except Exception:
                    continue
        except Exception as e:
            log(f"WS connection error: {e}")
        finally:
            # try reconnect after small delay
            await asyncio.sleep(2)
            log("WS reconnecting ...")
            asyncio.create_task(self._connect_and_subscribe())

    def start(self):
        self._loop = asyncio.new_event_loop()
        self._task = threading.Thread(target=self._run_loop, daemon=True)
        self._task.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_subscribe())

    def get_book(self, symbol):
        return self.book.get(symbol)

    def get_ticker(self, symbol):
        return self.ticker.get(symbol)

# ---- Target manager (daily progression & total profit tracking) ----
class TargetManager:
    def __init__(self):
        self.normal_profit = 0.0
        self.sniper_profit = 0.0
        self.normal_day = 1
        self.sniper_day = 1
        self.normal_target = NORMAL_TARGET_DAY1
        self.sniper_target = SNIPER_TARGET_DAY1
        self.today = datetime.utcnow().date()

    def reset_if_day_changed(self):
        d = datetime.utcnow().date()
        if d != self.today:
            self.today = d
            self.normal_day += 1
            self.sniper_day += 1
            self._recalc_targets()

    def _recalc_targets(self):
        if self.normal_profit + INITIAL_BALANCE >= SWITCH_BALANCE:
            self.normal_target = NORMAL_TARGET_DAY1
        else:
            self.normal_target = NORMAL_TARGET_DAY1 * (NORMAL_MULTIPLIER ** (self.normal_day - 1))
        if self.sniper_profit + INITIAL_BALANCE >= SWITCH_BALANCE:
            self.sniper_target = SNIPER_TARGET_DAY1
        else:
            self.sniper_target = SNIPER_TARGET_DAY1 * (SNIPER_MULTIPLIER ** (self.sniper_day - 1))

    def add_normal_profit(self, p):
        self.normal_profit += p
        self._recalc_targets()

    def add_sniper_profit(self, p):
        self.sniper_profit += p
        self._recalc_targets()

    def normal_finished(self):
        return self.normal_profit >= self.normal_target

    def sniper_finished(self):
        return self.sniper_profit >= self.sniper_target

# ---- Import strategy modules (these are separate files you'll paste) ----
import normal_trading
import meme_sniper

# ---- Async loops for strategies ----
async def normal_loop(client: BitgetClient, ws: WSManager, tm: TargetManager):
    log("normal_loop started")
    # choose a representative leverage
    lev = (NORMAL_LEVERAGE_MIN + NORMAL_LEVERAGE_MAX) // 2
    while True:
        try:
            tm.reset_if_day_changed()
            if tm.normal_finished():
                # minimal sleep when finished (still monitor)
                await asyncio.sleep(5)
                continue
            # iterate coins
            for s in NORMAL_COINS:
                try:
                    result = await normal_trading.run_once(client, ws, s, lev)
                    if result and "profit" in result:
                        tm.add_normal_profit(result["profit"])
                        log(f"Normal profit {result['profit']:.4f} | total normal profit {tm.normal_profit:.4f}")
                except Exception as e:
                    log(f"normal_trading error for {s}: {e}")
                await asyncio.sleep(0.2)
            await asyncio.sleep(0.5)
        except Exception as e:
            log(f"normal_loop top error: {e}")
            await asyncio.sleep(1)

async def sniper_loop(client: BitgetClient, ws: WSManager, tm: TargetManager):
    log("sniper_loop started")
    lev = (SNIPER_LEVERAGE_MIN + SNIPER_LEVERAGE_MAX) // 2
    while True:
        try:
            tm.reset_if_day_changed()
            if tm.sniper_finished():
                await asyncio.sleep(3)
                continue
            for s in MEME_COINS:
                try:
                    result = await meme_sniper.run_once(client, ws, s, lev)
                    if result and "profit" in result:
                        tm.add_sniper_profit(result["profit"])
                        log(f"Sniper profit {result['profit']:.4f} | total sniper profit {tm.sniper_profit:.4f}")
                except Exception as e:
                    log(f"meme_sniper error for {s}: {e}")
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.3)
        except Exception as e:
            log(f"sniper_loop top error: {e}")
            await asyncio.sleep(1)

# ---- Auto-restart watcher (re-exec process after AUTO_RESTART_SECONDS) ----
def start_autorestart():
    def _watch():
        start = time.time()
        while True:
            time.sleep(10)
            if time.time() - start > AUTO_RESTART_SECONDS:
                log("Auto-restart triggered. Re-exec process now.")
                python = sys.executable
                os.execv(python, [python] + sys.argv)
    t = threading.Thread(target=_watch, daemon=True)
    t.start()

# ---- MAIN ----
def main():
    client = BitgetClient()
    tm = TargetManager()
    ws = WSManager(NORMAL_COINS + MEME_COINS)
    ws.start()
    start_autorestart()

    loop = asyncio.get_event_loop()
    tasks = [
        normal_loop(client, ws, tm),
        sniper_loop(client, ws, tm)
    ]
    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        log("Stopped by user")

if __name__ == "__main__":
    main()
                  
