# risk_manager.py
from config import (
    DAILY_STOPLOSS,
    DAILY_TARGET,
    MODE_TARGET,
    MODE_STOPLOSS
)

class RiskManager:
    def __init__(self):
        self.daily_profit = {"normal": 0, "sniper": 0}
        self.total_profit = 0

    def update_profit(self, mode):
        # In real bot: pull PnL from Bitget API
        pnl = 0.5  # placeholder PnL increment
        self.daily_profit[mode] += pnl
        self.total_profit += pnl
        return self.daily_profit[mode]

    def check_limits(self, mode):
        if self.daily_profit[mode] <= -MODE_STOPLOSS[mode]:
            return "stop"
        if self.daily_profit[mode] >= MODE_TARGET[mode]:
            return "slowdown"
        if self.total_profit <= -DAILY_STOPLOSS:
            return "shutdown"
        if self.total_profit >= DAILY_TARGET:
            return "target_hit"
        return "continue"
        
