# src/core/db/connection.py
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from src.utils.logger import get_logger

logger = get_logger("DB")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "trade_record_position"),
    "autocommit": os.getenv("DB_AUTOCOMMIT", "False").lower() == "true",
}

@contextmanager
def get_connection():
    """
    Provide a MySQL connection that automatically closes after use.
    Ensures all cursors are buffered to prevent 'Unread result found' errors.
    """
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)

        # ✅ Monkey-patch conn.cursor() to always use buffered=True
        original_cursor = conn.cursor
        def buffered_cursor(*args, **kwargs):
            kwargs["buffered"] = True
            return original_cursor(*args, **kwargs)
        conn.cursor = buffered_cursor

        yield conn

    except Error as e:
        logger.error(f"Database connection error: {e}")
        raise

    finally:
        if conn and conn.is_connected():
            conn.close()
