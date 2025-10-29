import pandas as pd
from datetime import datetime
from enum import Enum
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class RetraceStatus(str, Enum):
    PENDING = "pending"      # waiting for price to re-enter FVG
    ACTIVE = "active"        # still within valid scanning range
    MITIGATED = "mitigated"  # price has re-entered the gap
    EXPIRED = "expired"      # too many candles passed (invalid zone)


class RetraceService:
    MAX_CANDLES = 15  # maximum valid candles after FVG created

    def __init__(self):
        self.logger = get_logger("RetraceService")

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run_step(self, symbol: str, timeframe: str):
        """
        Periodically called — polls DB for active FVG zones and checks retrace.
        """
        try:
            fvgs = self._get_pending_fvgs(symbol, timeframe)
            if not fvgs:
                self.logger.info(f"[{symbol}-{timeframe}] No FVG zones waiting for retrace.")
                return

            for fvg in fvgs:
                self._process_fvg(symbol, timeframe, fvg)

        except Exception as e:
            self.logger.exception(f"Error in RetraceService.run_step: {e}")

    # =========================================================
    # CORE LOGIC
    # =========================================================
    def _process_fvg(self, symbol, timeframe, fvg):
        """
        For each FVG zone, check if price has re-entered (mitigated)
        or if it should be expired.
        """
        start_time = fvg["end_time"]
        direction = fvg["direction"]
        gap_low = float(fvg["gap_low"])
        gap_high = float(fvg["gap_high"])

        df = self._get_candles_after(symbol, timeframe, start_time, n=self.MAX_CANDLES)
        if df is None or df.empty:
            self.logger.info(f"⚠️ No candles found after FVG at {start_time}")
            return

        for i, row in df.iterrows():
            time, high, low = row["time"], row["high"], row["low"]

            # --- Bullish retrace ---
            if direction == "bullish" and low <= gap_high:
                self._update_progress(fvg, i + 1)  # ✅ update how many checked
                self._mark_retrace_found(fvg, time)
                return

            # --- Bearish retrace ---
            if direction == "bearish" and high >= gap_low:
                self._update_progress(fvg, i + 1)  # ✅ update how many checked
                self._mark_retrace_found(fvg, time)
                return

            # --- Expired ---
            if i + 1 >= self.MAX_CANDLES:
                self._update_progress(fvg, self.MAX_CANDLES)  # ✅ ensure it's logged as max
                self._mark_expired(fvg)
                return

        # --- Still active ---
        checked = len(df)
        self._update_progress(fvg, checked)
        self.logger.info(
            f"⏳ Still scanning FVG {fvg['id']} | {checked}/{self.MAX_CANDLES} candles checked"
        )

    # =========================================================
    # DATABASE OPS
    # =========================================================
    def _get_pending_fvgs(self, symbol, timeframe):
        """
        Get FVG zones that are waiting for retrace.
        """
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT id, symbol, timeframe, bos_id, direction, gap_low, gap_high,
                   start_time, end_time, created_at,
                   IFNULL(candles_checked, 0) as candles_checked
            FROM strategy_bos_fvg_retrace_fvg_zones
            WHERE symbol = %s AND timeframe = %s
              AND status IN (%s, %s)
            ORDER BY end_time ASC
            """
            cursor.execute(query, (symbol, timeframe, RetraceStatus.PENDING.value, RetraceStatus.ACTIVE.value))
            return cursor.fetchall()

    def _mark_retrace_found(self, fvg, time):
        """Mark FVG as mitigated when price re-enters."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_bos_fvg_retrace_fvg_zones
                SET status = %s, mitigated_at = %s
                WHERE id = %s
                """,
                (RetraceStatus.MITIGATED.value, time, fvg["id"]),
            )
            conn.commit()

        self.logger.info(
            f"✅ Retrace found | {fvg['direction']} | Zone {fvg['gap_low']} - {fvg['gap_high']} | at {time}"
        )

    def _mark_expired(self, fvg):
        """Mark FVG as expired if too many candles passed without retrace."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_bos_fvg_retrace_fvg_zones
                SET status = %s
                WHERE id = %s
                """,
                (RetraceStatus.EXPIRED.value, fvg["id"]),
            )
            conn.commit()

        self.logger.info(
            f"⌛ Expired | {fvg['direction']} | Zone {fvg['gap_low']} - {fvg['gap_high']}"
        )

    def _update_progress(self, fvg, checked):
        """Keep track of how many candles have been scanned so far."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_bos_fvg_retrace_fvg_zones
                SET status = %s, candles_checked = %s
                WHERE id = %s
                """,
                (RetraceStatus.ACTIVE.value, checked, fvg["id"]),
            )
            conn.commit()

    # =========================================================
    # DATA HELPERS
    # =========================================================
    def _get_candles_after(self, symbol, timeframe, start_time, n=15):
        """Return up to n candles after FVG was created."""
        if symbol == "XAUUSDc" and timeframe == "M15":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No data source for {symbol}-{timeframe}")

        # Normalize timestamps
        if pd.api.types.is_integer_dtype(df["time"]):
            df["time"] = pd.to_datetime(df["time"], unit="s")
        else:
            df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)

        # Convert start_time
        if isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time)
        elif isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)

        df = df[df["time"] > start_time].head(n).reset_index(drop=True)
        return df if not df.empty else None
