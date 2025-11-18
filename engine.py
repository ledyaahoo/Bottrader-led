# engine.py
import time
from websocket_client import WebSocketClient

class Engine:
    def __init__(self):
        self.ws_client = WebSocketClient()
        self.last_restart = time.time()
        self.restart_interval = 6*60*60  # 6 hours

    def check_restart(self):
        if time.time() - self.last_restart >= self.restart_interval:
            print("Restart interval reached. Restarting bot...")
            self.restart()
    
    def restart(self):
        try:
            self.ws_client.disconnect()
        except Exception:
            pass
        self.ws_client.connect()
        self.last_restart = time.time()
        print("Bot restarted successfully.")
        
