import os
import time
import asyncio
import traceback
from datetime import datetime, timedelta
import pytz

from engine import TradingEngine
from profit_tracker import ProfitTracker
from risk_manager import RiskManager
from strategy_normal import NormalStrategy
from strategy_meme import MemeSnipeStrategy
from utils import log, colored

# ===============================
# REGION: INISIASI UTAMA
# ===============================

API_KEY = os.getenv("BITGET_API_KEY")
API_SECRET = os.getenv("BITGET_API_SECRET")
API_PASS = os.getenv("BITGET_API_PASS")

if not API_KEY or not API_SECRET or not API_PASS:
    raise Exception("❌ Environment Variable untuk API BITGET belum di set di secret repo!")

MODE = os.getenv("BOT_MODE", "NORMAL").upper()

SUPPORTED_MODES = ["NORMAL", "MEME"]

if MODE not in SUPPORTED_MODES:
    raise Exception("❌ BOT_MODE tidak valid (NORMAL / MEME)")

# ===============================
# WAKTU WIB
# ===============================

WIB = pytz.timezone("Asia/Jakarta")

def now_wib():
    return datetime.now(WIB)

# ===============================
# TARGET PROFIT RULES (FINAL)
# ===============================

def calculate_daily_target(mode: str, current_equity: float) -> float:
    """
    Mode NORMAL:
      - Modal awal 3$
      - Target awal 30$ per hari
      - Target naik kelipatan ×3 setiap harinya
      - Setelah mencapai 3000$, kelipatan menjadi ×1 per hari (target tetap)

    Mode MEME SNIPE:
      - Target minimal 40$
      - Pertumbuhan target harian ×1.5
      - Setelah profit snipe mencapai total 3000$, kelipatan berubah ke ×1 per hari
    """

    if mode == "NORMAL":
        if current_equity < 3000:
            return 30
        else:
            return 30  # flat daily after 3000

    if mode == "MEME":
        if current_equity < 3000:
            return 40
        else:
            return 40  # flat after 3000

    return 30


# ===============================
# PEMILIHAN STRATEGI
# ===============================

def load_strategy(mode: str):
    if mode == "NORMAL":
        return NormalStrategy()
    if mode == "MEME":
        return MemeSnipeStrategy()
    raise Exception("Mode strategi tidak ditemukan")


# ===============================
# FUNGSI UTAMA BOT
# ===============================

async def run_bot():
    log(colored("🚀 MEMULAI BOT TRADING BITGET...", "yellow"))

    engine = TradingEngine(
        api_key=API_KEY,
        api_secret=API_SECRET,
        api_pass=API_PASS
    )

    tracker = ProfitTracker()
    risk = RiskManager()
    strategy = load_strategy(MODE)

    log(colored(f"🔧 MODE BOT: {MODE}", "cyan"))

    last_reset_day = now_wib().day

    while True:
        try:
            # === RESET PROFIT HARIAN SAAT GANTI HARI (WIB) ===
            if now_wib().day != last_reset_day:
                tracker.reset_daily_profit()
                last_reset_day = now_wib().day
                log(colored("📆 Hari baru — profit harian direset!", "green"))

            equity = await engine.get_wallet_balance()
            if equity is None:
                log("Gagal membaca balance... retry 5 detik")
                await asyncio.sleep(5)
                continue

            daily_target = calculate_daily_target(MODE, equity)
            current_profit = tracker.get_daily_profit()

            log(f"[EQUITY] {equity:.4f} | [PROFIT HARIAN] {current_profit:.4f} / {daily_target}")

            # === CEK APAKAH TARGET SUDAH TERCAPAI ===
            target_hit = current_profit >= daily_target

            if target_hit:
                log(colored("🎯 TARGET HARIAN TERCAPAI — ENTRY hanya pada peluang sempurna!", "green"))

            # === AMBIL DATA MARKET ===
            market_data = await engine.get_market_data(strategy.symbol)
            if market_data is None:
                await asyncio.sleep(2)
                continue

            # === HITUNG SIGNAL STRATEGI ===
            signal = strategy.generate_signal(
                price=market_data["price"],
                candles=market_data["candles"],
                orderbook=market_data["orderbook"],
                target_met=target_hit
            )

            if signal is None:
                await asyncio.sleep(1)
                continue

            # === CEK RISIKO ===
            if not risk.check(signal, equity):
                log(colored("⚠️ Risiko tidak layak — entry dibatalkan", "red"))
                await asyncio.sleep(1)
                continue

            # === HITUNG SIZE ORDER (menggunakan modal 3$) ===
            size = risk.calculate_position_size(
                equity=equity,
                base_capital=3  # sesuai permintaan: modal fix 3$
            )

            # === EKSEKUSI ORDER ===
            order = await engine.execute_order(
                symbol=strategy.symbol,
                side=signal["side"],
                qty=size,
                tp=signal["tp"],
                sl=signal["sl"]
            )

            if order:
                tracker.update_profit(order)

            await asyncio.sleep(1)

        except Exception as e:
            log(colored(f"❌ ERROR: {str(e)}", "red"))
            traceback.print_exc()
            await asyncio.sleep(3)


# ===============================
# ENTRY POINT
# ===============================

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        log(colored("🛑 BOT DIHENTIKAN OLEH USER", "magenta"))
            
