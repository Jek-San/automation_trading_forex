import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger
from src.core.db.connection import get_connection
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc


class FibBacktestService:
    def __init__(self):
        self.logger = get_logger("FibBacktestService")

  
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleantimestamp = timestamp.replace(":", "_").replace(" ", "_")
    # ===================================================
    # Entrypoint
    # ===================================================
    def run_all(self, save_to_db=False, export_excel=True, excel_path=f"backtest_results_{cleantimestamp}.xlsx"):
        setups = self._get_all_setups()
        if setups.empty:
            self.logger.warning("No setups found in DB.")
            return

        results = []
        total = len(setups)
        self.logger.info(f"Starting backtest for {total} setups...")

        for idx, setup in setups.iterrows():
            try:
                result = self._backtest_setup(setup)
                results.append(result)
                self.logger.info(
                    f"[{idx+1}/{total}] Setup {setup['id']} ({result['direction']}) → {result['exit_reason']} | {result['result_r']}R"
                )
            except Exception as e:
                self.logger.exception(f"Error testing setup id={setup['id']}: {e}")

        df_results = pd.DataFrame(results)

        if export_excel:
            df_results.to_excel(excel_path, index=False)
            self.logger.info(f"📊 Backtest results saved to {excel_path}")

        if save_to_db:
            self._save_results_to_db(df_results)
            self.logger.info("🗄️ Results saved to database.")

        self.logger.info("✅ Backtest completed successfully.")

    # ===================================================
    # Core logic
    # ===================================================
    def _backtest_setup(self, setup):
        symbol = setup["symbol"]
        timeframe = setup["timeframe"]
        discovered_at = setup["last_swing_discovered_at"]
        # 1:1.6
        # entry = float(setup["entry_price"])
        # sl = float(setup["sl_price"])
        # tp = float(setup["tp_price"])
        # trend = setup["trend"]


        # 1:1
        # entry = float(setup["entry_price"])
        # sl = float(setup["sl_price"])
        
        # trend = setup["trend"]
        # if trend == "bearish":
        #     tp = entry -abs(entry - sl)
        # else:
        #     tp = entry + abs(entry - sl)



        # 1:5point
        entry = float(setup["entry_price"])
        sl = float(setup["sl_price"])
        
        trend = setup["trend"]
        if trend == "bearish":
            tp = entry -7
        else:
            tp = entry + 7
        # Determine direction
        direction = "buy" if trend == "bullish" else "sell"

        df = self._get_candles(symbol, timeframe)
        df = df[df["timestamp"] >= discovered_at].reset_index(drop=True)

        entry_time, exit_time, exit_price, exit_reason = self._simulate_trade(df, entry, sl, tp, trend)

        result_pips, result_r, duration_min = self._calculate_metrics(
            symbol, entry, sl, tp, entry_time, exit_time, exit_price, trend
        )

        return {
            "setup_id": setup["id"],
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "exit_price": exit_price,
            "result_pips": result_pips,
            "result_r": result_r,
            "exit_reason": exit_reason,
            "duration_min": duration_min,
            "created_at": datetime.utcnow(),
        }

    # ===================================================
    # Trade simulation logic
    # ===================================================
    def _simulate_trade(self, df, entry, sl, tp, trend, max_wait_min=1800):
        """
        Simulate trade behavior for a fib setup.

        - Waits for entry until max_wait_min passed since setup start
        - Once entered, monitors candle-by-candle for TP or SL
        - If price never hits entry → result = 'expired'
        - If entered but never hits TP/SL → result = 'timeout'
        """

        entered = False
        entry_time = None
        first_candle_time = df["timestamp"].iloc[0]
        expire_after = first_candle_time + pd.Timedelta(minutes=max_wait_min)

        for _, row in df.iterrows():
            high, low, ts = row["high"], row["low"], row["timestamp"]

            # Stop waiting for entry if too long
            if not entered and ts > expire_after:
                return None, None, None, "expired"

            # Wait for entry trigger
            if not entered:
                if low <= entry <= high:
                    entered = True
                    entry_time = ts
                else:
                    continue

            # After entry, check TP/SL sequence
            if trend == "bullish":
                # BUY: first stop-loss, then take-profit
                if low <= sl:
                    return entry_time, ts, sl, "sl"
                if high >= tp:
                    return entry_time, ts, tp, "tp"
            else:  # bearish
                # SELL: first take-profit, then stop-loss
                if low <= tp:
                    return entry_time, ts, tp, "tp"
                if high >= sl:
                    return entry_time, ts, sl, "sl"

        # Never triggered TP/SL
        if not entered:
            return None, None, None, "expired"
        else:
            return entry_time, None, None, "timeout"

    # ===================================================
    # Metrics calculation logic
    # ===================================================
    def _calculate_metrics(self, symbol, entry, sl, tp, entry_time, exit_time, exit_price, trend=None):
        if entry_time is None or exit_time is None or exit_price is None:
            return 0, 0, None

        pip_factor = 10 if "XAU" in symbol else 10000

        if trend == "bearish":
            # SELL: profit = entry - exit
            result_pips = (entry - exit_price) * pip_factor
        else:
            # BUY: profit = exit - entry
            result_pips = (exit_price - entry) * pip_factor

        risk_pips = abs(entry - sl) * pip_factor
        result_r = round(result_pips / risk_pips, 2) if risk_pips != 0 else 0
        duration_min = int((exit_time - entry_time).total_seconds() / 60)

        return round(result_pips, 1), result_r, duration_min

    # ===================================================
    # Candle data retrieval
    # ===================================================
    def _get_candles(self, symbol, timeframe):
        if symbol == "XAUUSDc" and timeframe == "M15":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No candle data function for {symbol}-{timeframe}")

        if "timestamp" not in df.columns:
            if "time" in df.columns:
                df["timestamp"] = pd.to_datetime(df["time"], unit="s")
            else:
                raise ValueError("No timestamp or time column in candle data")

        return df.sort_values("timestamp").reset_index(drop=True)

    # ===================================================
    # Get all setups from DB
    # ===================================================
    def _get_all_setups(self):
        with get_connection() as conn:
            query = """
                SELECT id, symbol, timeframe, trend,
                       entry_price, sl_price, tp_price,
                       last_swing_discovered_at
                FROM strategy_swing_point_fib_trade_setup
                WHERE symbol='XAUUSDc' AND timeframe='M15'
                ORDER BY last_swing_discovered_at ASC
            """
            df = pd.read_sql(query, conn)
        return df

    # ===================================================
    # DB Writer
    # ===================================================
    def _save_results_to_db(self, df):
        if df.empty:
            return

        with get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                cursor.execute(
                    """
                    INSERT INTO strategy_swing_point_fib_backtest_result
                    (setup_id, symbol, timeframe, direction,
                     entry_time, exit_time,
                     entry_price, stop_loss, take_profit, exit_price,
                     result_pips, result_r, exit_reason, duration_min, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        row["setup_id"], row["symbol"], row["timeframe"], row["direction"],
                        row["entry_time"], row["exit_time"],
                        row["entry_price"], row["stop_loss"], row["take_profit"], row["exit_price"],
                        row["result_pips"], row["result_r"], row["exit_reason"], row["duration_min"], row["created_at"]
                    ),
                )
            conn.commit()
