# src/core/strategies/swing_point_fib/major_wave_fib_service.py

from datetime import datetime
from decimal import Decimal
from src.utils.logger import get_logger
from src.core.db.connection import get_connection

class MajorWaveFibService:
    """
    Major Wave Fibonacci Service
    - Uses last 9 swings to detect trend and define Fibonacci zones
    - Avoids reprocessing the same last swing
    """
    def __init__(self, window_size=9):
        self.window_size = window_size
        self.logger = get_logger("SwingPoint_MajorWaveFibService")

    # ===================================================
    # Public entrypoint
    # ===================================================
    def run_step(self, symbol: str, timeframe: str):
        try:
            swings = self._get_recent_swings(symbol, timeframe)
            if len(swings) < self.window_size:
                self.logger.info("Not enough swings to process.")
                return

            # Sliding window over swings
            for start in range(len(swings) - self.window_size + 1):
                window = swings[start:start + self.window_size]

                last_swing = window[-1]
                if last_swing["processed"]:
                    continue  # skip already processed last swing

                trend = self._detect_trend(window)
                if trend == "neutral":
                    self.logger.info(f"Window starting at {window[0]['candle_time']} is neutral, skipping.")
                    self._mark_swing_processed(last_swing["id"])
                    continue

                fib_low, fib_high = self._pick_fib_points(window, trend)

                self._save_fib_setup(symbol, timeframe, trend, fib_low, fib_high, last_swing["id"],last_swing["candle_time"],last_swing['discovered_at'])
                self._mark_swing_processed(last_swing["id"])

        except Exception as e:
            self.logger.exception(f"Error in MajorWaveFibService.run_step: {e}")

    # ===================================================
    # Helpers
    # ===================================================
    def _get_recent_swings(self, symbol, timeframe):
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, swing_type, price, candle_time, processed, discovered_at
                FROM strategy_swing_point
                WHERE symbol=%s AND timeframe=%s
                ORDER BY candle_time ASC
            """, (symbol, timeframe))
            swings = cursor.fetchall()
            # Ensure boolean
            for s in swings:
                s["processed"] = bool(s["processed"])
            return swings

    def _detect_trend(self, window):
        """
        Determine trend: bullish, bearish, or neutral
        - bullish: mostly higher highs and higher lows
        - bearish: mostly lower highs and lower lows
        """
        highs = [s["price"] for s in window if s["swing_type"] == "high"]
        lows = [s["price"] for s in window if s["swing_type"] == "low"]

        if len(highs) < 2 or len(lows) < 2:
            return "neutral"

        # Compare first vs last swing in window
        if highs[-1] > highs[0] and lows[-1] > lows[0]:
            return "bullish"
        elif highs[-1] < highs[0] and lows[-1] < lows[0]:
            return "bearish"
        else:
            return "neutral"

    def _pick_fib_points(self, window, trend):
        """
        Pick Fibonacci high/low based on trend
        """
        highs = [s["price"] for s in window if s["swing_type"] == "high"]
        lows = [s["price"] for s in window if s["swing_type"] == "low"]

        if trend == "bullish":
            fib_low = min(lows)
            fib_high = max(highs)
        elif trend == "bearish":
            fib_low = min(lows)
            fib_high = max(highs)
        else:
            fib_low, fib_high = None, None
        return Decimal(fib_low), Decimal(fib_high)

    def _save_fib_setup(self, symbol, timeframe, trend, fib_low, fib_high, last_swing_id, last_swing_time, last_swing_discovered_at):
        """
        Save Fibonacci setup in DB
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO strategy_swing_point_fib_setup_major_wave
                (symbol, timeframe, trend, fib_low, fib_high, last_swing_id,last_swing_candle_time, last_swing_discovered_at, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (symbol, timeframe, trend, fib_low, fib_high, last_swing_id,last_swing_time, last_swing_discovered_at, datetime.utcnow()))
            conn.commit()
            self.logger.info(f"Saved Fibonacci setup: {trend} {fib_low}-{fib_high}")

    def _mark_swing_processed(self, swing_id):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE strategy_swing_point
                SET processed=1
                WHERE id=%s
            """, (swing_id,))
            conn.commit()
