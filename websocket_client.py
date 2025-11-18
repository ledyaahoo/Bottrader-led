# websocket_client.py
import websocket
import json
import threading
import time
from config import WS_URL

class WebSocketClient:
    def __init__(self):
        self.ws = None
        self.connected = False

    def connect(self):
        def run():
            try:
                self.ws = websocket.WebSocketApp(
                    WS_URL,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_close=self.on_close
                )
                self.ws.run_forever(ping_interval=20)
            except Exception as e:
                print("WS Error:", e)
        
        threading.Thread(target=run, daemon=True).start()
        time.sleep(1)

    def on_open(self, ws):
        self.connected = True
        print("[WS] Connected.")

    def on_message(self, ws, msg):
        data = json.loads(msg)
        # Real bot parses orderbook, trades, delta engine
        print("[WS] Data:", data)

    def on_close(self, ws):
        self.connected = False
        print("[WS] Closed. Reconnecting...")
        time.sleep(1)
        self.connect()

    def disconnect(self):
        try:
            self.ws.close()
        except:
            pass
            
