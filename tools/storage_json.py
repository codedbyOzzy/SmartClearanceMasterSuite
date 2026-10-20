# -*- coding: utf-8 -*-
"""
tools/storage_json.py
Takip JSON dosyalarını kilit altında anlık kopya alıp atomik replace ile yazar.
Yarım yazım / eşzamanlı tarama+senkron kayıp riskini kapatır.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any, Optional

_file_locks = {}
_map_lock = threading.Lock()


def _lock_for(path: str) -> threading.Lock:
    key = os.path.normcase(os.path.abspath(path))
    with _map_lock:
        if key not in _file_locks:
            _file_locks[key] = threading.Lock()
        return _file_locks[key]


def load_json(path: str, default: Any) -> Any:
    """Dosyayı okur; yoksa veya bozuksa default döner."""
    if not os.path.exists(path):
        return default
    lock = _lock_for(path)
    with lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if data is not None else default
        except (OSError, json.JSONDecodeError, TypeError):
            return default


def save_json_atomic(path: str, data: Any, snapshot_lock: Optional[threading.Lock] = None) -> None:
    """
    snapshot_lock verilirse onun altında list/dict kopyası alınır, sonra
    geçici dosyaya yazılıp os.replace ile hedefe taşınır.
    """
    if snapshot_lock is not None:
        with snapshot_lock:
            payload = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        payload = json.dumps(data, ensure_ascii=False, indent=2)

    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise
