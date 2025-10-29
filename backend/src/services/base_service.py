# src/services/base_service.py
import asyncio
import traceback
from src.utils.logger import get_logger

class BaseService:
    def __init__(self, name: str, interval: int = 5):
        self.name = name
        self.interval = interval
        self.running = False
        self.task = None
        self.logger = get_logger(f"service.{self.name}")

    async def start(self):
        if self.running:
            self.logger.warning(f"{self.name} is already running.")
            return

        self.logger.info("Starting service...")
        self.running = True
        self.task = asyncio.create_task(self._loop())

    async def stop(self):
        if not self.running:
            self.logger.warning(f"{self.name} is not running.")
            return

        self.logger.info("Stopping service...")
        self.running = False
        if self.task:
            self.task.cancel()

    async def _loop(self):
        try:
            while self.running:
                await self.run_once()
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            self.logger.info("Loop cancelled.")
        except Exception as e:
            self.logger.error(f"Service error: {e}")
            traceback.print_exc()
        finally:
            self.running = False

    async def run_once(self):
        raise NotImplementedError
