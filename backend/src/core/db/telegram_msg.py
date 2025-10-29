from datetime import datetime
from mysql.connector import Error
from .connection import get_connection
from src.utils.logger import get_logger

logger = get_logger("DB.telegram_msg")


def retrieve_telegram_messages():
    sql = "SELECT message_id, sender_id, sender_username, text, timestamp FROM telegram_message"
    data = []

    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for record in rows:
                record["timestamp"] = datetime.fromisoformat(record["timestamp"])
                data.append(record)
    except Error as e:
        logger.error(f"Error retrieving messages: {e}")

    return data

def record_telegram_message(message_id, sender_id, sender_username, text, timestamp):
    sql = """
        INSERT INTO telegram_message (message_id, sender_id, sender_username, text, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (message_id, sender_id, sender_username, text, timestamp)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()
            logger.info(f"Recorded signal message: {message_id} and {text}")
    except Error as e:
        logger.error(f"Error recording signal message: {e}")