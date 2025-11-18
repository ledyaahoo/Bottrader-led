import datetime
from utils import log, colored

class ProfitTracker:
    """
    Menghitung profit harian untuk NORMAL dan MEME SNIPER
    Target kelipatan otomatis
    Tracking per trade dan per hari
    """

    def __init__(self, normal_target=30, meme_target=40):
        self.normal_target_base = normal_target
        self.meme_target_base = meme_target

        self.normal_total_profit = 0
        self.meme_total_profit = 0

        self.normal_day_index = 1
        self.meme_day_index = 1

        self.normal_target_daily = self.normal_target_base * self.normal_day_index
        self.meme_target_daily = self.meme_target_base * 1.5 * self.meme_day_index

        self.start_time = datetime.datetime.now()
        self.timezone_offset = 7  # WIB

    # ======================================================
    # HITUNG PROFIT PER TRADE
    # ======================================================
    def add_normal_profit(self, pnl):
        self.normal_total_profit += pnl
        log(colored(f"[NORMAL PROFIT] Trade PnL: {pnl}, Total: {self.normal_total_profit}", "green" if pnl>0 else "red"))
        self.check_normal_target()

    def add_meme_profit(self, pnl):
        self.meme_total_profit += pnl
        log(colored(f"[MEME PROFIT] Trade PnL: {pnl}, Total: {self.meme_total_profit}", "green" if pnl>0 else "red"))
        self.check_meme_target()

    # ======================================================
    # CEK TARGET HARAN NORMAL
    # ======================================================
    def check_normal_target(self):
        if self.normal_total_profit >= self.normal_target_daily:
            log(colored(f"🎯 NORMAL TARGET DAY {self.normal_day_index} TERPENUHI: {self.normal_total_profit}$", "yellow"))
            self.normal_day_index +=1
            self.normal_target_daily = self.normal_target_base * self.normal_day_index
            # tetap trading tapi pilih peluang sempurna

    # ======================================================
    # CEK TARGET HARAN MEME
    # ======================================================
    def check_meme_target(self):
        if self.meme_total_profit >= self.meme_target_daily:
            log(colored(f"🎯 MEME TARGET DAY {self.meme_day_index} TERPENUHI: {self.meme_total_profit}$", "yellow"))
            self.meme_day_index +=1
            self.meme_target_daily = self.meme_target_base * 1.5 * self.meme_day_index
            # tetap trading tapi pilih peluang sempurna

    # ======================================================
    # STATUS PROFIT HARIAN
    # ======================================================
    def get_status(self):
        now_wib = datetime.datetime.utcnow() + datetime.timedelta(hours=self.timezone_offset)
        return {
            "time_wib": now_wib.strftime("%Y-%m-%d %H:%M:%S"),
            "normal_total_profit": self.normal_total_profit,
            "meme_total_profit": self.meme_total_profit,
            "normal_target_daily": self.normal_target_daily,
            "meme_target_daily": self.meme_target_daily,
            "normal_day_index": self.normal_day_index,
            "meme_day_index": self.meme_day_index
        }

    # ======================================================
    # RESET DAILY PROFIT (opsional)
    # ======================================================
    def reset_daily(self):
        self.normal_total_profit = 0
        self.meme_total_profit = 0
        log(colored("🔄 Reset daily profit tracker", "cyan"))
      
