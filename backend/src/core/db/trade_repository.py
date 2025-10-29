# src/core/db/trade_repository.py
from src.core.db.connection import get_connection
from datetime import datetime, timedelta

def get_realized_pnl_since_last_snapshot():
    """
    Sum realized pnl of closed trades that haven't been applied to balance yet.
    Simpler approach: sum all closed trades today (or since last snapshot logic if you track that).
    Adjust query to match your schema.
    """
    conn = get_connection()
    cur = conn.cursor()
    # Example: sum closed trades since midnight (change as needed)
    cur.execute("""
        SELECT COALESCE(SUM(pnl), 0)
        FROM trade_history
        WHERE status = 'closed'
          AND closed_at >= CURRENT_DATE
    """)
    row = cur.fetchone()
    cur.close()
    return float(row[0] or 0.0)

def get_floating_pnl_from_open_positions():
    """
    Sum current unrealized profit for open trades.
    Assumes you have an open_positions table with current_pnl or can compute from entry price + current price.
    Adjust to your DB schema.
    """
    conn = get_connection()
    cur = conn.cursor()
    # If you store current_pnl in open_positions:
    cur.execute("""
        SELECT COALESCE(SUM(current_pnl), 0)
        FROM open_positions
        WHERE status = 'open'
    """)
    row = cur.fetchone()
    cur.close()
    return float(row[0] or 0.0)
