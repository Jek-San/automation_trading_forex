# src/services/telegram_service.py
import asyncio
import os
from dotenv import load_dotenv

from src.services.base_service import BaseService
from src.core.telegram.telegram_handler import TelegramHandler
from src.utils.logger import get_logger
class TelegramService(BaseService):
    def __init__(self, name="TelegramService", interval=None):
        super().__init__(name, interval)
        load_dotenv()
        self.handler = TelegramHandler(
            api_id=os.getenv("TELEGRAM_API_ID"),
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            phone=os.getenv("TELEGRAM_PHONE")
        )
        self.description = "Listens and Handles incoming messages from Telegram messages."
        self.task = None
        self.logger = get_logger("service.telegram_service")


    async def start(self):
        """Start Telegram client in the background."""

        if self.task and not self.task.done():
            self.logger.warning("⚠️ Telegram already running.")
            return

        self.logger.info("▶️ Starting Telegram service...")
        # from src.core.mt5.mt5_logic import check_price_now
        # self.logger.warning(check_price_now("BTCUSDc", 'buy'))
        self.running = True  # ✅ Add this
        self.task = asyncio.create_task(self.handler.start())

    async def stop(self):
        """Stop the Telegram listener gracefully."""
        self.running = False  # ✅ Add this
        if self.handler.running:
            await self.handler.stop()
        if self.task:
            self.task.cancel()
        self.logger.info("🛑 Telegram service stopped.")

    async def run_once(self):
        """No periodic logic, Telegram runs continuously."""
        pass

    # Optional helpers for API endpoints
    def pause(self):
        self.handler.pause()

    def resume(self):
        self.handler.resume()

    def get_status(self):
        return self.handler.get_status()
