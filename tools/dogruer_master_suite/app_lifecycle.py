# -*- coding: utf-8 -*-
"""Düzenli kapanış ve kritik hataların status bar / ops.log'a düşmesi."""
from __future__ import annotations

from typing import Any, Optional


def report_critical(service: str, message: str, exc: Optional[BaseException] = None, app=None) -> str:
    """Ops log + son hata; UI açıksa status bar yenilenir."""
    try:
        from tools.ops_log import exception as log_exc, get_last_error
        log_exc(service, message, exc)
        shown = get_last_error() or message
    except Exception:
        shown = message
        print("[%s] CRITICAL: %s" % (service, message))

    if app is not None:
        try:
            bar = getattr(app, "status_bar", None)
            if bar and getattr(app, "_ui_alive", lambda: False)():
                app._schedule_ui(bar.update_status)
        except Exception:
            pass
    return shown


def stop_background_services(app: Any) -> None:
    """Watchdog ve GTB/Kantar/Telegram döngülerini durdur; RPA'yı frenle."""
    try:
        sup = getattr(app, "supervisor", None)
        if sup is not None:
            sup.watchdog_running = False
    except Exception:
        pass

    gtb = getattr(app, "gtb_tracker", None)
    if gtb is not None:
        try:
            if hasattr(gtb, "stop_worker"):
                gtb.stop_worker()
            else:
                gtb.is_running = False
        except Exception:
            pass

    kantar = getattr(app, "kantar_tracker", None)
    if kantar is not None:
        try:
            if hasattr(kantar, "stop_worker"):
                kantar.stop_worker()
            else:
                kantar.is_running = False
        except Exception:
            pass

    tg = getattr(app, "telegram_service", None)
    if tg is not None:
        try:
            if hasattr(tg, "stop_polling"):
                tg.stop_polling()
            else:
                tg.is_running = False
        except Exception:
            pass

    try:
        rpa_view = getattr(app, "views", {}) or {}
        rpa = getattr(rpa_view.get("RPA_STATION"), "rpa", None) if hasattr(rpa_view, "get") else None
        if rpa is None:
            rpa = getattr(getattr(app, "view_rpa", None), "rpa", None)
        if rpa is not None and hasattr(rpa, "trigger_emergency_stop"):
            rpa.trigger_emergency_stop()
    except Exception:
        pass


def prepare_shutdown(app: Any, *, logout_auth: bool = True) -> None:
    """UI ve arka planı durdurur; kök pencereyi yok etmez (çağıran destroy eder)."""
    try:
        app._closed = True
    except Exception:
        pass
    try:
        stop = getattr(app, "_sync_stop", None)
        if stop is not None:
            stop.set()
    except Exception:
        pass
    try:
        bar = getattr(app, "status_bar", None)
        if bar is not None and hasattr(bar, "stop_ticker"):
            bar.stop_ticker()
    except Exception:
        pass

    stop_background_services(app)

    if logout_auth:
        try:
            from tools.auth_manager import get_auth_manager
            am = get_auth_manager()
            am.set_ui_dispatcher(None)
            am.logout()
        except Exception:
            pass
