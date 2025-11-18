from config import *
import time

class OrderManager:

    def __init__(self, api_client):
        self.api = api_client
        self.active_orders = []

    def place_order(self, pair, side, qty, leverage, mode):
        """
        Eksekusi order real ke Bitget cross margin
        """
        # placeholder API call
        order = {
            "pair": pair,
            "side": side,
            "qty": qty,
            "leverage": leverage,
            "mode": mode,
            "status": "placed"
        }
        self.active_orders.append(order)
        print(f"[ORDER] {mode.upper()} {side.upper()} {qty} {pair} @ leverage {leverage}")
        return order

    def close_order(self, order_id):
        # placeholder API close
        self.active_orders = [o for o in self.active_orders if o.get("id") != order_id]
        print(f"[CLOSE] Order {order_id} closed")

    def manage_slots(self, current_modal, day_target_level):
        """
        Mengatur max order & margin allocation sesuai target profit
        """
        if day_target_level == 2:
            max_orders = MAX_ORDER_TARGET2
            normal_margin = current_modal * NORMAL_MARGIN_RATIO
            sniper_margin = current_modal * SNIPER_MARGIN_RATIO
        else:
            max_orders = MAX_ORDER_INITIAL
            normal_margin = current_modal * 0.5
            sniper_margin = current_modal * 0.5
        return max_orders, normal_margin, sniper_margin
        
