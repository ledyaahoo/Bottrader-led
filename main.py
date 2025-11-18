# main.py
import os
import time
from config import NORMAL_PAIRS, SNIPER_PAIRS

# Placeholder engine imports
# from normal_engine import NormalEngine
# from sniper_engine import SniperEngine

def scan_normal():
    for pair in NORMAL_PAIRS:
        print(f"[NORMAL] Scanning {pair} ...")
        # TODO: normal engine logic

def scan_sniper():
    for pair in SNIPER_PAIRS:
        print(f"[SNIPER] Scanning {pair} ...")
        # TODO: sniper engine logic

def start_bot():
    print("Ultra-Safe Hybrid Bot Running...")
    while True:
        scan_normal()
        scan_sniper()
        # 1 detik delay, bisa disesuaikan dengan mode ultra-fast
        time.sleep(1)

if __name__ == "__main__":
    start_bot()
    
