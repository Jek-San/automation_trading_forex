from datetime import datetime
from decimal import Decimal
from src.utils.logger import get_logger
from src.core.db.connection import get_connection

class MajorWaveFibTradeSetupService:
    """
    Fibonacci Trade Setup Service
    - Uses fib setups from major wave service
    - Creates trade setups (entry, sl, tp) based on fixed retracement levels
    """

    def __init__(self):
        self.logger = get_logger("SwingPoint_MajorWaveFibTradeSetupService")

    # ===================================================
    # Public Entrypoint
    # ===================================================
    def run_step(self, symbol: str, timeframe: str):
        try:
            setups = self._get_unprocessed_fib_setups(symbol, timeframe)
            if not setups:
                self.logger.info(f"No new Fibonacci setups to process for {symbol}-{timeframe}")
                return

            for setup in setups:
                entry, sl, tp = self._calculate_levels(setup)
                if not entry or not sl or not tp:
                    self.logger.warning(f"Invalid fib values for setup {setup['id']}, skipping.")
                    self._mark_fib_processed(setup["id"])
                    continue

                self._save_trade_setup(symbol, timeframe, setup, entry, sl, tp, setup['last_swing_discovered_at'])
                self._mark_fib_processed(setup["id"])

        except Exception as e:
            self.logger.exception(f"Error in FibTradeSetupService.run_step: {e}")

    # ===================================================
    # Helpers
    # ===================================================
    def _get_unprocessed_fib_setups(self, symbol, timeframe):
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT id, trend, fib_low, fib_high, last_swing_candle_time, last_swing_discovered_at
                FROM strategy_swing_point_fib_setup_major_wave
                WHERE symbol=%s AND timeframe=%s
                  AND processed=0
                ORDER BY last_swing_discovered_at ASC
            """, (symbol, timeframe))
            setups = cur.fetchall()
            return setups

    def _calculate_levels(self, setup):
        """
        Calculate entry (61.8%), SL (100%), and TP (0%) based on fib levels.
        For bullish trend:
            entry = fib_high - (fib_high - fib_low) * 0.618
            sl = fib_low
            tp = fib_high
        For bearish trend:
            entry = fib_low + (fib_high - fib_low) * 0.618
            sl = fib_high
            tp = fib_low
        """
        fib_low = Decimal(setup["fib_low"])
        fib_high = Decimal(setup["fib_high"])
        trend = setup["trend"]

        if trend == "bullish":
            entry = fib_high - (fib_high - fib_low) * Decimal("0.618")
            sl = fib_low
            tp = fib_high
        elif trend == "bearish":
            entry = fib_low + (fib_high - fib_low) * Decimal("0.618")
            sl = fib_high
            tp = fib_low
        else:
            return None, None, None

        return entry, sl, tp

    def _save_trade_setup(self, symbol, timeframe, fib_setup, entry, sl, tp, last_swing_discovered_at):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO strategy_swing_point_fib_trade_setup
                (symbol, timeframe, fib_setup_id, trend, entry_price, sl_price, tp_price, fib_low, fib_high, last_swing_discovered_at, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                symbol,
                timeframe,
                fib_setup["id"],
                fib_setup["trend"],
                entry,
                sl,
                tp,
                fib_setup["fib_low"],
                fib_setup["fib_high"],
                last_swing_discovered_at,
                datetime.utcnow(),
            ))
            conn.commit()

            self.logger.info(f"Created Fib Trade Setup for {symbol}-{timeframe}: "
                             f"{fib_setup['trend']} | Entry={entry} SL={sl} TP={tp}")

    def _mark_fib_processed(self, fib_id):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE strategy_swing_point_fib_setup_major_wave
                SET processed=1
                WHERE id=%s
            """, (fib_id,))
            conn.commit()
