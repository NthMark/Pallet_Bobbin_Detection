# logger_config.py
"""
Shared logging configuration for the camera app.
Usage:
    from logger_config import get_logger
    logger = get_logger(__name__)
    logger.info("Hello")
"""

import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys
from typing import Optional

# Internal guard to avoid duplicate init
_CONFIGURED = False

def _ensure_log_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        # Fallback to temp dir if home is not writable
        import tempfile
        tmp = tempfile.gettempdir()
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass

def _build_handlers(log_file: str):
    # Timed rotating file: rotate daily, keep last 10 files
    file_handler = TimedRotatingFileHandler(
        log_file, when="D", interval=1, backupCount=10, encoding="utf-8", delay=True
    )
    console_handler = logging.StreamHandler(stream=sys.stdout)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)
    return file_handler, console_handler

def _configure_root_if_needed(default_level: int = logging.INFO):
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Allow overriding log dir/file via env vars
    log_dir = os.getenv("CAMERA_APP_LOG_DIR", os.path.join(os.path.expanduser("~"), "camera_app_logs"))
    log_name = os.getenv("CAMERA_APP_LOG_NAME", "app.log")
    _ensure_log_dir(log_dir)
    log_file = os.path.join(log_dir, log_name)

    root = logging.getLogger()
    root.setLevel(default_level)

    # Avoid duplicate handlers if something already configured logging
    # Remove only our own stream/file handlers to prevent duplicates
    existing_types = tuple(h.__class__ for h in root.handlers)

    file_h, console_h = _build_handlers(log_file)

    if TimedRotatingFileHandler not in existing_types:
        root.addHandler(file_h)
    if logging.StreamHandler not in existing_types:
        root.addHandler(console_h)

    # Tone down noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    root.info("=== Logging initialized (dir=%s, file=%s, keep=10 days) ===", log_dir, log_name)
    _CONFIGURED = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger. Ensures the root logging is configured exactly once.
    """
    _configure_root_if_needed()
    return logging.getLogger(name if name else __name__)

def set_log_level(level: str | int) -> None:
    """
    Dynamically change log level at runtime.
    level can be 'DEBUG','INFO','WARNING','ERROR','CRITICAL' or logging.* constants.
    """
    _configure_root_if_needed()
    root = logging.getLogger()
    if isinstance(level, str):
        level = level.upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        root.setLevel(level_map.get(level, logging.INFO))
    else:
        root.setLevel(level)

def add_file_handler(path: str) -> None:
    """
    Optional: attach an extra file handler (e.g., per-session log).
    """
    _configure_root_if_needed()
    root = logging.getLogger()
    fh = logging.FileHandler(path, encoding="utf-8")
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
