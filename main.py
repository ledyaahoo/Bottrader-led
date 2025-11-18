import time
from config import *
from strategy import Strategy
from order_manager import OrderManager
from websocket_client import WSClient

# =====================
# Initialize
# =====================
current_modal = 3.0  # modal awal
strategy = Strategy(delta_buffer=DELTA_BUFFER)
ws_client = WSClient(NORMAL_PAIRS + MEME_PAIRS)
order_mgr = OrderManager(api_client=None)  # nanti bisa diganti API client asli

ws_client.start()
print("Bot started, monitoring prices...")

# =====================
# Scheduler / Main Loop
# =====================
while True:
    for pair in NORMAL_PAIRS:
        price = ws_client.price_data.get(pair)
        if not price:
            continue
        # Ambil candle dummy / bisa diganti API real
        candles = [{"high":price*1.01,"low":price*0.99,"close":price} for _ in range(20)]
        signal = strategy.normal_signal(candles, price)
        if signal:
            order_mgr.place_order(pair, signal, qty=current_modal/3, leverage=LEVERAGE_NORMAL, mode="normal")

    for pair in MEME_PAIRS:
        price = ws_client.price_data.get(pair)
        whale = ws_client.whale_data.get(pair)
        if not price:
            continue
        candles = [{"high":price*1.01,"low":price*0.99,"close":price} for _ in range(20)]
        signal = strategy.sniper_signal(candles, price, whale)
        if signal:
            order_mgr.place_order(pair, signal, qty=current_modal*0.55/2, leverage=LEVERAGE_SNIPER_BIG, mode="sniper")

    # Target profit harian, scaling modal, max order, auto restart
    # bisa diimplementasikan di sini

    time.sleep(1)
  
