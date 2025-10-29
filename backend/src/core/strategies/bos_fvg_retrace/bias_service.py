# src/core/strategies/bos_fvg_retrace/bias_service.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from scipy import stats
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class BiasService:
    """
    Compute adaptive market bias (Z-test + Bayesian) per session.
    Reference time: BOS candle_time (UTC).
    """

    def __init__(self):
        self.logger = get_logger("BiasService")
        self.sessions = {
            "Asia": {"start": 0, "end": 8},      # UTC hours
            "London": {"start": 8, "end": 16},
            "NewYork": {"start": 16, "end": 23},
        }

    # ===================================================
    # Public Entrypoint
    # ===================================================
    def run_step(self, symbol: str, bos_time_utc: datetime):
        """
        Run bias computation for given BOS timestamp (UTC-based).
        """
        try:
            self.logger.info(f"[BiasService] Running bias check for {symbol} at {bos_time_utc} UTC")

            candles = self._get_candles(symbol)
            if candles is None or len(candles) < 1000:
                self.logger.warning("Not enough candle data for bias analysis.")
                return

            bos_df = self._get_bos_events(symbol)
            if bos_df is None or len(bos_df) == 0:
                self.logger.warning("No BOS data found for Bayesian update.")
                return

            for session_name, hours in self.sessions.items():
                z_result = self._run_z_test(candles, bos_time_utc, hours)
                bayes_result = self._update_bayesian_confidence(bos_df, bos_time_utc, z_result, hours)

                final_bias = {
                    "symbol": symbol,
                    "session": session_name,
                    "bias": "bullish" if bayes_result["posterior"] >= 0.5 else "bearish",
                    "z_confidence": round(float(z_result["confidence"]), 3),
                    "bayesian_confidence": round(float(bayes_result["posterior"]), 3),
                    "z_score": round(float(z_result["z_score"]), 4),
                    "bos_bullish_count": bayes_result.get("bullish_count", 0),
                    "bos_bearish_count": bayes_result.get("bearish_count", 0),
                    "evidence_used": bayes_result.get("evidence_used", 0),
                    "mean_return": round(float(z_result["mean"]), 6),
                    "std_return": round(float(z_result["std"]), 6),
                    "sample_size": z_result["n"],
                    "bias_date": bos_time_utc.date(),
                    "updated_at": datetime.utcnow(),
                }

                self._save_bias_to_db(final_bias)
                self._log_summary(session_name, bos_time_utc, z_result, bayes_result)

        except Exception as e:
            self.logger.exception(f"Error in BiasService.run_step: {e}")

    def run_daily_analysis(self, symbol: str):
        """
        Run bias update once per day for all sessions.
        Uses the most recent candle timestamp as reference.
        """
        candles = self._get_candles(symbol)
        if candles is None or len(candles) == 0:
            self.logger.warning("No candle data available for daily bias.")
            return

        # handle UNIX timestamp (seconds)
        if "time" in candles.columns and np.issubdtype(candles["time"].dtype, np.number):
            candles["timestamp"] = pd.to_datetime(candles["time"], unit="s", utc=True)
        elif "timestamp" not in candles.columns:
            raise ValueError("Candle data missing 'time' or 'timestamp' column")

        latest_time = candles["timestamp"].max()

        # normalize to start of the day in UTC
        bos_time_utc = datetime(
            latest_time.year, latest_time.month, latest_time.day, 0, 0, 0, tzinfo=latest_time.tzinfo
        )

        self.logger.info(f"Running daily market bias update for {symbol} ({bos_time_utc.date()})")
        self.run_step(symbol, bos_time_utc)


    @staticmethod
    def get_current_session(now=None):
        """
        Detect the current trading session based on UTC time.
        Adjust hours if your broker uses another timezone.
        """
        now = now or datetime.utcnow().time()

        if time(23, 0) <= now or now < time(7, 0):
            return "Asia"
        elif time(7, 0) <= now < time(15, 0):
            return "London"
        else:
            return "NewYork"

    # ───────────────────────────────
    # 📈 Get latest bias for given symbol/session/date
    # ───────────────────────────────
    def get_latest_bias(self, symbol: str, session: str, bias_date=None):
        """
        Fetch latest saved bias for a given symbol & session.
        """
        bias_date = bias_date or datetime.utcnow().date()
        query = """
            SELECT symbol, session, bias, z_confidence, bayesian_confidence,
                   z_score, bos_bullish_count, bos_bearish_count,
                   evidence_used, mean_return, std_return, sample_size, bias_date
            FROM strategy_bos_fvg_retrace_market_bias_daily
            WHERE symbol = %s AND session = %s AND bias_date = %s
            LIMIT 1
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (symbol, session, bias_date))
                result = cursor.fetchone()
                return result
        except Exception as e:
            self.logger.error(f"Error fetching bias: {e}")
            return None

    # ───────────────────────────────
    # 🧭 Convenience wrapper to get current session bias
    # ───────────────────────────────
    def get_current_session_bias(self, symbol: str):
        """
        Automatically determine the current session and return today's bias.
        Example return:
        {
            'symbol': 'XAUUSDc',
            'session': 'London',
            'bias': 'bullish',
            'z_confidence': 0.998,
            ...
        }
        """
        session = self.get_current_session()
        return self.get_latest_bias(symbol, session)
    # ===================================================
    # Z-Test (90-day Statistical Bias)
    # ===================================================
    def _run_z_test(self, df: pd.DataFrame, bos_time_utc: datetime, hours: dict):
        """
        Perform Z-test on returns for the last 90 days before BOS time (session-filtered).
        """
        start_time = bos_time_utc - timedelta(days=90)
        window_df = df[(df["timestamp"] >= start_time) & (df["timestamp"] < bos_time_utc)]
        session_df = window_df[window_df["timestamp"].dt.hour.between(hours["start"], hours["end"])].copy()

        # 🔹 Ensure numeric types (avoid Decimal)
        for col in ["open", "high", "low", "close"]:
            if col in session_df.columns:
                session_df[col] = session_df[col].astype(float)

        session_df.loc[:, "return"] = session_df["close"].pct_change()
        session_df = session_df.dropna()

        if len(session_df) < 30:
            return {"direction": "neutral", "z_score": 0, "confidence": 0.5, "mean": 0, "std": 0, "n": 0}

        mean = session_df["return"].mean()
        std = session_df["return"].std()
        n = len(session_df)

        if std == 0 or np.isnan(std):
            return {"direction": "neutral", "z_score": 0, "confidence": 0.5, "mean": mean, "std": std, "n": n}

        z_score = mean / (std / np.sqrt(n))
        p_value = 1 - stats.norm.cdf(abs(z_score))

        direction = "bullish" if mean > 0 else "bearish"
        confidence = min(1.0, max(0.5, 1 - p_value))

        return {
            "direction": direction,
            "z_score": float(z_score),
            "confidence": float(confidence),
            "mean": float(mean),
            "std": float(std),
            "n": n,
        }

    # ===================================================
    # Bayesian Update (10-day Structural Evidence)
    # ===================================================
    def _update_bayesian_confidence(self, bos_df, bos_time_utc, z_result, hours):
        """
        Bayesian update using BOS events within 10 days before given BOS timestamp.
        """
        start_time = bos_time_utc - timedelta(days=10)
        bos_recent = bos_df[(bos_df["candle_time"] >= start_time) & (bos_df["candle_time"] < bos_time_utc)]
        bos_recent = bos_recent[bos_recent["candle_time"].dt.hour.between(hours["start"], hours["end"])]

        bullish_count = (bos_recent["direction"] == "bullish").sum()
        bearish_count = (bos_recent["direction"] == "bearish").sum()
        total = bullish_count + bearish_count

        if total == 0:
            return {"posterior": z_result["confidence"], "evidence_used": 0, "bullish_count": 0, "bearish_count": 0}

        prior = z_result["confidence"]
        likelihood_bull = (bullish_count + 1) / (total + 2)
        likelihood_bear = (bearish_count + 1) / (total + 2)

        posterior = (likelihood_bull * prior) / ((likelihood_bull * prior) + (likelihood_bear * (1 - prior)))

        return {
            "posterior": float(posterior),
            "evidence_used": total,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
        }

    # ===================================================
    # Database & Logging
    # ===================================================
    def _save_bias_to_db(self, bias_data):
        # --- Ensure NumPy types are converted to Python native types ---
        safe_data = {k: (v.item() if hasattr(v, "item") else v) for k, v in bias_data.items()}

        query = """
            INSERT INTO strategy_bos_fvg_retrace_market_bias_daily (
                symbol, session, bias, z_confidence, bayesian_confidence,
                z_score, bos_bullish_count, bos_bearish_count,
                evidence_used, mean_return, std_return, sample_size, bias_date
            )
            VALUES (%(symbol)s, %(session)s, %(bias)s, %(z_confidence)s, %(bayesian_confidence)s,
                    %(z_score)s, %(bos_bullish_count)s, %(bos_bearish_count)s,
                    %(evidence_used)s, %(mean_return)s, %(std_return)s, %(sample_size)s, %(bias_date)s)
            ON DUPLICATE KEY UPDATE
                bias = VALUES(bias),
                z_confidence = VALUES(z_confidence),
                bayesian_confidence = VALUES(bayesian_confidence),
                z_score = VALUES(z_score),
                bos_bullish_count = VALUES(bos_bullish_count),
                bos_bearish_count = VALUES(bos_bearish_count),
                evidence_used = VALUES(evidence_used),
                mean_return = VALUES(mean_return),
                std_return = VALUES(std_return),
                sample_size = VALUES(sample_size),
                updated_at = CURRENT_TIMESTAMP
        """

        try:
            # ✅ FIX: ensure proper use of the generator context
            from contextlib import contextmanager
            from src.core.db.connection import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:  # ✅ properly open cursor
                    cursor.execute(query, safe_data)
                    conn.commit()

            self.logger.info(
                f"✅ Saved bias for {safe_data['symbol']} {safe_data['session']} ({safe_data['bias_date']})"
            )

        except Exception as e:
            self.logger.error(f"❌ Error saving bias to DB: {e}")
            raise

    def _log_summary(self, session_name, bos_time_utc, z_result, bayes_result):
        self.logger.info(
            f"[BiasService] {session_name} ({bos_time_utc}) → "
            f"Z-Test: {z_result['direction']} (z={z_result['z_score']:.2f}, conf={z_result['confidence']:.2f}) | "
            f"Bayes posterior={bayes_result['posterior']:.2f} from {bayes_result['evidence_used']} BOS"
        )

    # ===================================================
    # Helpers
    # ===================================================
    def _get_candles(self, symbol):
        if symbol == "XAUUSDc":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No data source for {symbol}")

        if np.issubdtype(df["time"].dtype, np.number):
            df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        else:
            raise ValueError("No valid time column found in candle data")

        return df.reset_index(drop=True)

    def _get_bos_events(self, symbol):
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT direction, candle_time
                FROM strategy_bos_fvg_retrace_structure_events
                WHERE symbol=%s
                ORDER BY candle_time DESC
                LIMIT 1000
                """,
                (symbol,),
            )
            rows = cursor.fetchall()

        if not rows:
            return pd.DataFrame(columns=["direction", "candle_time"])

        bos_df = pd.DataFrame(rows)
        bos_df["candle_time"] = pd.to_datetime(bos_df["candle_time"], utc=True)
        return bos_df

    def _get_last_bias_date(self, symbol):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bias_date
                FROM strategy_bos_fvg_retrace_market_bias_daily
                WHERE symbol=%s
                ORDER BY bias_date DESC
                LIMIT 1
            """, (symbol,))
            row = cursor.fetchone()
            return row[0] if row else None
