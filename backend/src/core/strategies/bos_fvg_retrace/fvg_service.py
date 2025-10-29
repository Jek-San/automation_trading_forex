import pandas as pd
from datetime import datetime
from enum import Enum
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class FVGStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    FOUND = "found"
    NOT_FOUND = "not_found"


class FVGService:
    MAX_CANDLES = 15   # maximum candle distance after BOS
    MIN_CANDLES = 3    # minimum candles before starting to check

    def __init__(self):
        self.logger = get_logger("FVGService")

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def run_step(self, symbol: str, timeframe: str):
        """
        Step function that processes BOS events incrementally.
        """
        try:
            bos_events = self._get_pending_bos(symbol, timeframe)
            if not bos_events:
                self.logger.info(f"[{symbol}-{timeframe}] No BOS waiting for FVG.")
                return

            for bos in bos_events:
                self._process_bos_event(symbol, timeframe, bos)

        except Exception as e:
            self.logger.exception(f"Error in FVGService.run_step: {e}")

    # =========================================================
    # INTERNAL LOGIC
    # =========================================================
    def _process_bos_event(self, symbol, timeframe, bos_event):
        """
        Progressively check if an FVG forms after a BOS event.
        Keeps scanning until MAX_CANDLES are reached.
        """
        bos_time = bos_event["candle_time"]
        direction = bos_event["direction"]
        prev_checked = bos_event.get("candles_checked", 0)

        # Load candles
        df = self._get_candles_after(symbol, timeframe, bos_time, n=self.MAX_CANDLES)
        if df is None or df.empty:
            self.logger.info(f"⚠️ No candles found after BOS at {bos_time}")
            return

        available = len(df)
        self.logger.info(
            f"🔍 BOS {bos_event['id']} | {available} candles available (previously checked {prev_checked})"
        )

        # Not enough candles yet
        if available < self.MIN_CANDLES:
            self.logger.info(f"⏳ Waiting for more candles after BOS at {bos_time}")
            return

        # Scan candles
        candles_to_check = df.head(min(available, self.MAX_CANDLES))
        fvg = self._detect_fvg(candles_to_check, direction)

        if fvg:
            # ✅ Found FVG
            self._save_fvg_event(symbol, timeframe, bos_event, fvg)
            self._update_bos_status(bos_event["id"], FVGStatus.FOUND)
            self.logger.info(
                f"✅ FVG found after BOS ({direction}) at {fvg['start_time']} "
                f"→ gap {fvg['gap_low']} - {fvg['gap_high']}"
            )
            return

        # ❌ No FVG found yet
        new_checked = min(available, self.MAX_CANDLES)
        if new_checked >= self.MAX_CANDLES:
            self._update_bos_status(bos_event["id"], FVGStatus.NOT_FOUND)
            self.logger.info(
                f"❌ No FVG found after {self.MAX_CANDLES} candles for BOS at {bos_time}. Marked not_found."
            )
        else:
            # Still scanning
            self._update_progress(bos_event["id"], new_checked)
            self.logger.info(
                f"🔄 Still scanning BOS {bos_event['id']} → {new_checked}/{self.MAX_CANDLES} candles checked"
            )

    # =========================================================
    # FVG DETECTION
    # =========================================================
    def _detect_fvg(self, df: pd.DataFrame, direction: str):
        """
        Detect FVG pattern:
          - Bullish: c0.high < c2.low
          - Bearish: c0.low > c2.high
        """
        for i in range(2, len(df)):
            c0, c1, c2 = df.iloc[i - 2], df.iloc[i - 1], df.iloc[i]
            if direction == "bullish" and c0["high"] < c2["low"]:
                return {
                    "direction": "bullish",
                    "gap_low": float(c0["high"]),
                    "gap_high": float(c2["low"]),
                    "start_time": c0["time"],
                    "end_time": c2["time"],
                }
            elif direction == "bearish" and c0["low"] > c2["high"]:
                return {
                    "direction": "bearish",
                    "gap_low": float(c2["high"]),
                    "gap_high": float(c0["low"]),
                    "start_time": c0["time"],
                    "end_time": c2["time"],
                }
        return None

    # =========================================================
    # DATABASE OPS
    # =========================================================
    def _get_pending_bos(self, symbol, timeframe):
        """
        Get BOS that are still waiting for FVG scan or are scanning.
        """
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT id, symbol, timeframe, type, direction, broken_price, candle_time,
                   processed_by_fvg, IFNULL(candles_checked, 0) as candles_checked
            FROM strategy_bos_fvg_retrace_structure_events
            WHERE symbol = %s AND timeframe = %s
              AND processed_by_fvg IN (%s, %s)
            ORDER BY candle_time ASC
            """
            cursor.execute(query, (symbol, timeframe, FVGStatus.PENDING, FVGStatus.SCANNING))
            return cursor.fetchall()

    def _update_bos_status(self, bos_id, status: FVGStatus):
        """Mark BOS as found/not_found/pending/scanning"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_bos_fvg_retrace_structure_events
                SET processed_by_fvg = %s
                WHERE id = %s
                """,
                (status.value, bos_id),
            )
            conn.commit()

    def _update_progress(self, bos_id, candle_count):
        """Update BOS progress (scanning stage)"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE strategy_bos_fvg_retrace_structure_events
                SET processed_by_fvg = %s, candles_checked = %s
                WHERE id = %s
                """,
                (FVGStatus.SCANNING.value, candle_count, bos_id),
            )
            conn.commit()

    def _save_fvg_event(self, symbol, timeframe, bos_event, fvg):
        """Insert new FVG zone"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO strategy_bos_fvg_retrace_fvg_zones
                (symbol, timeframe, bos_id, direction, gap_low, gap_high, start_time, end_time, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    symbol,
                    timeframe,
                    bos_event["id"],
                    fvg["direction"],
                    fvg["gap_low"],
                    fvg["gap_high"],
                    fvg["start_time"],
                    fvg["end_time"],
                    datetime.utcnow(),
                ),
            )
            conn.commit()

    # =========================================================
    # DATA HELPERS
    # =========================================================
    def _get_candles_after(self, symbol, timeframe, start_time, n=10):
        """Return up to n candles after BOS candle_time"""
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

        # Convert start_time type
        if isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time)
        elif isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)

        df = df[df["time"] > start_time].head(n + 2).reset_index(drop=True)
        return df if not df.empty else None
