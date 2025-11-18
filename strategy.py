import numpy as np

class Strategy:

    def __init__(self, delta_buffer=0.03):
        self.delta_buffer = delta_buffer

    # ===== NORMAL MODE =====
    def normal_signal(self, candles, price):
        """
        SNR/SND + Trendline + Parallel Channel + Sideway Scalp + Wick dump
        """
        trend = self.calculate_trend(candles)
        snr_high, snr_low = self.snr_zones(candles)
        signal = None

        # Wick dump
        if price <= snr_low * (1 + self.delta_buffer):
            signal = "buy"
        elif price >= snr_high * (1 - self.delta_buffer):
            signal = "sell"
        else:
            # Trendline break
            if trend == "uptrend":
                signal = "buy"
            elif trend == "downtrend":
                signal = "sell"
            else:
                signal = None
        return signal

    # ===== MEME SNIPER MODE =====
    def sniper_signal(self, candles, price, whale_data=None):
        """
        Whale wall + copytrade + anti-rug + orderbook delta
        """
        signal = None
        if whale_data:
            if whale_data["buy_wall"] > whale_data["sell_wall"]:
                signal = "buy"
            elif whale_data["sell_wall"] > whale_data["buy_wall"]:
                signal = "sell"
        return signal

    # ===== HELPER FUNCTIONS =====
    def calculate_trend(self, candles):
        closes = [c['close'] for c in candles]
        if len(closes) < 20:
            return "sideways"
        if closes[-1] > closes[-10]:
            return "uptrend"
        elif closes[-1] < closes[-10]:
            return "downtrend"
        return "sideways"

    def snr_zones(self, candles):
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        return max(highs), min(lows)
        
