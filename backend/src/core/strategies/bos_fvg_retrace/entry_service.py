# src/core/strategies/bos_fvg_retrace/entry_service.py

import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class EntryService:
    """
    Detects valid retrace FVGs (mitigated) and creates trade entries
    with ATR-based SL and TP.
    """

    ATR_PERIOD = 14
    RR_RATIO = 1.0  # risk:reward (1:1 by default)

    def __init__(self):
        self.logger = get_logger("EntryService")

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run_step(self, symbol: str, timeframe: str):
        """
        Called after retrace stage. Finds FVGs that were mitigated
        but not yet turned into trade entries.
        """
        try:
            fvgs = self._get_mitigated_fvgs_without_entry(symbol, timeframe)
            if not fvgs:
                self.logger.info(f"[{symbol}-{timeframe}] No mitigated FVGs ready for entry.")
                return

            for fvg in fvgs:
                self._create_entry(symbol, timeframe, fvg)

        except Exception as e:
            self.logger.exception(f"Error in EntryService.run_step: {e}")

    # =========================================================
    # CORE LOGIC
    # =========================================================
    def _create_entry(self, symbol, timeframe, fvg):
        """
        Create an entry, SL, and TP using ATR-based distance.
        Entry is based on the close of the mitigation candle.
        """
        # 1️⃣ Fetch recent candles ending at the mitigation candle
        df = self._get_recent_candles(symbol, timeframe, end_time=fvg["mitigated_at"], lookback=100)
        if df is None or len(df) < self.ATR_PERIOD:
            self.logger.warning(f"⚠️ Not enough candles to calculate ATR for FVG {fvg['id']}")
            return

        atr = self._calculate_atr(df, self.ATR_PERIOD)
        atr_value = round(float(atr.iloc[-1]), 2)

        # 2️⃣ Get the mitigation candle close price
        end_time = pd.to_datetime(fvg["mitigated_at"])
        mitigation_candle = df[df["time"] == end_time]
        if mitigation_candle.empty:
            self.logger.warning(f"⚠️ Mitigation candle not found for {fvg['id']}")
            return

        close_price = float(mitigation_candle["close"].iloc[-1])

        direction = fvg["direction"]

        # 3️⃣ Define entry, SL, TP
        if direction == "bullish":
            entry = close_price
            sl = float(fvg["gap_low"]) - atr_value
            tp = entry + (entry - sl) * self.RR_RATIO
        else:
            entry = close_price
            sl = float(fvg["gap_high"]) + atr_value
            tp = entry - (sl - entry) * self.RR_RATIO

        # 4️⃣ Save to DB
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO strategy_bos_fvg_retrace_trades
                (fvg_id, symbol, timeframe, direction, entry_price, stop_loss, take_profit,
                atr_used, rr_ratio, mitigated_at, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            """, (
                fvg["id"], symbol, timeframe, direction,
                entry, sl, tp, atr_value, self.RR_RATIO, fvg["mitigated_at"]
            ))
            conn.commit()

        self.logger.info(
            f"📈 Entry created | {direction} | Entry={entry:.2f}, SL={sl:.2f}, TP={tp:.2f}, ATR={atr_value}"
        )

    # =========================================================
    # DATABASE OPS
    # =========================================================
    def _get_mitigated_fvgs_without_entry(self, symbol, timeframe):
        """
        Find FVGs that have been mitigated but no trade created yet.
        """
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT fvg.id, fvg.symbol, fvg.timeframe, fvg.direction,
                       fvg.gap_low, fvg.gap_high, fvg.mitigated_at
                FROM strategy_bos_fvg_retrace_fvg_zones fvg
                LEFT JOIN strategy_bos_fvg_retrace_trades t
                  ON t.fvg_id = fvg.id
                WHERE fvg.symbol = %s AND fvg.timeframe = %s
                  AND fvg.status = 'mitigated'
                  AND t.id IS NULL
                ORDER BY fvg.mitigated_at ASC
            """, (symbol, timeframe))
            return cursor.fetchall()

    # =========================================================
    # DATA HELPERS
    # =========================================================
    def _get_recent_candles(self, symbol, timeframe, end_time, lookback=100):
        """Fetch candles ending exactly at the retrace candle (mitigated_at)."""
        if symbol == "XAUUSDc" and timeframe == "M15":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No data source for {symbol}-{timeframe}")

        # ✅ Convert from UNIX timestamp → datetime
        if pd.api.types.is_integer_dtype(df["time"]):
            df["time"] = pd.to_datetime(df["time"], unit="s")
        else:
            df["time"] = pd.to_datetime(df["time"])

        # ✅ Align mitigated_at as datetime
        end_time = pd.to_datetime(end_time)

        # ✅ Get up to the candle that existed before or at mitigated_at
        df = df[df["time"] <= end_time].sort_values("time").tail(lookback).reset_index(drop=True)

        return df if not df.empty else None

    def _calculate_atr(self, df, period=14):
        """Calculate Average True Range (ATR)."""
        high, low, close = df["high"], df["low"], df["close"]

        tr = pd.concat([
            (high - low),
            (high - close.shift()),
            (close.shift() - low)
        ], axis=1).abs().max(axis=1)

        atr = tr.rolling(period).mean()
        return atr
