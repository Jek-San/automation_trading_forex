# src/core/strategies/swing_point_fib/controller.py
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc
from datetime import datetime
from src.utils.logger import get_logger

# (later we’ll import the others here)

# from src.core.strategies.bos_fvg_retrace.state_service import StateService
from src.core.strategies.swing_point_fib.structure_service import SwingPointService
from src.core.strategies.swing_point_fib.major_swing_fib_service import MajorWaveFibService
from src.core.strategies.swing_point_fib.fib_trade_setup_service import MajorWaveFibTradeSetupService
from src.core.strategies.swing_point_fib.signal_service import MajorWaveFibSignalService
import pandas as pd

class SwingPointController:
    """
    Central orchestrator for BOS-FVG-Retrace strategy.
    Runs all related sub-services in correct order.
    """

    def __init__(self):
        self.logger = get_logger("core.strategies.swing_point_fib.controller ")
        self.swing_point_service = SwingPointService()
        self.major_wave_fib_service = MajorWaveFibService()
        self.major_wave_fib_trade_setup_service = MajorWaveFibTradeSetupService()
        self.major_wave_fib_signal_service = MajorWaveFibSignalService()

        
       
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
        self.logger.info(f"🚀 Running Swing_Point_FIB pipeline for {symbol}-{timeframe}")
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
            
            self.swing_point_service.run_step(symbol, timeframe)
            self.major_wave_fib_service.run_step(symbol, timeframe)
            self.major_wave_fib_trade_setup_service.run_step(symbol, timeframe)
            self.major_wave_fib_signal_service.run_step(symbol, timeframe)
            
           
           
            


        except Exception as e:
            self.logger.exception(f"Error running BOS-FVG-Retrace pipeline: {e}")
