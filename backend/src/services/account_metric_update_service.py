# src/services/account_metric_update_service.py
import asyncio
from src.services.base_service import BaseService
from src.core.account.account_metric_service import AccountMetricService
from src.core.metrics.drawdown_service import DrawdownService
from src.utils.logger import get_logger

logger = get_logger("service.account_metric_update_service")


class AccountMetricUpdateService(BaseService):
    def __init__(self, interval: int = 300):
        super().__init__(name="AccountMetricUpdateService", interval=interval)
        self.description = "Periodically append account snapshot to account_metrics and update drawdown."

    async def run_once(self):
        try:
            # 1️⃣ Get last known balance (from DB)
            # 1️⃣ Detect today’s daily baseline
            starting_balance = AccountMetricService.get_daily_baseline()

            # 2️⃣ Ensure today's daily_metrics row exists (creates new if new day)
            DrawdownService.ensure_today_record(starting_balance)

            # 3️⃣ Append a new account snapshot
            balance = AccountMetricService.update_metrics()

            # 4️⃣ Update peak/low/ending for the day
            DrawdownService.update_balance_metrics(balance)
            logger.info("✅ Account metrics refreshed successfully.")

        except Exception as e:
            logger.exception("❌ Failed to update account metrics: %s", e)
