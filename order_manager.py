# order_manager.py
from config import LEVERAGE_NORMAL, LEVERAGE_SNIPER
from utils import api_place_order

class OrderManager:
    def __init__(self):
        self.orders = []

    def execute(self, signals, mode="normal"):
        for signal in signals:
            self.place_order(signal, mode)

    def place_order(self, signal, mode):
        pair = signal["pair"]
        side = signal["side"]
        size = signal["size"]
        leverage = LEVERAGE_SNIPER if mode == "sniper" else LEVERAGE_NORMAL
        success = api_place_order(pair, side, size, leverage)
        if success:
            self.orders.append({"pair": pair, "side": side, "size": size, "mode": mode})
            print(f"[ORDER] {mode.upper()} | {pair} | {side} | size={size} | lev={leverage}")
            
