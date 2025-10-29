import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class SwingPointService:
    """
    Independent service to record swing highs and lows into the DB.
    Supports both major trend and mini-wave (scalping) swings.
    """

    def __init__(self, mode="strict"):
        self.mode = mode
        self.logger = get_logger("Swing_Point_SwingPointService")

    # ===================================================
    # Public entrypoint
    # ===================================================
    def run_step(self, symbol: str, timeframe: str):
        try:
            df = self._get_recent_candles(symbol, timeframe)
            if df is None or len(df) < 10:
                return

            df = self._prepare_candles(df)

            if self.mode == "loose":
                self._detect_swing_loose(df, symbol, timeframe)
            else:
                self._detect_swing_strict(df, symbol, timeframe)

        except Exception as e:
            self.logger.exception(f"Error in SwingPointService.run_step: {e}")

    # ===================================================
    # Swing Detection
    # ===================================================
    def _detect_swing_loose(self, df, symbol, timeframe):
        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]

            if curr["high"] > prev["high"]:
                power = self._calculate_power_score(df, i, "high")
                self._record_swing(symbol, timeframe, "high", curr["high"], curr["timestamp"], source="loose", power_score=power)

            if curr["low"] < prev["low"]:
                power = self._calculate_power_score(df, i, "low")
                self._record_swing(symbol, timeframe, "low", curr["low"], curr["timestamp"], source="loose", power_score=power)

    def _detect_swing_strict(self, df, symbol, timeframe, window_size=3):
        highs, lows, timestamps = df["high"].values, df["low"].values, df["timestamp"].values

        for i in range(window_size, len(df) - window_size):
            swing_time = pd.to_datetime(timestamps[i]).to_pydatetime()
            discovered_at = pd.to_datetime(timestamps[i + window_size]).to_pydatetime()

            if highs[i] == max(highs[i - window_size:i + window_size + 1]):
                power = self._calculate_power_score(df, i, "high")
                self._record_swing(symbol, timeframe, "high", highs[i], swing_time, source="strict", power_score=power, discovered_at=discovered_at)

            if lows[i] == min(lows[i - window_size:i + window_size + 1]):
                power = self._calculate_power_score(df, i, "low")
                self._record_swing(symbol, timeframe, "low", lows[i], swing_time, source="strict", power_score=power, discovered_at=discovered_at)

    # ===================================================
    # Record swing in DB
    # ===================================================
    def _record_swing(self, symbol, timeframe, swing_type, price, candle_time,
                      source="strict", power_score=1.0, discovered_at=None):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM strategy_swing_point
                WHERE symbol=%s AND timeframe=%s AND swing_type=%s AND candle_time=%s
            """, (symbol, timeframe, swing_type, candle_time))

            if cursor.fetchone():
                return

            cursor.execute("""
                INSERT INTO strategy_swing_point
                (symbol, timeframe, swing_type, price, candle_time, discovered_at, power_score, source, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                symbol, timeframe, swing_type, price,
                candle_time, discovered_at or candle_time,
                power_score, source, datetime.utcnow()
            ))
            conn.commit()

    # ===================================================
    # Power Score Calculation
    # ===================================================
    def _calculate_power_score(self, df, idx, swing_type, lookback=10):
        """
        Compute power score based on volatility, range, and structure strength.
        Returns value typically between 0.5–3.0
        """
        try:
            avg_range = df["high"].sub(df["low"]).rolling(lookback).mean().iloc[idx]
            curr_range = df["high"].iloc[idx] - df["low"].iloc[idx]

            # Recent momentum (close movement over last few candles)
            momentum = abs(df["close"].iloc[idx] - df["close"].iloc[max(0, idx - 3)]) / avg_range

            # Strength factor (how extreme is it vs recent swings)
            if swing_type == "high":
                prev_extreme = df["high"].iloc[max(0, idx - lookback):idx].max()
                extremity = (df["high"].iloc[idx] - prev_extreme) / avg_range
            else:
                prev_extreme = df["low"].iloc[max(0, idx - lookback):idx].min()
                extremity = (prev_extreme - df["low"].iloc[idx]) / avg_range

            power = 0.5 + (curr_range / avg_range) * 0.3 + momentum * 0.3 + extremity * 0.4
            return round(max(0.5, min(power, 5.0)), 2)
        except Exception:
            return 1.0

    # ===================================================
    # Helpers
    # ===================================================
    def _get_recent_candles(self, symbol, timeframe):
        if symbol == "XAUUSDc" and timeframe == "M15":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No data function for {symbol}-{timeframe}")
        return df.tail(5000).reset_index(drop=True)

    def _prepare_candles(self, df):
        if "timestamp" not in df.columns:
            if "time" in df.columns:
                df["timestamp"] = df["time"].apply(lambda x: datetime.utcfromtimestamp(int(x)))
            else:
                df["timestamp"] = df.iloc[:, 0].apply(lambda x: datetime.utcfromtimestamp(int(x)))
        df["timestamp"] = df["timestamp"].apply(lambda x: x.replace(microsecond=0))
        return df
