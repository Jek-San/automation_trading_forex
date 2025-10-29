import pandas as pd
from datetime import datetime, timezone
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc

class SetupService:
    """
    Generates trade setups after confirmed rejection.
    Rules:
      - Entry: close of rejection candle
      - SL: sweep extreme ± ATR (from context)
      - TP1: RR-based (1.5x or 2x by default)
      - TP2: optional context extreme (recent_high/recent_low)
    """

    def __init__(self, symbol: str, timeframe: str = "M15", atr_period: int = 14, rr: float = 2.0):
        self.symbol = symbol
        self.timeframe = timeframe
        self.atr_period = atr_period
        self.rr = rr
        self.logger = get_logger("core.strategies.liquidity_sweep_rejection.setup_service_rr")

    # ===================================================
    # Entry point
    # ===================================================
    def run_step(self):
        confirmed_rejections = self._get_confirmed_rejections()
        if not confirmed_rejections:
            self.logger.info(f"[{self.symbol}] No confirmed rejections found.")
            return

        for rej in confirmed_rejections:
            self._generate_setup(rej)

    # ===================================================
    # Core logic
    # ===================================================
    def _generate_setup(self, rejection):
        direction = rejection["direction"]
        sweep_level = float(rejection["sweep_level"])
        rejection_time = rejection["rejection_time"]

        candles = self._get_recent_candles()
        candles['atr'] = self._compute_atr(candles, self.atr_period)

        # Rejection candle
        rej_candle = candles[candles["time"] == rejection_time].iloc[0]
        entry = rej_candle['close']
        atr = rej_candle['atr']

        # Fetch context extremes
        context = self._get_latest_context()
        recent_high = context["recent_high"]
        recent_low = context["recent_low"]

        # SL = sweep extreme ± ATR
        if direction == "buy-side":
            sl = sweep_level - atr
            distance_to_sl = entry - sl
            tp1 = entry + distance_to_sl * self.rr
            tp2 = recent_high  # optional extended target
        else:  # sell-side
            sl = sweep_level + atr
            distance_to_sl = sl - entry
            tp1 = entry - distance_to_sl * self.rr
            tp2 = recent_low  # optional extended target

        # Save setup to DB
        self._save_setup(rejection, entry, sl, tp1, tp2)
        self.logger.info(
            f"[{self.symbol}] ✅ Setup generated | Entry={entry}, SL={sl}, TP1={tp1}, TP2={tp2}, RR={self.rr}"
        )

    # ===================================================
    # DB & helpers
    # ===================================================
    def _get_confirmed_rejections(self):
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT r.*, s.sweep_level
                FROM strategy_liq_sweep_rejection_rejection_context r
                JOIN strategy_liq_sweep_rejection_sweep_contexts s
                  ON r.sweep_id = s.id
                WHERE r.setup_generated = FALSE
                  AND s.symbol = %s
                  AND r.symbol = %s
                """,
                (self.symbol, self.symbol)
            )
            return cursor.fetchall()

    def _get_latest_context(self):
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT recent_high, recent_low, pdh, pdl
                FROM strategy_liq_sweep_rejection_market_contexts
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (self.symbol,)
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"No active context for symbol {self.symbol}")
            return row

    def _save_setup(self, rejection, entry, sl, tp1, tp2):
        with get_connection() as conn:
            created_at_utc = datetime.now(timezone.utc)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO strategy_liq_sweep_rejection_setups
                (sweep_id, rejection_id, symbol, timeframe, entry, sl, tp1, tp2, rr, created_at, created_at_utc)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    rejection["sweep_id"],
                    rejection["id"],
                    self.symbol,
                    self.timeframe,
                    entry,
                    sl,
                    tp1,
                    tp2,
                    self.rr,
                    datetime.utcnow(),
                    created_at_utc
                ),
            )
            cursor.execute(
                """
                UPDATE strategy_liq_sweep_rejection_rejection_context
                SET setup_generated = TRUE
                WHERE id = %s
                """,
                (rejection["id"],)
            )
            conn.commit()

    def _get_recent_candles(self, limit=300):
        df = get_data_m15_xauusdc().tail(limit).reset_index(drop=True)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(None)
        return df

    def _compute_atr(self, candles, period=14):
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
