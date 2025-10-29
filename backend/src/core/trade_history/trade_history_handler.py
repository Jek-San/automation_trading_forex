import asyncio
from src.utils.logger import get_logger
from src.core.db.trade_history_repository import (
    get_trades_with_null_profit,
    get_trade_by_position_and_store,
    store_trade_in_db
)

logger = get_logger("core.trade_history_handler")

class TradeHistoryHandler:
    def __init__(self, interval=60):
        self.interval = interval
        self.running = False
        self.shutdown_event = asyncio.Event()

    async def start_loop(self):
        """Start infinite trade history update loop"""
        self.running = True
        logger.info("📈 Trade History Handler started.")

        while self.running and not self.shutdown_event.is_set():
            try:
                await self.update_trade_history_once()
            except asyncio.CancelledError:
                logger.info("Trade history loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in trade history loop: {e}")
            await asyncio.sleep(self.interval)

    async def stop(self):
        """Stop the update loop"""
        self.running = False
        self.shutdown_event.set()
        logger.info("🛑 Trade History Handler stopped.")

    async def update_trade_history_once(self):
        """Perform one cycle of trade history update"""
        trades = await asyncio.get_running_loop().run_in_executor(None, get_trades_with_null_profit)
        if not trades:
            logger.debug("No trades with null profit found.")
            return

        logger.info(f"🔍 Found {len(trades)} trades needing update.")
        for trade in trades:
            try:
                position_id = trade["trade_position_id"]
                data = await asyncio.get_running_loop().run_in_executor(
                    None, get_trade_by_position_and_store, position_id
                )
                if data:
                    await asyncio.get_running_loop().run_in_executor(None, store_trade_in_db, data)
                    logger.info(f"✅ Updated trade history for position {position_id}")
            except Exception as e:
                logger.error(f"⚠️ Failed to update trade {trade}: {e}")
