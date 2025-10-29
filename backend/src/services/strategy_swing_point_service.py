# src/services/strategy_swing_point_service.py
from src.services.base_service import BaseService
from src.core.strategies.swing_point_fib.controller import SwingPointController
from src.utils.logger import get_logger

class StrategySwingPointService(BaseService):
    """
    Background service wrapper for BOS-FVG-Retrace strategy.
    Runs periodically via the main scheduler.
    """

    def __init__(self, symbol="XAUUSDc", timeframe="M15", interval=900):
        super().__init__(name="SwingPointService", interval=interval)
        self.logger = get_logger("core.services.strategy_swing_point_service")
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = SwingPointController()

    async def run_once(self):
        """This is called by scheduler every interval (e.g., every 15 minutes)."""
        self.logger.info(f"⏱ Running SwingPoint step for {self.symbol}-{self.timeframe}")
        self.strategy.run(self.symbol, self.timeframe)
