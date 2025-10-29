# src/services/trailing_service.py
import asyncio
from src.services.base_service import BaseService
from src.core.trailing_trade.trailing_handler import TrailingHandler
from src.utils.logger import get_logger

logger = get_logger("service.trailing_service")

class TrailingService(BaseService):
    def __init__(self, name="TrailingService", interval=None):
        super().__init__(name, interval)
        self.handler = TrailingHandler(interval=15)
        self.task = None
        self.description = "Trailing Stop Service"

    async def start(self):
        """Start trailing stop service"""
        if self.task and not self.task.done():
            logger.warning("⚠️ TrailingService already running.")
            return

        logger.info("🚀 Starting Trailing Service...")
        self.running = True
        self.task = asyncio.create_task(self.handler.start())

    async def stop(self):
        """Stop the service"""
        self.running = False
        if self.handler:
            await self.handler.stop()
        if self.task:
            self.task.cancel()
        logger.info("🛑 Trailing Service stopped.")

    async def run_once(self):
        """Optional single-run for manual trigger"""
        await asyncio.get_running_loop().run_in_executor(None, self.handler.trailing_stop_manager)
