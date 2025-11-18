import asyncio
import numpy as np
from datetime import datetime

from utils import log, colored


PAIR_NORMAL = [
    "BTCUSDT_UMCBL",
    "ETHUSDT_UMCBL",
    "SOLUSDT_UMCBL",
    "LTCUSDT_UMCBL",
    "UNIUSDT_UMCBL",
    "HYPEUSDT_UMCBL",
    "ASTERUSDT_UMCBL"   # ralat sesuai yang kamu minta: ASTER bukan ASTR
]


# ======================================================================
#  NORMAL TRADING ENGINE (SNR / SND / TRENDLINE / VOLUME / REVERSAL)
# ======================================================================

class NormalTradingBot:

    def __init__(self, engine, config):
        self.engine = engine
        self.config = config

        self.open_positions = {
            "long": 0,
            "short": 0
        }

        self.max_long = 3
        self.max_short = 3

        self.current_leverage = 30  # default
        self.target_day_reached = 0

        log(colored("NORMAL MODE LOADED", "cyan"))


    # ===================================================================
    # KALKULASI SNR SND (SUPPLY DEMAND) OTOMATIS
    # ===================================================================

    def compute_snr_snd(self, candles):
        """
        Ambil beberapa level harga signifikan.
        Support/resistance otomatis.
        """
        highs = [c[2] for c in candles]
        lows = [c[3] for c in candles]

        support = min(lows[-20:])
        resistance = max(highs[-20:])
        mid = (support + resistance) / 2

        return {
            "support": support,
            "resistance": resistance,
            "mid": mid
        }

    # ===================================================================
    # TRENDLINE BREAKOUT / BREAKDOWN
    # ===================================================================

    def detect_trendline_break(self, candles):
        closes = [c[4] for c in candles]

        recent = closes[-10:]
        earlier = closes[-30:-10]

        # tren turun → breakout long
        if min(recent) > max(earlier):
            return "breakout"

        # tren naik → breakdown short
        if max(recent) < min(earlier):
            return "breakdown"

        return None

    # ===================================================================
    # VOLUME SPIKE (CONTINUATION ATAU EXHAUSTION)
    # ===================================================================

    def detect_volume_spike(self, candles):
        volumes = [c[5] for c in candles]
        avg = np.mean(volumes[-20:])
        last = volumes[-1]

        if last > avg * 2.5:
            return "big_spike"

        if last < avg * 0.5:
            return "weak"

        return "normal"

    # ===================================================================
    # SIDEWAY SCALP (5–15 MENIT)
    # ===================================================================

    def detect_sideway(self, candles):
        highs = [c[2] for c in candles[-20:]]
        lows = [c[3] for c in candles[-20:]]

        volatility = (max(highs) - min(lows)) / np.mean(highs)

        return volatility < 0.005  # sangat sempit

    # ===================================================================
    # REVERSAL BESAR + WICK DOMINAN (ANTI RUG NORMAL)
    # ===================================================================

    def detect_reversal_wick(self, candles):
        last = candles[-1]
        high, low, close, open_, vol = last[2], last[3], last[4], last[1], last[5]

        wick_up = high - max(open_, close)
        wick_down = min(open_, close) - low

        # detect dump cepat 35% → auto short → long bawah
        body = abs(close - open_)

        if wick_up > body * 2:
            return "sell_signal"

        if wick_down > body * 2:
            return "buy_signal"

        return None

    # ===================================================================
    # PELUANG ENTRY UTAMA NORMAL MODE
    # ===================================================================

    def generate_signal(self, data):
        candles = data["candles"]
        price = data["price"]

        snr = self.compute_snr_snd(candles)
        trend = self.detect_trendline_break(candles)
        vol = self.detect_volume_spike(candles)
        side = self.detect_sideway(candles)
        wick = self.detect_reversal_wick(candles)

        # PRIORITAS SIGNAL
        # ============================

        # 1. trendline breakout
        if trend == "breakout" and price > snr["resistance"]:
            return "long"

        if trend == "breakdown" and price < snr["support"]:
            return "short"

        # 2. big volume spike
        if vol == "big_spike":
            if price > snr["mid"]:
                return "long"
            else:
                return "short"

        # 3. sideway scalp
        if side:
            if price < snr["mid"]:
                return "long_scalp"
            else:
                return "short_scalp"

        # 4. wick reversal besar (dump/pump abnormal)
        if wick == "sell_signal":
            return "short"

        if wick == "buy_signal":
            return "long"

        return None

    # ===================================================================
    # EKSEKUSI POSISI NORMAL MODE
    # ===================================================================

    async def execute_normal(self, symbol, daily_state):
        """
        daily_state = status target harian main.py
        """

        data = await self.engine.get_market_data(symbol)
        if data is None:
            return

        signal = self.generate_signal(data)
        price = data["price"]

        # limit posisi
        if signal in ["long", "long_scalp"]:
            if self.open_positions["long"] >= self.max_long:
                return

        if signal in ["short", "short_scalp"]:
            if self.open_positions["short"] >= self.max_short:
                return

        qty = await self.calculate_qty(daily_state, price)

        # RISK MANAGEMENT → SL / TP
        sl = price * 0.99       # SL 1%
        tp = price * 1.004      # scalp cepat normal
        if signal == "long":
            tp = price * 1.008
        if signal == "short":
            tp = price * 0.992

        # OPEN POSITION
        if "long" in signal:
            self.open_positions["long"] += 1
            side = "open_long"
        else:
            self.open_positions["short"] += 1
            side = "open_short"

        result = await self.engine.execute_order(
            symbol=symbol,
            side=side,
            qty=qty,
            tp=tp,
            sl=sl
        )

        if result:
            pnl = result["pnl"]
            log(colored(f"[NORMAL] PNL {symbol}: {pnl}", "green" if pnl > 0 else "red"))

        # selesai trade → kosongkan slot
        if "long" in signal:
            self.open_positions["long"] -= 1
        else:
            self.open_positions["short"] -= 1


    # ===================================================================
    # PERHITUNGAN QTY BERDASARKAN TARGET HARIAN & LEVERAGE DINAMIS
    # ===================================================================

    async def calculate_qty(self, daily_state, price):
        """
        daily_state:
            - profit_normal
            - target_normal
            - day_index
        """

        balance = await self.engine.get_wallet_balance()
        if balance is None:
            balance = 3

        # aturan leverage
        if daily_state["day"] >= 2:
            self.current_leverage = 20
        else:
            self.current_leverage = 30

        margin_to_use = balance * 0.40  # sesuai revisi baru: 40% normal

        contract_value = margin_to_use * self.current_leverage
        qty = contract_value / price

        return round(qty, 4)
      
