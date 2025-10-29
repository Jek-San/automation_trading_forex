# src/core/strategies/bos_fvg_retrace/controller.py
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc
from datetime import datetime
from src.utils.logger import get_logger

from src.core.strategies.liquidity_sweep_rejection.context_service import ContextService
from src.core.strategies.liquidity_sweep_rejection.sweep_service import SweepService
from src.core.strategies.liquidity_sweep_rejection.rejection_service import RejectionService
from src.core.strategies.liquidity_sweep_rejection.setup_service import SetupService
# (later we’ll import the others here)

# from src.core.strategies.bos_fvg_retrace.state_service import StateService
import pandas as pd

class LiquiditySweepRejectionController:
    """
    Central orchestrator for BOS-FVG-Retrace strategy.
    Runs all related sub-services in correct order.
    """

    def __init__(self):
        self.logger = get_logger("core.strategies.liquidity_sweep_rejection.controller ")

        self.context_service = ContextService()
        self.sweep_service = SweepService("XAUUSDc", "M15")
        self.rejection_service = RejectionService("XAUUSDc", "M15")
        self.setup_service = SetupService("XAUUSDc", "M15")
       
    def _get_recent_candles(self, symbol, timeframe):
        if symbol == "XAUUSDc" and timeframe == "M15":
            df = get_data_m15_xauusdc()
        else:
            raise ValueError(f"No data function for {symbol}-{timeframe}")
        return df.tail(300).reset_index(drop=True)
    def run(self, symbol: str, timeframe: str):
        """
        Main orchestration entry point.
        To be triggered every new candle close.
        """
        self.logger.info(f"🚀 Running Liquidity_sweep_rejection pipeline for {symbol}-{timeframe}")
        df = self._get_recent_candles(symbol, timeframe)
        if df is None or len(df) < 10:
            return
        if "time" in df.columns:
            df["timestamp"] = df["time"].apply(lambda x: datetime.utcfromtimestamp(int(x)))
        # from src.core.mt5.get_data_helper import  get_data_m15_xauusdc_mt5
        
        # real_data = get_data_m15_xauusdc_mt5()
        # real_data["time"] = pd.to_datetime(real_data["time"], utc=True)
        # self.logger.info("from db")
        # print(df.tail(10))
        # self.logger.info("from realdata")
        # print(real_data.tail(10))



        try:
            
            
            self.context_service.run_step(symbol)
            self.sweep_service.run_step()
            self.rejection_service.run_step()
            self.setup_service.run_step()
           
           
            


        except Exception as e:
            self.logger.exception(f"Error running BOS-FVG-Retrace pipeline: {e}")
