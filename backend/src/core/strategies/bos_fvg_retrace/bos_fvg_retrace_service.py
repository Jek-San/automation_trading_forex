# src/core/strategies/bos_fvg_retrace/bos_fvg_retrace_service.py
from src.core.db.get_data_xauusdc import get_data_m15_xauusdc
from datetime import datetime
from src.utils.logger import get_logger
from src.core.strategies.bos_fvg_retrace.structure_service import StructureService
# (later we’ll import the others here)
from src.core.strategies.bos_fvg_retrace.fvg_service import FVGService
from src.core.strategies.bos_fvg_retrace.retrace_service import RetraceService
from src.core.strategies.bos_fvg_retrace.entry_service import EntryService
from src.core.strategies.bos_fvg_retrace.entry_to_signal_service import EntryToSignalService
from src.core.strategies.bos_fvg_retrace.bias_service import BiasService
# from src.core.strategies.bos_fvg_retrace.state_service import StateService
import pandas as pd

class BosFvgRetraceService:
    """
    Central orchestrator for BOS-FVG-Retrace strategy.
    Runs all related sub-services in correct order.
    """

    def __init__(self):
        self.logger = get_logger("BosFvgRetraceService")
        self.structure_service = StructureService()
        self.fvg_service = FVGService()
        self.retrace_service = RetraceService()
        self.entry_service = EntryService()
        self.entry_to_signal_service = EntryToSignalService()
        self.bias_service = BiasService()
        self.last_bias_run_date = None
        # self.state_service = StateService()
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
        self.logger.info(f"🚀 Running BOS-FVG-Retrace pipeline for {symbol}-{timeframe}")
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
            today_utc = datetime.utcnow().date()
            if self.last_bias_run_date != today_utc:
                self.logger.info("[BiasService] Running daily bias update (auto-trigger).")
                self.bias_service.run_daily_analysis(symbol)
                self.last_bias_run_date = today_utc
            # 1️⃣ Structure Detection
            self.structure_service.run_step(symbol, timeframe)

            # 2️⃣ FVG Detection (to be implemented later)
            self.fvg_service.run_step(symbol, timeframe)

            # 3️⃣ Retrace Detection (to be implemented later)
            self.retrace_service.run_step(symbol, timeframe)

            self.entry_service.run_step(symbol, timeframe)

            self.entry_to_signal_service.run_step(symbol, timeframe)

            


        except Exception as e:
            self.logger.exception(f"Error running BOS-FVG-Retrace pipeline: {e}")
