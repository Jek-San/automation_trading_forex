import pandas as pd
from src.core.db.connection import get_connection
from src.utils.logger import get_logger

logger = get_logger("core.mt5.get_data_xauusdc")


def fetch_ohlc_data(table_name: str):
    """Generic function to fetch OHLCV data from the given table."""
    query = f"""
        SELECT time, open, high, low, close, tick_volume, spread, real_volume
        FROM {table_name}
        ORDER BY time ASC
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"No data found in {table_name}.")
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            cursor.close()
            return df

    except Exception as e:
        logger.error(f"Error fetching data from {table_name}: {e}")
        return pd.DataFrame()


# --- Helper wrappers for each timeframe ---
def get_data_m1_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_m1_data")

def get_data_m5_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_m5_data")

def get_data_m15_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_m15_data")

def get_data_m30_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_m30_data")

def get_data_h1_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_h1_data")

def get_data_h4_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_h4_data")

def get_data_d1_xauusdc():
    return fetch_ohlc_data("ohlc_xauusdc_d1_data")
