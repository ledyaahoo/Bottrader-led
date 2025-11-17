# ws_engine.py
# WebSocket engine for Bitget (public channels: books + ticker)
# Keeps small deque buffers per symbol (orderbook deltas) and exposes fast queries.
# Uses websockets (pip install websockets)

import asyncio, json, time, threading
from collections import deque, defaultdict

import websockets

WS_URL = "wss://ws.bitget.com/mix/v1/stream"

class WSBuffer:
    """Holds limited history snapshots of orderbook deltas / snapshots."""
    def __init__(self, maxlen=200):
        self.book = deque(maxlen=maxlen)   # raw snapshots (dict)
        self.ts = deque(maxlen=maxlen)     # timestamps

class WSManager:
    def __init__(self, symbols, max_snapshots=150):
        self.symbols = list(dict.fromkeys(symbols))
        self.max_snapshots = max_snapshots
        self._running = False
        self._thread = None
        # store per-symbol buffers
        self.buffers = {s: WSBuffer(maxlen=max_snapshots) for s in self.symbols}
        # last full snapshot quick-access
        self.latest_book = {}
        self.latest_ticker = {}
        # internal loop
        self.loop = None

    async def _connect(self):
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20, max_size=None) as ws:
                    # subscribe channels
                    for s in self.symbols:
                        sub_books = {"op":"subscribe","args":[{"instType":"USDT-FUTURES","channel":"books","instId":s}]}
                        sub_tick = {"op":"subscribe","args":[{"instType":"USDT-FUTURES","channel":"ticker","instId":s}]}
                        await ws.send(json.dumps(sub_books))
                        await ws.send(json.dumps(sub_tick))
                    # listen
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        # unified parsing
                        try:
                            if "arg" in msg and "channel" in msg["arg"]:
                                ch = msg["arg"]["channel"]
                                inst = msg["arg"].get("instId") or msg["arg"].get("symbol")
                                data = msg.get("data")
                                if not inst or not data:
                                    continue
                                # choose first data element if list
                                payload = data[0] if isinstance(data, list) and len(data)>0 else data
                                if ch == "books":
                                    # store snapshot
                                    self.latest_book[inst] = payload
                                    self.buffers[inst].book.append(payload)
                                    self.buffers[inst].ts.append(time.time())
                                elif ch == "ticker":
                                    self.latest_ticker[inst] = payload
                            elif "topic" in msg and "data" in msg:
                                topic = msg["topic"]
                                if "books" in topic:
                                    inst = topic.split(":")[-1]
                                    payload = msg["data"]
                                    self.latest_book[inst] = payload
                                    self.buffers[inst].book.append(payload)
                                    self.buffers[inst].ts.append(time.time())
                                elif "ticker" in topic:
                                    inst = topic.split(":")[-1]
                                    self.latest_ticker[inst] = msg["data"]
                        except Exception:
                            continue
            except Exception as e:
                # reconnect after short sleep
                await asyncio.sleep(1)
                continue

    def start(self):
        if self._running:
            return
        self._running = True
        self.loop = asyncio.new_event_loop()
        def _target():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._connect())
        self._thread = threading.Thread(target=_target, daemon=True)
        self._thread.start()

    def get_latest_book(self, symbol):
        return self.latest_book.get(symbol)

    def get_latest_ticker(self, symbol):
        return self.latest_ticker.get(symbol)

    def get_buffer(self, symbol):
        return list(self.buffers.get(symbol).book) if symbol in self.buffers else []

    # lightweight helpers:
    def top_imbalance(self, symbol, top_n=5):
        """Return (sum_bids, sum_asks) from latest snapshot top_n"""
        b = self.get_latest_book(symbol)
        if not b:
            return 0.0, 0.0
        try:
            bids = b.get("bids", [])[:top_n]
            asks = b.get("asks", [])[:top_n]
            sum_bids = sum(float(x[1]) for x in bids) if bids else 0.0
            sum_asks = sum(float(x[1]) for x in asks) if asks else 0.0
            return sum_bids, sum_asks
        except Exception:
            return 0.0, 0.0
                                  
