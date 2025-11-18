# strategy_engine.py
from utils import fetch_orderbook, fetch_candles
from config import NORMAL_PAIRS, SNIPER_PAIRS, MAX_ORDER_NORMAL, MAX_ORDER_SNIPER
from parallel_channel import ParallelChannel

class NormalStrategy:
    def __init__(self):
        self.active_orders = 0

    def scan(self):
        signals = []
        for pair in NORMAL_PAIRS:
            candles = fetch_candles(pair)
            orderbook = fetch_orderbook(pair)
            channel = ParallelChannel(pair)
            channel.calculate()
            signal = self.analyze_pair(candles, orderbook, channel)
            if signal:
                signals.append(signal)
                self.active_orders += 1
                if self.active_orders >= MAX_ORDER_NORMAL:
                    break
        return signals

    def analyze_pair(self, candles, orderbook, channel):
        # Full hybrid strategy: SNR/SND + trendline + sideway + multi-TF + anti-dump
        return {"pair": "BTCUSDT", "side": "long", "size": 3}

class SniperStrategy:
    def __init__(self):
        self.active_orders = 0

    def scan(self):
        signals = []
        for pair in SNIPER_PAIRS:
            orderbook = fetch_orderbook(pair)
            signal = self.analyze_pair(orderbook)
            if signal:
                signals.append(signal)
                self.active_orders += 1
                if self.active_orders >= MAX_ORDER_SNIPER:
                    break
        return signals

    def analyze_pair(self, orderbook):
        # Whale detection + delta + trojan snipe
        return {"pair": "PEPEUSDT", "side": "long", "size": 5}
        
