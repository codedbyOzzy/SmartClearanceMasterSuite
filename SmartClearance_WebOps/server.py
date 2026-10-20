# -*- coding: utf-8 -*-
"""
SmartClearance WebOps — bağımsız yerel web sunucusu
Sadece: Operasyon Kokpiti · GTB · Kantar
"""
from __future__ import annotations

import os
import re
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cockpit_data import extract_beyanname_candidates, load_cockpit_records

app = FastAPI(title="SmartClearance WebOps", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(PACKAGE_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(PACKAGE_ROOT / "templates"))

_gtb = None
_kantar = None
_lock = threading.Lock()


def _gtb_svc():
    global _gtb
    with _lock:
        if _gtb is None:
            from tools.gtb_engine.gtb_tracker_service import get_gtb_tracker_service

            _gtb = get_gtb_tracker_service()
            try:
                _gtb.start_worker()
            except Exception:
                pass
        return _gtb


def _kantar_svc():
    global _kantar
    with _lock:
        if _kantar is None:
            from tools.kantar_engine.kantar_tracker_service import get_kantar_tracker_service

            _kantar = get_kantar_tracker_service()
            try:
                _kantar.start_worker()
            except Exception:
                pass
        return _kantar


def _page(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request, name, {"static_v": "20261020b", **ctx})


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _page(request, "index.html", title="SmartClearance")


@app.get("/kokpit", response_class=HTMLResponse)
def page_kokpit(request: Request):
    return _page(request, "kokpit.html", title="Operasyon Kokpiti")


@app.get("/gtb", response_class=HTMLResponse)
def page_gtb(request: Request):
    return _page(request, "gtb.html", title="GTB Beyanname Takip")


@app.get("/kantar", response_class=HTMLResponse)
def page_kantar(request: Request):
    return _page(request, "kantar.html", title="Kantar DBA Takip")


@app.get("/health")
def health():
    return {"status": "ok", "app": "SmartClearance_WebOps", "port": int(os.environ.get("WEBOPS_PORT", "8060"))}


@app.get("/api/cockpit")
def api_cockpit(q: str = "", filter_type: str = "all", limit: int = Query(200, ge=1, le=500)):
    return load_cockpit_records(q=q, filter_type=filter_type, limit=limit)


@app.get("/api/gtb/takip/listele")
def gtb_listele(sadece_aktif: bool = True):
    try:
        items = _gtb_svc().list_tracked(only_active=sadece_aktif)
        beyannameler = []
        for r in items:
            beyannameler.append(
                {
                    **r,
                    "durum": r.get("durum") or r.get("gtb_durum") or "İzleniyor",
                    "son_kontrol": r.get("son_kontrol") or r.get("son_sorgu_zamani") or "—",
                    "son_kontrol_zamani": r.get("son_kontrol") or r.get("son_sorgu_zamani") or "—",
                    "ekleyen_kullanici": r.get("ekleyen_kullanici") or "Sistem",
                }
            )
        return {"success": True, "beyannameler": beyannameler, "count": len(beyannameler)}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "beyannameler": []}, status_code=500)


@app.post("/api/gtb/takip/ekle")
def gtb_ekle(payload: Dict[str, Any] = Body(default={})):
    try:
        raw = payload.get("beyannameler") or payload.get("beyanname_no") or ""
        candidates = extract_beyanname_candidates(str(raw) if not isinstance(raw, list) else "\n".join(map(str, raw)))
        eklenenler = []
        svc = _gtb_svc()
        for b_no in candidates:
            res = svc.add_to_tracking(b_no)
            if res.get("success"):
                eklenenler.append(b_no)
        return {
            "success": len(eklenenler) > 0,
            "eklenen_sayisi": len(eklenenler),
            "eklenen": len(eklenenler),
            "eklenenler": eklenenler,
            "error": None if eklenenler else "Geçerli beyanname bulunamadı.",
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "eklenen_sayisi": 0}, status_code=500)


@app.post("/api/gtb/takip/sil/{beyanname_no}")
def gtb_sil(beyanname_no: str):
    try:
        return {"success": bool(_gtb_svc().remove_from_tracking(beyanname_no))}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/gtb/takip/kontrol-et")
def gtb_kontrol():
    try:
        res = _gtb_svc().run_full_cycle()
        return {"success": bool(res.get("success")), **res}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/gtb/takip/sorgula/{beyanname_no}")
def gtb_sorgula(beyanname_no: str):
    try:
        return _gtb_svc().query_single_now(beyanname_no)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/kantar/takip/listele")
def kantar_listele(sadece_aktif: bool = True):
    try:
        svc = _kantar_svc()
        items = svc.list_tracked(only_active=sadece_aktif)
        return {"success": True, "items": items, "count": len(items), "last_scan": getattr(svc, "last_scan_time", "—")}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "items": []}, status_code=500)


@app.post("/api/kantar/takip/ekle")
def kantar_ekle(payload: Dict[str, Any] = Body(default={})):
    try:
        raw = str(payload.get("konteynerler") or payload.get("konteyner_no") or "")
        eklenen = []
        svc = _kantar_svc()
        for p in re.split(r"[\s,;/\n\r]+", raw):
            clean = re.sub(r"[^A-Z0-9]", "", p.upper())
            if len(clean) < 4:
                continue
            if svc.add_to_tracking(clean, kaynak="manuel").get("success"):
                eklenen.append(clean)
        return {
            "success": len(eklenen) > 0,
            "eklenen_sayisi": len(eklenen),
            "eklenenler": eklenen,
            "error": None if eklenen else "Geçerli konteyner bulunamadı.",
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/kantar/takip/sil/{konteyner_no}")
def kantar_sil(konteyner_no: str):
    try:
        return {"success": bool(_kantar_svc().remove_from_tracking(konteyner_no))}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/kantar/takip/kontrol-et")
def kantar_kontrol():
    try:
        res = _kantar_svc().run_full_cycle()
        if res.get("status") == "already_running":
            return {"success": False, "error": "Tarama zaten devam ediyor.", **res}
        ok = res.get("success", True) if "success" in res else True
        return {"success": bool(ok), **res}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/kantar/takip/sorgula/{konteyner_no}")
def kantar_sorgula(konteyner_no: str):
    try:
        return _kantar_svc().query_single_now(konteyner_no)
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    import uvicorn

    host = os.environ.get("WEBOPS_HOST", "127.0.0.1")
    port = int(os.environ.get("WEBOPS_PORT", "8060"))
    open_br = os.environ.get("WEBOPS_NO_BROWSER", "").lower() not in ("1", "true", "yes")
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/"
    print("=" * 60)
    print("  SmartClearance WebOps")
    print("  Kokpit · GTB · Kantar")
    print(f"  {url}")
    print("  CTRL+C ile durdurun")
    print("=" * 60)
    if open_br:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
