import asyncio
from src.services.base_service import BaseService
from src.utils.logger import get_logger
from src.core.trade_history.trade_history_handler import TradeHistoryHandler

logger = get_logger("service.trade_history_service")

class TradeHistoryService(BaseService):
    """Service to update trade history periodically"""

    def __init__(self, name="TradeHistoryService", interval=60):
        super().__init__(name, interval)
        self.handler = TradeHistoryHandler()
        self.task = None
        self.description = "Updates trade history periodically"

    async def start(self):
        """Start the trade history update loop"""
        if self.task and not self.task.done():
            logger.warning("⚠️ TradeHistoryService already running.")
            
            return

        logger.info("🚀 Starting Trade History Service...")
        self.running = True  # ✅ Set running flag
        self.task = asyncio.create_task(self.handler.start_loop())

    async def stop(self):
        self.running = False
        """Stop the trade history update loop"""
        if self.handler:
            await self.handler.stop()
        if self.task:
            self.task.cancel()
        logger.info("🛑 Trade History Service stopped.")

    async def run_once(self):
        """Manually trigger single update"""
        await self.handler.update_trade_history_once()
