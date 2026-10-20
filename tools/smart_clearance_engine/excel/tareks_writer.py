# -*- coding: utf-8 -*-
"""
tareks_writer.py — Taslak pipeline'inin urettigi fatura verisini
TAREKSTASLAK.xlsx formatinda (35 sutun) bir Excel workbook'una yazar.

sablon.xlsx KULLANILMAZ: basliklar bu koddan yazilir, stil minimumdur.
Eksik/belirsiz alanlar SARI hucreyle isaretlenir.
"""
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment

from tools.smart_clearance_engine.excel import tareks_schema as S

WARN_FILL  = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
HEADER_FONT = Font(bold=True)


def _parse_date(date_str):
    """'MAY.05.2026' veya '2026.05.05' ya da '2026-05-05' formatlarini
    datetime.date nesnesine cevirir (saat bilgisi olmadan)."""
    if not date_str:
        return None
    from datetime import datetime as _dt
    for fmt in ("%b.%d.%Y", "%Y.%m.%d", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return _dt.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            pass
    return date_str   # ceviremediyse string olarak yaz


def build_tareks_workbook(fatura: dict) -> openpyxl.Workbook:
    """fatura: draft_pipeline'in urettigi tek bir fatura sozlugu.
    Donen: openpyxl.Workbook (kaydedilmeye/stream'e hazir)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = S.SHEET_NAME

    # --- 1. satir: basliklar ------------------------------------------------
    for col_idx, baslik in S.HEADERS.items():
        cell = ws.cell(row=1, column=col_idx, value=baslik)
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    # --- Fatura genelinde sabit olan degerler --------------------------------
    invoice_no      = fatura.get("invoice_no")
    invoice_date    = _parse_date(fatura.get("invoice_date"))
    ctr_no          = fatura.get("ctr_no")
    origin_country  = fatura.get("origin_country") or ""
    mense_kod       = S.MENSE_KOD_MAP.get(origin_country.upper(), None)

    # Belge No: lc_no, bl_no ya da packing list'te bulunan numara
    belge_no = fatura.get("bl_no") or fatura.get("lc_no") or None

    # --- Veri satirlari ------------------------------------------------------
    for row_idx, kalem in enumerate(fatura.get("kalemler", []), start=S.FIRST_DATA_ROW):
        marka      = (kalem.get("marka") or "").upper()
        imalatci   = S.OZL_IMALATCI_MAP.get(marka, {})
        has_warn   = bool(kalem.get("warnings"))

        values = {
            S.COL_GTIP:          kalem.get("gtip"),
            S.COL_MENSE:         mense_kod,
            S.COL_BELGE_TURU:    S.BELGE_TURU_SABIT,
            S.COL_BELGE_TARIHI:  None,
            S.COL_BELGE_NO:      belge_no,
            S.COL_MUAFIYET:      kalem.get("muafiyet"),
            S.COL_TICARI_TANIM:  kalem.get("turkce_tanim"),   # Turkce tanim: RADYAL BINEK OTO...
            S.COL_FATURA_TARIHI: invoice_date,
            S.COL_FATURA_NO:     invoice_no,
            S.COL_MIKTAR:        kalem.get("miktar"),
            S.COL_MIKTAR_CINSI:  S.MIKTAR_CINSI_SABIT,
            S.COL_KALEM_FIYAT:   kalem.get("kalem_fiyat"),
            S.COL_KAP_ADEDI:     S.KAP_ADEDI_SABIT,
            S.COL_KONTEYNER:     ctr_no,
            S.COL_OZL_UNVAN:     imalatci.get("unvan"),
            S.COL_OZL_ADRES:     imalatci.get("adres"),
            S.COL_OZL_TELEFON:   imalatci.get("telefon"),
            S.COL_OZL_MARKA:     kalem.get("marka"),
            S.COL_OZL_MODEL:     kalem.get("ticari_tanim"),   # Model kodu: 185/65R14T,04,LW31
            S.COL_OZL_URUN_ADI:  kalem.get("turkce_tanim"),
            27:                  S.GONDER_SABIT,   # NOT NULL — her zaman 'True'
        }

        for col_idx in range(1, S.TOTAL_COLS + 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=values.get(col_idx))
            if has_warn:
                cell.fill = WARN_FILL
            if col_idx in (S.COL_BELGE_TARIHI, S.COL_FATURA_TARIHI) and values.get(col_idx) is not None:
                cell.number_format = "DD.MM.YYYY"
            
            # Fix decimal rounding issues visually affecting imports
            if col_idx == S.COL_KALEM_FIYAT:
                cell.number_format = '0.00'

    # --- Sutun genislikleri (okunabilirlik) ----------------------------------
    COL_WIDTHS = {
        S.COL_GTIP:          15,
        S.COL_MENSE:         10,
        S.COL_BELGE_TURU:    14,
        S.COL_BELGE_NO:      18,
        S.COL_MUAFIYET:      20,
        S.COL_TICARI_TANIM:  30,
        S.COL_FATURA_NO:     16,
        S.COL_MIKTAR:        8,
        S.COL_KALEM_FIYAT:   14,
        S.COL_KONTEYNER:     16,
        S.COL_OZL_UNVAN:     35,
        S.COL_OZL_ADRES:     45,
        S.COL_OZL_MARKA:     12,
        S.COL_OZL_MODEL:     20,
        S.COL_OZL_URUN_ADI:  25,
    }
    col_letter = lambda n: openpyxl.utils.get_column_letter(n)
    for col_idx, width in COL_WIDTHS.items():
        ws.column_dimensions[col_letter(col_idx)].width = width

    return wb
