import websocket
import json
import threading

class WSClient:

    def __init__(self, pairs):
        self.pairs = pairs
        self.price_data = {p: None for p in pairs}
        self.whale_data = {p: {"buy_wall":0,"sell_wall":0} for p in pairs}

    def on_message(self, ws, msg):
        data = json.loads(msg)
        # placeholder parsing
        pair = data.get("pair")
        price = data.get("price")
        buy_wall = data.get("buy_wall",0)
        sell_wall = data.get("sell_wall",0)
        if pair in self.pairs:
            self.price_data[pair] = price
            self.whale_data[pair] = {"buy_wall": buy_wall, "sell_wall": sell_wall}

    def start(self):
        def run_ws():
            while True:
                # placeholder untuk connect WS
                pass
        thread = threading.Thread(target=run_ws)
        thread.daemon = True
        thread.start()
      
