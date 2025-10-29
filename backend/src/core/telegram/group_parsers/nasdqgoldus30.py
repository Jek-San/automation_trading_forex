import re
from src.utils.logger import get_logger

logger = get_logger("core.telegram.group_parsers.nasdqgoldus30")


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
class ModelSignalV1(BaseModel):
    @classmethod
    def can_parse(cls, text: str) -> bool:
        # Only process shorter messages that contain BUY/SELL and XAUUSD
        text_upper = text.upper()
        return len(text) <= 150 and ("BUY" in text_upper or "SELL" in text_upper)

    @classmethod
    def parse(cls, message: str):
        if len(message) > 150:
            logger.warning("Message too long. Skipping.")
            return None

        # logger.info("Parsing message:\n%s", message)
        lines = message.split('\n')

        action, instrument = None, "XAUUSDc"
        range1, range2, tp1, tp2, sl = None, None, None, None, None
        tp_list = []
        comment = "nasdqgoldus30"

        # -------------------------------
        # 🔍 Detect BUY / SELL action
        # -------------------------------
        for line in lines:
            line = line.strip().upper()
            if 'LIMIT' in line:
                return None
            if "BUY" in line:
                action = "buy"
                # logger.info("Detected BUY action in message.")
                break
            elif "SELL" in line:
                action = "sell"
                # logger.info("Detected SELL action in message.")
                break

        if action is None:
            # logger.warning("No action detected in message.")
            return None

        # -------------------------------
        # 🔍 Parse each line
        # -------------------------------
        for line in lines:
            line = line.strip().upper()
            if not line:
                continue

            # logger.info("Processing line: %s", line)

            # --- Price Range ---
            price_match = re.search(r'(\d{3,4}\.?\d*)\s*[-/]\s*(\d{3,4}\.?\d*)', line)
            if price_match:
                range1 = float(price_match.group(1))
                range2 = float(price_match.group(2))
                # logger.info(f"Parsed range: {range1} - {range2}")
                continue

            # handle "@ price"
            if "@" in line:
                match = re.search(r'@?\s*(\d{3,4}\.?\d*)', line)
                if match:
                    price = float(match.group(1))
                    range1, range2 = price - 1, price + 1
                    # logger.info(f"Parsed price @ {price}, range set {range1}-{range2}")
                    continue

            # fallback for single price after XAUUSD SELL 1975
            if range1 is None and 'XAUUSD' in line:
                match = re.search(r'(\d{3,4}\.?\d*)', line)
                if match:
                    price = float(match.group(1))
                    range1, range2 = price - 1, price + 1
                    # logger.info(f"Parsed range from single price: {range1} - {range2}")
                    continue

            # --- Stop Loss ---
            if "SL" in line or "STOPLOSS" in line:
                sl_match = re.search(r'(SL|STOPLOSS).*?(\d{3,4}\.?\d*)', line)
                if sl_match:
                    sl = float(sl_match.group(2))
                    # logger.info(f"Parsed SL: {sl}")
                    continue

            # --- Take Profit (TP1 / TP2 / TP / Cyrillic ТР) ---
            if re.search(r'TP\d*', line) or re.search(r'ТР\d*', line):
                tp_matches = re.findall(r'(?:TP|ТР)\d*\s*[:\-]?\s*(\d{3,4}\.?\d*)', line)
                if tp_matches:
                    parsed_tps = [float(tp) for tp in tp_matches]
                    tp_list.extend(parsed_tps)
                    # logger.info(f"Parsed TP(s): {parsed_tps}")
                continue

        # -------------------------------
        # ✅ Post-parse processing
        # -------------------------------
        # if not tp_list:
            # logger.warning("No TP values found in entire message.")

        # assign up to 3 TPs
        tp1 = tp_list[0] if len(tp_list) > 0 else None
        tp2 = tp_list[1] if len(tp_list) > 1 else tp1

        # fallback if TP seems invalid (<1000)
        if tp1 is not None and tp1 < 1000 and range1 and range2:
            # logger.info("TP values look like pips; adjusting based on price range.")
            mid_price = (range1 + range2) * 0.5
            tp1 = mid_price + 10 if action == "buy" else mid_price - 10
            tp2 = tp1

        # sanity check
        if None in [range1, range2, sl, tp1, tp2]:
            # logger.warning("Incomplete data in message. Missing values.")
            return None

        if not re.match(r'^\d{3,4}\.?\d*$', str(range1)) or not re.match(r'^\d{3,4}\.?\d*$', str(range2)):
            # logger.warning("Invalid price range format.")
            return None

        # -------------------------------
        # 🧾 Final formatted signal
        # -------------------------------
        signal = {
            "instrument": instrument,
            "action": action,
            "range1": f"{range1:.2f}",
            "range2": f"{range2:.2f}",
            "tp1": f"{tp1:.2f}",
            "tp2": f"{tp2:.2f}",
            "sl": f"{sl:.2f}",
            "comment": comment
        }

        logger.info(f"✅ Parsed signal: {signal}")
        return signal
