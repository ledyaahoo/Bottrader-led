# normal_trading.py
# Implements Normal strategy: SNR/SND placeholders + volume spike + retest confirmation
# Exposes one coroutine: async def run_once(client, ws, symbol, leverage)

import asyncio, math, random
from datetime import datetime, timedelta

MIN_TRADE_USDT = 1.5    # minimal trade notional
STOPLOSS_PCT = 0.01     # 1% SL baseline

async def run_once(client, ws, symbol, leverage):
    """
    client: BitgetClient instance
    ws: WSManager instance (provides get_book / get_ticker)
    symbol: e.g. "BTCUSDT"
    leverage: chosen leverage int
    Returns: dict with 'profit' estimate when simulated/executed
    """
    try:
        # 1) Use websocket snapshots primarily
        book = ws.get_book(symbol) or client.get_orderbook(symbol)
        ticker = ws.get_ticker(symbol) or client.get_ticker(symbol)

        # basic checks
        if not ticker:
            return None

        # === SIGNAL LOGIC (best-effort, replace with your advanced SNR/SND) ===
        #  - volume spike check: compare latest trades depth proxy
        #  - retest check: placeholder returns True often
        try:
            # extract last price
            last = None
            if isinstance(ticker, dict) and "data" in ticker and isinstance(ticker["data"], list) and len(ticker["data"])>0:
                last = float(ticker["data"][0].get("last", ticker["data"][0].get("lastPrice", 0)))
            elif isinstance(ticker, dict) and "last" in ticker:
                last = float(ticker["last"])
        except:
            last = None

        # minimal price available
        if last is None:
            return None

        # volume spike heuristic (use book)
        vol_spike = False
        try:
            if book and "data" in book:
                # book["data"] could be list of snapshots
                b = book["data"][0] if isinstance(book["data"], list) else book["data"]
                bids = b.get("bids", [])
                asks = b.get("asks", [])
                top_bid = float(bids[0][1]) if bids else 0.0
                top_ask = float(asks[0][1]) if asks else 0.0
                # heuristic: if top sizes are large vs price ~ quick check
                if (top_bid + top_ask) > (last * 5):  # heuristic threshold
                    vol_spike = True
        except Exception:
            vol_spike = False

        # retest confirmation - placeholder quick check (you should replace with channel/SNR detection)
        retest_ok = True

        # decide to enter only when both conditions (strict)
        if not (vol_spike and retest_ok):
            return None

        # determine side by small momentum (random placeholder — replace with EMA / structure)
        side = "open_long" if random.random() > 0.5 else "open_short"

        # size determination: normal uses moderate portion (25-45% typical but split across positions)
        # we pick safe percent of available balance (caller uses INITIAL_BALANCE to start)
        # Here we use fixed minimal or fraction-based size
        balance_snapshot = client.get_account_balance()
        if balance_snapshot and isinstance(balance_snapshot, dict):
            # try to get equity
            try:
                equity = float(balance_snapshot.get("data", [])[0].get("equity", INITIAL_BALANCE))
            except:
                equity = INITIAL_BALANCE
        else:
            equity = INITIAL_BALANCE

        # Use 30% of balance as sample (but never less than MIN_TRADE_USDT)
        size_usdt = max(MIN_TRADE_USDT, equity * 0.30)

        # place order via client
        resp = client.place_market_order(symbol, side, size_usdt, leverage=leverage)

        # Estimate profit conservatively (1% on notional for normal)
        estimated_profit = size_usdt * 0.01

        # log minimal result via return
        return {"profit": estimated_profit, "resp": resp}
    except Exception as e:
        print(f"[normal_trading] error {e}")
        return None
      
