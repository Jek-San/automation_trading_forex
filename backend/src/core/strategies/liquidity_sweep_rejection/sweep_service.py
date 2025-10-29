# src/core/strategies/liquidity_sweep/sweep_service.py

import pandas as pd
from datetime import datetime, timezone
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class SweepService:
    """
    Detects liquidity sweeps based on the latest confirmed context.

    A sweep is defined as:
    - Buy-side: candle.high > context.recent_high
    - Sell-side: candle.low < context.recent_low

    This service:
    - Fetches latest active market context (bias, swing high/low)
    - Compares the latest closed candle with those levels
    - Records a sweep event (buy/sell side) when breached
    """

    def __init__(self, symbol: str, timeframe: str = "M15"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.logger = get_logger("core.strategies.liquidity_sweep.sweep_service")

    # ===================================================
    # Public Entry Point
    # ===================================================
    def run_step(self):
        """Run this at each new candle close."""
        try:
            candles = self._get_recent_candles()
            candles["time"] = candles["time"].apply(self._unix_to_datetime)
            if candles is None or candles.empty:
                self.logger.warning(f"No candle data for {self.symbol}.")
                return

            context = self._get_latest_active_context()
            if context is None:
                self.logger.warning(f"No active context found for {self.symbol}.")
                return

            # -------------------------------------------------------
            # Determine last processed time (fallback to context.created_at)
            # -------------------------------------------------------
            last_checked_time = context.get("last_process_checking_sweep") or context["created_at"]
            new_candles = candles[candles["time"] > pd.Timestamp(last_checked_time)]

            if new_candles.empty:
                self.logger.info("No new candles to process.")
                return

            # -------------------------------------------------------
            # Loop through each new candle sequentially
            # -------------------------------------------------------
            for _, candle in new_candles.iterrows():
                sweep_direction = self._check_for_sweep(context, candle)

                if sweep_direction:
                    self._record_sweep(context, candle, sweep_direction)
                    self._mark_context_swept(context["id"], sweep_direction)
                    if sweep_direction == "buy-side":
                        context["is_swept_high"] = True
                    elif sweep_direction == "sell-side":
                        context["is_swept_low"] = True
                    self.logger.info(
                        f"{self.symbol} {sweep_direction} sweep detected at {candle['time']}"
                    )

                # Always update the last checked candle time
                self._update_last_processed_time(context["id"], candle["time"])

        except Exception as e:
            self.logger.exception(f"Error in SweepService.run_step: {e}")

    # ===================================================
    # Internal Logic
    # ===================================================

    def _update_last_processed_time(self, context_id, candle_time):
        """Store the last candle time that was checked for sweep detection."""
        # If already datetime or Timestamp, just use it directly
        if isinstance(candle_time, (datetime, pd.Timestamp)):
            formatted_time = candle_time
        else:
            formatted_time = self._unix_to_datetime(candle_time)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_liq_sweep_rejection_market_contexts
                SET last_process_checking_sweep = %s
                WHERE id = %s
                """,
                (formatted_time, context_id),
            )
            conn.commit()
    def _check_for_sweep(self, context, candle):
        """Check if current candle swept recent highs/lows."""
        recent_high = context["recent_high"]
        recent_low = context["recent_low"]
        if bool(context.get("is_swept_high")) and bool(context.get("is_swept_low")):
            return None

        # detect new sweep
        if candle["high"] > recent_high and not context.get("is_swept_high"):
            return "buy-side"
        elif candle["low"] < recent_low and not context.get("is_swept_low"):
            return "sell-side"
        return None
    def _mark_context_swept(self, context_id, direction):
        with get_connection() as conn:
            cursor = conn.cursor()
            if direction == "buy-side":
                cursor.execute(
                    "UPDATE strategy_liq_sweep_rejection_market_contexts SET is_swept_high = TRUE WHERE id = %s",
                    (context_id,),
                )
            elif direction == "sell-side":
                cursor.execute(
                    "UPDATE strategy_liq_sweep_rejection_market_contexts SET is_swept_low = TRUE WHERE id = %s",
                    (context_id,),
                )
            conn.commit()



    # ===================================================
    # Database Access
    # ===================================================
    def _get_latest_active_context(self):
        """Fetch the latest active context from DB."""
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT * FROM strategy_liq_sweep_rejection_market_contexts
                WHERE symbol = %s AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
                """,
                (self.symbol,)
            )
            row = cursor.fetchone()
            self.logger.info(f"Market context: {row}")
            return pd.Series(row) if row else None

    def _record_sweep(self, context, candle, direction):
        """Insert detailed sweep record."""
        with get_connection() as conn:
            cur = conn.cursor()

            sweep_level = (
                context["recent_high"] if direction == "buy-side" else context["recent_low"]
            )
            candle_time = self._unix_to_datetime(candle["time"])

            cur.execute(
                """
                INSERT INTO strategy_liq_sweep_rejection_sweep_contexts
                (context_id, symbol, timeframe, direction, sweep_level,
                candle_time, candle_open, candle_high, candle_low, candle_close,
                status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    context["id"],
                    self.symbol,
                    self.timeframe,
                    direction,
                    sweep_level,
                    candle_time,
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    "pending",
                    datetime.utcnow(),
                ),
            )
            conn.commit()

    # ===================================================
    # Data Getter
    # ===================================================
    def _get_recent_candles(self, limit=300):
        """Fetch latest candles for this symbol/timeframe."""
        if self.symbol != "XAUUSDc":
            raise ValueError(f"No data getter for {self.symbol}")
        if self.timeframe == "M15":
            # print("get_data_m15_xauusdc")
            # print(get_data_m15_xauusdc().tail(5).reset_index(drop=True))
            return get_data_m15_xauusdc().tail(limit).reset_index(drop=True)
        else:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

    from datetime import datetime, timezone


    @staticmethod
    def _unix_to_datetime(ts):
        if ts is None:
            return None
        if isinstance(ts, (datetime, pd.Timestamp)):
            return ts.replace(tzinfo=None)
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
