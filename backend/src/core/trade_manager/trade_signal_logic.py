# src/core/trade_manager/trade_signal_logic.py
from src.utils.logger import get_logger

logger = get_logger("trade_signal_logic")

def select_order_type(message: str):
    """Determine which type of order to place."""
    message_upper = message.upper()
    if "LIMIT" in message_upper:
        return "limit_order"
    elif "STOP" in message_upper:
        return "stop_order"
    return "instant_order"

def should_retry(current_success, current_failed, max_retries, success_target):
    """Decide whether to retry or not."""
    return current_success < success_target and current_failed < max_retries
