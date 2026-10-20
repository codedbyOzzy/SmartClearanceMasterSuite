# -*- coding: utf-8 -*-
"""
Web Ops Hub — yerel FastAPI sunucusu
Sadece: Operasyon Kokpiti · GTB Beyanname Takip · Kantar DBA Takip
Mevcut motorları bağlar; iş mantığını değiştirmez.
Port: 8060
"""
from __future__ import annotations

import os
import re
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

HUB_DIR = Path(__file__).resolve().parent
ROOT = HUB_DIR.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.web_ops_hub.cockpit_data import extract_beyanname_candidates, load_cockpit_records

STATIC_DIR = HUB_DIR / "static"
TEMPLATES_DIR = HUB_DIR / "templates"

app = FastAPI(title="SmartClearance Web Ops Hub", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_gtb = None
_kantar = None
_gtb_lock = threading.Lock()
_kantar_lock = threading.Lock()


def _get_gtb():
    global _gtb
    with _gtb_lock:
        if _gtb is None:
            from tools.gtb_engine.gtb_tracker_service import get_gtb_tracker_service

            _gtb = get_gtb_tracker_service()
            try:
                _gtb.start_worker()
            except Exception:
                pass
        return _gtb


def _get_kantar():
    global _kantar
    with _kantar_lock:
        if _kantar is None:
            from tools.kantar_engine.kantar_tracker_service import get_kantar_tracker_service

            _kantar = get_kantar_tracker_service()
            try:
                _kantar.start_worker()
            except Exception:
                pass
        return _kantar


def _page(request: Request, name: str, **ctx):
    # Starlette 1.x: TemplateResponse(request, name, context)
    return templates.TemplateResponse(
        request,
        name,
        {"static_v": "20261020", **ctx},
    )


# ── Sayfalar ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def hub_home(request: Request):
    return _page(request, "index.html", title="Giriş")


@app.get("/kokpit", response_class=HTMLResponse)
def page_kokpit(request: Request):
    return _page(request, "kokpit.html", title="Operasyon Kokpiti")


@app.get("/gtb-takip", response_class=HTMLResponse)
def page_gtb(request: Request):
    return _page(request, "gtb.html", title="GTB Beyanname Takip")


@app.get("/kantar-takip", response_class=HTMLResponse)
def page_kantar(request: Request):
    return _page(request, "kantar.html", title="Kantar DBA Takip")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "WebOpsHub",
        "modules": ["kokpit", "gtb", "kantar"],
        "port": 8060,
    }


# ── Kokpit API ────────────────────────────────────────────────────────────────

@app.get("/api/cockpit")
def api_cockpit(
    q: str = Query(""),
    filter_type: str = Query("all"),
    limit: int = Query(200, ge=1, le=500),
):
    data = load_cockpit_records(q=q, filter_type=filter_type, limit=limit)
    return data


# ── GTB API (eski gtb_takip.js sözleşmesi) ────────────────────────────────────

@app.get("/api/gtb/takip/listele")
def gtb_listele(sadece_aktif: bool = Query(True)):
    try:
        svc = _get_gtb()
        items = svc.list_tracked(only_active=sadece_aktif)
        # JS alan adlarıyla uyum
        beyannameler = []
        for r in items:
            beyannameler.append(
                {
                    **r,
                    "durum": r.get("durum") or r.get("gtb_durum") or "İzleniyor",
                    "son_kontrol": r.get("son_kontrol") or r.get("son_sorgu_zamani") or "—",
                    "son_kontrol_zamani": r.get("son_kontrol") or r.get("son_sorgu_zamani") or "—",
                    "ekleyen_kullanici": r.get("ekleyen_kullanici") or "Sistem",
                    "ref_no": r.get("ref_no") or r.get("ref") or "—",
                }
            )
        return {"success": True, "beyannameler": beyannameler, "count": len(beyannameler)}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "beyannameler": []}, status_code=500)


