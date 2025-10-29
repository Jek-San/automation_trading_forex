from datetime import date
from src.core.db.connection import get_connection
from src.utils.logger import get_logger

logger = get_logger("drawdown_service")


class DrawdownService:
    MAX_DRAWDOWN_PERCENT = 10.0  # configurable limit

    @staticmethod
    def ensure_today_record(balance: float):
        """Create today's daily_metrics record if not exists."""
        today = date.today()

        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM daily_metrics WHERE date=%s", (today,))
            record = cur.fetchone()

            if record:
                return record

            # Create a new record for today
            cur.execute("""
                INSERT INTO daily_metrics (date, starting_balance, peak_balance, lowest_balance, ending_balance)
                VALUES (%s, %s, %s, %s, %s)
            """, (today, balance, balance, balance, balance))
            conn.commit()
            logger.info(f"📅 New daily_metrics created for {today} | start={balance:.2f}")
            return {"date": today, "starting_balance": balance, "peak_balance": balance, "lowest_balance": balance}

    @staticmethod
    def update_balance_metrics(balance: float):
        """Update peak, lowest, and ending balance for the day."""
        today = date.today()

        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM daily_metrics WHERE date=%s", (today,))
            record = cur.fetchone()

            if not record:
                DrawdownService.ensure_today_record(balance)
                return

            peak = max(float(balance), float(record["peak_balance"]))
            lowest = min(float(balance), float(record["lowest_balance"]))
            profit =  float(record["ending_balance"]) - float(record["starting_balance"])
            profit_percent = (profit / float(record["starting_balance"])) * 100

            # calculate drawdown
            drawdown = (peak - float(record['ending_balance'])) / peak * 100
            cur.execute("""
                UPDATE daily_metrics
                SET peak_balance=%s,
                    lowest_balance=%s,
                    ending_balance=%s,
                    drawdown=%s,
                    pnl_percent=%s
                WHERE date=%s
            """, (peak, lowest, balance,drawdown,profit_percent, today))
            conn.commit()

    @staticmethod
    def get_today_metrics():
        """Fetch today's daily_metrics row."""
        today = date.today()
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM daily_metrics WHERE date=%s", (today,))
            return cur.fetchone()

    @staticmethod
    def get_drawdown_percent():
        """Compute today's drawdown % from peak to lowest."""
        record = DrawdownService.get_today_metrics()
        if not record:
            return 0.0
        dd_percent = float(record["drawdown"])
        return dd_percent

    @staticmethod
    def is_allowed_to_trade():
        """Return False if today's drawdown >= limit."""
        dd = DrawdownService.get_drawdown_percent()
        logger.info(f"📊 Drawdown: {dd:.2f}%")
        if dd >= DrawdownService.MAX_DRAWDOWN_PERCENT:
            logger.error(f"🚫 Drawdown {dd:.2f}% exceeded limit {DrawdownService.MAX_DRAWDOWN_PERCENT}%")
            return False
        logger.info(f"✅ Drawdown {dd:.2f}% within limit.")
        return True
