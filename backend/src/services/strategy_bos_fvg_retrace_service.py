# src/services/strategy_bos_fvg_retrace_service.py
from src.services.base_service import BaseService
from src.core.strategies.bos_fvg_retrace.bos_fvg_retrace_service import BosFvgRetraceService
from src.utils.logger import get_logger

class StrategyBosFvgRetraceService(BaseService):
    """
    Background service wrapper for BOS-FVG-Retrace strategy.
    Runs periodically via the main scheduler.
    """

    def __init__(self, symbol="XAUUSDc", timeframe="M15", interval=900):
        super().__init__(name="BosFvgRetraceService", interval=interval)
        self.logger = get_logger("StrategyBosFvgRetraceService")
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = BosFvgRetraceService()

    async def run_once(self):
        """This is called by scheduler every interval (e.g., every 15 minutes)."""
        self.logger.info(f"⏱ Running BOS-FVG-Retrace step for {self.symbol}-{self.timeframe}")
        self.strategy.run(self.symbol, self.timeframe)
