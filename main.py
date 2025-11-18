import asyncio
import datetime
from engine_normal import EngineNormalWS
from engine_meme import EngineMemeWS
from utils import log, colored

class MainBot:
    """
    Main execution file
    - Menjalankan Normal Trading Bot
    - Menjalankan Meme Sniper Bot
    - Menghitung profit total harian
    - Menerapkan target profit harian & multiplier
    - Auto restart setiap 6 jam
    - Auto close posisi lemah sebelum restart
    - Pemisahan modal awal $3
    """

    def __init__(self, config, secret_repo):
        self.config = config
        self.secret_repo = secret_repo
        self.balance = 3.0  # modal awal
        self.day_index_normal = 1
        self.day_index_sniper = 1
        self.engine_normal = EngineNormalWS(config, secret_repo)
        self.engine_meme = EngineMemeWS(config, secret_repo)
        self.running = True
        self.last_restart = datetime.datetime.now()

    # ======================================================
    # LOAD SECRETS
    # ======================================================
    async def load_secrets(self):
        await self.engine_normal.load_secrets()
        await self.engine_meme.load_secrets()
        log(colored("✅ All secrets loaded successfully", "green"))

    # ======================================================
    # START ENGINES
    # ======================================================
    async def start_engines(self):
        await asyncio.gather(
            self.engine_normal.ws_connect(),
            self.engine_meme.ws_connect(),
            self.monitor_profit_loop()
        )

    # ======================================================
    # MONITOR PROFIT HARIAN
    # ======================================================
    async def monitor_profit_loop(self):
        while self.running:
            total_profit_normal = sum([o["qty"] for o in self.engine_normal.order_history])
            total_profit_sniper = sum([o["qty"] for o in self.engine_meme.order_history])

            # Normal mode target
            target_normal = self.engine_normal.target_profit_day * self.day_index_normal
            if total_profit_normal >= target_normal:
                self.day_index_normal += 1
                # Adjust slot & leverage
                self.engine_normal.slots["max"] += 0  # tetap 3 per run
                self.engine_normal.adjust_leverage()
                log(colored(f"🎯 Normal mode target harian tercapai, hari ke-{self.day_index_normal}", "green"))

            # Meme sniper target
            target_sniper = self.engine_meme.target_profit_day * self.day_index_sniper
            if total_profit_sniper >= target_sniper:
                self.day_index_sniper += 1
                self.engine_meme.adjust_leverage()
                log(colored(f"🎯 Meme sniper target harian tercapai, hari ke-{self.day_index_sniper}", "green"))

            # Auto restart 6 jam
            now = datetime.datetime.now()
            if (now - self.last_restart).total_seconds() > 21600:
                log(colored("🔄 Auto restart main bot", "cyan"))
                await self.restart_engines()
                self.last_restart = now

            await asyncio.sleep(5)

    # ======================================================
    # RESTART ENGINES
    # ======================================================
    async def restart_engines(self):
        log(colored("🛠 Restarting engines...", "yellow"))
        self.engine_normal.slots = {"long":0,"short":0,"max":3}
        self.engine_meme.slots = {"long":0,"short":0,"max":2}
        # Close posisi lemah sebelum restart
        await self.close_weak_positions()

    async def close_weak_positions(self):
        # Placeholder: implementasi auto-close posisi floating profit kecil
        log(colored("💡 Closing weak positions if any", "yellow"))
        # Bisa loop order_history dan cek floating profit

# ======================================================
# MAIN RUN
# ======================================================
if __name__ == "__main__":
    import config
    secret_repo_url = config.SECRET_REPO_URL
    bot = MainBot(config.CONFIG, secret_repo_url)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.load_secrets())
    loop.run_until_complete(bot.start_engines())
        # ======================================================
    # HITUNG KELIPATAN TARGET PROFIT
    # ======================================================
    def compute_target_profit(self):
        # Normal mode
        base_normal = self.engine_normal.target_profit_day
        multiplier_normal = 3 ** (self.day_index_normal - 1)
        self.engine_normal.current_target = min(base_normal * multiplier_normal, 3000)

        # Meme sniper mode
        base_sniper = self.engine_meme.target_profit_day
        multiplier_sniper = 1.5 ** (self.day_index_sniper - 1)
        self.engine_meme.current_target = min(base_sniper * multiplier_sniper, 3000)

    # ======================================================
    # PEMBAGIAN MARGIN NORMAL VS SNIPER
    # ======================================================
    def compute_margin_allocation(self):
        total_balance = self.balance
        if self.day_index_normal == 1:
            self.engine_normal.balance = total_balance * 0.6
            self.engine_meme.balance = total_balance * 0.4
        elif self.day_index_normal == 2:
            self.engine_normal.balance = total_balance * 0.4
            self.engine_meme.balance = total_balance * 0.3
            # sisanya 30% tidak digunakan
        elif self.day_index_normal >=3:
            # Maksimal order 6
            self.engine_normal.slots["max"] = 3
            self.engine_meme.slots["max"] = 3
            self.engine_normal.balance = total_balance * 0.5
            self.engine_meme.balance = total_balance * 0.3
            # sisanya 20% cadangan
                # ======================================================
    # MAIN RUN LOOP FINAL
    # ======================================================
    async def start_engines(self):
        await self.load_secrets()
        self.compute_target_profit()
        self.compute_margin_allocation()
        await asyncio.gather(
            self.engine_normal.ws_connect(),
            self.engine_meme.ws_connect(),
            self.monitor_profit_loop(),
            self.execution_loop()
        )

    # ======================================================
    # EXECUTION LOOP – ENTRY PELUANG SEMPURNA
    # ======================================================
    async def execution_loop(self):
        while self.running:
            for symbol in self.config["normal_pairs"]:
                signal = self.engine_normal.generate_signal_normal(symbol)
                if signal and self.engine_normal.can_open_order(signal.replace("_scalp","")):
                    qty = self.engine_normal.balance / self.engine_normal.slots["max"]
                    await self.engine_normal.execute_order(symbol, signal.replace("_scalp",""), qty)

            for symbol in self.config["meme_pairs"]:
                signal = self.engine_meme.generate_signal_meme(symbol)
                if signal and self.engine_meme.can_open_order(signal.replace("_scalp","")):
                    qty = self.engine_meme.balance / self.engine_meme.slots["max"]
                    await self.engine_meme.execute_order(symbol, signal.replace("_scalp",""), qty)

            # Update kelipatan target & margin setiap loop
            self.compute_target_profit()
            self.compute_margin_allocation()

            await asyncio.sleep(0.3)  # ultra fast, tetap ±0.3 detik per tick
