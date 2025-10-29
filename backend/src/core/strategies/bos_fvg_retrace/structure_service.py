# src/core/strategies/bos_fvg_retrace/structure_service.py

import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc

class StructureService:
    def __init__(self, mode="loose"):
        """
        mode = 'loose' or 'strict'
        loose  → record BOS when candle close breaks previous candle high/low
        strict → record BOS when close breaks confirmed swing high/low
        """
        self.mode = mode
        self.logger = get_logger("StructureService")

    # ===================================================
    # Public entrypoint
    # ===================================================
    def run_step(self, symbol: str, timeframe: str):
        try:
            df = self._get_recent_candles(symbol, timeframe)
            if df is None or len(df) < 10:
                return


            df = self._prepare_candles(df)

            if self.mode == "loose":
                bos_events = self._detect_bos_loose(df)
            else:
                bos_events = self._detect_bos_strict(df)

            self._save_new_bos(symbol, timeframe, bos_events)

        except Exception as e:
            self.logger.exception(f"Error in StructureService.run_step: {e}")

    # ===================================================
    # Core BOS Logic
    # ===================================================

    def _detect_bos_loose(self, df: pd.DataFrame):
        """Detect BOS instantly when candle closes beyond previous high/low"""
        bos_events = []

        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]

            # Bullish BOS: close breaks previous high
            if curr["close"] > prev["high"]:
                bos_events.append({
                    "type": "BOS_HIGH",
                    "direction": "bullish",
                    "broken_price": float(prev["high"]),
                    "candle_time": curr["timestamp"],
                })

            # Bearish BOS: close breaks previous low
            elif curr["close"] < prev["low"]:
                bos_events.append({
                    "type": "BOS_LOW",
                    "direction": "bearish",
                    "broken_price": float(prev["low"]),
                    "candle_time": curr["timestamp"],
                })

        self.logger.info(f"[Loose Mode] Found {len(bos_events)} BOS events")
        return bos_events

    def _detect_bos_strict(self, df: pd.DataFrame, window_size=3):
        bos_events = []

        highs, lows = df["high"].values, df["low"].values
        timestamps = df["timestamp"].values

        # Identify swing highs/lows
        swing_highs = []
        swing_lows = []
        for i in range(window_size, len(df) - window_size):
            if highs[i] == max(highs[i - window_size:i + window_size + 1]):
                swing_highs.append((i, highs[i]))
                self.logger.info(f"high :{df.iloc[i]['high'], df.iloc[i]['timestamp']}")
            if lows[i] == min(lows[i - window_size:i + window_size + 1]):
                swing_lows.append((i, lows[i]))
                self.logger.info(f"low {df.iloc[i]['low'], df.iloc[i]['timestamp']}")
        
        # ===== Structure tracking =====
        structure_state = None
        last_higher_low = None
        last_lower_high = None

        for i in range(window_size, len(df)):
            curr_close = df.iloc[i]["close"]
            curr_time = df.iloc[i]["timestamp"]

            # 1️⃣ Establish initial direction if none
            if structure_state is None and len(swing_highs) > 1 and len(swing_lows) > 1:
                if swing_highs[1][1] > swing_highs[0][1] and swing_lows[1][1] > swing_lows[0][1]:
                    structure_state = "bullish"
                    last_higher_low = swing_lows[1][1]
                    self.logger.info(f"Initial structure: {structure_state} and last higher low: {last_higher_low}")
                elif swing_highs[1][1] < swing_highs[0][1] and swing_lows[1][1] < swing_lows[0][1]:
                    structure_state = "bearish"
                    last_lower_high = swing_highs[1][1]
                    self.logger.info(f"Initial structure: {structure_state} and last lower high: {last_lower_high}")
                continue  # move on to next candle

            # 2️⃣ If structure is bullish → look for break below last higher low
            if structure_state == "bullish" and last_higher_low:
                if curr_close < last_higher_low:
                    bos_events.append({
                        "type": "BOS_LOW",
                        "direction": "bearish",
                        "broken_price": float(last_higher_low),
                        "candle_time": curr_time,
                    })
                    # flip structure
                    structure_state = "bearish"
                    # set new protected high (most recent swing high before this break)
                    recent_highs = [h for (idx, h) in swing_highs if idx < i]
                    if recent_highs:
                        last_lower_high = recent_highs[-1]

            # 3️⃣ If structure is bearish → look for break above last lower high
            elif structure_state == "bearish" and last_lower_high:
                if curr_close > last_lower_high:
                    bos_events.append({
                        "type": "BOS_HIGH",
                        "direction": "bullish",
                        "broken_price": float(last_lower_high),
                        "candle_time": curr_time,
                    })
                    # flip structure
                    structure_state = "bullish"
                    # set new protected low (most recent swing low before this break)
                    recent_lows = [l for (idx, l) in swing_lows if idx < i]
                    if recent_lows:
                        last_higher_low = recent_lows[-1]

        self.logger.info(f"[Strict Mode Improved] Found {len(bos_events)} BOS events")
        return bos_events

    # ===================================================
    # Database save
    # ===================================================

    def _save_new_bos(self, symbol, timeframe, bos_events):
        if not bos_events:
            return

        with get_connection() as conn:
            cursor = conn.cursor()

            for bos in bos_events:
                # Check if already exists
                cursor.execute(
                    """
                    SELECT id FROM strategy_bos_fvg_retrace_structure_events
                    WHERE symbol=%s AND timeframe=%s AND type=%s AND candle_time=%s
                    """,
                    (symbol, timeframe, bos["type"], bos["candle_time"]),
                )
                if cursor.fetchone():
                    continue  # Skip duplicate

                # Insert new BOS
                cursor.execute(
                    """
                    INSERT INTO strategy_bos_fvg_retrace_structure_events
                    (symbol, timeframe, type, direction, broken_price, candle_time, created_at, processed_by_fvg)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, "pending")
                    """,
                    (
                        symbol,
                        timeframe,
                        bos["type"],
                        bos["direction"],
                        bos["broken_price"],
                        bos["candle_time"],
                        datetime.utcnow(),
                    ),
                )

            conn.commit()
            self.logger.info(f"Inserted new BOS (deduped) into DB")

    # ===================================================
    # Helpers
    # ===================================================

    def _get_recent_candles(self, symbol, timeframe):
        if symbol == "XAUUSDc" and timeframe == "M15":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No data function for {symbol}-{timeframe}")
        return df.tail(300).reset_index(drop=True)

    def _prepare_candles(self, df):
        if "timestamp" not in df.columns:
            if "time" in df.columns:
                df["timestamp"] = df["time"].apply(lambda x: datetime.utcfromtimestamp(int(x)))
            else:
                df["timestamp"] = df.iloc[:, 0].apply(lambda x: datetime.utcfromtimestamp(int(x)))
        df["timestamp"] = df["timestamp"].apply(lambda x: x.replace(microsecond=0))
        return df