@app.post("/api/gtb/takip/ekle")
def gtb_ekle(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _get_gtb()
        raw = payload.get("beyannameler") or payload.get("beyanname_no") or ""
        if isinstance(raw, list):
            candidates = []
            for x in raw:
                candidates.extend(extract_beyanname_candidates(str(x)))
        else:
            candidates = extract_beyanname_candidates(str(raw))
        # tekil koru
        seen = set()
        ordered = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                ordered.append(c)

        eklenenler = []
        for b_no in ordered:
            res = svc.add_to_tracking(
                b_no,
                dosya_no=str(payload.get("dosya_no") or "—"),
                firma=str(payload.get("firma") or "WH-HANKOOK"),
                ref=str(payload.get("ref") or payload.get("ref_no") or "—"),
            )
            if res.get("success"):
                eklenenler.append(b_no)
                # İsteğe bağlı anlık sorgu (ilk eklenen)
        return {
            "success": len(eklenenler) > 0,
            "eklenen_sayisi": len(eklenenler),
            "eklenen": len(eklenenler),
            "eklenenler": eklenenler,
            "error": None if eklenenler else "Geçerli bir beyanname numarası bulunamadı.",
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "eklenen_sayisi": 0}, status_code=500)


@app.post("/api/gtb/takip/sil/{beyanname_no}")
def gtb_sil(beyanname_no: str):
    try:
        svc = _get_gtb()
        ok = svc.remove_from_tracking(beyanname_no)
        return {"success": bool(ok)}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/gtb/takip/kontrol-et")
def gtb_kontrol():
    try:
        svc = _get_gtb()
        res = svc.run_full_cycle()
        return {"success": bool(res.get("success")), **res}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/gtb/takip/sorgula/{beyanname_no}")
def gtb_sorgula(beyanname_no: str):
    try:
        svc = _get_gtb()
        res = svc.query_single_now(beyanname_no)
        return res
    except Exception as e:
        return {"success": False, "error": str(e), "beyanname_no": beyanname_no}


# ── Kantar API ────────────────────────────────────────────────────────────────

@app.get("/api/kantar/takip/listele")
def kantar_listele(sadece_aktif: bool = Query(True)):
    try:
        svc = _get_kantar()
        items = svc.list_tracked(only_active=sadece_aktif)
        return {"success": True, "items": items, "count": len(items), "last_scan": getattr(svc, "last_scan_time", "—")}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "items": []}, status_code=500)


@app.post("/api/kantar/takip/ekle")
def kantar_ekle(payload: Dict[str, Any] = Body(default={})):
    try:
        svc = _get_kantar()
        raw = payload.get("konteynerler") or payload.get("konteyner_no") or ""
        parts = re.split(r"[\s,;/\n\r]+", str(raw))
        eklenen = []
        for p in parts:
            clean = re.sub(r"[^A-Z0-9]", "", p.upper())
            if len(clean) < 4:
                continue
            res = svc.add_to_tracking(
                clean,
                dosya_no=str(payload.get("dosya_no") or "—"),
                ref=str(payload.get("ref") or "—"),
                firma=str(payload.get("firma") or "WH-HANKOOK"),
                kaynak=str(payload.get("kaynak") or "manuel"),
            )
            if res.get("success"):
                eklenen.append(clean)
        return {
            "success": len(eklenen) > 0,
            "eklenen_sayisi": len(eklenen),
            "eklenenler": eklenen,
            "error": None if eklenen else "Geçerli konteyner numarası bulunamadı.",
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/kantar/takip/sil/{konteyner_no}")
def kantar_sil(konteyner_no: str):
    try:
        svc = _get_kantar()
        ok = svc.remove_from_tracking(konteyner_no)
        return {"success": bool(ok)}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/kantar/takip/kontrol-et")
def kantar_kontrol():
    try:
        svc = _get_kantar()
        res = svc.run_full_cycle()
        # run_full_cycle sometimes returns status=already_running
        ok = res.get("success", True) if "success" in res else res.get("status") != "error"
        if res.get("status") == "already_running":
            return {"success": False, "error": "Tarama zaten devam ediyor.", **res}
        return {"success": bool(ok), **res}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/kantar/takip/sorgula/{konteyner_no}")
def kantar_sorgula(konteyner_no: str):
    try:
        svc = _get_kantar()
        res = svc.query_single_now(konteyner_no)
        return res
    except Exception as e:
        return {"success": False, "error": str(e), "konteyner_no": konteyner_no}


def start(host: str = "127.0.0.1", port: int = 8060, open_browser: bool = True):
    import uvicorn

    url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/"
    print("=" * 64)
    print("  SmartClearance Web Ops Hub")
    print("  Modüller: Kokpit · GTB · Kantar")
    print(f"  Adres   : {url}")
    print("  Durdur  : CTRL+C")
    print("=" * 64)
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    host = os.environ.get("WEB_OPS_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_OPS_PORT", "8060"))
    open_br = os.environ.get("WEB_OPS_NO_BROWSER", "").strip() not in ("1", "true", "yes")
    start(host=host, port=port, open_browser=open_br)
