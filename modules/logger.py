"""
X簿 - logger.py
ログ管理モジュール
APIキー・ファイル内容・記録本文は絶対に記録しない
"""

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "xbook.log"


def get_logger() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("xbook")
    if logger.handlers:
        return logger  # 既に設定済みなら再利用する

    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def log_error(module: str, error: Exception):
    """
    エラーをログに記録する。
    エラーメッセージのみ記録し、ユーザーデータ（記録本文・ファイル内容）は含めない。
    """
    logger = get_logger()
    logger.error(f"[{module}] {type(error).__name__}: {error}")
