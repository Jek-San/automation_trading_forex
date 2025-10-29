# src/core/strategies/liquidity_sweep_rejection/context_service.py

import pandas as pd
from datetime import datetime, timedelta, timezone
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import (
    get_data_m15_xauusdc,
    get_data_h1_xauusdc,
    get_data_h4_xauusdc,
    get_data_d1_xauusdc,
)


class ContextService:
    """
    Maintains confirmed market structure context.
    Only updates when a swing high/low is *confirmed* by N following candles.

    Context fields:
      - recent_high / recent_low (confirmed swings)
      - bias
      - structure_state
      - PDH / PDL / PDC
      - is_active flag
    """

    def __init__(self, confirm_bars: int = 3):
        self.logger = get_logger("core.strategies.liquidity_sweep_rejection.context_service")
        self.confirm_bars = confirm_bars

    # ===================================================
    # Entry Point
    # ===================================================
    def run_step(self, symbol: str):
        """
        Run this each H1 close. Will only create a new context if new swing confirmed.
        """
        try:
            h1 = self._get_recent_candles(symbol, "H1")
            h4 = self._get_recent_candles(symbol, "H4")
            d1 = self._get_recent_candles(symbol, "D1")

            if len(h1) < 30 or len(h4) < 20:
                self.logger.warning("Insufficient candles for context update.")
                return

            # Bias from H4
            bias, structure_state = self._compute_bias(h4)

            # Confirmed structure from H1
            recent_high, recent_low = self._get_confirmed_swings(h1)

            # PDH/PDL/PDC from D1
            pdh, pdl, pdc = self._get_previous_day_levels(d1)

            # Current active context
            last_context = self._get_active_context(symbol)

            # Check for confirmed structure change
            if self._context_needs_update(last_context, recent_high, recent_low):
                if last_context:
                    self._deactivate_old_context(symbol, last_context["id"])
                last_candle_time = h1.iloc[-1]["time"]
                self._save_context(
                    symbol,
                    bias,
                    structure_state,
                    recent_high,
                    recent_low,
                    pdh,
                    pdl,
                    pdc,
                    last_candle_time,
                )
                self.logger.info(f"[{symbol}] ✅ New confirmed context created.")
            else:
                self.logger.info(f"[{symbol}] No new swing confirmed → context holds.")

        except Exception as e:
            self.logger.exception(f"Error in ContextService.run_step: {e}")

    # ===================================================
    # Core Logic
    # ===================================================
    def _get_confirmed_swings(self, df: pd.DataFrame):
        """
        Find the most recent *confirmed* swing high and swing low
        using N-bar confirmation rule.
        """
        highs = df["high"].values
        lows = df["low"].values

        swing_highs, swing_lows = [], []

        for i in range(self.confirm_bars, len(df) - self.confirm_bars):
            window_before = highs[i - self.confirm_bars:i]
            window_after = highs[i + 1:i + 1 + self.confirm_bars]
            if highs[i] > max(window_before) and highs[i] > max(window_after):
                swing_highs.append((i, highs[i]))

            window_before = lows[i - self.confirm_bars:i]
            window_after = lows[i + 1:i + 1 + self.confirm_bars]
            if lows[i] < min(window_before) and lows[i] < min(window_after):
                swing_lows.append((i, lows[i]))

        if not swing_highs or not swing_lows:
            return None, None

        last_high_idx, last_high_val = swing_highs[-1]
        last_low_idx, last_low_val = swing_lows[-1]

        # Only accept confirmed swings before the last few bars (avoid live bar)
        if last_high_idx > len(df) - self.confirm_bars - 1:
            last_high_val = None
        if last_low_idx > len(df) - self.confirm_bars - 1:
            last_low_val = None

        return last_high_val, last_low_val

    def _compute_bias(self, df: pd.DataFrame, lookback: int = 20):
        """Directional bias from H4 structure."""
        df = df.tail(lookback).reset_index(drop=True)
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        bias = "neutral"
        structure_state = "flat"

        try:
            if closes[-1] > closes[-5]:
                bias = "bullish"
                structure_state = "impulse"
            elif closes[-1] < closes[-5]:
                bias = "bearish"
                structure_state = "impulse"
            else:
                structure_state = "correction"
        except Exception:
            pass

        return bias, structure_state

    def _get_previous_day_levels(self, df: pd.DataFrame):
        if df is None or df.empty:
            return None, None, None

        df["date"] = pd.to_datetime(df["time"]).dt.date
        last_date = df.iloc[-1]["date"]
        prev_day = last_date - timedelta(days=1)
        prev_rows = df[df["date"] == prev_day]

        if not prev_rows.empty:
            row = prev_rows.iloc[-1]
        else:
            row = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

        return float(row["high"]), float(row["low"]), float(row["close"])

    # ===================================================
    # Context DB lifecycle
    # ===================================================
    def _get_active_context(self, symbol):
        """
        Ambil context terakhir (paling baru) untuk referensi update.
        Sekarang tidak menonaktifkan context lama.
        """
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT * FROM strategy_liq_sweep_rejection_market_contexts
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (symbol,),
            )
            return cursor.fetchone()

    def _context_needs_update(self, last_context, recent_high, recent_low):
        """
        Update context hanya jika:
          1️⃣ Tidak ada context sebelumnya
          2️⃣ Ada swing baru (recent_high > last_high atau recent_low < last_low)
          3️⃣ Atau sudah lewat 3 hari dari context terakhir
        """
        if last_context is None:
            return True
        if recent_high is None or recent_low is None:
            return False

        # Rule 1: struktur baru
        if (
            recent_high > last_context["recent_high"]
            or recent_low < last_context["recent_low"]
        ):
            return True

        # Rule 2: refresh time
        last_time = last_context["created_at"]
        now = datetime.utcnow()
        if (now - last_time).total_seconds() > 72 * 3600:  # 3 hari
            return True

        return False
    def _deactivate_old_context(self, symbol, context_id):
        pass
        # with get_connection() as conn:
        #     cursor = conn.cursor()
        #     cursor.execute(
        #         "UPDATE strategy_liq_sweep_rejection_market_contexts SET is_active = FALSE WHERE id = %s AND symbol = %s",
        #         (context_id, symbol),
        #     )
        #     conn.commit()
        #     self.logger.info(f"Old context {context_id} deactivated for {symbol}")

    def _save_context(self, symbol, bias, structure_state, recent_high, recent_low, pdh, pdl, pdc,last_candle_time):
        """
        Simpan context baru TANPA menonaktifkan context lama.
        Field baru: is_swept_high dan is_swept_low.
        """
        created_at = datetime.fromtimestamp(last_candle_time, tz=timezone.utc)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO strategy_liq_sweep_rejection_market_contexts
                (symbol, bias, structure_state, recent_high, recent_low, pdh, pdl, pdc,
                is_swept_high, is_swept_low, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, FALSE,TRUE, %s)
                """,
                (
                    symbol,
                    bias,
                    structure_state,
                    recent_high,
                    recent_low,
                    pdh,
                    pdl,
                    pdc,
                    created_at,
                ),
            )
            conn.commit()
            self.logger.info(f"[{symbol}] ✅ New context inserted (no deactivation).")

    # ===================================================
    # Candle helpers
    # ===================================================
    def _get_recent_candles(self, symbol, timeframe):
        if symbol != "XAUUSDc":
            raise ValueError(f"No data getter for {symbol}")

        if timeframe == "M15":
            return get_data_m15_xauusdc().tail(300).reset_index(drop=True)
        elif timeframe == "H1":
            return get_data_h1_xauusdc().tail(300).reset_index(drop=True)
        elif timeframe == "H4":
            return get_data_h4_xauusdc().tail(300).reset_index(drop=True)
        elif timeframe == "D1":
            return get_data_d1_xauusdc().tail(30).reset_index(drop=True)
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
