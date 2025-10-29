import re
from src.utils.logger import get_logger

logger = get_logger("core.telegram.group_parsers.caesarinvest1206")


# --- Base model interface ---
class BaseModel:
    @classmethod
    def can_parse(cls, text: str) -> bool:
        """Quick test if this parser should handle the message."""
        raise NotImplementedError

    @classmethod
    def parse(cls, text: str) -> dict:
        """Main parsing logic."""
        raise NotImplementedError


# --- 🧠 Model 1 (your current logic) ---

class ModelSignalV1:
    """
    Parses messages like:
        Gold sell limit 4020.5 - 4023.5 SL 4030.5
        GOLD BUY LIMIT 4010 - 4013 SL 4000
    If no TP is provided, auto-calculates TP1 (1:1) and TP2 (1:2) based on SL distance.
    """

    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.upper()
        return (
            "LIMIT" in text
            and re.search(r'\b(BUY|SELL)\b', text)
            and re.search(r'\d{3,5}\.?\d*\s*[-–]\s*\d{3,5}\.?\d*', text)
        )

    @classmethod
    def parse(cls, text: str):
        text_upper = text.upper()

        instrument = "XAUUSDc" if ("XAUUSD" in text_upper or "GOLD" in text_upper) else "UNKNOWN"
        action, range1, range2, sl = None, None, None, None
        tp_list = []

        # --- Extract BUY / SELL
        action_match = re.search(r'\b(BUY|SELL)\b', text_upper)
        if action_match:
            action = action_match.group(1).lower()

        # --- Extract range
        range_match = re.search(r'(\d{3,5}\.?\d*)\s*[-–]\s*(\d{3,5}\.?\d*)', text_upper)
        if range_match:
            range1 = float(range_match.group(1))
            range2 = float(range_match.group(2))

        # --- Extract SL
        sl_match = re.search(r'\bSL[:\s]*([0-9]+\.?[0-9]*)', text_upper)
        if sl_match:
            sl = float(sl_match.group(1))

        # --- Extract TPs if any
        tp_matches = re.findall(r'TP\d*\s*[:\-]?\s*([0-9]+\.?[0-9]*)', text_upper)
        if tp_matches:
            tp_list = [float(tp) for tp in tp_matches]

        # --- Validation
        if None in [action, range1, range2, sl]:
            logger.warning(f"Incomplete limit-order signal: {text}")
            return None

        entry_price = (range1 + range2) / 2

        # --- Auto-generate TP1 / TP2 if not provided
        if not tp_list:
            risk = abs(entry_price - sl)
            if action == "buy":
                tp1 = entry_price + risk  # 1:1
                tp2 = entry_price + 2 * risk  # 1:2
            else:  # sell
                tp1 = entry_price - risk
                tp2 = entry_price - 2 * risk
        else:
            tp1 = tp_list[0] if len(tp_list) > 0 else None
            tp2 = tp_list[1] if len(tp_list) > 1 else tp1

        # --- Build result
        signal = {
            "instrument": instrument,
            "action": action,
            "range1": f"{min(range1, range2):.2f}",
            "range2": f"{max(range1, range2):.2f}",
            "tp1": f"{tp1:.2f}" if tp1 else None,
            "tp2": f"{tp2:.2f}" if tp2 else None,
            "sl": f"{sl:.2f}",
            "comment": "caesarinvest1206",
        }

        logger.info(f"✅ Parsed V1 limit signal: {signal}")
        return signal
class ModelSignalV2_HighRisk:
    """Parses casual messages like:
       'Saya coba masuk high risk setup ya 4035-4038 SL 4045'
    """

    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.upper()
        # detect numeric range like 4035-4038 and SL
        return bool(re.search(r'\d{3,4}\s*[-–]\s*\d{3,4}', text)) and "SL" in text

    @classmethod
    def parse(cls, text: str):
        text = text.upper()

        # --- Extract range ---
        range_match = re.search(r'(\d{3,4}\.?\d*)\s*[-–]\s*(\d{3,4}\.?\d*)', text)
        if not range_match:
            logger.warning("No valid range found.")
            return None
        range1, range2 = float(range_match.group(1)), float(range_match.group(2))
        range_low, range_high = sorted([range1, range2])

        # --- Extract SL ---
        sl_match = re.search(r'SL\s*[:\-]?\s*(\d{3,4}\.?\d*)', text)
        if not sl_match:
            logger.warning("No SL found.")
            return None
        sl = float(sl_match.group(1))

        # --- Infer action (buy/sell) ---
        if sl > range_high:
            action = "sell"
        elif sl < range_low:
            action = "buy"
        else:
            action = "unknown"

        # --- Default instrument ---
        instrument = "XAUUSDC"

        # --- Generate 1:1 and 1:2 TP levels ---
        avg_entry = (range_low + range_high) / 2
        risk = abs(avg_entry - sl)
        if action == "buy":
            tp1 = avg_entry + risk
            tp2 = avg_entry + (risk * 2)
        elif action == "sell":
            tp1 = avg_entry - risk
            tp2 = avg_entry - (risk * 2)
        else:
            tp1 = tp2 = None

        signal = {
            "instrument": instrument,
            "action": action,
            "range1": f"{range_low:.2f}",
            "range2": f"{range_high:.2f}",
            "sl": f"{sl:.2f}",
            "tp1": f"{tp1:.2f}" if tp1 else None,
            "tp2": f"{tp2:.2f}" if tp2 else None,
            "comment": "caesarinvest1206",
        }

        logger.info(f"✅ Parsed high-risk signal: {signal}")
        return signal

# --- All models here (more can be added later) ---
MODELS = [ModelSignalV1,ModelSignalV2_HighRisk]


# --- Unified entry point ---
def parse_signal(text: str):
    """Try each model until one succeeds."""
    for model in MODELS:
        if model.can_parse(text):
            logger.info(f"Trying model: {model.__name__}")
            result = model.parse(text)
            if result:
                result["model_used"] = model.__name__
                return result
    logger.warning("No model matched or parsed successfully.")
    return None
