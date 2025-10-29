# src/core/mt5/mt5_logic.py
import logging
import time
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from src.services.mt5_client import MT5Client
from src.core.db.connection import get_connection   # your context manager
from src.utils.logger import get_logger
from src.core.account.account_metric_service import AccountMetricService

logger = get_logger("core.mt5.logic")


# ---------- DB helper to store trade using your connection helper ----------
def store_trade_record_db(trade_data: Dict[str, Any]):
    """
    Store trade record into DB using the get_connection() context manager.
    trade_data expected to contain keys used in your previous code.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
            INSERT INTO trades (
                trade_signal_id,trade_position_id, trade_time, symbol, trade_type, volume, price,
                close_time, close_price, commission, swap, profit, comment, message, type_order
            ) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                trade_data.get("TradeSignalId"),
                trade_data.get("Position"),
                trade_data.get("Time"),
                trade_data.get("Symbol"),
                trade_data.get("Type"),
                trade_data.get("Volume"),
                trade_data.get("Price"),
                trade_data.get("Close Time"),
                trade_data.get("Close Price"),
                trade_data.get("Commission"),
                trade_data.get("Swap"),
                trade_data.get("Profit"),
                trade_data.get("Comment"),
                trade_data.get("Message"),
                trade_data.get("TypeOrder")
            ))
            conn.commit()
            logger.info("Trade record saved to DB for position %s", trade_data.get("Position"))
    except Exception as e:
        logger.exception("Failed to save trade record: %s", e)


# ---------- Helper functions (pure logic) ----------
def extract_days_from_comment(comment: str) -> Optional[float]:
    match = re.search(r'Expired (\d+(?:\.\d+)?) days', comment or "")
    if match:
        return float(match.group(1))
    return None


def calculate_position_size(price_diff: float, risk_percent: float = 0.01) -> float:
    """
    Calculate lot size for XAUUSD such that:
    - 0.01 lot loses $1 per 1.0 price movement
    - risk_percent defines % of balance to risk
    """
    balance = float(AccountMetricService.get_daily_baseline_value())

    if price_diff <= 0:
        raise ValueError("price_diff must be > 0")

    risk_amount = balance * risk_percent  # 1% of balance
    loss_per_0_01lot = price_diff * 1.0   # $1 per 1.0 move per 0.01 lot

    # how many 0.01-lot units we can afford to lose
    lot_0_01_units = risk_amount / loss_per_0_01lot

    position_size = lot_0_01_units * 0.01
    rounded_size = math.floor(position_size * 100) / 100.0

    return max(rounded_size, 0.01)

# ---------- MT5-backed operations (use MT5Client) ----------
def check_price_now(symbol: str, type_trade: str) -> Optional[float]:
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        return None

    tick = client.symbol_info_tick(symbol)
    if tick is None:
        logger.error("Failed to get tick for %s", symbol)
        return None

    if type_trade.lower() == "buy":
        return tick.ask
    elif type_trade.lower() == "sell":
        return tick.bid
    else:
        logger.error("Unknown trade type: %s", type_trade)
        return None


def check_balance() -> Optional[float]:
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        return None
    info = client.account_info()
    return getattr(info, "balance", None)


def close_all_positions():
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        return
    positions = client.positions_get()
    if not positions:
        logger.info("No open positions to close")
        return

    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        volume = pos.volume
        # determine closing price
        tick = client.symbol_info_tick(symbol)
        if not tick:
            logger.error("No tick for %s when closing", symbol)
            continue
        close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "price": close_price,
            "deviation": 10,
            "magic": 234000,
            "comment": "Closing position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = client.order_send(request)
        if not result or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
            logger.error("Failed to close position %s: %s", ticket, getattr(result, "retcode", None))
        else:
            logger.info("Closed position %s on %s", ticket, symbol)


# ---------- Order placement functions adapted from your code ----------
# Note: return order ticket on success, None on failure, or "break" where that behavior is meaningful

import MetaTrader5 as mt5  # used for constants; allowed here


def _prepare_common_order_fields(client: MT5Client, symbol: str, signal: dict) -> Optional[Dict[str, Any]]:
    """Validate symbol and return full tick data for order creation."""
    if not client.symbol_select(symbol, True):
        logger.error("Failed to select symbol %s", symbol)
        return None

    tick = client.symbol_info_tick(symbol)
    if tick is None:
        logger.error("No tick for %s", symbol)
        return None

    return {
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "point": mt5.symbol_info(symbol).point,
        "digits": mt5.symbol_info(symbol).digits,
        "spread": tick.ask - tick.bid,
    }


def place_order_with_sl_tp(signal: dict) -> Optional[str]:
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        return None

    symbol = signal["instrument"]
    pre = _prepare_common_order_fields(client, symbol, signal)
    if pre is None:
        return None

    bid = pre["bid"]
    ask = pre["ask"]
    current_price = bid if signal["action"].lower() == "sell" else ask

    # compute lot size from signal and balance
    stop_loss_points = abs(float(signal["sl"]) - float(current_price))
    
    lot_size = calculate_position_size( price_diff=stop_loss_points)
    volume = signal.get("volume", lot_size)

    # optional range validation (your existing logic)
    range1 = signal.get("range1")
    range2 = signal.get("range2")
    if range1 is not None and range2 is not None:
        if signal.get("comment") == "wolfxsignals":
            min_range = min(range1, range2) - 1
            max_range = max(range1, range2) + 1
        else:
            min_range = min(range1, range2) - 1
            max_range = max(range1, range2) + 1
        if not (min_range <= current_price <= max_range):
            logger.info("Price %s is outside allowed range %s-%s", current_price, min_range, max_range)
            return "break"

    # build request
    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY if signal["action"].lower() == "buy" else mt5.ORDER_TYPE_SELL,
        "price": current_price,
        "deviation": 10,
        "magic": 234000,
        "comment": signal.get("comment", ""),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # set sl/tp for special symbols if present
    if "sl" in signal:
        try:
            order_request["sl"] = float(signal["sl"])
        except Exception:
            pass
    if "tp1" in signal:
        try:
            order_request["tp"] = float(signal["tp1"])
        except Exception:
            pass

    # send
    result = client.order_send(order_request)
    if not result or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
        logger.error("Order send failed: %s", getattr(result, "retcode", None))
        return None

    ticket = getattr(result, "order", None)
    logger.info("Order placed ticket=%s", ticket)

    # save into DB (use your store function or the helper)
    trade_data = {
        "TradeSignalId": signal["id"],
        "Position": str(ticket),
        "Time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "Symbol": symbol,
        "Type": signal.get("action", "").upper(),
        "Volume": volume,
        "Price": current_price,
        "Comment": signal.get("comment", ""),
        "Message": signal.get("message", ""),
        "TypeOrder": "instant_order"
    }
    try:
        store_trade_record_db(trade_data)
    except Exception:
        logger.exception("Failed to write trade to DB after order")

    return ticket


def place_stop_order(signal: dict) -> Optional[str]:
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        return None

    symbol = signal["instrument"]
    logger.info(f"signal is : {signal}")
    pre = _prepare_common_order_fields(client, symbol, signal)
    if pre is None:
        return None

    bid = pre["bid"]
    ask = pre["ask"]
    current_price = bid if signal["action"].lower() == "sell" else ask
    range1 = signal.get("range1")
    range2 = signal.get("range2")
    if range1 is None or range2 is None:
        logger.error("Stop order requires range1/range2")
        return None

    stop_price = (range1 + range2) / 2
    action = signal["action"].lower()

    # ✅ Check valid direction
    if action == "buy" and stop_price <= current_price:
        logger.error("Buy stop must be above current price")
        return None
    if action == "sell" and stop_price >= current_price:
        logger.error("Sell stop must be below current price")
        return None

    # ✅ Enforce broker minimum stop distance
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logger.error("Symbol info not found for %s", symbol)
        return None

    stop_level = symbol_info.trade_stops_level * symbol_info.point or 0
    buffer = stop_level * 2  # double the min distance, just to be safe

    if action == "buy":
        min_allowed = current_price + stop_level
        if stop_price < min_allowed:
            stop_price = round(current_price + buffer, symbol_info.digits)
            logger.warning(
                f"Adjusted buy stop price to {stop_price} (was too close to current {current_price})"
            )
    elif action == "sell":
        max_allowed = current_price - stop_level
        if stop_price > max_allowed:
            stop_price = round(current_price - buffer, symbol_info.digits)
            logger.warning(
                f"Adjusted sell stop price to {stop_price} (was too close to current {current_price})"
            )

    # Expiration logic
    days_to_expire = extract_days_from_comment(signal.get("message", ""))
    expiration = None
    if days_to_expire:
        expiration_dt = datetime.now(timezone.utc) + timedelta(days=days_to_expire)
        expiration = int(expiration_dt.timestamp())

    stop_loss_points = abs(float(signal["sl"]) - float(current_price))
    
    lot_size = calculate_position_size(price_diff=stop_loss_points)
    volume = signal.get("volume", lot_size)

    order_request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_STOP if action == "buy" else mt5.ORDER_TYPE_SELL_STOP,
        "price": float(stop_price),
        "deviation": 10,
        "magic": 234000,
        "comment": signal.get("comment", ""),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    if expiration:
        order_request.update({"type_time": mt5.ORDER_TIME_SPECIFIED, "expiration": expiration})

    for key in ["sl", "tp1"]:
        try:
            if key in signal:
                order_request["sl" if key == "sl" else "tp"] = float(signal[key])
        except Exception:
            pass
    logger.info(f"Order request: {order_request}")
    # ✅ Send order
    result = client.order_send(order_request)
    if not result or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
        logger.error("Stop order failed: %s", getattr(result, "retcode", None))
        return None

    ticket = getattr(result, "order", None)
    logger.info("Stop order placed ticket=%s", ticket)

    trade_data = {
        "TradeSignalId": signal["id"],
        "Position": str(ticket),
        "Time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "Symbol": symbol,
        "Type": signal.get("action", "").upper(),
        "Volume": volume,
        "Price": stop_price,
        "Comment": signal.get("comment", ""),
        "Message": signal.get("message", ""),
        "TypeOrder": "stop_order",
    }
    store_trade_record_db(trade_data)
    return ticket

def place_limit_order(signal: dict) -> Optional[str]:
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        return None

    symbol = signal["instrument"]
    pre = _prepare_common_order_fields(client, symbol, signal)
    if pre is None:
        return None
    
    bid = pre["bid"]
    ask = pre["ask"]
    current_price = bid if signal["action"].lower() == "sell" else ask

    # compute price from range
    range1 = signal.get("range1")
    range2 = signal.get("range2")
    if range1 is None or range2 is None:
        logger.error("Limit order requires range1/range2")
        return None

    price = (range1 + range2) / 2
    # price validation as before
    if signal["action"].lower() == "buy" and price >= current_price:
        logger.error("Limit price must be lower than current price for buy")
        return None
    if signal["action"].lower() == "sell" and price <= current_price:
        logger.error("Limit price must be higher than current price for sell")
        return None

    stop_loss_points = abs(float(signal["sl"]) - float(current_price))
    
    lot_size = calculate_position_size( price_diff=stop_loss_points)
    volume = signal.get("volume", lot_size)
    days_to_expire = extract_days_from_comment(signal.get("message", ""))
    expiration = None
    if days_to_expire:
        expiration_dt = datetime.now(timezone.utc) + timedelta(days=days_to_expire)
        expiration = int(expiration_dt.timestamp())

    order_request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY_LIMIT if signal["action"].lower() == "buy" else mt5.ORDER_TYPE_SELL_LIMIT,
        "price": float(price),
        "deviation": 10,
        "magic": 234000,
        "comment": signal.get("comment", ""),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if expiration:
        order_request.update({"type_time": mt5.ORDER_TIME_SPECIFIED, "expiration": expiration})
    if "sl" in signal:
        try:
            order_request["sl"] = float(signal["sl"])
        except Exception:
            pass
    if "tp1" in signal:
        try:
            order_request["tp"] = float(signal["tp1"])
        except Exception:
            pass
    result = client.order_send(order_request)
    if not result or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
        logger.error("Limit order failed: %s", getattr(result, "retcode", None))
        return None

    ticket = getattr(result, "order", None)
    logger.info("Limit order placed ticket=%s", ticket)

    trade_data = {
        "TradeSignalId": signal["id"],
        "Position": str(ticket),
        "Time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "Symbol": symbol,
        "Type": signal.get("action", "").upper(),
        "Volume": volume,
        "Price": price,
        "Comment": signal.get("comment", ""),
        "Message": signal.get("message", ""),
        "TypeOrder": "limit_order"
    }
    store_trade_record_db(trade_data)
    return ticket


# ---------- trailing stop manager (uses client) ----------
# src/core/mt5/mt5_logic.py
# def trailing_stop_manager():
#     client = MT5Client.get_instance()
#     if not client.ensure_connected():
#         return

#     positions = client.positions_get()
#     if not positions:
#         return

#     total_profit = 0.0
#     for pos in positions:
#         ticket = pos.ticket
#         symbol = pos.symbol
#         entry_price = pos.price_open
#         sl = pos.sl
#         comment = pos.comment

#         tick = client.symbol_info_tick(symbol)
#         if not tick:
#             logger.warning("Missing tick for %s", symbol)
#             continue
#         current_price = tick.bid if pos.type == mt5.ORDER_TYPE_SELL else tick.ask

#         info = client.symbol_info(symbol)
#         if not info:
#             logger.warning("Missing symbol info for %s", symbol)
#             continue

#         point = info.point
#         tick_value = info.trade_tick_value
#         tick_size = info.trade_tick_size

#         profit_points = (current_price - entry_price) if pos.type == mt5.ORDER_TYPE_BUY else (entry_price - current_price)
#         profit_points = profit_points / point
#         usd_per_point = (tick_value / (tick_size / point)) * 0.01
#         # profit_usd = profit_points * usd_per_point
#         profit_usd = pos.profit

#         total_profit += profit_usd

#         # example trail steps (use your existing lists)
#         # trail_steps = [8, 12, 16, 20, 30, 40, 50, 60, 70, 80]
#         # sl_steps = [5, 8, 12, 16, 20, 30, 40, 50, 60]
#         trail_steps = [8, 12, 16, 20, 30, 40, 50, 60, 70, 80]  # profit thresholds in USD
#         sl_usd = [5, 8, 12, 16, 20, 30, 40, 50, 60, 70]        # desired locked profit in USD

#         if comment in ['FVG_SIGNALH4', 'FVG_SIGNALH1', 'EMA_M15_SIGNALM1']:
#             trail_steps = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
#             sl_usd = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90]

#         # apply highest applicable SL
#         for step, sl_target in zip(reversed(trail_steps), reversed(sl_usd)):
#             if profit_usd >= step:
#                 # convert sl_target (in USD) to price distance
#                 sl_offset_points = sl_target / (info.trade_contract_size * pos.volume) / point
#                 new_sl = entry_price + sl_offset_points * point if pos.type == mt5.ORDER_TYPE_BUY else entry_price - sl_offset_points * point

#                 apply_sl = False
#                 if pos.type == mt5.ORDER_TYPE_BUY and (sl == 0.0 or new_sl > sl):
#                     apply_sl = True
#                 if pos.type == mt5.ORDER_TYPE_SELL and (sl == 0.0 or new_sl < sl):
#                     apply_sl = True

#                 if apply_sl:
#                     info = client.symbol_info(symbol)
#                     min_stop_distance = info.trade_stops_level * info.point
#                     usd_per_point = info.trade_tick_value / info.trade_tick_size
#                     sl_offset_points = sl_target / (usd_per_point * pos.volume)
#                     new_sl = entry_price + sl_offset_points * info.point if pos.type == mt5.ORDER_TYPE_BUY else entry_price - sl_offset_points * info.point
#                     new_sl = round(new_sl, info.digits)
#                     logger.info("Updating SL for %s: %s -> %s", symbol, sl, new_sl)

#                     # enforce broker min stop distance
#                     if abs(current_price - new_sl) < min_stop_distance:
#                         logger.warning(f"SL too close for {symbol}. current={current_price}, new_sl={new_sl}, min={min_stop_distance}")
#                         continue

#                     # correct logical direction
#                     if pos.type == mt5.ORDER_TYPE_BUY and new_sl >= current_price:
#                         new_sl = current_price - min_stop_distance
#                     if pos.type == mt5.ORDER_TYPE_SELL and new_sl <= current_price:
#                         new_sl = current_price + min_stop_distance

#                     request = {
#                         "action": mt5.TRADE_ACTION_SLTP,
#                         "position": ticket,
#                         "sl": new_sl,
#                         "tp": pos.tp,
#                         "symbol": symbol,
#                     }

#                     result = client.order_send(request)
#                     if not result or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
#                         logger.error("SL update failed for %s: %s", symbol, getattr(result, "retcode", None))
#                     else:
#                         logger.info("SL moved for %s to %.2f (profit: %.2f USD)", symbol, new_sl, profit_usd)
#                 break


#     logger.info("Trailing stop pass complete. Positions=%s, EstProfit= %.2f", len(positions), total_profit)

def trailing_stop_manager(isActive: bool = False):
    """
    Single-pass trailing stop manager for XAUUSD using price-step trailing
    with breathing buffer to handle normal market oscillations.
    """
    client = MT5Client.get_instance()
    if not client.ensure_connected():
        logger.error("MT5 not connected")
        return

    positions = client.positions_get()
    if not positions:
        return

    total_positions = len(positions)
    total_profit = 0.0
    if total_positions > 1:
        logger.warning("Too many positions (%s)", total_positions)
        isActive = True

    trail_step = 2.0   # SL moves every 2 price units
    trail_start = 7.0  # trailing starts only after 7 units move
    breathing_buffer = 0.5  # Allow SL to trail 0.5 units below the step to handle market breathing

    for pos in positions:
        try:
            if pos.symbol != "XAUUSDc":
                continue  # Only process XAUUSD

            ticket = pos.ticket
            symbol = pos.symbol
            entry_price = pos.price_open
            current_sl = pos.sl
            current_tp = getattr(pos, "tp", 0.0)
            volume = getattr(pos, "volume", 0.0)

            tick = client.symbol_info_tick(symbol)
            if not tick:
                logger.warning("Missing tick for %s", symbol)
                continue
            current_price = tick.bid if pos.type == mt5.ORDER_TYPE_SELL else tick.ask

            info = client.symbol_info(symbol)
            if not info:
                logger.warning("Missing symbol info for %s", symbol)
                continue

            point = info.point
            digits = info.digits

            total_profit += getattr(pos, "profit", 0.0)
            
            # Minimum allowed distance from broker
            min_stop_distance = info.trade_stops_level * point

            # Compute price move from entry
            if pos.type == mt5.ORDER_TYPE_BUY:
                price_move = current_price - entry_price
            else:
                price_move = entry_price - current_price

            # Check if price has moved enough to start trailing
            if price_move < trail_start:
                continue

            # Number of full steps
            steps = int(price_move // trail_step)

            # New SL at last full step minus breathing buffer
            if pos.type == mt5.ORDER_TYPE_BUY:
                new_sl = entry_price + steps * trail_step - breathing_buffer
                # Must not be too close to current price
                if new_sl >= current_price - min_stop_distance:
                    new_sl = current_price - min_stop_distance
                # Validation: don't move SL backward
                if current_sl > 0 and new_sl <= current_sl:
                    continue
            else:  # SELL
                new_sl = entry_price - steps * trail_step + breathing_buffer
                if new_sl <= current_price + min_stop_distance:
                    new_sl = current_price + min_stop_distance
                if current_sl > 0 and new_sl >= current_sl:
                    continue

            # Round to broker precision
            new_sl = round(new_sl / point) * point

            # Avoid tiny adjustments
            min_change = point * 10
            if current_sl > 0 and abs(new_sl - current_sl) < min_change:
                continue

            # Build request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": new_sl,
                "tp": current_tp,
                "symbol": symbol,
            }

            logger.info("Prepared SL update for %s: current_sl=%s -> new_sl=%s", symbol, current_sl, new_sl)

            if isActive:
                result = client.order_send(request)
                retcode = getattr(result, "retcode", None)
                comment_ret = getattr(result, "comment", "")
                if not result or retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error("SL update failed for %s: retcode=%s comment=%s", symbol, retcode, comment_ret)
                else:
                    logger.info("✓ SL updated for %s -> %s", symbol, new_sl)
            else:
                logger.info("DRY-RUN: would send order_send for %s: %s", symbol, request)

        except Exception as ex:
            logger.exception("Error processing position %s: %s", getattr(pos, "ticket", "unknown"), ex)

    logger.info("Trailing stop pass complete. Positions=%d, EstProfit=$%.2f", total_positions, total_profit)
