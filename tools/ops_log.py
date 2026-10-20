# -*- coding: utf-8 -*-
"""
tools/ops_log.py
Uygulama operasyon günlüğü. Sessiz except: pass yerine kullanılır.
Kayıtlar %LOCALAPPDATA%\\SmartClearance\\logs\\ops.log altına yazılır.
"""
from __future__ import annotations

import os
import threading
import traceback
from datetime import datetime
from typing import Optional

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")
LOG_PATH = os.path.join(LOG_DIR, "ops.log")

_lock = threading.Lock()
_last_error: Optional[str] = None
_last_error_at: Optional[str] = None
_last_error_service: Optional[str] = None


def get_last_error() -> Optional[str]:
    with _lock:
        if not _last_error:
            return None
        svc = _last_error_service or "sistem"
        when = _last_error_at or ""
        return f"{svc}: {_last_error} ({when})"


def info(service: str, message: str) -> None:
    _write("INFO", service, message)


def warning(service: str, message: str) -> None:
    _write("WARN", service, message)


def error(service: str, message: str) -> None:
    global _last_error, _last_error_at, _last_error_service
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        _last_error = message
        _last_error_at = ts
        _last_error_service = service
    _write("ERROR", service, message, ts=ts)


def exception(service: str, message: str, exc: Optional[BaseException] = None) -> None:
    extra = ""
    if exc is not None:
        extra = f"{type(exc).__name__}: {exc}"
        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            extra = f"{extra}\n{tb.strip()}"
    full = f"{message} | {extra}".strip(" |")
    error(service, full)


def _write(level: str, service: str, message: str, ts: Optional[str] = None) -> None:
    ts = ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] [{service}] {message}\n"
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with _lock:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
                if len(line) > 4000:
                    f.write("\n")
        if level != "INFO":
            print(f"[{service}] {level}: {message[:500]}")
    except OSError:
        print(f"[{service}] {level}: {message[:500]}")
