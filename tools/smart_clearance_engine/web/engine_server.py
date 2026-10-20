# -*- coding: utf-8 -*-
"""
engine_server.py — SmartClearance Motoru Bağımsız Yerel Web Sunucusu
Doğruer MasterSuite için Excel Aktarım & Master Data Kontrol servislerini sağlar.
Port: 8050 (Varsayılan)
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from typing import List

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import uvicorn
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tools.smart_clearance_engine.config import (
    TEMPLATES_DIR, STATIC_DIR, TEMPLATE_XLSX
)
from tools.smart_clearance_engine.storage import (
    new_run_dir, run_dir_for, safe_output_path,
    ensure_template, template_exists, save_template,
    master_katalog_exists, save_master_katalog,
    ensure_eklenecek_template
)
from tools.smart_clearance_engine.services.pipeline import run_pipeline
from tools.smart_clearance_engine.services.master_pipeline import run_master_pipeline
from tools.smart_clearance_engine.services.mail_export import build_excel_mail, build_master_mail

app = FastAPI(title="SmartClearance Engine", docs_url=None, redoc_url=None)

# Statik dosyaları bağla
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 şablonları
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["acik_talep_sayisi"] = lambda: 0
templates.env.globals["static_v"] = "2026"
templates.env.filters["bahsetme_vurgula"] = lambda text: text or ""
templates.env.filters["tarih_bicimle"] = lambda d: str(d) if d else ""
templates.env.filters["goreli_zaman"] = lambda d: str(d) if d else ""

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

@app.on_event("startup")
def startup_event():
    ensure_template()
    ensure_eklenecek_template()

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "SmartClearanceEngine"}

@app.get("/", response_class=HTMLResponse)
def root_redirect():
    return RedirectResponse(url="/excel-aktarim", status_code=303)

# ══════════════════════════════════════════════════════════════════════════════
# MODÜL 1: EXCEL AKTARIM (FATURA / PACKING LIST / KONŞİMENTO -> EVRİM EXCEL)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/excel-aktarim", response_class=HTMLResponse)
def excel_aktarim_home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "static_v": "2026", "kullanici": "MasterSuite"}
    )

@app.post("/islem")
async def islem(pdfler: List[UploadFile] = File(...)):
    ensure_template()
    if not template_exists():
        return RedirectResponse(url="/excel-aktarim?hata=sablon_bulunamadi", status_code=303)

    run_id, run_dir = new_run_dir()
    fatura_dir = run_dir / "uploads"
    pdf_paths = []
    for f in pdfler:
        if not f.filename.lower().endswith(".pdf"):
            continue
        try:
            dest = fatura_dir / Path(f.filename).name
            dest.write_bytes(await f.read())
            pdf_paths.append(dest)
        except OSError:
            continue

    report = run_pipeline(pdf_paths, run_dir)
    (run_dir / "rapor.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # MasterSuite Aktivite & Not Günlüğüne Otomatik Kayıt
    try:
        from tools.supabase_sync_manager import get_supabase_manager
        sm = get_supabase_manager()
        if sm:
            for inv in report.get("invoices", []):
                inv_no = inv.get("invoice_no", "")
                k_count = len(inv.get("kalemler", []))
                sm.add_activity_log(
                    dosya_no="",
                    ref_no=inv_no,
                    islem_tipi="FATURA",
                    baslik=f"Evrim Beyanname Exceli Üretildi ({inv_no})",
                    icerik=f"Fatura No: {inv_no} | {k_count} kalem ürün | Çıktı: {inv.get('output_filename')}",
                    etiket="Hata" if inv.get("parse_failed") else "Tamamlandı"
                )
    except Exception as e:
        try:
            from tools.ops_log import exception as ops_exception
            ops_exception("smart_clearance", "Aktivite günlüğü yazılamadı (excel aktarım)", e)
        except Exception:
            pass

    return RedirectResponse(url=f"/sonuc/{run_id}", status_code=303)

@app.get("/sonuc/{run_id}", response_class=HTMLResponse)
def sonuc(request: Request, run_id: str):
    run_dir = run_dir_for(run_id)
    report_path = run_dir / "rapor.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for inv in report.get("invoices", []):
        inv["mail"] = build_excel_mail(inv)
    return templates.TemplateResponse(
        "sonuc.html",
        {"request": request, "run_id": run_id, "report": report, "static_v": "2026"}
    )

@app.get("/indir/{run_id}/{dosya_adi}")
def indir_cikti(run_id: str, dosya_adi: str):
    run_dir = run_dir_for(run_id)
    path = safe_output_path(run_dir, dosya_adi)
    if path is None:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return FileResponse(path, media_type=XLSX_MEDIA, filename=path.name)

@app.get("/sablon-indir")
def indir_sablon():
    return FileResponse(TEMPLATE_XLSX, media_type=XLSX_MEDIA, filename="Evrim_sablon.xlsx")

@app.post("/sablon/yukle")
async def sablon_yukle(sablon: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await sablon.read())
        tmp_path = Path(tmp.name)
    save_template(tmp_path)
    tmp_path.unlink(missing_ok=True)
    return RedirectResponse(url="/excel-aktarim?mesaj=sablon_guncellendi", status_code=303)


# ══════════════════════════════════════════════════════════════════════════════
# MODÜL 2: MASTER DATA KONTROL (ÜRÜN KODU, GTİP & TANIM ÇAPRAZ DENETİMİ)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/master-kontrol", response_class=HTMLResponse)
def master_kontrol_home(request: Request):
    return templates.TemplateResponse(
        "master_kontrol.html",
        {"request": request, "katalog_var": master_katalog_exists(), "static_v": "2026", "kullanici": "MasterSuite"}
    )

@app.post("/master-kontrol/katalog-yukle")
async def master_katalog_yukle(katalog: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await katalog.read())
        tmp_path = Path(tmp.name)
    save_master_katalog(tmp_path)
    tmp_path.unlink(missing_ok=True)
    return RedirectResponse(url="/master-kontrol?mesaj=katalog_guncellendi", status_code=303)

@app.post("/master-kontrol")
async def master_kontrol_calistir(faturalar: List[UploadFile] = File(...)):
    if not master_katalog_exists():
        return RedirectResponse(url="/master-kontrol?hata=katalog_yok", status_code=303)

    run_id, run_dir = new_run_dir()
    fatura_dir = run_dir / "uploads"
    pdf_paths = []
    for f in faturalar:
        if not f.filename.lower().endswith(".pdf"):
            continue
        try:
            dest = fatura_dir / Path(f.filename).name
            dest.write_bytes(await f.read())
            pdf_paths.append(dest)
        except OSError:
            continue

    report = run_master_pipeline(pdf_paths, run_dir)
    (run_dir / "master_rapor.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # MasterSuite Aktivite & Not Günlüğüne Otomatik Kayıt
    try:
        from tools.supabase_sync_manager import get_supabase_manager
        sm = get_supabase_manager()
        if sm:
            tot = report.get("total", 0)
            mat = report.get("matched_count", 0)
            mis = report.get("missing_count", 0)
            tag = "Tamamlandı" if mis == 0 else "Acil"
            sm.add_activity_log(
                dosya_no="",
                ref_no="",
                islem_tipi="NOT",
                baslik=f"Master Data Kontrol Tamamlandı ({tot} Ürün)",
                icerik=f"Toplam: {tot} ürün | Eşleşen: {mat} | Tanım Farklı: {report.get('mismatch_count', 0)} | Master'da Olmayan: {mis}",
                etiket=tag
            )
    except Exception as e:
        try:
            from tools.ops_log import exception as ops_exception
            ops_exception("smart_clearance", "Aktivite günlüğü yazılamadı (master kontrol)", e)
        except Exception:
            pass

    return RedirectResponse(url=f"/master-kontrol/sonuc/{run_id}", status_code=303)

@app.get("/master-kontrol/sonuc/{run_id}", response_class=HTMLResponse)
def master_kontrol_sonuc(request: Request, run_id: str):
    run_dir = run_dir_for(run_id)
    report = json.loads((run_dir / "master_rapor.json").read_text(encoding="utf-8"))
    if not report.get("katalog_hata"):
        report["mail"] = build_master_mail(report)
    return templates.TemplateResponse(
        "master_sonuc.html",
        {"request": request, "run_id": run_id, "report": report, "static_v": "2026"}
    )

@app.get("/master-kontrol/indir/{run_id}/{dosya_adi}")
def master_kontrol_indir(run_id: str, dosya_adi: str):
    run_dir = run_dir_for(run_id)
    path = safe_output_path(run_dir, dosya_adi)
    if path is None:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return FileResponse(path, media_type=XLSX_MEDIA, filename=path.name)

if __name__ == "__main__":
    port = int(os.environ.get("SC_PORT", 8050))
    print(f"SmartClearance Engine starting on http://127.0.0.1:{port} ...")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
