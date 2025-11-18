import asyncio
import websockets
import json
import datetime
import numpy as np
from utils import log, colored

class EngineNormalWS:
    """
    Engine NORMAL MODE – PURE WEBSOCKET
    - Multi-timeframe 5m → 4h
    - SNR/SND (Bang Ran)
    - Paralel Channel
    - Trendline break / retest
    - Volume spike / exhaustion
    - Wick reversal / dump detection
    - Sideway scalp 5–15 menit
    - Auto short / auto long dynamic
    - Leverage & margin dynamic
    - Slot management
    - Target profit harian & kelipatan
    """

    def __init__(self, config, secret_repo):
        self.config = config
        self.secret_repo = secret_repo
        self.ws_url = "wss://api.bitget.com/api/mix/v1/market/tickers"
        self.market_data = {}  # Symbol: real-time price/orderbook
        self.candle_buffer = {}  # Symbol: {tf: [OHLCV,...]}
        self.timeframes = ["5m", "15m", "1h", "4h"]
        self.slots = {"long":0, "short":0, "max":3}
        self.balance = 3.0
        self.last_restart = datetime.datetime.now()
        self.target_profit_day = 30
        self.day_index = 1
        self.leverage = 25
        self.order_history = []
        self.ws_connection = None
        self.running = True

        # Initialize candle buffer per symbol per timeframe
        for symbol in self.config["normal_pairs"]:
            self.candle_buffer[symbol] = {tf: [] for tf in self.timeframes}

        log(colored("✅ EngineNormalWS (PURE WEBSOCKET) loaded", "cyan"))

    async def load_secrets(self):
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(self.secret_repo) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.api_key = data.get("API_KEY")
                    self.api_secret = data.get("API_SECRET")
                    self.passphrase = data.get("PASSPHRASE")
                    log(colored("✅ Secret keys loaded from repo", "green"))
                else:
                    raise Exception("Failed to fetch secret keys")

    async def ws_connect(self):
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws_connection = ws
                    await self.subscribe_symbols(ws)
                    log(colored("🟢 WebSocket connected", "green"))

                    async for message in ws:
                        await self.handle_message(json.loads(message))

            except Exception as e:
                log(colored(f"WebSocket error: {e}, reconnecting in 5s...", "red"))
                await asyncio.sleep(5)

    async def subscribe_symbols(self, ws):
        args = [f"ticker:{s}" for s in self.config["normal_pairs"]]
        msg = json.dumps({"op":"subscribe","args":args})
        await ws.send(msg)
        log(colored(f"Subscribed to {args}", "yellow"))

    async def handle_message(self, msg):
        # Update market_data
        if "data" in msg:
            sym = msg["arg"]["instId"]
            last_price = float(msg["data"][0]["last"])
            self.market_data[sym] = {
                "price": last_price,
                "orderbook": msg["data"][0].get("book", {})
            }

            # Build candle buffer (5m,15m,1h,4h)
            await self.update_candle_buffer(sym, last_price)

    async def update_candle_buffer(self, symbol, price):
        now = datetime.datetime.utcnow()
        for tf in self.timeframes:
            interval_sec = self.tf_to_seconds(tf)
            if len(self.candle_buffer[symbol][tf])==0:
                candle = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 0,
                    "start_time": now
                }
                self.candle_buffer[symbol][tf].append(candle)
            else:
                last_candle = self.candle_buffer[symbol][tf][-1]
                elapsed = (now - last_candle["start_time"]).total_seconds()
                if elapsed < interval_sec:
                    last_candle["high"] = max(last_candle["high"], price)
                    last_candle["low"] = min(last_candle["low"], price)
                    last_candle["close"] = price
                else:
                    # start new candle
                    candle = {
                        "open": last_candle["close"],
                        "high": price,
                        "low": price,
                        "close": price,
                        "volume": 0,
                        "start_time": now
                    }
                    self.candle_buffer[symbol][tf].append(candle)

    def tf_to_seconds(self, tf):
        if tf.endswith("m"):
            return int(tf[:-1])*60
        elif tf.endswith("h"):
            return int(tf[:-1])*3600
        elif tf.endswith("d"):
            return int(tf[:-1])*86400
        else:
            return 300
                # ======================================================
    # COMPUTE SNR/SND (Bang Ran Method)
    # ======================================================
    def compute_snr_snd(self, candles, period=20):
        highs = [c["high"] for c in candles[-period:]]
        lows = [c["low"] for c in candles[-period:]]
        support = min(lows)
        resistance = max(highs)
        mid = (support + resistance)/2
        return {"support":support, "resistance":resistance, "mid":mid}

    # ======================================================
    # PARALLEL CHANNEL DETECTION
    # ======================================================
    def compute_parallel_channel(self, candles, period=20):
        highs = [c["high"] for c in candles[-period:]]
        lows = [c["low"] for c in candles[-period:]]
        top = np.mean(highs[-3:])
        bottom = np.mean(lows[-3:])
        midline = (top+bottom)/2
        return {"top":top,"bottom":bottom,"midline":midline}

    # ======================================================
    # TRENDLINE BREAK / BREAKOUT / BREAKDOWN
    # ======================================================
    def detect_trendline_break(self, candles):
        closes = [c["close"] for c in candles]
        recent = closes[-10:]
        earlier = closes[-30:-10] if len(closes) >=30 else closes[:-10]
        if len(earlier)==0:
            return None
        if min(recent) > max(earlier):
            return "breakout"
        if max(recent) < min(earlier):
            return "breakdown"
        return None

    # ======================================================
    # SIDEWAY DETECTION FOR SCALP
    # ======================================================
    def detect_sideway(self, candles):
        highs = [c["high"] for c in candles[-20:]]
        lows = [c["low"] for c in candles[-20:]]
        volatility = (max(highs)-min(lows))/np.mean(highs)
        return volatility < 0.005

    # ======================================================
    # VOLUME SPIKE / EXHAUSTION
    # ======================================================
    def detect_volume_spike(self, candles):
        volumes = [c["volume"] for c in candles]
        avg = np.mean(volumes[-20:])
        last = volumes[-1] if volumes else 0
        if last > avg*2.5:
            return "big_spike"
        if last < avg*0.5:
            return "weak"
        return "normal"

    # ======================================================
    # WICK REVERSAL / DUMP DETECTION
    # ======================================================
    def detect_reversal_wick(self, candles):
        if not candles:
            return None
        last = candles[-1]
        open_ = last["open"]
        close = last["close"]
        high = last["high"]
        low = last["low"]
        body = abs(close-open_)
        wick_up = high - max(open_, close)
        wick_down = min(open_, close) - low
        if wick_up > body*2:
            return "sell_signal"
        if wick_down > body*2:
            return "buy_signal"
        return None

    # ======================================================
    # RETEST AREA CONFIRMATION
    # ======================================================
    def detect_retest(self, price, snr):
        if price <= snr["support"]*1.002 and price >= snr["support"]*0.998:
            return "support_retest"
        if price >= snr["resistance"]*0.998 and price <= snr["resistance"]*1.002:
            return "resistance_retest"
        return None
            # ======================================================
    # GENERATE SIGNAL NORMAL MODE
    # ======================================================
    def generate_signal_normal(self, symbol):
        price = self.market_data.get(symbol,{}).get("price",None)
        if price is None:
            return None

        candles = self.candle_buffer[symbol]["15m"]  # gunakan timeframe utama untuk trend
        snr = self.compute_snr_snd(candles)
        channel = self.compute_parallel_channel(candles)
        trend = self.detect_trendline_break(candles)
        vol = self.detect_volume_spike(candles)
        side = self.detect_sideway(candles)
        wick = self.detect_reversal_wick(candles)
        retest = self.detect_retest(price, snr)

        # Prioritas signal
        if trend=="breakout" and price>snr["resistance"]:
            return "long"
        if trend=="breakdown" and price<snr["support"]:
            return "short"
        if vol=="big_spike":
            return "long" if price>snr["mid"] else "short"
        if side:
            return "long_scalp" if price<snr["mid"] else "short_scalp"
        if wick=="sell_signal":
            return "short"
        if wick=="buy_signal":
            return "long"
        if retest=="support_retest":
            return "long"
        if retest=="resistance_retest":
            return "short"
        return None
            # ======================================================
    # EXECUTE ORDER (CROSS MARGIN)
    # ======================================================
    async def execute_order(self, symbol, side, qty):
        """
        side: long / short
        qty: quantity in USD
        """
        order = {
            "symbol":symbol,
            "side":side,
            "qty":qty,
            "time":datetime.datetime.now()
        }
        self.order_history.append(order)
        if side=="long":
            self.slots["long"] += 1
        else:
            self.slots["short"] += 1
        log(colored(f"[ORDER EXECUTED] {order}", "yellow"))
        return order

    # ======================================================
    # SLOT MANAGEMENT
    # ======================================================
    def can_open_order(self, side):
        if side=="long" and self.slots["long"] < self.slots["max"]:
            return True
        if side=="short" and self.slots["short"] < self.slots["max"]:
            return True
        return False

    # ======================================================
    # LEVERAGE & MARGIN DYNAMIC
    # ======================================================
    def adjust_leverage(self):
        # contoh logika: turunkan jika target profit hari ke-2 tercapai
        if self.day_index >=2:
            self.leverage = max(20, self.leverage-5)
                # ======================================================
    # MAIN LOOP NORMAL MODE
    # ======================================================
    async def run(self):
        while self.running:
            for symbol in self.config["normal_pairs"]:
                signal = self.generate_signal_normal(symbol)
                if signal and self.can_open_order(signal.replace("_scalp","")):
                    qty = self.balance * 0.4 / self.slots["max"]  # contoh margin
                    await self.execute_order(symbol, signal.replace("_scalp",""), qty)

            # Check profit target harian
            total_profit = sum([o["qty"] for o in self.order_history])
            if total_profit >= self.target_profit_day * self.day_index:
                self.day_index +=1
                log(colored(f"🎯 Target profit harian tercapai, hari ke-{self.day_index}", "green"))

            # Auto restart tiap 6 jam
            now = datetime.datetime.now()
            if (now - self.last_restart).total_seconds() > 21600:
                log(colored("🔄 Auto restart engine normal", "cyan"))
                self.slots = {"long":0, "short":0, "max":3}
                self.last_restart = now

            await asyncio.sleep(0.3)  # ultra fast loop
