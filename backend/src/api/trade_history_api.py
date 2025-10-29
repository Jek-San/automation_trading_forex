from fastapi import APIRouter, HTTPException
from src.core.db.connection import get_connection

router = APIRouter(prefix="/trades", tags=["Trades"])

@router.get("/")
# def get_trades():
#     """Get all executed trades"""
#     with get_connection() as conn:
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("""
#             SELECT 
#             t.trade_position_id,
#             t.symbol,
#             t.trade_type,
#             t.volume,
#             t.price,
#             t.close_price,
#             t.profit,
#             t.type_order AS trade_type_order,
#             s.type_order AS signal_type_order,
#             s.instrument,
#             s.action,
#             s.range1,
#             s.range2,
#             s.tp1,
#             s.sl,
#             s.comment AS source,
            
#             CASE 
#                 WHEN t.type_order = s.type_order THEN 'MATCH'
#                 ELSE 'DIFFERENT'
#             END AS type_order_status
#         FROM trades t
#         LEFT JOIN trading_signals s ON t.trade_signal_id = s.id
#         WHERE t.trade_signal_id IS NOT NULL
#         ORDER BY t.trade_time DESC
        
#         """)
#         trades = cursor.fetchall()
#         return trades

def get_trades():
    """Get all executed trades"""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT trade_position_id, trade_signal_id,symbol, trade_type, trade_time, comment as source, type_order, profit
            FROM trades
            WHERE trade_signal_id IS NOT NULL AND PROFIT IS NOT NULL
            ORDER BY trade_time DESC
        """)
        trades = cursor.fetchall()
        return trades

@router.get("/{trade_id}")
def get_trade_detail(trade_id: int):
    """Get single trade detail"""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM trades
            WHERE trade_position_id = %s
        """, (trade_id,))
        trade = cursor.fetchone()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        return trade


@router.get("/signal/{signal_id}")
def get_trades_by_signal(signal_id: int):
    """Get all trades linked to a specific signal"""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM trades
            WHERE trade_signal_id = %s
            ORDER BY trade_time DESC
        """, (signal_id,))
        trades = cursor.fetchall()
        return trades
