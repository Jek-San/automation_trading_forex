import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Callable
from src.core.db.connection import get_connection  # your unified DB connector
from src.utils.logger import get_logger
from src.services.mt5_client import MT5Client

logger = get_logger("core.mt5.data_fetcher")

# -----------------------------------------------
# Generic Data Fetcher Class
# -----------------------------------------------
class MT5DataFetcher:
    def __init__(self, symbol: str, table_name: str, timeframe: int, candle_seconds: int):
        self.symbol = symbol
        self.table_name = table_name
        self.timeframe = timeframe
        self.candle_seconds = candle_seconds
        self.client = MT5Client.get_instance()

    def ensure_mt5_ready(self):
        if not self.client.ensure_connected():
            logger.error("❌ MT5 connection failed.")
            return False
        return True

    def fetch_chunk(self, start_ts: int, end_ts: int) -> Optional[pd.DataFrame]:
        """Fetch historical OHLC data for a specific range."""
        try:
            utc_start = datetime.utcfromtimestamp(start_ts).replace(tzinfo=timezone.utc)
            utc_end = datetime.utcfromtimestamp(end_ts).replace(tzinfo=timezone.utc)

            rates = mt5.copy_rates_range(self.symbol, self.timeframe, utc_start, utc_end)
            if rates is None or len(rates) == 0:
                return None

            df = pd.DataFrame(rates)
            for col in ["tick_volume", "spread", "real_volume"]:
                if col not in df.columns:
                    df[col] = 0

            df["symbol"] = self.symbol
            df["time"] = df["time"].astype("int64")

            return df[
                ["symbol", "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
            ]

        except Exception as e:
            logger.error(f"Error fetching data chunk: {e}")
            return None

    def get_last_db_timestamp(self, conn) -> int:
        """Return last timestamp stored for this symbol."""
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT MAX(time) FROM {self.table_name} WHERE symbol = %s",
            (self.symbol,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] or 0

    def get_last_complete_timestamp(self) -> int:
        """Last fully closed candle (add buffer)."""
        now = datetime.now(timezone.utc)
        floored = now - timedelta(
            seconds=(now.timestamp() % self.candle_seconds) + 120  # 2-minute buffer
        )
        return int(floored.timestamp())

    def batch_insert(self, conn, data: pd.DataFrame) -> int:
        """Efficient batch insert."""
        if data.empty:
            return 0

        query = f"""
            REPLACE INTO {self.table_name} 
            (symbol, time, open, high, low, close, tick_volume, spread, real_volume)
            VALUES (%(symbol)s, %(time)s, %(open)s, %(high)s, %(low)s, %(close)s, %(tick_volume)s, %(spread)s, %(real_volume)s)
        """

        inserted_rows = 0
        cursor = conn.cursor()
        try:
            for i in range(0, len(data), 500):
                batch = data.iloc[i:i+500].to_dict("records")
                cursor.executemany(query, batch)
                conn.commit()
                inserted_rows += cursor.rowcount
            return inserted_rows
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            return 0
        finally:
            cursor.close()

    def update_to_latest(self):
        """Main sync routine — fetch missing candles and insert to DB."""
        if not self.ensure_mt5_ready():
            return

        conn_ctx = get_connection()
        conn = conn_ctx.__enter__()
        try:
            last_db_time = self.get_last_db_timestamp(conn)
            end_ts = self.get_last_complete_timestamp()

            if last_db_time >= end_ts:
                logger.info(f"{self.symbol} is already up-to-date.")
                return

            current = last_db_time or int(datetime(2011, 1, 1, tzinfo=timezone.utc).timestamp())
            total_inserted = 0
            safety_counter = 0

            while current < end_ts and safety_counter < 1_000_000:
                chunk_end = min(current + 3600, end_ts)
                df = self.fetch_chunk(current, chunk_end)
                if df is not None and not df.empty:
                    inserted = self.batch_insert(conn, df)
                    total_inserted += inserted
                    current = df["time"].max() + self.candle_seconds
                    # logger.info(
                    #     f"[{self.symbol}] Inserted {inserted} rows → new start: {datetime.utcfromtimestamp(current)}"
                    # )
                else:
                    current += self.candle_seconds
                safety_counter += 1

            logger.info(f"✅ {self.symbol} sync completed — total {total_inserted} records.")
        finally:
            conn_ctx.__exit__(None, None, None)
