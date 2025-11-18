import math
import time
import json
import logging
from datetime import datetime, timedelta
from statistics import mean

class RiskManager:
    """
    Komponen manajemen risiko paling lengkap:
    - Max risk per trade
    - Max daily loss
    - Max daily trade count
    - Exposure limiter
    - Volatility filter
    - Trailing stop adaptif
    - Stop loss dinamis
    - Cooldown setelah loss
    - Drawdown guard
    """

    def __init__(self, config):
        self.config = config

        # === RISK PARAMETERS ===
        self.max_risk_per_trade = config.get("max_risk_per_trade", 0.01)  # 1%
        self.max_daily_loss = config.get("max_daily_loss", 0.05)          # 5%
        self.max_daily_trades = config.get("max_daily_trades", 15)
        self.max_exposure = config.get("max_exposure", 0.2)               # 20% dari modal
        self.drawdown_limit = config.get("drawdown_limit", 0.15)          # 15% dari modal

        # === VOLATILITY PARAMETERS ===
        self.atr_period = config.get("atr_period", 14)
        self.volatility_multiplier = config.get("volatility_multiplier", 1.8)
        
        # === COOLDOWN SYSTEM ===
        self.cooldown_after_loss = config.get("cooldown_after_loss", 3)   # menit
        self.last_loss_time = None
        
        # === TRACKING ===
        self.daily_pnl = 0
        self.daily_trades = 0
        self.start_balance = config.get("account_balance", 100)
        self.current_balance = self.start_balance
        self.trade_history = []
        self.atr_values = []

        # === LOGGING ===
        logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


    # ========================================================
    #                    UPDATE EQUITY
    # ========================================================
    def update_balance(self, pnl):
        self.trade_history.append(pnl)
        self.current_balance += pnl
        self.daily_pnl += pnl
        self.daily_trades += 1
        if pnl < 0:
            self.last_loss_time = datetime.now()


    # ========================================================
    #                     DAILY FILTER
    # ========================================================
    def check_daily_limit(self):
        if abs(self.daily_pnl) >= self.start_balance * self.max_daily_loss:
            logging.warning("⚠️ Daily loss limit triggered. Trading stopped for today.")
            return False

        if self.daily_trades >= self.max_daily_trades:
            logging.warning("⚠️ Daily maximum trade count reached.")
            return False

        return True


    # ========================================================
    #                COOLDOWN AFTER LOSS
    # ========================================================
    def check_cooldown(self):
        if self.last_loss_time is None:
            return True

        elapsed = (datetime.now() - self.last_loss_time).seconds / 60
        if elapsed < self.cooldown_after_loss:
            logging.warning(f"⏳ Cooldown active: wait {self.cooldown_after_loss - elapsed:.1f} more minutes.")
            return False

        return True


    # ========================================================
    #             ATR / VOLATILITY CALCULATOR
    # ========================================================
    def update_atr(self, high, low, close):
        tr = high - low
        self.atr_values.append(tr)

        if len(self.atr_values) > self.atr_period:
            self.atr_values.pop(0)

        if len(self.atr_values) < self.atr_period:
            return None

        return mean(self.atr_values)


    # ========================================================
    #             VOLATILITY / NOISE FILTER
    # ========================================================
    def volatility_ok(self, atr, price):
        if atr is None:
            return False

        ratio = atr / price
        if ratio > 0.03:  # Volatilitas ekstrem (3%)
            logging.warning("⚠️ Market terlalu volatile.")
            return False

        return True


    # ========================================================
    #            DRAWDOWN PROTECTION SYSTEM
    # ========================================================
    def check_drawdown(self):
        dd = (self.start_balance - self.current_balance) / self.start_balance
        if dd >= self.drawdown_limit:
            logging.error("🚨 DRAW DOWN limit reached — trading STOPPED.")
            return False
        return True


    # ========================================================
    #           POSITION SIZE CALCULATOR (Advanced)
    # ========================================================
    def calculate_position_size(self, price, atr):
        """
        Rumus risk position:
        Risk = Equity * MaxRisk
        SL Distance = ATR * multiplier
        Size = Risk / SL
        """
        equity = self.current_balance
        max_risk = equity * self.max_risk_per_trade
        sl_distance = atr * self.volatility_multiplier

        if sl_distance == 0:
            return 0

        size = max_risk / sl_distance

        # Exposure guard
        max_size = equity * self.max_exposure / price
        return min(size, max_size)


    # ========================================================
    #             STOP LOSS & TAKE PROFIT (Dynamic)
    # ========================================================
    def generate_sl_tp(self, entry_price, atr):
        sl = entry_price - atr * self.volatility_multiplier
        tp = entry_price + atr * self.volatility_multiplier * 3
        return sl, tp


    # ========================================================
    #             TRAILING STOP SMART SYSTEM
    # ========================================================
    def trailing_stop(self, side, current_price, sl, atr):
        if side == "LONG":
            new_sl = max(sl, current_price - atr * 1.2)
        else:
            new_sl = min(sl, current_price + atr * 1.2)
        return new_sl


    # ========================================================
    #               RISK CHECK ENTRY FINAL
    # ========================================================
    def allow_trade(self, price, atr):
        checks = [
            self.check_daily_limit(),
            self.check_cooldown(),
            self.check_drawdown(),
            self.volatility_ok(atr, price)
        ]

        return all(checks)


    # ========================================================
    #                 EXPORT STATUS JSON
    # ========================================================
    def export_status(self):
        return {
            "balance": self.current_balance,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "drawdown": (self.start_balance - self.current_balance) / self.start_balance,
            "last_loss_time": str(self.last_loss_time),
        }


# ===========================================================
#                  STANDALONE TEST (Optional)
# ===========================================================
if __name__ == "__main__":
    cfg = {
        "max_risk_per_trade": 0.01,
        "max_daily_loss": 0.05,
        "max_daily_trades": 15,
        "atr_period": 14,
        "account_balance": 100,
        "volatility_multiplier": 1.8
    }

    rm = RiskManager(cfg)
    atr = rm.update_atr(100, 95, 97)

    print("ATR:", atr)
              
