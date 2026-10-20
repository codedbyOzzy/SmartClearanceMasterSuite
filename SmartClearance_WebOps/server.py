# -*- coding: utf-8 -*-
"""
SmartClearance WebOps — tam özellikli yerel web sunucusu
Kokpit · GTB · Kantar (PDF indir / birleştir / sync / filtre dahil)
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cockpit_data import extract_beyanname_candidates, load_cockpit_records, load_evrim_raw, load_excel_raw_for_sync

app = FastAPI(title="SmartClearance WebOps", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(PACKAGE_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(PACKAGE_ROOT / "templates"))

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SmartClearance"
YILPORT_SESSION = CONFIG_DIR / "yilport_session.json"

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
    return templates.TemplateResponse(request, name, {"static_v": "20261020c", **ctx})


def _ok(**kwargs):
    return {"success": True, **kwargs}


def _err(msg: str, status: int = 400):
    return JSONResponse({"success": False, "error": msg}, status_code=status)


# ── Sayfalar ──────────────────────────────────────────────────────────────────

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
    yp = YILPORT_SESSION.exists()
    return {
        "status": "ok",
        "app": "SmartClearance_WebOps",
        "port": int(os.environ.get("WEBOPS_PORT", "8060")),
        "yilport_session": yp,
    }


# ── Kokpit ────────────────────────────────────────────────────────────────────

@app.get("/api/cockpit")
def api_cockpit(q: str = "", filter_type: str = "all", limit: int = Query(300, ge=1, le=1000)):
    return load_cockpit_records(q=q, filter_type=filter_type, limit=limit)


@app.get("/api/cockpit/export")
def api_cockpit_export(q: str = "", filter_type: str = "all"):
    data = load_cockpit_records(q=q, filter_type=filter_type, limit=1000)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Dosya", "Referans", "BL", "Aşama", "Hat", "Vergi", "Bayi", "Liman", "Beyanname"])
    for it in data.get("items") or []:
        w.writerow([
            it.get("dosya"), it.get("ref"), it.get("bl"), it.get("stage_title"),
            it.get("hat"), it.get("vergi_mail"), it.get("bayi"), it.get("liman"), it.get("beyanname_no"),
        ])
    raw = buf.getvalue().encode("utf-8-sig")
    name = f"Operasyon_Kokpiti_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        io.BytesIO(raw),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/api/cockpit/gtb/{beyanname_no}")
def api_cockpit_gtb(beyanname_no: str):
    try:
        return _gtb_svc().query_single_now(beyanname_no)
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── GTB ───────────────────────────────────────────────────────────────────────

@app.get("/api/gtb/takip/listele")
def gtb_listele(
    sadece_aktif: bool = True,
    filtre: str = Query("ALL"),  # ALL | IN_PROC | CLOSED
    q: str = "",
):
    try:
        items = _gtb_svc().list_tracked(only_active=sadece_aktif)
        q_clean = (q or "").strip().upper()
        ft = (filtre or "ALL").upper()
        beyannameler = []
        closed = in_proc = 0
        for r in items:
            b_no = str(r.get("beyanname_no") or "")
            if not b_no or b_no.startswith("BEYAN"):
                continue
            durum = str(r.get("durum") or r.get("gtb_durum") or "İzleniyor")
            kapandi = bool(r.get("kapandi")) or "kapan" in durum.lower() or "tamamlan" in durum.lower()
            if kapandi:
                closed += 1
            else:
                in_proc += 1
            if ft == "CLOSED" and not kapandi:
                continue
            if ft == "IN_PROC" and kapandi:
                continue
            row = {
                **r,
                "durum": durum,
                "kapandi": kapandi,
                "son_kontrol": r.get("son_kontrol") or r.get("son_sorgu_zamani") or "—",
                "son_kontrol_zamani": r.get("son_kontrol") or r.get("son_sorgu_zamani") or "—",
                "degisim_tarihi": r.get("degisim_tarihi") or "—",
                "ref": r.get("ref") or r.get("ref_no") or "—",
                "dosya_no": r.get("dosya_no") or "—",
                "firma": r.get("firma") or "—",
                "ekleyen_kullanici": r.get("ekleyen_kullanici") or "Sistem",
            }
            if q_clean:
                hay = f"{b_no} {row['dosya_no']} {row['ref']} {row['firma']} {durum}".upper()
                if q_clean not in hay:
                    continue
            beyannameler.append(row)
        return {
            "success": True,
            "beyannameler": beyannameler,
            "count": len(beyannameler),
            "stats": {
                "total": closed + in_proc,
                "closed": closed,
                "in_proc": in_proc,
                "last_scan": getattr(_gtb_svc(), "last_scan_time", "—"),
                "scanning": bool(getattr(_gtb_svc(), "is_scanning", False)),
            },
        }
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/gtb/takip/ekle")
def gtb_ekle(payload: Dict[str, Any] = Body(default={})):
    try:
        raw = payload.get("beyannameler") or payload.get("beyanname_no") or ""
        if isinstance(raw, list):
            text = "\n".join(map(str, raw))
        else:
            text = str(raw)
        candidates = extract_beyanname_candidates(text)
        dosya = str(payload.get("dosya_no") or "—")
        firma = str(payload.get("firma") or "WH-HANKOOK")
        ref = str(payload.get("ref") or payload.get("ref_no") or "—")
        eklenenler = []
        svc = _gtb_svc()
        for b_no in candidates:
            res = svc.add_to_tracking(b_no, dosya_no=dosya, firma=firma, ref=ref)
            if res.get("success"):
                eklenenler.append(b_no)
        return {
            "success": len(eklenenler) > 0,
            "eklenen_sayisi": len(eklenenler),
            "eklenen": len(eklenenler),
            "eklenenler": eklenenler,
            "error": None if eklenenler else "Geçerli 16 haneli beyanname bulunamadı.",
        }
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/gtb/takip/sil/{beyanname_no}")
def gtb_sil(beyanname_no: str):
    try:
        return _ok(removed=bool(_gtb_svc().remove_from_tracking(beyanname_no)))
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/gtb/takip/sil-coklu")
def gtb_sil_coklu(payload: Dict[str, Any] = Body(default={})):
    try:
        liste = payload.get("beyannameler") or []
        n = _gtb_svc().remove_multiple_from_tracking(list(liste))
        return _ok(removed=n)
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/gtb/takip/temizle")
def gtb_temizle():
    try:
        n = _gtb_svc().clear_all_tracking()
        return _ok(cleared=n)
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/gtb/takip/kontrol-et")
def gtb_kontrol():
    try:
        res = _gtb_svc().run_full_cycle()
        return {"success": bool(res.get("success")), **res}
    except Exception as e:
        return _err(str(e), 500)


@app.get("/api/gtb/takip/sorgula/{beyanname_no}")
def gtb_sorgula(beyanname_no: str):
    try:
        return _gtb_svc().query_single_now(beyanname_no)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/gtb/takip/sync")
def gtb_sync():
    """Evrim + Excel kayıtlarından beyanname aktar."""
    try:
        evrim = load_evrim_raw()
        n = _gtb_svc().auto_sync_from_evrim_and_excel(evrim)
        return _ok(eklenen=n)
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/gtb/takip/vergi-mail-taslak")
def gtb_vergi_mail(payload: Dict[str, Any] = Body(default={})):
    """Vergi talebi mail taslağı (Outlook COM yoksa mailto + metin)."""
    beyans = payload.get("beyannameler") or []
    if not beyans:
        return _err("Beyanname seçilmedi.")
    lines = []
    for b in beyans:
        lines.append(f"- Beyanname: {b}")
    subject = f"Vergi Talebi — {len(beyans)} beyanname"
    body = (
        "Merhaba,\n\n"
        "Aşağıdaki beyannameler için vergi ödeme bilgisini rica ederiz:\n\n"
        + "\n".join(lines)
        + "\n\nSaygılarımızla,\nDoğruer Gümrük Müşavirliği"
    )
    mailto = f"mailto:?subject={quote(subject)}&body={quote(body)}"
    return _ok(subject=subject, body=body, mailto=mailto, count=len(beyans))


# ── Kantar ────────────────────────────────────────────────────────────────────

@app.get("/api/kantar/takip/listele")
def kantar_listele(
    sadece_aktif: bool = True,
    filtre: str = Query("ALL"),  # ALL | READY | PENDING
    q: str = "",
):
    try:
        svc = _kantar_svc()
        items = svc.list_tracked(only_active=sadece_aktif)
        q_clean = (q or "").strip().upper()
        ft = (filtre or "ALL").upper()
        out = []
        ready = pending = 0
        for item in items:
            durum = str(item.get("durum") or "⏳ Tartım Bekliyor")
            t_val = str(item.get("tartim_no") or "").strip()
            dba_val = str(item.get("dba") or "").strip()
            has_t = bool(t_val) and t_val not in ("—", "-", "None", "")
            has_dba = bool(dba_val) and dba_val not in ("—", "-", "None", "")
            hazir = bool(item.get("hazir")) or "hazır" in durum.lower() or has_t or has_dba
            if hazir:
                ready += 1
            else:
                pending += 1
            if ft == "READY" and not hazir:
                continue
            if ft == "PENDING" and hazir:
                continue
            row = {
                **item,
                "hazir": hazir,
                "konteyner_no": item.get("konteyner_no") or "",
                "dosya_no": item.get("dosya_no") or "—",
                "ref": item.get("ref") or "—",
                "kaynak": item.get("kaynak") or "—",
                "tartim_no": item.get("tartim_no") or "—",
                "tarih": item.get("tarih") or "—",
                "plaka": item.get("plaka") or "—",
                "firma": item.get("firma") or "—",
                "dba": item.get("dba") or item.get("agirlik") or "—",
                "durum": durum,
                "son_kontrol": item.get("son_kontrol") or "—",
                "has_pdf": bool(
                    (item.get("yerel_pdf_yolu") and os.path.exists(str(item.get("yerel_pdf_yolu"))))
                    or item.get("pdf_url")
                    or hazir
                ),
            }
            if q_clean:
                hay = f"{row['konteyner_no']} {row['dosya_no']} {row['tartim_no']} {row['plaka']} {row['firma']} {row['dba']} {row['kaynak']}".upper()
                if q_clean not in hay:
                    continue
            out.append(row)
        return {
            "success": True,
            "items": out,
            "count": len(out),
            "stats": {
                "total": ready + pending,
                "ready": ready,
                "pending": pending,
                "last_scan": getattr(svc, "last_scan_time", "—"),
                "scanning": bool(getattr(svc, "is_scanning", False)),
                "yilport_session": YILPORT_SESSION.exists(),
            },
        }
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/ekle")
def kantar_ekle(payload: Dict[str, Any] = Body(default={})):
    try:
        raw = str(payload.get("konteynerler") or payload.get("konteyner_no") or "")
        dosya = str(payload.get("dosya_no") or "—")
        ref = str(payload.get("ref") or "—")
        firma = str(payload.get("firma") or "WH-HANKOOK")
        kaynak = str(payload.get("kaynak") or "manuel")
        eklenen = []
        svc = _kantar_svc()
        for p in re.split(r"[\s,;/\n\r]+", raw):
            clean = re.sub(r"[^A-Z0-9]", "", p.upper())
            if len(clean) < 4:
                continue
            if svc.add_to_tracking(clean, dosya_no=dosya, ref=ref, firma=firma, kaynak=kaynak).get("success"):
                eklenen.append(clean)
        return {
            "success": len(eklenen) > 0,
            "eklenen_sayisi": len(eklenen),
            "eklenenler": eklenen,
            "error": None if eklenen else "Geçerli konteyner bulunamadı.",
        }
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/sil/{konteyner_no}")
def kantar_sil(konteyner_no: str):
    try:
        return _ok(removed=bool(_kantar_svc().remove_from_tracking(konteyner_no)))
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/sil-coklu")
def kantar_sil_coklu(payload: Dict[str, Any] = Body(default={})):
    try:
        n = _kantar_svc().remove_multiple_from_tracking(list(payload.get("konteynerler") or []))
        return _ok(removed=n)
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/temizle")
def kantar_temizle():
    try:
        return _ok(cleared=_kantar_svc().clear_all_tracking())
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/kontrol-et")
def kantar_kontrol():
    try:
        res = _kantar_svc().run_full_cycle()
        if res.get("status") == "already_running":
            return {"success": False, "error": "Tarama zaten devam ediyor.", **res}
        ok = res.get("success", True) if "success" in res else True
        return {"success": bool(ok), **res}
    except Exception as e:
        return _err(str(e), 500)


@app.get("/api/kantar/takip/sorgula/{konteyner_no}")
def kantar_sorgula(konteyner_no: str):
    try:
        return _kantar_svc().query_single_now(konteyner_no)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/kantar/takip/pdf/{konteyner_no}")
def kantar_pdf(konteyner_no: str):
    """Seçili konteynerin kantar tike PDF'ini indirir."""
    try:
        path = _kantar_svc().download_and_get_pdf(konteyner_no)
        if not path or not os.path.exists(path):
            return _err("PDF bulunamadı. Önce tartımı sorgulayın / tike hazır olmalı.", 404)
        clean = re.sub(r"[^A-Z0-9]", "", konteyner_no.upper())
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=f"Kantar_{clean}.pdf",
        )
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/pdf-birlestir")
def kantar_pdf_merge(payload: Dict[str, Any] = Body(default={})):
    """Hazır tike PDF'lerini tek dosyada birleştirip indirir."""
    try:
        svc = _kantar_svc()
        cntrs = payload.get("konteynerler") or None
        if cntrs is not None and len(cntrs) == 0:
            cntrs = None
        out_dir = CONFIG_DIR / "Kantar_Tickets"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / f"Kantar_Birlesik_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        res = svc.merge_all_pdfs(out_path, konteyner_list=cntrs)
        if not res.get("success") or not res.get("merged_path") or not os.path.exists(res["merged_path"]):
            return _err(res.get("error") or "PDF birleştirilemedi.", 400)
        return FileResponse(
            res["merged_path"],
            media_type="application/pdf",
            filename=os.path.basename(res["merged_path"]),
        )
    except Exception as e:
        return _err(str(e), 500)


