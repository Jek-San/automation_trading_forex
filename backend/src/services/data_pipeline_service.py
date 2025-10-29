# src/services/data_pipeline_service.py
import asyncio
import time
from datetime import datetime

from src.services.base_service import BaseService
from src.utils.logger import get_logger
from src.services.mt5_client import MT5Client
from src.core.mt5.data_pipeline_presets import (
    data_fetcher_xauusdc_m15,
    data_fetcher_xauusdc_m30,
    data_fetcher_xauusdc_h1,
    data_fetcher_xauusdc_h4,
    data_fetcher_xauusdc_d1,
)

logger = get_logger("service.data_pipeline_service")


class DataPipelineService(BaseService):
    """Service to run data update pipelines for multiple timeframes"""

    def __init__(self, name="DataPipelineService"):
        # BaseService interval isn’t used directly because each loop manages its own timing
        super().__init__(name, interval=1)
        self.client = MT5Client.get_instance()
        self.tasks: list[asyncio.Task] = []
        self.description = "Fetches market data periodically"

    async def start(self):
        if self.running:
            logger.warning("⚠️ DataPipelineService already running.")
            return

        logger.info("🚀 Starting Data Pipeline Service...")
        self.running = True

        # Launch concurrent pipelines
        self.tasks = [
            asyncio.create_task(self.run_data_pipeline("M15", data_fetcher_xauusdc_m15.update_to_latest, 60 * 3)),  # every 3 minutes
            asyncio.create_task(self.run_data_pipeline("M30", data_fetcher_xauusdc_m30.update_to_latest, 60 * 3)),  # every 3 minutes
            
            asyncio.create_task(self.run_data_pipeline("H1", data_fetcher_xauusdc_h1.update_to_latest, 60 * 10)),   # every 10 minutes
            asyncio.create_task(self.run_data_pipeline("H4", data_fetcher_xauusdc_h4.update_to_latest, 60 * 10)),   # every 10 minutes
            
            asyncio.create_task(self.run_data_pipeline("D1", data_fetcher_xauusdc_d1.update_to_latest, 60 * 60)),  # every hour

        ]

    async def stop(self):
        if not self.running:
            logger.warning("⚠️ DataPipelineService is not running.")
            return

        logger.info("🛑 Stopping Data Pipeline Service...")
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def run_once(self):
        """If scheduler triggers manual single run."""
        await self.run_data_pipeline("M15", data_fetcher_xauusdc_m15.update_to_latest, 0)

    def check_mt5_connection(self) -> bool:
        return self.client.ensure_connected()

    async def run_data_pipeline(self, label: str, fetcher_func, sleep_time: int):
        """Generic data fetcher loop for one timeframe."""
        while self.running:
            try:
                if not self.check_mt5_connection():
                    logger.error(f"❌ MT5 connection failed for {label}. Retrying in 30s...")
                    await asyncio.sleep(30)
                    continue

                start = time.monotonic()
                logger.info(f"📊 {label} update started at {datetime.now().strftime('%H:%M:%S')}")

                # Run the fetcher synchronously in executor (to avoid blocking the event loop)
                await asyncio.get_event_loop().run_in_executor(None, fetcher_func)

                elapsed = time.monotonic() - start
                logger.info(f"✅ {label} update completed in {elapsed:.2f}s")

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info(f"⏹️ {label} loop cancelled.")
                break
            except Exception as e:
                logger.error(f"🔥 {label} update error: {e}")
                await asyncio.sleep(60)
