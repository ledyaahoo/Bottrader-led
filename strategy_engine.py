# strategy_engine.py
# Implements Normal strategy + Meme Sniper strategy using WSManager buffers and BitgetClient
# Exposes async functions:
#   async def normal_run_once(client, ws, symbol, leverage)
#   async def sniper_run_once(client, ws, symbol, leverage)

import math, random, time, asyncio
from datetime import datetime

# Parameters (imported from main when used)
# MIN trade size (USD)
MIN_NOTIONAL = 1.5
# Normal uses ~30% fraction (configurable in main)
# Sniper uses 55-75% (we pick dynamic within range)
SNIPER_MIN_RATIO = 0.55
SNIPER_MAX_RATIO = 0.75
NORMAL_FRACTION = 0.30
STOPLOSS_PCT = 0.01  # 1% stoploss baseline
NORMAL_MAX_PER_SIDE = 3
SNIPER_MAX_PER_SIDE = 2

# Simple counters in-memory (symbol -> counts)
_normal_long_counts = {}
_normal_short_counts = {}
_sniper_long_counts = {}
_sniper_short_counts = {}

# Utility to get equity safely
def _get_equity_safe(client):
    bal = client.get_account_balance()
    try:
        if bal and isinstance(bal, dict):
            # Try typical path: {"data":[{"equity": "x", ...}]}
            data = bal.get("data")
            if isinstance(data, list) and len(data)>0:
                return float(data[0].get("equity", 0.0))
            if isinstance(data, dict):
                return float(data.get("equity", 0.0))
    except Exception:
        pass
    # fallback
    return float(getattr(client, "sim_balance", 3.0))

# -----------------------------
# NORMAL STRATEGY
# -----------------------------
async def normal_run_once(client, ws, symbol, leverage):
    """
    Normal strategy:
     - uses SNR/SND basic heuristics from book
     - volume spike detection (top 5 sums)
     - retest confirmation (placeholder minimal)
     - respects 3 long / 3 short caps per symbol
     - uses cross margin (client assumed)
    Returns {'profit': estimated_profit, 'resp': order_response} or None
    """
    try:
        book = ws.get_latest_book(symbol) or client.get_orderbook(symbol)
        ticker = ws.get_latest_ticker(symbol) or client.get_ticker(symbol)
        if not ticker:
            return None

        # signal detection
        sum_bids, sum_asks = ws.top_imbalance(symbol, top_n=5)
        vol_spike = False
        if (sum_bids + sum_asks) > 0:
            # if one side >= 1.5x of other -> spike
            if sum_bids > sum_asks * 1.5 or sum_asks > sum_bids * 1.5:
                vol_spike = True

        # basic retest: check buffer for small rebound signature (placeholder but uses buffer)
        buff = ws.get_buffer(symbol)
        retest_ok = False
        try:
            # if there are at least two snapshots and last shows price moving toward side
            if len(buff) >= 2:
                # approximate price from top of book
                last = buff[-1]
                prev = buff[-2]
                lp = (float(last.get("bids", [[0,0]])[0][0]) + 0.0) if last.get("bids") else None
                pp = (float(prev.get("bids", [[0,0]])[0][0]) + 0.0) if prev.get("bids") else None
                retest_ok = True  # keep simple: true if buffer exists
        except Exception:
            retest_ok = True

        # require either vol_spike or SNR presence (we use large sizes as SNR proxy)
        # SNR proxy:
        snr_present = False
        try:
            if book and "data" in book:
                d = book["data"][0] if isinstance(book["data"], list) else book["data"]
                bids = d.get("bids", [])[:10]
                asks = d.get("asks", [])[:10]
                if any(float(x[1]) > 1500 for x in bids) or any(float(x[1]) > 1500 for x in asks):
                    snr_present = True
        except Exception:
            snr_present = False

        if not (retest_ok and (vol_spike or snr_present)):
            return None

        # decide side by current imbalance
        side = "open_long" if sum_bids > sum_asks else "open_short"

        # enforce caps
        if side == "open_long":
            if _normal_long_counts.get(symbol,0) >= NORMAL_MAX_PER_SIDE:
                return None
        else:
            if _normal_short_counts.get(symbol,0) >= NORMAL_MAX_PER_SIDE:
                return None

        # compute size from equity
        equity = _get_equity_safe(client)
        size_usdt = max(MIN_NOTIONAL, equity * NORMAL_FRACTION)

        # place market order
        resp = client.place_market_order(symbol, side, size_usdt, leverage=leverage)
        # update counters
        if side == "open_long":
            _normal_long_counts[symbol] = _normal_long_counts.get(symbol,0) + 1
        else:
            _normal_short_counts[symbol] = _normal_short_counts.get(symbol,0) + 1

        # conservative profit estimate ~1% (normal)
        profit_est = size_usdt * 0.01
        return {"profit": profit_est, "resp": resp}
    except Exception as e:
        print(f"[normal_run_once] error {e}")
        return None