@app.post("/api/kantar/takip/sync")
def kantar_sync():
    try:
        evrim = load_evrim_raw()
        excel = load_excel_raw_for_sync()
        n = _kantar_svc().auto_sync_from_evrim_and_excel(evrim_records=evrim, excel_records=excel)
        return _ok(eklenen=n)
    except Exception as e:
        return _err(str(e), 500)


@app.get("/api/kantar/yilport/durum")
def yilport_durum():
    return _ok(exists=YILPORT_SESSION.exists(), path=str(YILPORT_SESSION))


@app.post("/api/kantar/yilport/oturum")
def yilport_oturum(payload: Dict[str, Any] = Body(default={})):
    """Tarayıcıdan kopyalanan çerez metnini kaydeder."""
    raw = str(payload.get("cookie") or payload.get("cookies") or "").strip().strip('"').strip("'")
    if not raw:
        return _err("Çerez metni boş.")
    cookies_dict = {}
    # JSON dict veya document.cookie formatı
    if raw.startswith("{"):
        try:
            cookies_dict = json.loads(raw)
        except Exception:
            return _err("JSON çerez parse edilemedi.")
    else:
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cookies_dict[k.strip()] = v.strip().strip('"')
    if not cookies_dict:
        return _err("Geçerli çerez bulunamadı.")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(YILPORT_SESSION, "w", encoding="utf-8") as f:
        json.dump(cookies_dict, f, indent=2)
    return _ok(saved=len(cookies_dict))


def main():
    import uvicorn

    host = os.environ.get("WEBOPS_HOST", "127.0.0.1")
    port = int(os.environ.get("WEBOPS_PORT", "8060"))
    open_br = os.environ.get("WEBOPS_NO_BROWSER", "").lower() not in ("1", "true", "yes")
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/"
    print("=" * 60)
    print("  SmartClearance WebOps (tam özellik)")
    print("  Kokpit · GTB · Kantar + PDF")
    print(f"  {url}")
    print("=" * 60)
    if open_br:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
