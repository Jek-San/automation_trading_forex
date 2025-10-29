# src/services/strategy_bos_fvg_retrace_service.py
from src.services.base_service import BaseService
from src.core.strategies.liquidity_sweep_rejection.controller import LiquiditySweepRejectionController
from src.utils.logger import get_logger

class StrategyLiqSweepRejectionService(BaseService):
    """
    Background service wrapper for BOS-FVG-Retrace strategy.
    Runs periodically via the main scheduler.
    """

    def __init__(self, symbol="XAUUSDc", timeframe="M15", interval=900):
        super().__init__(name="liq_sweep_rejection", interval=interval)
        self.logger = get_logger("core.services.strategy_liq_sweep_rejection_service")
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = LiquiditySweepRejectionController()

    async def run_once(self):
        """This is called by scheduler every interval (e.g., every 15 minutes)."""
        self.logger.info(f"⏱ Running LiqSweepRejection step for {self.symbol}-{self.timeframe}")
        self.strategy.run(self.symbol, self.timeframe)
