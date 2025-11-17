# main.py
# Orchestrator for hybrid bot (ws_engine + strategy_engine + BitgetClient)
# Usage: python main.py

import os, sys, time, json, hmac, hashlib, threading, asyncio
from datetime import datetime

# import local modules
from ws_engine import WSManager
import strategy_engine as strat

# ---- Config mirrored from your final spec (edit only non-secret) ----
NORMAL_COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","LTCUSDT","UNIUSDT","HYPEUSDT","ASTRUSDT"]
MEME_COINS   = ["PEPEUSDT","SHIBUSDT","FLOKIUSDT","WIFUSDT","BONKUSDT","AVNTUSDT","XPLUSDT","MANTAUSDT","WIFUUSDT"]

INITIAL_BALANCE = 3.0
NORMAL_BASE_TARGET = 30.0
NORMAL_MULTIPLIER = 3.0
SNIPER_BASE_TARGET = 40.0
SNIPER_MULTIPLIER = 1.5
SWITCH_BALANCE = 3000.0

NORMAL_LEV_MIN = 20
NORMAL_LEV_MAX = 30
SNIPER_LEV_MIN = 10
SNIPER_LEV_MAX = 15

SNIPER_MIN_RATIO = 0.55
SNIPER_MAX_RATIO = 0.75
NORMAL_FRACTION = 0.30

AUTO_RESTART_SECONDS = 6 * 3600  # 6 hours

# ---- logger
def log(msg):
    t = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] {msg}", flush=True)

# ---- Bitget Client (REST + signatures) - reads secrets from env
import requests
class BitgetClient:
    BASE = "https://api.bitget.com"
    def __init__(self):
        self.api_key = os.getenv("BITGET_API_KEY")
        self.api_secret = os.getenv("BITGET_API_SECRET")
        self.passphrase = os.getenv("BITGET_API_PASSPHRASE")
        self.enable_trading = os.getenv("BITGET_ENABLE_TRADING","false").lower() == "true"
        self.session = requests.Session()
        # optional simulated balance attr
        self.sim_balance = float(os.getenv("BOT_SIM_BALANCE", "3.0"))
        if not (self.api_key and self.api_secret and self.passphrase):
            log("⚠️ API secrets not found. Running may be simulated.")
    def _sign(self, ts, method, path, body=""):
        msg = f"{ts}{method}{path}{body}"
        sig = hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).digest()
        return base64.b64encode(sig).decode()
    def _headers(self, method, path, body=""):
        ts = str(int(time.time()*1000))
        sign = ""
        try:
            sign = self._sign(ts, method, path, body)
        except Exception:
            sign = ""
        return {
            "ACCESS-KEY": self.api_key or "",
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self.passphrase or "",
            "Content-Type": "application/json"
        }
    # REST calls
    def get_orderbook(self, symbol):
        try:
            path = f"/api/mix/v1/market/depth?symbol={symbol}&limit=50"
            r = self.session.get(self.BASE + path, timeout=8)
            return r.json()
        except Exception as e:
            log(f"get_orderbook error {e}")
            return None
    def get_ticker(self, symbol):
        try:
            path = f"/api/mix/v1/market/ticker?symbol={symbol}"
            r = self.session.get(self.BASE + path, timeout=8)
            return r.json()
        except Exception as e:
            log(f"get_ticker error {e}")
            return None
    def place_market_order(self, symbol, side, size_usdt, leverage=10):
        # side: 'open_long' or 'open_short' per earlier convention. If API differs, adjust accordingly.
        if not self.enable_trading:
            log(f"[SIM] ORDER {symbol} {side} {size_usdt}USDT lev={leverage}")
            return {"simulated": True}
        try:
            path = "/api/mix/v1/order/placeOrder"
            body = {"symbol": symbol, "marginCoin":"USDT", "size": str(size_usdt), "side": side, "orderType":"market"}
            body_str = json.dumps(body)
            headers = self._headers("POST", path, body_str)
            r = self.session.post(self.BASE + path, headers=headers, data=body_str, timeout=10)
            log(f"[ORDER] {r.status_code} {r.text}")
            return r.json()
        except Exception as e:
            log(f"place_market_order error {e}")
            return {"error": str(e)}
    def get_account_balance(self):
        try:
            path = "/api/mix/v1/account/accounts?productType=USDT-FUTURES"
            headers = self._headers("GET", path, "")
            r = self.session.get(self.BASE + path, headers=headers, timeout=8)
            return r.json()
        except Exception as e:
            log(f"get_account_balance error {e}")
            return None

