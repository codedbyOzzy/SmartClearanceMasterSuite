# -*- coding: utf-8 -*-
"""
master_pipeline.py — Master Data Kontrolu akisini uctan uca calistirir:
faturalari oku (mevcut app.parsers.process_pdf ile) -> master katalogla
karsilastir -> eksik urunler icin "mastera eklenecek" cikti Excel'ini uret.
"""
from tools.smart_clearance_engine.config import EKLENECEK_TEMPLATE_XLSX, MASTER_KATALOG_XLSX
from tools.smart_clearance_engine.parsers import process_pdf
from tools.smart_clearance_engine.parsers.master_katalog import load_master_katalog
from tools.smart_clearance_engine.domain.master_check import check_items_against_master, MISSING_CODE, DESCRIPTION_MISMATCH
from tools.smart_clearance_engine.excel.eklenecek_writer import build_eklenecek_workbook, build_tanim_uyusmuyor_workbook


def run_master_pipeline(pdf_paths, run_dir):
    try:
        katalog = load_master_katalog(MASTER_KATALOG_XLSX)
    except Exception as e:
        return {
            "katalog_hata": str(e),
            "katalog_kayit_sayisi": 0,
            "katalog_yinelenen_sayisi": 0,
            "parse_errors": [],
            "total": 0, "matched_count": 0, "mismatch_count": 0, "missing_count": 0,
            "rows": [], "eklenecek_filename": None, "tanim_uyusmuyor_filename": None,
        }

    all_items = []
    parse_errors = []
    for path in pdf_paths:
        try:
            evrak = process_pdf(path)
        except Exception as e:
            parse_errors.append({"filename": path.name, "error": str(e)})
            continue
        src_items = (evrak.packing_list.items if evrak.packing_list else []) or \
                    (evrak.invoice.items if evrak.invoice else [])
        # Her urun KENDI faturasinin mensesini tasir — ayni Master Data Kontrol
        # calistirmasinda FARKLI mense'li birden fazla fatura ayni anda islenirse
        # (orn. 5-10 fatura, karisik Kore/Macaristan), tek bir parti-geneli mense
        # varsaymak yanlis olurdu. Evrak seviyesindeki tespit (detect_origin,
        # gonderici basligina bakar) HER ZAMAN kullanilir — Kore sablonundaki
        # satir sonu ham ulke kodu ("KR" gibi) schema.ORIGIN_DISPLAY_NAME'in
        # bekledigi "KOREA"/"HUNGARY" formatiyla uyumsuz oldugu icin guvenilmez
        # (gercek bir dosyada bu yuzden Mense hucresi bos cikan bir bug yakalandi).
        evrak_origin = (evrak.packing_list.origin_country if evrak.packing_list else None) or \
                       (evrak.invoice.origin_country if evrak.invoice else None)
        for item in src_items:
            item.origin = evrak_origin
        all_items.extend(src_items)

    check = check_items_against_master(all_items, katalog)

    missing_rows = [r for r in check.rows if r.status == MISSING_CODE]
    eklenecek_filename = None
    if missing_rows:
        wb, _ = build_eklenecek_workbook(EKLENECEK_TEMPLATE_XLSX, missing_rows)
        eklenecek_filename = "mastera_eklenecek.xlsx"
        wb.save(run_dir / "outputs" / eklenecek_filename)

    mismatch_rows = [r for r in check.rows if r.status == DESCRIPTION_MISMATCH]
    tanim_uyusmuyor_filename = None
    if mismatch_rows:
        wb, _ = build_tanim_uyusmuyor_workbook(EKLENECEK_TEMPLATE_XLSX, mismatch_rows)
        tanim_uyusmuyor_filename = "tanim_uyusmuyor.xlsx"
        wb.save(run_dir / "outputs" / tanim_uyusmuyor_filename)

    return {
        "katalog_hata": None,
        "katalog_kayit_sayisi": katalog.row_count,
        "katalog_yinelenen_sayisi": len(katalog.duplicate_codes),
        "parse_errors": parse_errors,
        "total": len(check.rows),
        "matched_count": check.matched_count,
        "mismatch_count": check.mismatch_count,
        "missing_count": check.missing_count,
        "rows": [
            {
                "product_code": r.product_code,
                "invoice_description": r.invoice_description,
                "quantity": r.quantity,
                "status": r.status,
                "master_description": r.master_description,
                "master_turkish_description": r.master_turkish_description,
                "master_gtip": r.master_gtip,
                "master_origin": r.master_origin,
                "master_status": r.master_status,
                "origin": r.origin,
            }
            for r in check.rows
        ],
        "eklenecek_filename": eklenecek_filename,
        "tanim_uyusmuyor_filename": tanim_uyusmuyor_filename,
    }
