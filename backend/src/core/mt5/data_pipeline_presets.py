from MetaTrader5 import TIMEFRAME_M15, TIMEFRAME_M30, TIMEFRAME_H1, TIMEFRAME_D1, TIMEFRAME_H4
from src.core.mt5.data_fetcher import MT5DataFetcher

# Preconfigured fetchers
data_fetcher_xauusdc_m15 = MT5DataFetcher("XAUUSDc", "ohlc_xauusdc_m15_data", TIMEFRAME_M15, 900)
data_fetcher_xauusdc_m30 = MT5DataFetcher("XAUUSDc", "ohlc_xauusdc_m30_data", TIMEFRAME_M30, 1800)
data_fetcher_xauusdc_h1  = MT5DataFetcher("XAUUSDc", "ohlc_xauusdc_h1_data",  TIMEFRAME_H1, 3600)
data_fetcher_xauusdc_h4  = MT5DataFetcher("XAUUSDc", "ohlc_xauusdc_h4_data",  TIMEFRAME_H4, 14400)
data_fetcher_xauusdc_d1  = MT5DataFetcher("XAUUSDc", "ohlc_xauusdc_d1_data",  TIMEFRAME_D1, 86400)
