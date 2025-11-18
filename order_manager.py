import asyncio
from datetime import datetime, timedelta
from utils import log, colored

class OrderManager:
    """
    Mengatur slot order, prioritas, max order
    - Normal mode: 3 long / 3 short
    - Meme mode: 2 long / 2 short
    - Max slot 5 → 7 jika balance > $30
    - Auto close weak positions
    - Restart 6 jam
    """

    def __init__(self, engine, normal_bot, meme_bot, main_config):
        self.engine = engine
        self.normal_bot = normal_bot
        self.meme_bot = meme_bot
        self.config = main_config

        # Slot max
        self.max_order_normal = 3
        self.max_order_meme = 2
        self.max_total_order = 5

        # Tracking
        self.open_orders = {"normal_long":0, "normal_short":0,
                            "meme_long":0, "meme_short":0}
        self.last_restart = datetime.now()

        log(colored("ORDER MANAGER LOADED", "cyan"))

    # ======================================================
    # CHECK MAX SLOT
    # ======================================================
    def check_slot(self, mode, side):
        if mode=="normal":
            if side=="long" and self.open_orders["normal_long"]>=self.max_order_normal:
                return False
            if side=="short" and self.open_orders["normal_short"]>=self.max_order_normal:
                return False
        elif mode=="meme":
            if side=="long" and self.open_orders["meme_long"]>=self.max_order_meme:
                return False
            if side=="short" and self.open_orders["meme_short"]>=self.max_order_meme:
                return False
        return True

    # ======================================================
    # UPDATE SLOT ORDER
    # ======================================================
    def update_slot(self, mode, side, increment=True):
        key = f"{mode}_{side}"
        if increment:
            self.open_orders[key]+=1
        else:
            self.open_orders[key]-=1

    # ======================================================
    # AUTO RESTART 6 JAM
    # ======================================================
    async def auto_restart(self):
        now = datetime.now()
        if (now - self.last_restart).seconds >= 21600:  # 6 jam
            log(colored("🔄 Auto restart OrderManager...", "yellow"))
            await self.close_weak_positions()
            self.last_restart = now

    # ======================================================
    # CLOSE POSISI LEMAH
    # ======================================================
    async def close_weak_positions(self):
        # close posisi floating kecil / risiko tinggi
        # dapat di implementasikan dengan cek PnL < threshold
        log(colored("⚠️ Closing weak positions (floating small)...", "yellow"))
        # integrasi engine.execute_order untuk exit posisi
        # placeholder, bisa expand sesuai strategi

    # ======================================================
    # ADJUST MAX TOTAL ORDER SESUAI BALANCE
    # ======================================================
    async def adjust_max_total_order(self):
        balance = await self.engine.get_wallet_balance()
        if balance and balance>=30:
            self.max_total_order = 7
            self.max_order_normal = 3
            self.max_order_meme = 4
        else:
            self.max_total_order = 5
            self.max_order_normal = 3
            self.max_order_meme = 2

    # ======================================================
    # EKSEKUSI ORDER SESUAI PRIORITAS
    # ======================================================
    async def execute(self, daily_state):
        # normal mode first
        for symbol in self.config["normal_pairs"]:
            await self.normal_bot.execute_normal(symbol, daily_state)

        # meme sniper mode
        for symbol in self.config["meme_pairs"]:
            await self.meme_bot.execute_meme(symbol)

        # adjust slot & max order sesuai balance
        await self.adjust_max_total_order()

        # auto restart jika sudah 6 jam
        await self.auto_restart()
        
