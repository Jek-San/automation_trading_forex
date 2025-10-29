import re
from src.utils.logger import get_logger

logger = get_logger("core.telegram.group_parsers.wolfx")

import statistics

def check_signal(parsed):
    """Smart sanity + typo correction for parsed signal dict."""
    action = parsed.get("action", "").lower()
    instrument = parsed.get("instrument", "")
    comment = parsed.get("comment", "").lower()

    # --- 1️⃣ Basic validation ---
    if not action or not instrument:
        return False

    # --- 2️⃣ Collect numeric fields ---
    nums = {}
    for k in ["range1", "range2", "tp1", "tp2", "sl"]:
        try:
            if parsed.get(k):
                nums[k] = float(parsed[k])
        except:
            pass
    if len(nums) < 3:
        return False

    # --- 3️⃣ Basic price sanity ---
    prices = list(nums.values())
    if not all(10 < p < 100000 for p in prices):
        return False

    # --- 4️⃣ Detect outlier using median ---
    median_price = statistics.median(prices)
    deviations = {k: abs(v - median_price) for k, v in nums.items()}

    # threshold = 1.5% deviation
    outliers = [k for k, v in deviations.items() if v / median_price > 0.015]

    if len(outliers) == 1:
        k = outliers[0]
        v = nums[k]

        # looks like 4442 vs 4042 typo → same suffix digits
        if str(int(v))[1:] == str(int(median_price))[1:]:
            corrected = float(str(int(median_price))[0] + str(int(v))[1:])
            parsed[k] = f"{corrected:.2f}"
            print(f"⚙️ Auto-corrected {k}: {v} → {corrected}")
            nums[k] = corrected
        else:
            # try to round to nearest "reasonable" level
            if abs(v - median_price) > 20:
                corrected = round(median_price, 1)
                parsed[k] = f"{corrected:.2f}"
                nums[k] = corrected
                print(f"⚙️ Adjusted {k} to median {corrected}")
    elif len(outliers) > 1:
        print(f"❌ Too many anomalies: {outliers}")
        return False

    # --- 5️⃣ Ensure logical order ---
    r1, r2 = nums.get("range1"), nums.get("range2")
    sl = nums.get("sl")
    tp1 = nums.get("tp1")
    tp2 = nums.get("tp2")

    # Auto-swap if reversed
    if r1 and r2 and r1 > r2:
        parsed["range1"], parsed["range2"] = f"{r2:.2f}", f"{r1:.2f}"
        r1, r2 = r2, r1
        print(f"↔️ Swapped range1 & range2")

    tp = max(tp1 or 0, tp2 or 0)

    if action == "buy" and not (sl < r1 < tp):
        print("❌ Buy structure invalid")
        return False
    if action == "sell" and not (sl > r1 > tp):
        print("❌ Sell structure invalid")
        return False

    # --- 6️⃣ Filter invalid message types ---
    if any(kw in comment for kw in ["hit", "closed", "update", "wait", "analysis"]):
        return False

    # --- 7️⃣ Confidence scoring ---
    score = 0
    if len(nums) >= 3: score += 1
    if sl and tp: score += 1
    if abs(tp - sl) / (tp + sl) < 0.1: score -= 1
    parsed["confidence_score"] = round(score / 2, 2)

    return True


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

        lines = message.split('\n')

        action, instrument = None, "XAUUSDc"
        range1, range2, tp1, tp2, sl = None, None, None, None, None
        tp_list = []
        comment = "wolfxsignals"

        # ---------------------------------
        # 🔍 Detect BUY / SELL action
        # ---------------------------------
        for line in lines:
            line = line.strip().upper()
            if 'LIMIT' in line:
                return None
            if "BUY" in line:
                action = "buy"
                break
            elif "SELL" in line:
                action = "sell"
                break

        if action is None:
            return None

        # ---------------------------------
        # 🧠 Helper: Smart Normalization
        # ---------------------------------
        def normalize_pair(n1, n2, tps=None, sl=None):
            """Smartly infer missing digits and correct short forms."""
            try:
                n1 = float(n1)
                n2 = float(n2)
            except ValueError:
                return None, None

            # --- Guess missing digits ---
            if n1 < 1000 or n2 < 1000:
                larger = max(n1, n2)
                if larger < 1000 and tps:
                    guess_base = int(max(tps) // 1000) * 1000
                elif larger < 1000 and sl:
                    guess_base = int(sl // 1000) * 1000
                elif larger < 1000:
                    guess_base = 4000  # default gold zone
                else:
                    guess_base = int(larger // 1000) * 1000

                if n1 < 1000:
                    n1 = guess_base + n1
                if n2 < 1000:
                    n2 = guess_base + n2

            # --- Handle huge diff (e.g. 442 vs 4039) ---
            if abs(n1 - n2) > 200:
                if n1 < n2 and n1 < 1000:
                    n1 += int(n2 // 1000) * 1000
                elif n2 < n1 and n2 < 1000:
                    n2 += int(n1 // 1000) * 1000

            # --- Order range ---
            low, high = sorted([n1, n2])

            # --- Sanity check ---
            if not (1500 <= low <= 5000):
                return None, None
            if not (1500 <= high <= 5000):
                return None, None

            return low, high

        # ---------------------------------
        # 🔍 Parse each line
        # ---------------------------------
        for line in lines:
            line = line.strip().upper()
            if not line:
                continue

            # --- Price Range (smart tolerant) ---
            price_match = re.search(r'(\d{2,4}\.?\d*)\s*[-/_\s]+\s*(\d{2,4}\.?\d*)', line)
            if price_match:
                num1 = price_match.group(1)
                num2 = price_match.group(2)
                range1, range2 = normalize_pair(num1, num2)
                if range1 and range2:
                    continue

            # --- Handle "@ price" ---
            if "@" in line:
                match = re.search(r'@?\s*(\d{3,4}\.?\d*)', line)
                if match:
                    price = float(match.group(1))
                    range1, range2 = price - 1, price + 1
                    continue

            # --- Fallback: single price after XAUUSD ---
            if range1 is None and 'XAUUSD' in line:
                match = re.search(r'(\d{2,4}\.?\d*)', line)
                if match:
                    price = float(match.group(1))
                    # Attempt to fix missing digits later with TP context
                    range1, range2 = price - 1, price + 1
                    continue

            # --- Stop Loss ---
            if "SL" in line or "STOPLOSS" in line:
                sl_match = re.search(r'(SL|STOPLOSS).*?(\d{2,4}\.?\d*)', line)
                if sl_match:
                    sl = float(sl_match.group(2))
                    continue

            # --- Take Profit (TP1 / TP2 / TP / Cyrillic ТР) ---
            if re.search(r'TP\d*', line) or re.search(r'ТР\d*', line):
                tp_matches = re.findall(r'(?:TP|ТР)\d*\s*[:\-]?\s*(\d{2,4}\.?\d*)', line)
                if tp_matches:
                    parsed_tps = [float(tp) for tp in tp_matches]
                    tp_list.extend(parsed_tps)
                continue

        # ---------------------------------
        # 🔁 Post-correction using TP/SL context
        # ---------------------------------
        if (range1 and range1 < 1000) or (range2 and range2 < 1000):
            if tp_list or sl:
                tps = [float(tp) for tp in tp_list if tp]
                new_r1, new_r2 = normalize_pair(range1 or 0, range2 or 0, tps=tps, sl=sl)
                if new_r1 and new_r2:
                    range1, range2 = new_r1, new_r2

        # ---------------------------------
        # ✅ Post-parse processing
        # ---------------------------------
        tp1 = tp_list[0] if len(tp_list) > 0 else None
        tp2 = tp_list[1] if len(tp_list) > 1 else tp1

        # Fallback if TP seems invalid (<1000)
        if tp1 is not None and tp1 < 1000 and range1 and range2:
            mid_price = (range1 + range2) * 0.5
            tp1 = mid_price + 10 if action == "buy" else mid_price - 10
            tp2 = tp1

        # Infer range again if single small number found like "BUY 442" but TP=4050
        if range1 and range1 < 1000 and tp1 and tp1 > 2000:
            guess_base = int(tp1 // 1000) * 1000
            range1 = guess_base + range1
            range2 = range1 + 1

        # Sanity check
        if None in [range1, range2, sl, tp1, tp2]:
            return None

        if not (1500 <= range1 <= 5000 and 1500 <= range2 <= 5000):
            return None

        # ---------------------------------
        # 🧾 Final formatted signal
        # ---------------------------------
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
    """Handles messages like:
       #XAUUUSD_BUY 3961/58
       TP 3964
       TP 3967
       SL 3954
    """

    @classmethod
    def can_parse(cls, text: str) -> bool:
        text_upper = text.upper()
        # Must start with '#' and contain BUY/SELL and a range like 3961/58
        return text_upper.startswith("#") and ("/" in text_upper) and ("BUY" in text_upper or "SELL" in text_upper)

    @classmethod
    def parse(cls, message: str):
        lines = [l.strip().upper() for l in message.splitlines() if l.strip()]

        action, instrument = None, "XAUUSDc"
        range1, range2, sl, tp_list = None, None, None, []
        comment = "wolfxsignals"

        # --- 🔍 Parse header (first line)
        header = lines[0]
        if "BUY" in header:
            action = "buy"
        elif "SELL" in header:
            action = "sell"

        # Instrument: try to extract (handles #XAUUUSD or #XAUUSD)
        instr_match = re.search(r'#?([A-Z]{5,6})', header)
        if instr_match:
            instrument = "XAUUSDC"

        # Price range like 3961/58 or 1975/78
        price_match = re.search(r'(\d{3,4})/(\d{2,4})', header)
        if price_match:
            high = float(price_match.group(1))
            low = float(price_match.group(2))
            # Normalize if short-form (e.g. 3961/58 → 3958–3961)
            if low < 100:
                base = int(high // 100) * 100
                low = base + low
            range1, range2 = sorted([low, high])

        # --- 🔍 Parse body lines
        for line in lines[1:]:
            if line.startswith("TP"):
                match = re.search(r'TP\s*\d*\s*[:\-]?\s*(\d{3,4}\.?\d*)', line)
                if match:
                    tp_list.append(float(match.group(1)))
            elif line.startswith("SL"):
                match = re.search(r'SL\s*[:\-]?\s*(\d{3,4}\.?\d*)', line)
                if match:
                    sl = float(match.group(1))

        # --- ✅ Post processing
        if not all([action, range1, range2, sl]) or not tp_list:
            logger.warning("Incomplete data in ModelSignalV2.")
            return None

        tp1 = tp_list[0]
        tp2 = tp_list[min(1, len(tp_list)-1)]  # second TP if available

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

        logger.info(f"✅ Parsed V2 signal: {signal}")
        return signal


# --- All models here (more can be added later) ---
MODELS = [ModelSignalV1, ModelSignalV2]


# --- Unified entry point ---
def parse_signal(text: str):
    """Try each model until one succeeds and passes validation."""
    for model in MODELS:
        if model.can_parse(text):
            logger.info(f"Trying model: {model.__name__}")
            result = model.parse(text)

            if result:
                if not check_signal(result):
                    logger.warning(f"Rejected by sanity check: {result}")
                    continue  # try next model
                
                result["model_used"] = model.__name__
                return result

    logger.warning("No model matched or parsed successfully.")
    return None