# ---- TargetManager class handles daily multipliers & switching
class TargetManager:
    def __init__(self):
        self.normal_profit = 0.0
        self.sniper_profit = 0.0
        self.normal_day = 1
        self.sniper_day = 1
        self.normal_target = NORMAL_BASE_TARGET
        self.sniper_target = SNIPER_BASE_TARGET
        self._today = datetime.utcnow().date()
    def reset_if_needed(self):
        d = datetime.utcnow().date()
        if d != self._today:
            self._today = d
            self.normal_day += 1
            self.sniper_day += 1
            self.recalc()
    def recalc(self):
        if self.normal_profit + INITIAL_BALANCE >= SWITCH_BALANCE:
            self.normal_target = NORMAL_BASE_TARGET
        else:
            self.normal_target = NORMAL_BASE_TARGET * (NORMAL_MULTIPLIER ** (self.normal_day - 1))
        if self.sniper_profit + INITIAL_BALANCE >= SWITCH_BALANCE:
            self.sniper_target = SNIPER_BASE_TARGET
        else:
            self.sniper_target = SNIPER_BASE_TARGET * (SNIPER_MULTIPLIER ** (self.sniper_day - 1))
    def add_normal(self,p): self.normal_profit += p; self.recalc()
    def add_sniper(self,p): self.sniper_profit += p; self.recalc()
    def normal_done(self): return self.normal_profit >= self.normal_target
    def sniper_done(self): return self.sniper_profit >= self.sniper_target

# ---- auto-restart watcher
def start_autorestart():
    def _watch():
        t0 = time.time()
        while True:
            time.sleep(10)
            if time.time() - t0 > AUTO_RESTART_SECONDS:
                log("Auto-restart triggered. Re-exec now.")
                python = sys.executable
                os.execv(python, [python] + sys.argv)
    th = threading.Thread(target=_watch, daemon=True)
    th.start()

# ---- main runner coroutine wiring
async def normal_loop(client, ws, tm):
    log("normal_loop started")
    lev = (NORMAL_LEV_MIN + NORMAL_LEV_MAX) // 2
    while True:
        try:
            tm.reset_if_needed()
            if tm.normal_done():
                await asyncio.sleep(5)
                continue
            for s in NORMAL_COINS:
                try:
                    res = await strat.normal_run_once(client, ws, s, lev)
                    if res and "profit" in res:
                        tm.add_normal(res["profit"])
                        log(f"[NORMAL] {s} +{res['profit']:.4f} total={tm.normal_profit:.4f}")
                except Exception as e:
                    log(f"normal_loop error for {s}: {e}")
                await asyncio.sleep(0.2)
            await asyncio.sleep(0.5)
        except Exception as e:
            log(f"normal_loop top error: {e}")
            await asyncio.sleep(1)

async def sniper_loop(client, ws, tm):
    log("sniper_loop started")
    lev = (SNIPER_LEV_MIN + SNIPER_LEV_MAX) // 2
    while True:
        try:
            tm.reset_if_needed()
            if tm.sniper_done():
                await asyncio.sleep(3)
                continue
            for s in MEME_COINS:
                try:
                    res = await strat.sniper_run_once(client, ws, s, lev)
                    if res and "profit" in res:
                        tm.add_sniper(res["profit"])
                        log(f"[SNIPER] {s} +{res['profit']:.4f} total={tm.sniper_profit:.4f}")
                except Exception as e:
                    log(f"sniper_loop error for {s}: {e}")
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.3)
        except Exception as e:
            log(f"sniper_loop top error: {e}")
            await asyncio.sleep(1)

def main():
    client = BitgetClient()
    # start WS: subscribe both normal + meme symbols
    all_symbols = list(dict.fromkeys(NORMAL_COINS + MEME_COINS))
    ws = WSManager(all_symbols)
    ws.start()
    tm = TargetManager()
    start_autorestart()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.gather(normal_loop(client, ws, tm), sniper_loop(client, ws, tm)))
    except KeyboardInterrupt:
        log("Stopped by user")

if __name__ == "__main__":
    main()
      
