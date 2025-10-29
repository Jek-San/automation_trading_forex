from datetime import datetime
from decimal import Decimal
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.signals import insert_signal
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class MajorWaveFibSignalService:
    """
    Converts unprocessed Fibonacci trade setups into main signal format.
    - Simulates candles from discovery date to current
    - Converts to standard bot signal format like EntryToSignalService
    """

    def __init__(self):
        self.logger = get_logger("SwingPoint_MajorWaveFibSignalService")

    # ===================================================
    # MAIN RUN
    # ===================================================
    def run_step(self, symbol: str, timeframe: str):
        setups = self._get_unprocessed_trade_setups(symbol, timeframe)
        if not setups:
            self.logger.info(f"No trade setups to process for {symbol}-{timeframe}")
            return

        df_candles = self._prepare_candles(self._get_recent_candles(symbol, timeframe))

        for setup in setups:
            entry = Decimal(setup["entry_price"])
            trend = setup["trend"]

            # Filter candles after discovery
            df_filtered = df_candles[df_candles["timestamp"] >= setup["last_swing_discovered_at"]]

            # Skip if entry already hit
            # if self._entry_already_hit(df_filtered, entry, trend):
            #     self.logger.info(f"Entry already hit for setup {setup['id']}, marking processed")
            #     self._mark_trade_setup_processed(setup["id"])
            #     continue

            # Convert to standard bot signal
            self._convert_to_signal(setup)

            # Mark setup as processed
            self._mark_trade_setup_processed(setup["id"])

    # ===================================================
    # CONVERT TO SIGNAL
    # ===================================================
    def _convert_to_signal(self, setup):
        try:
            action = "buy" if setup["trend"] == "bullish" else "sell"

            signal = {
                "instrument": setup["symbol"],
                "action": action,
                "range1": float(setup["entry_price"]),
                "range2": float(setup["entry_price"]),
                "tp1": float(setup["tp_price"]),
                "tp2": float(setup["tp_price"]),
                "sl": float(setup["sl_price"]),
                "comment": "Major Wave Fib",
                "message": f"Entry from Fib trade setup ID {setup['id']}.",
            }

            insert_signal(signal)
            self.logger.info(f"✅ Converted Fib setup #{setup['id']} to signal | {action.upper()} Entry={setup['entry_price']:.2f}")

        except Exception as e:
            self.logger.error(f"❌ Failed to convert Fib setup #{setup['id']}: {e}")

    # ===================================================
    # DATABASE OPS
    # ===================================================
    def _get_unprocessed_trade_setups(self, symbol, timeframe):
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT *
                FROM strategy_swing_point_fib_trade_setup
                WHERE symbol=%s AND timeframe=%s AND processed=0
                ORDER BY last_swing_discovered_at ASC
                
            """, (symbol, timeframe))
            return cur.fetchall()

    def _mark_trade_setup_processed(self, setup_id):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE strategy_swing_point_fib_trade_setup
                SET processed=1
                WHERE id=%s
            """, (setup_id,))
            conn.commit()

    # ===================================================
    # CANDLES
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

    def _entry_already_hit(self, df, entry, trend):
        entry_f = float(entry)
        if trend == "bullish":
            return (df["high"].astype(float) >= entry_f).any()
        elif trend == "bearish":
            return (df["low"].astype(float) <= entry_f).any()
        return False