class ModelSignalV2(BaseModel):
    """
    Parses short-format signals like:
    GOLD BUY 3990
    Tp1:3994
    Tp:3998
    Sl:3985
    """
    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.upper()
        # Detect short signal with GOLD or XAUUSD and a single number entry
        return bool(re.search(r'\b(GOLD|XAUUSD)\b', text)) and ("TP" in text or "SL" in text)

    @classmethod
    def parse(cls, text: str):
        lines = text.strip().splitlines()
        text_upper = text.upper()
        instrument = "XAUUSDc" if "XAUUSD" in text_upper or "GOLD" in text_upper else "UNKNOWN"
        action, entry, tp1, tp2, sl = None, None, None, None, None

        # --- Detect action + entry
        first_line = lines[0].upper().replace(":", " ").replace("-", " ")
        action_match = re.search(r'\b(BUY|SELL)\b', first_line)
        if action_match:
            action = action_match.group(1).lower()
            price_match = re.search(r'(\d{3,5}\.?\d*)', first_line)
            if price_match:
                entry = float(price_match.group(1))

        # --- Parse TP/SL lines
        for line in lines[1:]:
            line_upper = line.upper()
            if "TP" in line_upper:
                tps = re.findall(r'\d{3,5}\.?\d*', line_upper)
                if len(tps) >= 1:
                    if tp1 is None:
                        tp1 = float(tps[0])
                    elif tp2 is None:
                        tp2 = float(tps[0])
            elif "SL" in line_upper:
                sl_match = re.search(r'\d{3,5}\.?\d*', line_upper)
                if sl_match:
                    sl = float(sl_match.group(0))

        # --- Validate required fields
        if not all([instrument, action, entry, tp1, sl]):
            logger.warning(f"Incomplete short-format signal: {text}")
            return None

        # --- Convert to unified dict format
        signal = {
            "instrument": instrument,
            "action": action,
            "range1": f"{entry - 0.5:.2f}",
            "range2": f"{entry + 0.5:.2f}",
            "tp1": f"{tp1:.2f}",
            "tp2": f"{tp2 or tp1:.2f}",
            "sl": f"{sl:.2f}",
            "comment": "nasdqgoldus30",
        }

        logger.info(f"✅ Parsed V2 signal: {signal}")
        return signal
class ModelSignalV3(BaseModel):
    """
    Parses short text signals like:

    GOLD BUY 3994
    Tp1:3997
    TP2:3999
    TP3:4002
    Sl:3990
    """

    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.upper()
        return bool(re.search(r'\b(GOLD|XAUUSD)\b', text)) and ("TP" in text or "SL" in text)

    @classmethod
    def parse(cls, text: str):
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        text_upper = text.upper()
        instrument = "XAUUSDc" if ("XAUUSD" in text_upper or "GOLD" in text_upper) else "UNKNOWN"

        action, entry, sl = None, None, None
        tps = []

        # --- Parse first line (example: "GOLD BUY 3994")
        first_line = lines[0].upper().replace(":", " ").replace("-", " ")
        action_match = re.search(r'\b(BUY|SELL)\b', first_line)
        if action_match:
            action = action_match.group(1).lower()
            price_match = re.search(r'(\d{3,5}\.?\d*)', first_line)
            if price_match:
                entry = float(price_match.group(1))

        # --- Parse following lines for TP/SL
        for line in lines[1:]:
            line_upper = line.upper()
            if "TP" in line_upper:
                match = re.search(r'(\d{3,5}\.?\d*)', line_upper)
                if match:
                    tps.append(float(match.group(1)))
            elif "SL" in line_upper:
                sl_match = re.search(r'(\d{3,5}\.?\d*)', line_upper)
                if sl_match:
                    sl = float(sl_match.group(0))

        # --- Only keep first two TPs if more are found
        tp1 = tps[0] if len(tps) > 0 else None
        tp2 = tps[1] if len(tps) > 1 else None

        # --- Validation
        if not all([instrument, action, entry, sl, tp1]):
            logger.warning(f"Incomplete short-format signal: {text}")
            return None

        # --- Final dict
        signal = {
            "instrument": instrument,
            "action": action,
            "range1": f"{entry - 0.5:.2f}",
            "range2": f"{entry + 0.5:.2f}",
            "entry": f"{entry:.2f}",
            "tp1": f"{tp1:.2f}",
            "tp2": f"{tp2:.2f}" if tp2 else None,
            "sl": f"{sl:.2f}",

            "comment": "nasdqgoldus30",
        }

        logger.info(f"✅ Parsed V3 signal: {signal}")
        return signal


# --- All models here (more can be added later) ---
MODELS = [ModelSignalV1, ModelSignalV2, ModelSignalV3]


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
