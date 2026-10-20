# -*- coding: utf-8 -*-
"""
pipeline.py — Bir "islem"in (run) tum adimlarini sirayla calistirir:
PDF'leri oku -> fatura numarasina gore grupla -> her fatura icin capraz
kontrol yap -> PL+Fatura kalemlerini satir satir birlestir -> her fatura
icin KENDI ayri EXCEL_AKTARIM ciktisini uret.

Web katmani (routers) SADECE bu modulu cagirir; parsing/excel/gruplama
detaylarini bilmesi gerekmez.
"""
from tools.smart_clearance_engine.config import TEMPLATE_XLSX
from tools.smart_clearance_engine.parsers import process_pdf
from tools.smart_clearance_engine.parsers.common import parse_invoice_date
from tools.smart_clearance_engine.domain.cross_check import check_evrak_seti
from tools.smart_clearance_engine.excel.writer import build_invoice_workbook
from tools.smart_clearance_engine.services.grouping import group_by_invoice
from tools.smart_clearance_engine.services.merge_lines import build_declaration_lines


def run_pipeline(pdf_paths, run_dir):
    """Donen: rapor (dict) — sablonda dogrudan kullanilabilir.
    Her fatura icin runs/<run_id>/outputs/<invoice_no>.xlsx uretilir.
    """
    evrak_list = []
    parse_errors = []
    for path in pdf_paths:
        try:
            evrak_list.append(process_pdf(path))
        except Exception as e:
            parse_errors.append({"filename": path.name, "error": str(e)})

    groups = group_by_invoice(evrak_list)
    outputs_dir = run_dir / "outputs"

    invoices = []
    for invoice_no, evrak in sorted(groups.items()):
        warnings, infos = check_evrak_seti(evrak)
        lines = build_declaration_lines(evrak)

        origin, po_no, inv_date = _shipment_meta(evrak)
        if not lines:
            invoices.append({
                "invoice_no": invoice_no,
                "source_files": [str(f) for f in evrak.files],
                "warnings": list(warnings) + ["PDF tanınmadı / kalem yok — Excel üretilmedi"],
                "infos": infos,
                "kalemler": [],
                "unconfirmed_count": 0,
                "output_filename": None,
                "parse_failed": True,
            })
            continue

        wb, item_summary = build_invoice_workbook(
            TEMPLATE_XLSX, lines, invoice_no, inv_date, po_no, origin
        )
        out_filename = f"{_safe_filename(invoice_no)}.xlsx"
        wb.save(outputs_dir / out_filename)

        invoices.append({
            "invoice_no": invoice_no,
            "source_files": [str(f) for f in evrak.files],
            "warnings": warnings,
            "infos": infos,
            "kalemler": item_summary,  # [{"kod","aciklama","miktar","confirmed"}, ...]
            "unconfirmed_count": sum(1 for k in item_summary if not k["confirmed"]),
            "output_filename": out_filename,
            "parse_failed": False,
        })

    return {"invoices": invoices, "parse_errors": parse_errors}


def _shipment_meta(evrak):
    origin = (evrak.packing_list.origin_country if evrak.packing_list else None) or \
             (evrak.invoice.origin_country if evrak.invoice else None)
    po_no = evrak.packing_list.po_no if evrak.packing_list else None
    date_str = (evrak.packing_list.invoice_date if evrak.packing_list else None) or \
               (evrak.invoice.invoice_date if evrak.invoice else None)
    return origin, po_no, parse_invoice_date(date_str)


def _safe_filename(invoice_no):
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(invoice_no))
