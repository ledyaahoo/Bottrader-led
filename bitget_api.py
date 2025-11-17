# ===========================
# bitget_api.py  (API REAL)
# ===========================
import os
import time
import hmac
import hashlib
import base64
import requests

class BitgetClient:
    def __init__(self):
        self.api_key = os.getenv("BITGET_API_KEY")
        self.secret_key = os.getenv("BITGET_API_SECRET")
        self.passphrase = os.getenv("BITGET_API_PASSPHRASE")

        if not self.api_key or not self.secret_key or not self.passphrase:
            raise ValueError("❌ API tidak ditemukan! Set Secret di GitHub: BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE")

        self.base = "https://api.bitget.com"

    # =============== SIGNING ===============
    def _sign(self, timestamp, method, path, body=""):
        msg = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()

    def _headers(self, method, path, body=""):
        ts = str(int(time.time() * 1000))
        sign = self._sign(ts, method, path, body)
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

    # =============== REQUEST ===============
    def _req(self, method, endpoint, body={}):
        url = self.base + endpoint
        import json
        body_str = json.dumps(body) if body else ""
        head = self._headers(method.upper(), endpoint, body_str)

        if method == "GET":
            r = requests.get(url, headers=head)
        else:
            r = requests.post(url, headers=head, data=body_str)

        try:
            return r.json()
        except:
            return None

    # =============== MARKET PRICE ===============
    def get_price(self, symbol):
        r = self._req("GET", f"/api/mix/v1/market/mark-price?symbol={symbol}")
        try:
            return float(r["data"]["markPrice"])
        except:
            return None

    # =============== OPEN ORDER ===============
    def open_order(self, symbol, size, side, leverage):
        body = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "size": str(size),
            "side": side,       # buyLong / sellShort
            "orderType": "market",
            "leverage": str(leverage)
        }
        return self._req("POST", "/api/mix/v1/order/placeOrder", body)

    # =============== CLOSE ORDER ===============
    def close_order(self, symbol, size, side):
        body = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "size": str(size),
            "side": side,      # closeLong / closeShort
            "orderType": "market"
        }
        return self._req("POST", "/api/mix/v1/order/closeOrder", body)

    # =============== POSITION DATA ===============
    def get_positions(self, symbol):
        r = self._req("GET", f"/api/mix/v1/position/singlePosition?symbol={symbol}&marginCoin=USDT")
        try:
            return r["data"]
        except:
            return None

    # =============== ACCOUNT BALANCE ===============
    def get_balance(self):
        r = self._req("GET", "/api/mix/v1/account/account?marginCoin=USDT")
        try:
            return float(r["data"]["equity"])
        except:
            return None
          
