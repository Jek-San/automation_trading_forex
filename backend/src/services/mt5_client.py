# src/service/mt5_client.py
import time
import logging
import MetaTrader5 as mt5

from datetime import datetime

from src.utils.logger import get_logger
logger = logging.getLogger("service.mt5_client")


class MT5Client:
    """
    Lightweight wrapper for MetaTrader5. Use as a singleton via get_instance().
    Exposes minimal helpers so logic code doesn't call mt5.* directly all over the app.
    """

    _instance = None

    def __init__(self, retry=3, retry_delay=1.0):
        self.retry = retry
        self.retry_delay = retry_delay
        self._connected = False
        # Do not initialize automatically on import; call initialize()/ensure_connected() when you need it.

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MT5Client()
        return cls._instance

    def initialize(self) -> bool:
        """Try to initialize MT5 once (with retries). Returns True if successful."""
        if self._connected:
            return True

        tries = 0
        while tries < max(1, self.retry):
            try:
                if mt5.initialize():
                    logger.info("MT5 initialized successfully.")
                    self._connected = True
                    return True
                else:
                    logger.warning(f"mt5.initialize() failed: {mt5.last_error()}")
            except Exception as e:
                logger.exception("Exception while initializing MT5: %s", e)

            tries += 1
            time.sleep(self.retry_delay)
            logger.info("Retrying MT5 initialize... (attempt %s)", tries + 1)

        logger.error("Failed to initialize MT5 after %s attempts", tries)
        return False

    def ensure_connected(self) -> bool:
        """Ensure there is a connected MT5 session. Returns True if connected/initialized."""
        if self._connected:
            return True
        ok = self.initialize()
        if not ok:
            logger.error("MT5 connection could not be established.")
        return ok

    def shutdown(self):
        try:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 shutdown complete.")
        except Exception as e:
            logger.exception("Error shutting down MT5: %s", e)

    # --- thin wrappers around mt5 functions ---
    def symbol_select(self, symbol: str, visible: bool = True) -> bool:
        try:
            return mt5.symbol_select(symbol, visible)
        except Exception:
            logger.exception("symbol_select failed for %s", symbol)
            return False

    def symbol_info_tick(self, symbol: str):
        try:
            return mt5.symbol_info_tick(symbol)
        except Exception:
            logger.exception("symbol_info_tick failed for %s", symbol)
            return None

    def symbol_info(self, symbol: str):
        try:
            return mt5.symbol_info(symbol)
        except Exception:
            logger.exception("symbol_info failed for %s", symbol)
            return None
    def get_current_price(self, symbol: str):
      """Return current bid/ask price for a given instrument."""
      if not self.ensure_connected():
          logger.error("MT5 not connected.")
          return None

      tick = self.symbol_info_tick(symbol)
      if not tick:
          logger.error(f"No tick data available for {symbol}")
          return None

      return {
          "symbol": symbol,
          "bid": tick.bid,
          "ask": tick.ask,
          "spread": round(tick.ask - tick.bid, 5),
          "timestamp": datetime.fromtimestamp(tick.time).isoformat()
      }
    def get_trade_price(self, symbol: str, action: str):
        """
        Return the correct price for opening based on action.
        action: 'buy' -> ask price, 'sell' -> bid price
        """
        tick = self.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"No tick data for {symbol}")
            return None
        
        if action.lower() == "buy":
            return tick.ask
        elif action.lower() == "sell":
            return tick.bid
        else:
            logger.error("Invalid action. Use 'buy' or 'sell'")
            return None

    def order_send(self, request: dict):
        try:
            result = mt5.order_send(request)
            return result
        except Exception:
            logger.exception("order_send failed for request: %s", request)
            return None

    def positions_get(self, **kwargs):
        try:
            return mt5.positions_get(**kwargs)
        except Exception:
            logger.exception("positions_get failed with kwargs: %s", kwargs)
            return None

    def account_info(self):
        try:
            return mt5.account_info()
        except Exception:
            logger.exception("account_info failed")
            return None

    def history_deals_get(self, time_from, time_to):
        try:
            return mt5.history_deals_get(time_from, time_to)
        except Exception:
            logger.exception("history_deals_get failed")
            return None
