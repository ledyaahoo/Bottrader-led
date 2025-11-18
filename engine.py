import json
import time
import hmac
import hashlib
import asyncio
import traceback
import websockets
import aiohttp
from datetime import datetime

from utils import log, colored


BITGET_REST = "https://api.bitget.com"
BITGET_WS = "wss://ws.bitget.com/mix/v1/stream"


# ===================================================================
# ENGINE UTAMA (REST + WEBSOCKET)
# ===================================================================

class TradingEngine:
    def __init__(self, api_key, api_secret, api_pass):
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.api_pass = api_pass

        self.session = aiohttp.ClientSession()

        self.ws = None
        self.ws_ready = False

        # Cache data dari WS
        self.cache = {
            "price": None,
            "orderbook": None,
            "candles": []
        }

        # Jalankan WS (async)
        asyncio.create_task(self._start_ws())

    # ===================================================================
    # AUTH BITGET
    # ===================================================================

    def _sign(self, timestamp, method, request_path, body=""):
        msg = f"{timestamp}{method}{request_path}{body}"
        mac = hmac.new(self.api_secret, msg.encode(), hashlib.sha256)
        return mac.hexdigest()

    def _headers(self, method, path, body=""):
        timestamp = str(int(time.time() * 1000))
        sign = self._sign(timestamp, method, path, body)
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.api_pass,
            "Content-Type": "application/json"
        }

    # ===================================================================
    # HTTP REQUEST
    # ===================================================================

    async def _get(self, path, params=None):
        url = BITGET_REST + path
        try:
            async with self.session.get(url, headers=self._headers("GET", path), params=params) as resp:
                data = await resp.json()
                return data
        except Exception as e:
            log(colored(f"REST GET ERROR: {e}", "red"))
            return None

    async def _post(self, path, body_dict):
        url = BITGET_REST + path
        body = json.dumps(body_dict)
        try:
            async with self.session.post(url, headers=self._headers("POST", path, body), data=body) as resp:
                data = await resp.json()
                return data
        except Exception as e:
            log(colored(f"REST POST ERROR: {e}", "red"))
            return None

    # ===================================================================
    # GET MARKET DATA
    # ===================================================================

    async def get_market_data(self, symbol):
        """
        Ambil data dari WebSocket cache.
        Jika WS mati → fallback ke REST.
        """

        if self.ws_ready and self.cache["price"] is not None:
            return self.cache

        # fallback REST
        try:
            ticker = await self._get(f"/api/mix/v1/market/ticker?symbol={symbol}")
            kline = await self._get(f"/api/mix/v1/market/candles?symbol={symbol}&granularity=60&limit=60")
            depth = await self._get(f"/api/mix/v1/market/depth?symbol={symbol}&limit=20")

            if not ticker or not kline or not depth:
                return None

            price = float(ticker["data"]["last"])
            candles = [[float(i) for i in row] for row in kline["data"]]
            orderbook = {
                "bids": depth["data"]["bids"],
                "asks": depth["data"]["asks"]
            }

            return {
                "price": price,
                "candles": candles,
                "orderbook": orderbook
            }
        except:
            traceback.print_exc()
            return None

    # ===================================================================
    # GET BALANCE
    # ===================================================================

    async def get_wallet_balance(self, coin="USDT"):
        result = await self._get("/api/mix/v1/account/accounts?productType=USDT-FUTURES")

        try:
            for acc in result["data"]:
                if acc["marginCoin"] == coin:
                    return float(acc["available"])
        except:
            return None

    # ===================================================================
    # EXECUTE ORDER (REAL)
    # ===================================================================

    async def execute_order(self, symbol, side, qty, tp, sl):
        """
        Market order → langsung masuk
        """
        data = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "size": str(qty),
            "side": side,
            "orderType": "market",
            "reduceOnly": False
        }

        r = await self._post("/api/mix/v1/order/placeOrder", data)

        if r is None or "data" not in r:
            log(colored("⚠️ Order gagal!", "red"))
            return None

        order_id = r["data"]["orderId"]

        log(colored(f"🟢 ORDER MASUK: {side} | qty={qty}", "green"))

        # pasang TP / SL
        await self.set_tp_sl(symbol, qty, tp, sl, side)

        price_exec = await self._wait_fill(symbol, order_id)
        if price_exec:
            pnl = await self._calculate_pnl(symbol, side, price_exec, tp, sl, qty)
            return {
                "pnl": pnl,
                "side": side,
                "price": price_exec
            }

        return None

    # ===================================================================
    # TP/SL
    # ===================================================================

    async def set_tp_sl(self, symbol, qty, tp, sl, side):
        """
        Pasang SL & TP sebagai trigger order.
        """
        try:
            # TP
            await self._post("/api/mix/v1/order/placePlanOrder", {
                "symbol": symbol,
                "marginCoin": "USDT",
                "size": str(qty),
                "side": "close_long" if side == "open_long" else "close_short",
                "triggerPrice": str(tp),
                "orderType": "market",
                "executeType": "trigger"
            })

            # SL
            await self._post("/api/mix/v1/order/placePlanOrder", {
                "symbol": symbol,
                "marginCoin": "USDT",
                "size": str(qty),
                "side": "close_long" if side == "open_long" else "close_short",
                "triggerPrice": str(sl),
                "orderType": "market",
                "executeType": "trigger"
            })

            log(colored(f"📌 TP/SL dipasang → TP: {tp} | SL: {sl}", "cyan"))

        except Exception as e:
            log(colored(f"TP/SL ERROR: {e}", "red"))

    # ===================================================================
    # WAIT ORDER FILLED
    # ===================================================================

    async def _wait_fill(self, symbol, order_id):
        """
        Tunggu order sampai filled.
        """

        for _ in range(20):  # 20 detik
            r = await self._get(f"/api/mix/v1/order/detail?symbol={symbol}&orderId={order_id}")

            try:
                if r and r["data"]["state"] == "filled":
                    return float(r["data"]["avgPrice"])
            except:
                pass

            await asyncio.sleep(1)

        return None

    # ===================================================================
    # HITUNG PROFIT
    # ===================================================================

    async def _calculate_pnl(self, symbol, side, entry, tp, sl, qty):
        if side == "open_long":
            exit_price = tp if tp else sl
            pnl = (exit_price - entry) * qty
        else:
            exit_price = tp if tp else sl
            pnl = (entry - exit_price) * qty
        return pnl

    # ===================================================================
    # WEBSOCKET
    # ===================================================================

    async def _start_ws(self):
        """
        WS real-time: price, orderbook, candles 1m
        """
        while True:
            try:
                self.ws = await websockets.connect(BITGET_WS)
                await self._ws_subscribe()
                self.ws_ready = True
                log(colored("🟢 WebSocket tersambung", "green"))

                while True:
                    msg = await self.ws.recv()
                    self._ws_process(msg)

            except Exception as e:
                self.ws_ready = False
                log(colored(f"🔴 WS terputus: {e}", "red"))
                await asyncio.sleep(3)

    async def _ws_subscribe(self):
        channels = [
            {"instId": "BTCUSDT_UMCBL", "channel": "ticker"},
            {"instId": "BTCUSDT_UMCBL", "channel": "candle1m"},
            {"instId": "BTCUSDT_UMCBL", "channel": "books"}
        ]

        for c in channels:
            await self.ws.send(json.dumps({
                "op": "subscribe",
                "args": [c]
            }))

    def _ws_process(self, raw):
        try:
            data = json.loads(raw)
            if "arg" not in data:
                return

            channel = data["arg"]["channel"]

            if channel == "ticker":
                self.cache["price"] = float(data["data"][0]["last"])

            elif channel == "books":
                self.cache["orderbook"] = {
                    "bids": data["data"][0]["bids"],
                    "asks": data["data"][0]["asks"]
                }

            elif channel == "candle1m":
                k = data["data"][0]
                candle = [float(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
                self.cache["candles"].append(candle)
                if len(self.cache["candles"]) > 200:
                    self.cache["candles"].pop(0)

        except:
            traceback.print_exc()
          
