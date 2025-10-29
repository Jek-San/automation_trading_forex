# src/core/trade_manager/trade_signal_handler.py
import asyncio
from src.core.trade_manager.trade_signal_logic import select_order_type, should_retry
from src.core.db.signal_repository import update_signal_status
from src.utils.logger import get_logger

from src.core.mt5.mt5_logic import place_order_with_sl_tp, place_limit_order, place_stop_order
from src.services.mt5_client import MT5Client

logger = get_logger("core.trade_manager.trade_signal_handler")


class TradeSignalHandler:
    def __init__(self, semaphore, config):
        self.semaphore = semaphore
        self.config = config

    async def process_signal(self, signal):
        """Process a single trading signal."""
        async with self.semaphore:
            signal_dict = self._normalize_signal(signal)

            if not all([signal_dict.get('sl'), signal_dict.get('tp1'), signal_dict.get('tp2')]):
                logger.error(f"❌ Missing SL/TP for signal {signal_dict.get('id')}")
                return

            success_target = 1 if signal_dict['comment'] == 'FVG_SIGNALH4' else 3
            current_success = current_failed = 0
            from src.core.mt5.mt5_logic import check_price_now
            price_info =  check_price_now(signal_dict['instrument'], signal_dict['action'].lower())
            
            while should_retry(current_success, current_failed,
                               self.config['max_retries'], success_target):
                try:
                    order_type = select_order_type(signal_dict["message"])
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self._execute_order, signal_dict, order_type
                    )


                    if result not in [None, 'break']:
                        current_success += 1
                        await asyncio.get_event_loop().run_in_executor(
                            None, update_signal_status, signal_dict['id'], 'completed', price_info, order_type
                        )
                        logger.info(f"✅ Order placed successfully for {signal_dict['instrument']}")
                        break
                    else:
                        current_failed += 1
                        await asyncio.get_event_loop().run_in_executor(
                            None, update_signal_status, signal_dict['id'], 'failed'
                        )
                        logger.warning(f"⚠️ Order attempt failed for {signal_dict['instrument']}")
                    await asyncio.sleep(self.config['retry_delay'])

                except Exception as e:
                    logger.error(f"Error processing signal ID {signal_dict['id']}: {e}")
                    await asyncio.get_event_loop().run_in_executor(
                        None, update_signal_status, signal_dict['id'], 'error'
                    )
                    break


    async def cancel_signal(self, signal):
        signal_dict = self._normalize_signal(signal)
        await asyncio.get_event_loop().run_in_executor(
            None, update_signal_status, signal_dict['id'], 'cancelled'
        )

    def _normalize_signal(self, signal_tuple):
        """Convert tuple to dict if needed."""
        if isinstance(signal_tuple, dict):
            return signal_tuple
        fields = ['id','instrument','action','range1','range2','tp1','tp2','sl','comment','message']
        return dict(zip(fields, signal_tuple[:len(fields)]))

    def _execute_order(self, signal, order_type, force=True):
        order_methods = {
            'instant_order': place_order_with_sl_tp,
            'limit_order': place_limit_order,
            'stop_order': place_stop_order,
        }

        main_method = order_methods.get(order_type)
        if not main_method:
            raise ValueError(f"Unknown order type: {order_type}")

        try:
            ticket = main_method(signal)

            # ✅ If instant returns "break", decide pending type automatically
            if ticket == "break" and order_type == "instant_order":
                from src.core.mt5.mt5_logic import check_price_now
                price_info = check_price_now(signal["instrument"], signal["action"].lower())
                current_price = price_info["price"]
                range1, range2 = signal.get("range1"), signal.get("range2")
                if range1 and range2:
                    mid_price = (range1 + range2) / 2
                    action = signal["action"].lower()

                    # determine stop or limit
                    if (action == "buy" and mid_price > current_price) or (action == "sell" and mid_price < current_price):
                        logger.info("🟡 Switching to stop_order (pending beyond current price)")
                        return order_methods["stop_order"](signal)
                    else:
                        logger.info("🔵 Switching to limit_order (pending below current price)")
                        return order_methods["limit_order"](signal)

            if ticket not in [None, "break"]:
                print(f"✅ Order succeeded with type: {order_type}")
                return ticket
            else:
                print(f"⚠️ Order failed with type: {order_type}")
                raise Exception

        except Exception as e:
            if not force:
                print(f"⚠️ Failed to place {order_type} order: {e}")
                return None

            print(f"⚠️ Force mode: retrying with other order types after {order_type} failed.")
            for alt_type, method in order_methods.items():
                if alt_type == order_type:
                    continue
                try:
                    print(f"✅ Trying {alt_type} method")
                    ticket = method(signal)
                    if ticket not in [None, "break"]:
                        return ticket
                except Exception as e2:
                    print(f"❌ Fallback {alt_type} failed: {e2}")

            print("🚫 All order attempts failed.")
            return None