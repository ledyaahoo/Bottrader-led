# parallel_channel.py
from utils import fetch_candles

class ParallelChannel:
    def __init__(self, pair):
        self.pair = pair
        self.upper = 0
        self.lower = 0

    def calculate(self):
        candles = fetch_candles(self.pair)
        highs = [c["high"] for c in candles[-20:]]
        lows = [c["low"] for c in candles[-20:]]
        self.upper = max(highs)
        self.lower = min(lows)
        return self.upper, self.lower

    def check_signal(self, price):
        if price >= self.upper:
            return "break_out"
        elif price <= self.lower:
            return "break_down"
        else:
            return "sideway"
          
