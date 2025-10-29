# src/core/telegram/signal_parser_manager.py or logic

# from core.database import save_signal
from src.core.telegram.group_parsers import wolfx, agungalcaesar, nasdqgoldus30, kiboyhx,caesarinvest1206
# from ai_stuff.ai_ollama import parsing_text_ai
from src.utils.logger import get_logger
logger = get_logger("core.telegram.signal_parser_manager")
parsers = {
    "J111117": wolfx.parse_signal,
    "Wolfxsignalsforex": wolfx.parse_signal,
    # "Agungalcaesar": agungalcaesar.parse_signal,
    'NasdaqGoldUs30': nasdqgoldus30.parse_signal,
    "kiboyhx": kiboyhx.parse_signal,
    "caesarinvest1206": caesarinvest1206.parse_signal
}

def adjust_signal_rr(signal, target_rr=2.0):
    action = signal["action"].lower()
    r1 = float(signal["range1"])
    r2 = float(signal["range2"])
    sl = float(signal["sl"])
    tp1 = float(signal["tp1"])

    entry = (r1 + r2) / 2  # midpoint

    if action == "buy":
        risk = entry - sl
        reward = tp1 - entry
    elif action == "sell":
        risk = sl - entry
        reward = entry - tp1
    else:
        return signal  # unknown action

    if risk <= 0 or reward <= 0:
        print("⚠️ Invalid R:R structure")
        return signal

    rr = reward / risk
    if rr < target_rr:
        if action == "buy":
            tp1 = entry + risk * target_rr
        else:
            tp1 = entry - risk * target_rr

    signal["tp1"] = f"{tp1:.2f}"
    signal["rr"] = round(rr, 2)
    return signal

async def parse_signal_and_save(sender_username: str, message_text: str):
    parser = parsers.get(sender_username)
   
    parsed_signal = None
    logger.info(f"🔎 Parsing signal for {message_text}")

    if parser:
        logger.info(f"🧩 Using custom parser for {sender_username}")
        try:
            parsed_signal = parser(message_text)
        except Exception as e:
            logger.error(f"Error parsing {sender_username}: {e}")



    if parsed_signal:
        parsed_signal = adjust_signal_rr(parsed_signal)
        parsed_signal["sender_username"] = sender_username
        model_used = parsed_signal.get("model_used", "unknown")
        parsed_signal["message"] = f"{model_used} {message_text}"
        from src.core.db.signals import insert_signal
        insert_signal(parsed_signal)
        logger.info(f"✅ Signal saved: {parsed_signal}")
    else:
        logger.warning(f"⚠️ No valid signal found for {sender_username}")
