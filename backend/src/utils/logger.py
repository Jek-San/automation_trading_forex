import logging
import sys
import io
from logging.handlers import TimedRotatingFileHandler
from colorama import Fore, Style, init
from pathlib import Path

# --- Fix Windows console encoding for emoji / Unicode ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# --- Auto color reset after each print ---
init(autoreset=True)

# --- Color scheme for each log level ---
LEVEL_COLORS = {
    "DEBUG": Fore.BLUE,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}

# --- Format pattern ---
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
DATE_FORMAT = "%H:%M:%S"

# --- Base log folder ---
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class ColorFormatter(logging.Formatter):
    """Formatter that adds color based on log level."""
    def format(self, record):
        level_color = LEVEL_COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{level_color}{message}{Style.RESET_ALL}"


def get_logger(name: str = "app", level=logging.INFO):
    """
    Create a logger that:
    - Logs colorized output to console
    - Saves to a per-module daily rotating file (e.g. telegram.log.2025-10-06)
    - Keeps logs for 14 days
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # --- Console handler (color output) ---
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console_handler)

        # --- File handler (per-module daily log) ---
        safe_name = name.replace(".", "_")  # e.g. core.telegram -> core_telegram.log
        file_path = LOG_DIR / f"{safe_name}.log"

        file_handler = TimedRotatingFileHandler(
            filename=file_path,
            when="midnight",
            interval=1,
            backupCount=14,
            encoding="utf-8",
            utc=False
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
