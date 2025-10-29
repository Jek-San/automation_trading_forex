import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from src.services.mt5_client import MT5Client
from src.utils.logger import get_logger

logger = get_logger("core.mt5.get_data_helper")

def get_data_m15_xauusdc_mt5(limit=5000):
    """Fetch M15 OHLC data for XAUUSD directly from MT5."""
    client = MT5Client.get_instance()

    if not client.ensure_connected():
        logger.error("❌ MT5 connection failed.")
        return None

    symbol = "XAUUSDc"
    if not client.symbol_select(symbol):
        logger.error(f"❌ Failed to select symbol {symbol}")
        return None

    try:
        logger.info(f"📈 Fetching last {limit} M15 bars for {symbol}")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, limit)

        if rates is None or len(rates) == 0:
            logger.warning(f"No data returned for {symbol} M15.")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
        logger.info(f"✅ Retrieved {len(df)} rows for {symbol} M15.")
        return df

    except Exception as e:
        logger.exception(f"🔥 Error fetching MT5 data: {e}")
        return None

def get_data_m30_xauusdc_mt5(limit=5000):
    """Fetch M30 OHLC data for XAUUSD directly from MT5."""
    client = MT5Client.get_instance()

    if not client.ensure_connected():
        logger.error("❌ MT5 connection failed.")
        return None

    symbol = "XAUUSDc"
    if not client.symbol_select(symbol):
        logger.error(f"❌ Failed to select symbol {symbol}")
        return None

    try:
        logger.info(f"📈 Fetching last {limit} M30 bars for {symbol}")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, limit)

        if rates is None or len(rates) == 0:
            logger.warning(f"No data returned for {symbol} M30.")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
        logger.info(f"✅ Retrieved {len(df)} rows for {symbol} M30.")
        return df

    except Exception as e:
        logger.exception(f"🔥 Error fetching MT5 data: {e}")
        return None
    
def get_data_h1_xauusdc_mt5(limit=5000):
    """Fetch H1 OHLC data for XAUUSD directly from MT5."""
    client = MT5Client.get_instance()

    if not client.ensure_connected():
        logger.error("❌ MT5 connection failed.")
        return None

    symbol = "XAUUSDc"
    if not client.symbol_select(symbol):
        logger.error(f"❌ Failed to select symbol {symbol}")
        return None

    try:
        logger.info(f"📈 Fetching last {limit} H1 bars for {symbol}")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, limit)

        if rates is None or len(rates) == 0:
            logger.warning(f"No data returned for {symbol} H1.")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
        logger.info(f"✅ Retrieved {len(df)} rows for {symbol} H1.")
        return df

    except Exception as e:
        logger.exception(f"🔥 Error fetching MT5 data: {e}")
        return None