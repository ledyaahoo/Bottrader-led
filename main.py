# main.py
import time
from engine import Engine
from strategy_engine import NormalStrategy, SniperStrategy
from order_manager import OrderManager
from risk_manager import RiskManager
from config import INITIAL_BALANCE, TARGET_NORMAL, TARGET_SNIPER

def main():
    print("=== Ultra-Safe Hybrid Bot v2.1 Mode D ===")
    
    engine = Engine()
    normal_strategy = NormalStrategy()
    sniper_strategy = SniperStrategy()
    order_manager = OrderManager()
    risk_manager = RiskManager()
    
    balance = INITIAL_BALANCE
    daily_profit_normal = 0
    daily_profit_sniper = 0
    run_count = 0
    
    while True:
        run_count += 1
        print(f"\n--- Run {run_count} ---")
        
        # Normal Strategy Execution
        normal_signals = normal_strategy.scan()
        if normal_signals:
            order_manager.execute(normal_signals, mode="normal")
        
        # Sniper Strategy Execution
        sniper_signals = sniper_strategy.scan()
        if sniper_signals:
            order_manager.execute(sniper_signals, mode="sniper")
        
        # Update profit
        daily_profit_normal = risk_manager.update_profit("normal")
        daily_profit_sniper = risk_manager.update_profit("sniper")
        print(f"Daily Profit Normal: ${daily_profit_normal:.2f}")
        print(f"Daily Profit Sniper: ${daily_profit_sniper:.2f}")
        
        # Check targets
        if daily_profit_normal >= TARGET_NORMAL:
            print("Target Normal reached. Only perfect entries.")
        if daily_profit_sniper >= TARGET_SNIPER:
            print("Target Sniper reached. Only perfect entries.")
        
        # Auto restart every 6h
        time.sleep(0.3)  # simulate ultra-fast loop
        engine.check_restart()
        
if __name__ == "__main__":
    main()
    
