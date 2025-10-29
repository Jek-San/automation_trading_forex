from fastapi import APIRouter, HTTPException
from src.core.db.connection import get_connection

router = APIRouter(prefix="/signals", tags=["Trade Signals"])

@router.get("/")
def get_signals():
    """Get all trade signals"""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, instrument, action, range1, range2, tp1, tp2, sl, status,
                   created_at, price_entry, risk, reward, type_order, comment as source
            FROM trading_signals
            ORDER BY created_at DESC
        """)
        signals = cursor.fetchall()
        
        return signals


@router.get("/{signal_id}")
def get_signal_detail(signal_id: int):
    """Get a specific trade signal and its related trades"""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        # Get signal info
        cursor.execute("""
            SELECT *
            FROM trading_signals
            WHERE id = %s
        """, (signal_id,))
        signal = cursor.fetchone()

        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        # Get related trades
        cursor.execute("""
            SELECT trade_position_id, symbol, trade_type, volume, price, close_time,
                   close_price, profit, comment
            FROM trades
            WHERE trade_signal_id = %s
            ORDER BY trade_time DESC
        """, (signal_id,))
        trades = cursor.fetchall()

        signal["trades"] = trades
        return signal