# -----------------------------
# MEME SNIPER STRATEGY
# -----------------------------
async def sniper_run_once(client, ws, symbol, leverage):
    """
    Sniper strategy (ultra):
     - uses top 5 imbalance (whale pressure)
     - if clear whale pressure -> open 1-2 positions (caps)
     - uses SNIPER_MIN..MAX ratio of equity (midpoint used)
     - anti-rug basic: require persistent pressure across 2 snapshots
    """
    try:
        book = ws.get_latest_book(symbol) or client.get_orderbook(symbol)
        if not book:
            return None

        # compute sums
        try:
            d = book.get("data")[0] if isinstance(book.get("data"), list) else book.get("data")
            bids = d.get("bids", [])[:5]
            asks = d.get("asks", [])[:5]
            sum_bids = sum(float(x[1]) for x in bids) if bids else 0.0
            sum_asks = sum(float(x[1]) for x in asks) if asks else 0.0
        except Exception:
            return None

        # detect pressure: threshold 1.8x as you specified
        side = None
        if sum_bids > sum_asks * 1.8:
            side = "open_long"
        elif sum_asks > sum_bids * 1.8:
            side = "open_short"
        else:
            return None

        # require persistence across small buffer (anti-false)
        buff = ws.get_buffer(symbol)
        persistent = False
        if len(buff) >= 2:
            # check previous snapshot also had similar imbalance
            try:
                prev = buff[-2]
                pbids = sum(float(x[1]) for x in prev.get("bids", [])[:5]) if prev.get("bids") else 0.0
                pasks = sum(float(x[1]) for x in prev.get("asks", [])[:5]) if prev.get("asks") else 0.0
                if side == "open_long" and pbids > pasks * 1.6:
                    persistent = True
                if side == "open_short" and pasks > pbids * 1.6:
                    persistent = True
            except Exception:
                persistent = True
        else:
            # if no buffer, be conservative: skip
            return None

        if not persistent:
            return None

        # enforce sniper caps
        if side == "open_long":
            if _sniper_long_counts.get(symbol,0) >= SNIPER_MAX_PER_SIDE:
                return None
        else:
            if _sniper_short_counts.get(symbol,0) >= SNIPER_MAX_PER_SIDE:
                return None

        equity = _get_equity_safe(client)
        # choose fraction midpoint
        frac = (SNIPER_MIN_RATIO + SNIPER_MAX_RATIO) / 2.0
        size_usdt = max(MIN_NOTIONAL, equity * frac)

        # place market order aggressive
        resp = client.place_market_order(symbol, side, size_usdt, leverage=leverage)

        # update counters
        if side == "open_long":
            _sniper_long_counts[symbol] = _sniper_long_counts.get(symbol,0) + 1
        else:
            _sniper_short_counts[symbol] = _sniper_short_counts.get(symbol,0) + 1

        # estimated quick scalp 1.5%
        profit_est = size_usdt * 0.015
        return {"profit": profit_est, "resp": resp}
    except Exception as e:
        print(f"[sniper_run_once] error {e}")
        return None
      
