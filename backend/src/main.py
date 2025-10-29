# src/main.py
from fastapi import FastAPI
import asyncio


from src.services.base_service import BaseService
from src.services.telegram_service import TelegramService
from src.services.trade_signal_service import TradeSignalService
from src.services.trailing_service import TrailingService
from src.services.trade_history_service import TradeHistoryService
from src.services.data_pipeline_service import DataPipelineService
import logging

from src.core.app_state import scheduler
from src.api.service_api import router as service_router
from src.api.trade_signal_api import router as trade_signal_router
from src.api.trade_history_api import router as trade_history_router
from src.api.route_metrics import router as metrics_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = [
    "http://localhost:3006",
    "http://127.0.0.1:3006",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(service_router)
app.include_router(trade_signal_router)
app.include_router(trade_history_router)
app.include_router(metrics_router)


class DummyService(BaseService):
    async def run_once(self):
        print("Running dummy logic...")

@app.on_event("startup")
async def start_scheduler():
    print("🚀 Starting background scheduler...")
    # scheduler.register(DummyService("TestService", interval=2))
    telegram_service = TelegramService()
    trade_signal_service = TradeSignalService(
    config={
        "max_concurrent": 3,
        "max_retries": 3,
        "retry_delay": 30
    },
    interval=5  # optional
    )
    trailing_service = TrailingService()
    trade_history_service = TradeHistoryService()
    data_pipeline_service = DataPipelineService()
    # DEBUG
    from src.core.db.get_data_xauusdc import get_data_m15_xauusdc

    df = get_data_m15_xauusdc()
    # print(df.tail(50))
    # from src.core.mt5.get_data_helper import get_data_m15_xauusdc as get_data_m15_xauusdc_mt5
    # df = get_data_m15_xauusdc_mt5()
    # print(df.tail())
    from src.services.strategy_swing_point_service import StrategySwingPointService
    swing_point_service = StrategySwingPointService(
    symbol="XAUUSDc",
    timeframe="M15",
    interval=60
    )
    from src.services.strategy_bos_fvg_retrace_service import StrategyBosFvgRetraceService
    bos_fvg_retrace_service = StrategyBosFvgRetraceService(
    symbol="XAUUSDc",
    timeframe="M15",
    interval=60  
)
    from src.services.strategy_liq_sweep_rejection_service import StrategyLiqSweepRejectionService
    liq_sweep_rejection_service = StrategyLiqSweepRejectionService(
    symbol="XAUUSDc",
    timeframe="M15",
    interval=60
    )
    from src.services.account_metric_update_service import AccountMetricUpdateService
    account_metric_update_service = AccountMetricUpdateService(interval=300)  # 5 minutes
    scheduler.register(account_metric_update_service)
    scheduler.register(data_pipeline_service)
    scheduler.register(trade_history_service)
    scheduler.register(trailing_service)
    scheduler.register(trade_signal_service)
    scheduler.register(telegram_service)
    # STRATEGY SECTION
    scheduler.register(swing_point_service)
    scheduler.register(liq_sweep_rejection_service)
    scheduler.register(bos_fvg_retrace_service)

    asyncio.create_task(scheduler.start_all())  # run it in background

@app.on_event("shutdown")
async def stop_scheduler():
    print("🛑 Stopping background scheduler...")
    await scheduler.stop_all()

@app.get("/")
def root():
    return {"message": "Server running!"}
