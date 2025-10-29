import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class RejectionService:
    """
    Detects confirmed rejection after a liquidity sweep event.

    Confirmation rules:
      ✅ Check next N candles after sweep (default: 3)
      ✅ For buy-side sweep:
         - candle closes BELOW sweep level
         - candle high ≤ sweep_level (no new high)
         - candle body ≥ 0.5 * ATR
         - candle is bearish (close < open)
      ✅ For sell-side sweep:
         - candle closes ABOVE sweep level
         - candle low ≥ sweep_level (no new low)
         - candle body ≥ 0.5 * ATR
         - candle is bullish (close > open)
      ✅ If no valid rejection within N candles → mark as 'failed'
    """

    def __init__(self, symbol: str, timeframe: str = "M15", lookahead_bars: int = 3, atr_period: int = 14):
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookahead_bars = lookahead_bars
        self.atr_period = atr_period
        self.logger = get_logger("core.strategies.liquidity_sweep_rejection.rejection_service")

    # ===================================================
    # Entry point
    # ===================================================
    def run_step(self):
        """Run this on each new candle close."""
        try:
            pending_sweeps = self._get_pending_sweeps()

            if not pending_sweeps:
                self.logger.info(f"[{self.symbol}] No pending sweeps found.")
                return

            for sweep in pending_sweeps:
                self._evaluate_rejection(sweep)

        except Exception as e:
            self.logger.exception(f"Error in RejectionService.run_step: {e}")

    # ===================================================
    # Core logic
    # ===================================================
    def _evaluate_rejection(self, sweep):
        """Check next N candles after sweep for confirmed rejection using ATR hybrid logic.
        
        Handles edge cases where fewer than lookahead_bars exist.
        """
        sweep_time = sweep["candle_time"]
        sweep_level = float(sweep["sweep_level"])
        direction = sweep["direction"]

        # Load candle data and compute ATR
        candles = self._get_recent_candles()
        candles['atr'] = self._compute_atr(candles, self.atr_period)

        # Only consider candles *after* the sweep
        candles_after = candles[candles["time"] > sweep_time].head(self.lookahead_bars)
        candles_after_count = len(candles_after)

        if candles_after_count == 0:
            self.logger.info(f"[{self.symbol}] No new candles yet for sweep {sweep['id']}")
            return  # Wait for next run

        rejected = False
        confirm_type = None
        small_candle_counter = 0

        for candle in candles_after.itertuples():
            body_size = abs(candle.close - candle.open)
            atr = candle.atr

            # Strong rejection → instant confirm
            if direction == "buy-side" and candle.close < sweep_level:
                if body_size >= 0.8 * atr:
                    rejected = True
                    confirm_type = "instant"
                    self._mark_sweep_rejected(sweep, candle._asdict())
                    break
                else:
                    small_candle_counter += 1

            elif direction == "sell-side" and candle.close > sweep_level:
                if body_size >= 0.8 * atr:
                    rejected = True
                    confirm_type = "instant"
                    self._mark_sweep_rejected(sweep, candle._asdict())
                    break
                else:
                    small_candle_counter += 1

            # Check invalidation for delayed confirmation
            if small_candle_counter > 0:
                invalidated = False
                if direction == "buy-side" and candle.high > sweep_level:
                    invalidated = True
                elif direction == "sell-side" and candle.low < sweep_level:
                    invalidated = True

                if invalidated:
                    self.logger.info(f"[{self.symbol}] Sweep {sweep['id']} invalidated after small candle.")
                    small_candle_counter = 0
                    break  # Stop evaluating this sweep

                # Delayed confirmation after 2 small candles
                if small_candle_counter >= 2:
                    rejected = True
                    confirm_type = "delayed"
                    self._mark_sweep_rejected(sweep, candle._asdict())
                    break

        # Only mark as failed if enough candles have passed and no rejection confirmed
        if not rejected and candles_after_count >= self.lookahead_bars:
            self._mark_sweep_failed(sweep)
            self.logger.info(
                f"[{self.symbol}] ❌ No confirmed rejection after {candles_after_count} candles → failed."
            )
        else:
            # Not enough candles yet → keep sweep pending for next run
            self.logger.info(
                f"[{self.symbol}] Sweep {sweep['id']} pending, {candles_after_count}/{self.lookahead_bars} candles evaluated."
            )

    # ===================================================
    # DB interactions
    # ===================================================
    def _get_pending_sweeps(self):
        """Fetch all sweeps still pending evaluation."""
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT * FROM strategy_liq_sweep_rejection_sweep_contexts
                WHERE symbol = %s AND timeframe = %s AND status = 'pending'
                ORDER BY candle_time ASC
                """,
                (self.symbol, self.timeframe),
            )
            return cursor.fetchall()

    def _mark_sweep_rejected(self, sweep, candle):
        """Update sweep status and create rejection record."""
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE strategy_liq_sweep_rejection_sweep_contexts
                SET status = 'rejected', rejection_time = %s
                WHERE id = %s
                """,
                (candle["time"], sweep["id"]),
            )

            cursor.execute(
                """
                INSERT INTO strategy_liq_sweep_rejection_rejection_context
                (sweep_id, symbol, timeframe, rejection_time, close_price, direction, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sweep["id"],
                    self.symbol,
                    self.timeframe,
                    candle["time"],
                    candle["close"],
                    sweep["direction"],
                    datetime.utcnow(),
                ),
            )
            conn.commit()

    def _mark_sweep_failed(self, sweep):
        """Mark sweep as failed."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_liq_sweep_rejection_sweep_contexts
                SET status = 'failed'
                WHERE id = %s
                """,
                (sweep["id"],),
            )
            conn.commit()

    # ===================================================
    # Helpers
    # ===================================================
    def _get_recent_candles(self, limit: int = 300):
        """Load recent candles."""
        if self.symbol != "XAUUSDc":
            raise ValueError(f"No candle getter for {self.symbol}")
        df = get_data_m15_xauusdc().tail(limit).reset_index(drop=True)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(None)
        return df

    def _calculate_atr(self, df):
        """Calculate ATR (Average True Range)."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr
    
    def _compute_atr(self, candles, period=14):
        """Compute ATR for volatility-based rejection strength."""
        high = candles['high']
        low = candles['low']
        close = candles['close'].shift(1)
        tr = pd.concat([
            (high - low),
            (high - close).abs(),
            (low - close).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr

