# src/core/db/signal_repository.py
from src.core.db.connection import get_connection
from mysql.connector import Error
from src.utils.logger import get_logger

logger = get_logger("db.signal_repository")

def retrieve_pending_signals():
    """Fetch signals with status=pending."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM trading_signals WHERE status = 'pending'")
            return cursor.fetchall()
    except Error as e:
        logger.error(f"DB error retrieving pending signals: {e}")
        return []

def update_signal_status(signal_id, status, price=None, type_order=None):
    """Update the signal status."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE trading_signals
                SET status = %s, price_entry = %s, type_order = %s
                WHERE id = %s
                """,
                (status, price, type_order, signal_id),
            )
            logger.info(f"Price: {price}")
            conn.commit()
    except Error as e:
        logger.error(f"DB error updating signal {signal_id}: {e}")
