import logging
from pathlib import Path


def setup_logger(log_path: str | Path) -> logging.Logger:
    path = Path(log_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"save_automation:{path}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)

    return logger
