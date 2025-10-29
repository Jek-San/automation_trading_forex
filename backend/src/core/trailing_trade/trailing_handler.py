# src/handlers/trailing_handler.py
import asyncio
from src.core.mt5.mt5_logic import trailing_stop_manager
from src.utils.logger import get_logger

logger = get_logger("core.trailing_trade.trailing_handler")

class TrailingHandler:
    def __init__(self, interval: int = 15):
        self.interval = interval
        self.running = False
        self.task = None

    async def start(self):
        """Start trailing stop loop"""
        if self.running:
            logger.warning("⚠️ TrailingHandler already running.")
            return
        self.running = True
        logger.info("▶️ Starting trailing handler loop...")
        self.task = asyncio.create_task(self._loop())

    async def stop(self):
        """Graceful stop"""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("🛑 TrailingHandler stopped.")

    async def _loop(self):
        while self.running:
            try:
                await asyncio.get_running_loop().run_in_executor(None, trailing_stop_manager)
            except asyncio.CancelledError:
                logger.info("⏹️ Trailing loop cancelled.")
                break
            except Exception as e:
                logger.error(f"❌ Error in trailing handler: {e}")
            await asyncio.sleep(self.interval)
