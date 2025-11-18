# main.py
import os
from config import NORMAL_PAIRS, SNIPER_PAIRS

def start_bot():
    print("Starting Ultra-Safe Hybrid Bot...")
    print(f"Normal pairs: {NORMAL_PAIRS}")
    print(f"Sniper pairs: {SNIPER_PAIRS}")

    # Placeholder: integrasi engine, websocket, strategi disini
    for pair in NORMAL_PAIRS:
        print(f"Scan normal pair: {pair}")
    for pair in SNIPER_PAIRS:
        print(f"Scan sniper pair: {pair}")

if __name__ == "__main__":
    start_bot()
    
