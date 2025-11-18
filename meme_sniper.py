import asyncio
import numpy as np
from datetime import datetime
from utils import log, colored

PAIR_MEME = [
    "PEPEUSDT_UMCBL",
    "SHIBUSDT_UMCBL",
    "FLOKIUSDT_UMCBL",
    "WIFUSDT_UMCBL",
    "BONKUSDT_UMCBL",
    "AVNTUSDT_UMCBL",
    "XPLUSDT_UMCBL",
    "MANTAUSDT_UMCBL",
    "WIFUUSDT_UMCBL",
    "DASHUSDT_UMCBL",
    "ZCASHUSDT_UMCBL",
    "BEATUSDT_UMCBL",
    "XMRUSDT_UMCBL"
]

class MemeSniperBot:
    """
    Ultra Meme Sniper Bot
    - 2 long / 2 short slot
    - Whale detection + anti rug
    - Trojan Bot logic
    - Cross margin
    - Dynamic leverage
    """

    def __init__(self, engine, config):
        self.engine = engine
        self.config = config
        self.open_positions = {"long":0, "short":0}
        self.max_long = 2
        self.max_short = 2

        log(colored("MEME SNIPER MODE LOADED", "cyan"))

    # ======================================================
    # DETEKSI WHALE WALL / ORDERBOOK
    # ======================================================
    def detect_whale(self, orderbook):
        """
        Cari whale besar dari orderbook
        return signal: long/short/none
        """
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        # whale buy wall
        if bids and max([float(b[1]) for b in bids]) > 50000:
            return "long"

        # whale sell wall
        if asks and max([float(a[1]) for a in asks]) > 50000:
            return "short"

        return None

    # ======================================================
    # ENTRY SIGNAL MEME
    # ======================================================
    def generate_signal(self, data):
        price = data["price"]
        orderbook = data["orderbook"]
        signal = self.detect_whale(orderbook)

        # Anti rug: cek volume drop tiba2
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        bid_vol = sum([float(b[1]) for b in bids])
        ask_vol = sum([float(a[1]) for a in asks])

        if signal == "long" and bid_vol < ask_vol*0.2:
            signal = "exit_long_auto_short"
        if signal == "short" and ask_vol < bid_vol*0.2:
            signal = "exit_short_auto_long"

        return signal

    # ======================================================
    # HITUNG QTY & LEVERAGE
    # ======================================================
    async def calculate_qty(self, symbol, price):
        balance = await self.engine.get_wallet_balance()
        if balance is None:
            balance = 3  # default modal awal

        # dynamic leverage
        if price < 0.5:
            leverage = 13
        else:
            leverage = 20

        # margin cross: 55–75% untuk sniper
        margin = balance * 0.55
        contract_value = margin * leverage
        qty = contract_value / price
        return round(qty,4), leverage

    # ======================================================
    # EKSEKUSI POSISI MEME SNIPER
    # ======================================================
    async def execute_meme(self, symbol):
        data = await self.engine.get_market_data(symbol)
        if data is None:
            return

        signal = self.generate_signal(data)
        price = data["price"]
        qty, leverage = await self.calculate_qty(symbol, price)

        if signal in ["long","exit_short_auto_long"]:
            if self.open_positions["long"] >= self.max_long:
                return
            self.open_positions["long"] +=1
            side = "open_long"
            sl = price*0.99
            tp = price*1.01

        elif signal in ["short","exit_long_auto_short"]:
            if self.open_positions["short"] >= self.max_short:
                return
            self.open_positions["short"] +=1
            side = "open_short"
            sl = price*1.01
            tp = price*0.99
        else:
            return

        order = await self.engine.execute_order(
            symbol=symbol,
            side=side,
            qty=qty,
            tp=tp,
            sl=sl
        )

        if order:
            pnl = order.get("pnl",0)
            log(colored(f"[MEME] PNL {symbol}: {pnl}", "green" if pnl>0 else "red"))

        # kosongkan slot
        if "long" in side:
            self.open_positions["long"]-=1
        else:
            self.open_positions["short"]-=1
          
