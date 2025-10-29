# src/services/trade_signal_service.py
import asyncio
from src.services.base_service import BaseService
from src.core.db.signal_repository import retrieve_pending_signals
from src.core.trade_manager.trade_signal_handler import TradeSignalHandler
from src.utils.logger import get_logger

logger = get_logger("service.trade_signal_service")


class TradeSignalService(BaseService):
    def __init__(self, config, interval: int = 5):
        super().__init__(name="TradeSignalService", interval=interval)
        self.config = config
        self.semaphore = asyncio.Semaphore(config.get("max_concurrent", 3))
        self.handler = TradeSignalHandler(self.semaphore, config)

        self.description = "Checks for new pending signals and processes them."

    async def run_once(self):
        """Check for new pending signals and process them."""
        try:
            
            signals = await asyncio.get_event_loop().run_in_executor(None, retrieve_pending_signals)
            if not signals:
                logger.debug("No new signals found.")
                return
            from src.core.metrics.drawdown_service import DrawdownService
            if  DrawdownService.is_allowed_to_trade():
                logger.warning("🚫 Daily drawdown limit reached. Skipping all new signals.")
                            
                logger.info(f"📡 Found {len(signals)} pending signals.")
                tasks = [self.handler.process_signal(sig) for sig in signals]
                await asyncio.gather(*tasks)
            else:
                # cancell all the signal found
                logger.warning("🚫 Daily drawdown limit reached. Cancell all new signals.")
                logger.info(f"📡 Found {len(signals)} pending signals.")
                tasks = [self.handler.cancel_signal(sig) for sig in signals]
                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"❌ Error during run_once: {e}")
