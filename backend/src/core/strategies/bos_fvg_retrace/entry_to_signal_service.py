import pandas as pd
from datetime import datetime, date
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.signals import insert_signal
from src.core.strategies.bos_fvg_retrace.bias_service import BiasService


class EntryToSignalService:
    """
    Converts today's ATR-based retrace trade entries into main signal format
    and inserts them into the trading_signals table using insert_signal().
    """

    def __init__(self):
        self.logger = get_logger("EntryToSignalService")
        self.bias_service = BiasService()

    # =========================================================
    # MAIN RUN
    # =========================================================
    def run_step(self, symbol: str, timeframe: str):
        """
        Convert retrace trade entries (for today only) into main bot signals.
        """
        try:
            trades = self._get_today_trades(symbol, timeframe)
            if not trades:
                self.logger.info(f"[{symbol}-{timeframe}] No new trades to convert today.")
                return

            for trade in trades:
                bias = self.bias_service.get_current_session_bias("XAUUSDc")
                self._convert_to_signal(trade)
                # if bias['bias'] == trade['direction']:
                #     self._convert_to_signal(trade)
                # else:
                #     with get_connection() as conn:
                #         cursor = conn.cursor()
                #         cursor.execute("""
                #             UPDATE strategy_bos_fvg_retrace_trades
                #             SET converted_to_signal = 1
                #             WHERE id = %s
                #         """, (trade["id"],))
                #         conn.commit()
                #     self.logger.info(f"❌ Skipping trade #{trade['id']} (bias mismatch)")

        except Exception as e:
            self.logger.exception(f"Error in EntryToSignalService.run_step: {e}")

    # =========================================================
    # CORE LOGIC
    # =========================================================
    def _convert_to_signal(self, trade):
        """
        Convert a retrace trade row into a standard signal and insert to DB.
        """
        try:
            action = "buy" if trade["direction"] == "bullish" else "sell"

            signal = {
                "instrument": trade["symbol"],
                "action": action,
                "range1": float(trade["entry_price"]),
                "range2": float(trade["entry_price"]),
                "tp1": float(trade["take_profit"]),
                "tp2": float(trade["take_profit"]),
                "sl": float(trade["stop_loss"]),
                "comment": "BOS FVG Retrace (ATR-based)",
                "message": f"Entry from retrace trade ID {trade['id']}. Expired 0.1 days",
            }

            insert_signal(signal)

            # ✅ Mark this trade as converted (optional safety flag)
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE strategy_bos_fvg_retrace_trades
                    SET converted_to_signal = 1
                    WHERE id = %s
                """, (trade["id"],))
                conn.commit()

            self.logger.info(
                f"✅ Converted trade #{trade['id']} ({action.upper()}) to signal | Entry={trade['entry_price']:.2f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Failed to convert trade #{trade['id']}: {e}")

    # =========================================================
    # DATABASE OPS
    # =========================================================
    def _get_today_trades(self, symbol, timeframe):
        """
        Fetch retrace trades from today that haven't been converted yet.
        """
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, symbol, timeframe, direction,
                       entry_price, stop_loss, take_profit, mitigated_at
                FROM strategy_bos_fvg_retrace_trades
                WHERE symbol = %s
                  AND timeframe = %s
                  AND DATE(mitigated_at) = CURDATE()
                  AND (converted_to_signal IS NULL OR converted_to_signal = 0)
                ORDER BY mitigated_at ASC
            """, (symbol, timeframe))
            return cursor.fetchall()
