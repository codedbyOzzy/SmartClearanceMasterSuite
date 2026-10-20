# -*- coding: utf-8 -*-
"""
tools/secrets_store.py
Kimlik bilgilerini %LOCALAPPDATA%\\SmartClearance\\secrets.json
veya SMARTCLEARANCE_* ortam değişkenlerinden okur.
Kaynak koda token yazılmaz; boş dosya tohumlanmaz.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
SECRETS_PATH = os.path.join(CONFIG_DIR, "secrets.json")

_SECRET_KEYS = ("telegram_bot_token", "supabase_url", "supabase_anon_key", "gemini_api_key")

_ENV_MAP = {
    "telegram_bot_token": "SMARTCLEARANCE_TELEGRAM_BOT_TOKEN",
    "supabase_url": "SMARTCLEARANCE_SUPABASE_URL",
    "supabase_anon_key": "SMARTCLEARANCE_SUPABASE_ANON_KEY",
    "gemini_api_key": "SMARTCLEARANCE_GEMINI_API_KEY",
}

_lock = threading.Lock()
_cache: Optional[Dict[str, Any]] = None


def get_secret(name: str, default: str = "") -> str:
    env_key = _ENV_MAP.get(name)
    if env_key:
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            return env_val
    if name == "gemini_api_key":
        genv = os.environ.get("GEMINI_API_KEY", "").strip()
        if genv:
            return genv
    data = _load()
    val = data.get(name)
    if val is None or str(val).strip() == "":
        return default
    return str(val)


def set_secret(name: str, value: str) -> bool:
    """Belirtilen anahtarı yerel secrets.json dosyasına güvenli şekilde yazar."""
    global _cache
    with _lock:
        data = _load().copy()
        data[name] = value.strip()
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(SECRETS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            _cache = data
            return True
        except Exception as e:
            print(f"Secret kaydetme hatası: {e}")
            return False


def _load() -> Dict[str, Any]:
    global _cache
    with _lock:
        if _cache is not None:
            return _cache
        data = {}
        if os.path.exists(SECRETS_PATH):
            try:
                with open(SECRETS_PATH, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except (OSError, json.JSONDecodeError):
                data = {}
        _cache = data
        return _cache
