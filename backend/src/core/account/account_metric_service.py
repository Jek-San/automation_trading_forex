# src/core/account/account_metric_service.py
import datetime
from decimal import Decimal
from src.core.db.connection import get_connection
from src.utils.logger import get_logger

logger = get_logger("account_metric_service")

def to_decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


class AccountMetricService:
    _daily_baseline = None  # today's starting balance (dynamic)

    STARTING_CAPITAL = Decimal('596.8')  # very first starting balance
    @staticmethod
    def get_daily_baseline_value():
        """
        Return the current daily baseline balance (as Decimal) 
        without recalculating it.
        """
        if not AccountMetricService._daily_baseline:
            # fallback: ensure it is initialized
            AccountMetricService.get_daily_baseline()
        return AccountMetricService._daily_baseline["balance"]
    @staticmethod
    def get_realized_pnl_today():
        """Sum of trades closed today only."""
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(profit), 0)
                FROM trades
                WHERE close_time >= %s AND close_time < %s
            """, (today, tomorrow))
            result = cursor.fetchone()
            return to_decimal(result[0] or 0)
    @staticmethod
    def _get_last_metric_record():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT balance, timestamp
                FROM account_metrics
                ORDER BY timestamp DESC LIMIT 1
            """)
            return cursor.fetchone()

    @staticmethod
    def get_daily_baseline():
        """
        Returns today's starting balance:
        - If daily baseline already set -> reuse
        - Else try daily_metrics for today
        - Else take yesterday's ending balance
        - Else use STARTING_CAPITAL
        """
        today = datetime.date.today()

        if AccountMetricService._daily_baseline and AccountMetricService._daily_baseline["date"] == today:
            return to_decimal(AccountMetricService._daily_baseline["balance"])

        # check daily_metrics table first
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT starting_balance FROM daily_metrics WHERE date=%s", (today,))
            record = cursor.fetchone()
            if record:
                baseline = to_decimal(record["starting_balance"])
                AccountMetricService._daily_baseline = {"balance": baseline, "date": today}
                return baseline

        # fetch yesterday's ending_balance
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ending_balance FROM daily_metrics ORDER BY date DESC LIMIT 1")
            last_record = cursor.fetchone()
            baseline = to_decimal(last_record["ending_balance"]) if last_record else AccountMetricService.STARTING_CAPITAL

        AccountMetricService._daily_baseline = {"balance": baseline, "date": today}

        # create daily_metrics row for today
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_metrics (date, starting_balance, peak_balance, lowest_balance, ending_balance)
                VALUES (%s, %s, %s, %s, %s)
            """, (today, baseline, baseline, baseline, baseline))
            conn.commit()

        logger.info(f"📅 Daily baseline set for today: {baseline}")
        return baseline

    @staticmethod
    def get_latest():
        """Return last account_metrics row."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT balance, equity, floating_pnl, realized_pnl, drawdown, timestamp
                FROM account_metrics
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "balance": to_decimal(row[0]),
                "equity": to_decimal(row[1]),
                "floating_pnl": to_decimal(row[2]),
                "realized_pnl": to_decimal(row[3]),
                "drawdown": to_decimal(row[4]),
                "timestamp": row[5],
            }

    @staticmethod
    def update_metrics():
        baseline = AccountMetricService.get_daily_baseline()
        daily_realized = AccountMetricService.get_realized_pnl_today()
        balance = baseline + daily_realized

        floating_pnl = Decimal('0')
        equity = balance + floating_pnl

        last_metrics = AccountMetricService.get_latest()
        last_equity = last_metrics["equity"] if last_metrics else balance
        drawdown = ((last_equity - equity) / last_equity * Decimal('100')) if last_equity > 0 else Decimal('0')

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO account_metrics (timestamp, balance, equity, floating_pnl, realized_pnl, drawdown)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                datetime.datetime.now(),
                balance,
                equity,
                floating_pnl,
                daily_realized,
                drawdown,
            ))
            conn.commit()

        logger.info(f"💾 Metrics updated | Bal={balance} | Eq={equity} | DD={drawdown}%")
        return balance
