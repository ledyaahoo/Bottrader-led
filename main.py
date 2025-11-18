import time
from config import NORMAL_PAIRS, SNIPER_PAIRS

def start_bot():
    print("Starting Ultra-Safe Hybrid Bot...")
    while True:
        # Scan normal pairs
        for pair in NORMAL_PAIRS:
            print(f"[NORMAL] Scanning {pair} ...")
            # TODO: panggil normal_engine untuk cek entry

        # Scan sniper pairs
        for pair in SNIPER_PAIRS:
            print(f"[SNIPER] Scanning {pair} ...")
            # TODO: panggil sniper_engine untuk cek entry

        # Delay sebentar sebelum scanning lagi
        time.sleep(1)  # 1 detik
