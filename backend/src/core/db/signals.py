from datetime import datetime
from mysql.connector import Error
from .connection import get_connection
from src.utils.logger import get_logger

logger = get_logger("DB.signals")

# =========================
# 🔹 Retrieve all signals
# =========================
def get_signals():
    """Fetch all trading signals from the database."""
    sql = """
        SELECT id, instrument, action, range1, range2, tp1, tp2, sl, 
               comment, message, risk, reward, status, price_entry, created_at
        FROM trading_signals
        ORDER BY created_at DESC
    """
    signals = []

    try:
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    # Optionally parse timestamp to datetime object
                    if isinstance(row.get('created_at'), str):
                        try:
                            row['created_at'] = datetime.fromisoformat(row['created_at'])
                        except ValueError:
                            pass
                    signals.append(row)
        logger.info(f"📦 Retrieved {len(signals)} signals from database.")
        return signals

    except Error as e:
        logger.error(f"Database error while retrieving signals: {e}")
        return []


def insert_signal(signal):
    """Insert a new trading signal into the database."""
    required_keys = ['instrument', 'action', 'range1', 'range2', 'tp1', 'tp2', 'sl', 'comment']
    for key in required_keys:
        if key not in signal:
            logger.error(f"Missing required key: {key}")
            return

    try:
        action = signal['action'].lower()
        if action not in ('buy', 'sell'):
            raise ValueError(f"Invalid action: {action}")

        # Convert numeric fields
        r1, r2, sl = float(signal['range1']), float(signal['range2']), float(signal['sl'])
        tp1_val, tp2_val = float(signal['tp1']), float(signal['tp2'])

        # Risk/reward calc
        if action == 'buy':
            risk = abs(max(r1, r2) - sl)
            reward = abs(tp1_val - max(r1, r2))
        else:
            risk = abs(sl - min(r1, r2))
            reward = abs(min(r1, r2) - tp1_val)

        # DB insert
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO trading_signals 
                    (instrument, action, range1, range2, tp1, tp2, sl, comment, message, risk, reward)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    signal['instrument'], action, r1, r2,
                    tp1_val, tp2_val, sl,
                    signal['comment'], signal.get('message'),
                    risk, reward
                ))
                conn.commit()
        logger.info(f"✅ Signal inserted: {signal['instrument']} ({action})")

    except (ValueError, KeyError) as e:
        logger.error(f"Invalid signal data: {e}")
    except Error as e:
        logger.error(f"Database error: {e}")

# =========================
# 🔹 Update signal status
# =========================
def update_signal_status(signal_id, status, price_entry=None):
    """
    Update the status of a trading signal (e.g., 'triggered', 'closed', 'cancelled').
    """
    if not signal_id or not status:
        logger.warning("⚠️ Missing signal_id or status for update.")
        return False

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    UPDATE trading_signals
                    SET status = %s, price_entry = %s, updated_at = NOW()
                    WHERE id = %s
                """
                cursor.execute(query, (status, price_entry, signal_id))
                conn.commit()

        logger.info(f"✅ Signal {signal_id} updated to '{status}' (entry={price_entry})")
        return True

    except Error as e:
        logger.error(f"❌ Error updating signal status: {e}")
        return False
