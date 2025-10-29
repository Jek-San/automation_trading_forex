# src/core/db/trade_history_repository.py
from datetime import datetime, timedelta
from mysql.connector import Error
from src.core.db.connection import get_connection
from src.services.mt5_client import MT5Client
from src.utils.logger import get_logger
import MetaTrader5 as mt5

logger = get_logger("db.trade_history_repository")


def get_trades_with_null_profit():
    """Fetch trades that have null profit values (still open or not yet updated)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT trade_position_id FROM trades WHERE profit IS NULL")
            return cursor.fetchall()
    except Error as e:
        logger.error(f"❌ DB error retrieving trades with null profit: {e}")
        return []


def get_trade_by_position_and_store(position_id):
    """Fetch trade details from MT5 history and store in DB."""
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        logger.warning("⚠️ MT5 not connected, skipping trade update.")
        return

    time_from = datetime.now() - timedelta(days=30)
    time_to = datetime.now()

    deals = mt5.history_deals_get(time_from, time_to)
    if not deals:
        logger.warning(f"No MT5 deals found for period. Err: {mt5.last_error()}")
        return

    filtered = [d for d in deals if d.position_id == int(position_id)]
    if not filtered:
        # logger.info(f"No deals found for Position ID {position_id}")
        return

    # Find open-deal comment
    open_comment = next(
        (d.comment for d in filtered if d.entry == mt5.DEAL_ENTRY_IN),
        None
    )

    # Prepare data list
    trade_data = []
    for deal in filtered:
        entry_type = {
            mt5.DEAL_ENTRY_IN: "Open",
            mt5.DEAL_ENTRY_OUT: "Close",
            mt5.DEAL_ENTRY_INOUT: "Partial Close"
        }.get(deal.entry, "Unknown")

        trade_data.append({
            "Time": datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S'),
            "Position": deal.position_id,
            "Symbol": deal.symbol,
            "Type": "BUY" if deal.type == mt5.ORDER_TYPE_BUY else "SELL",
            "Volume": deal.volume,
            "Price": deal.price,
            "Close Time": None if entry_type == "Open" else datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S'),
            "Close Price": deal.price if entry_type == "Close" else None,
            "Commission": deal.commission,
            "Swap": deal.swap,
            "Profit": deal.profit,
            "Comment": open_comment if entry_type == "Close" else deal.comment
        })

    # Only store if has close deal
    if len(trade_data) >= 2:
        store_trade_in_db(trade_data[-1])
    else:
        logger.info(f"Not enough deals to store for position {position_id}")


def store_trade_in_db(trade_data: dict):
    """Update the trade record in DB once closed."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE trades
                SET 
                    symbol = %s,
                    volume = %s,
                    close_price = %s,
                    close_time = %s,
                    commission = %s,
                    swap = %s,
                    profit = %s,
                    comment = %s
                WHERE trade_position_id = %s
                """,
                (
                    trade_data["Symbol"],
                    trade_data["Volume"],
                    trade_data["Close Price"],
                    trade_data["Close Time"],
                    trade_data["Commission"],
                    trade_data["Swap"],
                    trade_data["Profit"],
                    trade_data["Comment"],
                    trade_data["Position"],
                ),
            )
            conn.commit()
            logger.info(f"✅ Trade {trade_data['Position']} updated successfully.")
    except Error as e:
        logger.error(f"❌ DB error updating trade {trade_data.get('Position')}: {e}")
