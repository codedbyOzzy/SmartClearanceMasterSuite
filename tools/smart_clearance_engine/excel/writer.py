# -*- coding: utf-8 -*-
"""
writer.py — Sablonun yapisal iskeletini (sutunlar/fontlar) kullanarak,
TEK BIR FATURAYA OZEL, bastan temiz bir EXCEL_AKTARIM ciktisi uretir.

Belirsiz/dogrulanamayan degerler (mense kodu bulunamadi, fiyat/agirlik
eksik) SARI ile isaretlenir ve hucreye aciklayici bir YORUM (comment)
eklenir — sutun yapisi degismedigi icin ek bir "not" sutunu KULLANILMAZ.
"""
from copy import copy

import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.comments import Comment

from tools.smart_clearance_engine.excel import schema as S

ASSUMPTION_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
DATA_SHEET = "Sayfa1"


def build_invoice_workbook(template_path, lines, invoice_no, invoice_date, po_no, origin_country):
    """lines: DeclarationLine listesi (bkz. services/merge_lines.py).
    Donen: (workbook, ozet_listesi [(code, quantity, confirmed), ...])
    """
    wb = openpyxl.load_workbook(template_path)
    ws = wb[DATA_SHEET]
    style_row = ws[S.FIRST_DATA_ROW] if ws.max_row >= S.FIRST_DATA_ROW else ws[1]

    _clear_existing_data_rows(ws)

    coo_code = S.COO_CODE_MAP.get(origin_country)
    referans = f"{po_no}{S.REFERANS_SUFFIX}" if po_no else None

    summary = []
    row_idx = S.FIRST_DATA_ROW
    for line in lines:
        notes = _uncertainty_notes(line, coo_code, origin_country)
        values = _row_values(line, coo_code, invoice_no, invoice_date, referans)

        for col_idx in range(1, S.TOTAL_COLS + 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=values.get(col_idx))
            if col_idx - 1 < len(style_row):
                src = style_row[col_idx - 1]
                if src.font:
                    cell.font = copy(src.font)
                if src.number_format:
                    cell.number_format = src.number_format
            
            # Fix decimal rounding issues visually affecting imports
            if col_idx == S.COL_NET_PRICE:
                cell.number_format = '0.00'
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 20
            elif col_idx in (S.COL_BRUT, S.COL_NET):
                cell.number_format = '0.000'
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 20
                
            if notes:
                cell.fill = ASSUMPTION_FILL

        if notes:
            ws.cell(row=row_idx, column=S.COL_CMMF).comment = Comment(
                "; ".join(notes), "Evrim Otomasyon"
            )

        summary.append({
            "kod": line.code,
            "aciklama": line.description,
            "miktar": line.quantity,
            "confirmed": not notes,
        })
        row_idx += 1

    return wb, summary


def _row_values(line, coo_code, invoice_no, invoice_date, referans):
    return {
        S.COL_QUANTITY: line.quantity,
        S.COL_BIRIM: S.BIRIM_SABIT,
        S.COL_CMMF: line.code,
        S.COL_NET_PRICE: line.amount,
        S.COL_CURRENCY: S.VARSAYILAN_PARA_BIRIMI,
        S.COL_COO: coo_code,
        S.COL_BRUT: line.gross_weight,
        S.COL_NET: line.net_weight,
        S.COL_FATURA: invoice_no,
        S.COL_FATURA_TARIHI: invoice_date,
        S.COL_REFERANS: referans,
        S.COL_ISLEM_NITELIGI: S.ISLEM_NITELIGI_SABIT,
        S.COL_KULLANILMIS: S.KULLANILMIS_SABIT,
        S.COL_SIPARIS_TURU: S.SIPARIS_TURU_SABIT,
        S.COL_EDI_BELGE_KOD: S.EDI_BELGE_KOD_SABIT,
    }


def _uncertainty_notes(line, coo_code, origin_country):
    notes = []
    if not coo_code:
        notes.append(f"Mense ulke kodu bilinmiyor (tespit edilen mense: {origin_country or 'BILINMIYOR'})")
    if line.missing_price:
        notes.append("Birim fiyat bulunamadi")
    if line.missing_weight:
        notes.append("Agirlik bulunamadi")
    return notes


def _clear_existing_data_rows(ws):
    if ws.max_row >= S.FIRST_DATA_ROW:
        ws.delete_rows(S.FIRST_DATA_ROW, ws.max_row - S.FIRST_DATA_ROW + 1)
