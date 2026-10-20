# -*- coding: utf-8 -*-
"""
waybill.py — Konsimento (Sea Waybill) sablonlarindan alan cikarma.

Konsimento sablonu tasiyicidan tasiyiciya degisir (Hapag-Lloyd, ONE/MSC,
Maersk...). Bu yuzden veriler SIRALI METIN KONUMUNA degil, ANKOR (regex)
desenlerine gore cikarilir; boylece sablon farketmeksizin calisir. Bazi
sayfalarda kenar bosluguna dik yazilmis metin ters/karisik sirada
gelebilir (orn. "Plain" -> "nialP"), bu metinler zaten regex'lerle
eslesmedigi icin sonucu etkilemez.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from tools.smart_clearance_engine.parsers.common import search, to_number


@dataclass
class Waybill:
    template: Optional[str] = None
    invoice_ref: Optional[str] = None
    bl_no: Optional[str] = None
    lc_no: Optional[str] = None
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    port_of_loading: Optional[str] = None
    containers: list = field(default_factory=list)
    package_count: Optional[float] = None
    gross_weight: Optional[float] = None
    measurement: Optional[float] = None
    freight_term: Optional[str] = None


def parse_waybill(text: str) -> Waybill:
    wb = Waybill()
    wb.template = _detect_template(text)
    wb.invoice_ref = search(r"INVOICE\s*NO\.?\s*:?\s*(\d{6,})", text)
    wb.lc_no = search(r"LETTER OF CREDIT NUMBER\s*:\s*([A-Z0-9_]+)", text) \
        or search(r"(TR_KOR_[A-Z0-9_]+)", text)
    wb.freight_term = search(r"\b(FREIGHT PREPAID|FREIGHT COLLECT)\b", text)

    if wb.template == "HAPAG_LLOYD":
        _parse_hapag_lloyd(wb, text)
    elif wb.template == "ONE_MSC":
        _parse_one_msc(wb, text)
    return wb


def _detect_template(text):
    if "SHIPPER/EXPORTER" in text and "SEA WAYBILL NO" in text.upper():
        return "ONE_MSC"
    if "Hapag-Lloyd" in text or "SWB-No" in text:
        return "HAPAG_LLOYD"
    return "UNKNOWN"


def _parse_hapag_lloyd(wb, text):
    # "SWB-No.: Page:" bos baslik satirini atlamak icin deger >= 6 karakter olmali
    wb.bl_no = search(r"SWB-No\.\s*:?\s*([A-Z0-9]{6,})", text)
    vm = re.search(r"VESSEL NAME:\s*([A-Z0-9 ]+?)\s+VOYAGE:\s*(\S+)", text)
    if vm:
        wb.vessel, wb.voyage = vm.group(1).strip(), vm.group(2).strip()
    wb.port_of_loading = search(r"PORT OF LOADING:\s*([A-Z ,]+?)(?:\n|$)", text)

    m = re.search(
        r"([A-Z]{4}\s?\d{6,7})\s+(\d[\d,]*)\s*PACKAGES?\s+([\d,]+\.\d+)\s+"
        r"([\d,]+\.\d+)\s*\n\s*SEAL",
        text,
    )
    if m:
        wb.containers.append(m.group(1).replace(" ", ""))
        wb.package_count = to_number(m.group(2))
        wb.gross_weight = to_number(m.group(3))
        wb.measurement = to_number(m.group(4))

    if not wb.invoice_ref:
        m2 = re.search(r"\d{6,8}\s+[A-Z]+\d+\s+\d\s*/\s*\d\s*\n\s*(\d{6,})", text)
        if m2:
            wb.invoice_ref = m2.group(1)


def _parse_one_msc(wb, text):
    wb.bl_no = search(r"SEA WAYBILL NO\.?\s*\n?\s*\S+\s+(\S+)", text)
    if not wb.bl_no:
        wb.bl_no = search(r"B/L NO\.?:\s*([A-Z0-9]+)", text)

    vm = re.search(r"OCEAN VESSEL VOYAGE NO\..*?\n\s*(.+?)\s+(\S+W)\b", text, re.DOTALL)
    if not vm:
        vm = re.search(r"VESSEL VOYAGE:\s*(.+?)\s+(\S+W)\b", text)
    if vm:
        wb.vessel, wb.voyage = vm.group(1).strip(), vm.group(2).strip()

    wb.port_of_loading = search(
        r"PORT OF LOADING.*?\n.*?\n\s*([A-Z ,]+?),\s*(?:KOREA|CHINA)", text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not wb.port_of_loading:
        wb.port_of_loading = search(r"PORT OF LOADING\s+([A-Z ,]+?)(?:\s+FINAL|\n|$)", text, flags=re.IGNORECASE)

    # 1. Tum konteynerleri topla
    for cm in re.finditer(
        r"([A-Z]{4}\d{6,7})\s*/\s*([A-Z0-9]+)\s*/\s*(\d[\d,]*)\s*(?:PACKAGES?|PIECES)\s*/.*?/"
        r"([\d,]+\.\d+)KGS/([\d,]+\.\d+)(?:M3|CBM)",
        text, re.IGNORECASE,
    ):
        cntr = cm.group(1)
        if cntr not in wb.containers:
            wb.containers.append(cntr)

    # 2. Genel toplam satirini ara: orn. "2438 2438 PIECES IN TOTAL 25533.068KGS 195.000CBM"
    tot_m = re.search(
        r"(\d[\d,]*)\s*(?:PIECES|PACKAGES)\s+IN\s+TOTAL\s+([\d,]+\.\d+)KGS\s+([\d,]+\.\d+)(?:CBM|M3)",
        text, re.IGNORECASE,
    )
    if tot_m:
        wb.package_count = to_number(tot_m.group(1))
        wb.gross_weight = to_number(tot_m.group(2))
        wb.measurement = to_number(tot_m.group(3))
    else:
        m = re.search(
            r"([A-Z]{4}\d{6,7})\s*/\s*([A-Z0-9]+)\s*/\s*(\d[\d,]*)\s*(?:PACKAGES?|PIECES)\s*/.*?/"
            r"([\d,]+\.\d+)KGS/([\d,]+\.\d+)(?:M3|CBM)",
            text, re.IGNORECASE,
        )
        if m:
            if m.group(1) not in wb.containers:
                wb.containers.append(m.group(1))
            wb.package_count = to_number(m.group(3))
            wb.gross_weight = to_number(m.group(4))
            wb.measurement = to_number(m.group(5))

    if not wb.invoice_ref:
        m_ord = re.search(r"ORDER\s*NO\.?:?\s*(\d{6,})", text, re.IGNORECASE)
        if m_ord:
            wb.invoice_ref = m_ord.group(1)
        else:
            m_po = re.search(r"PO\s*NO\.?:?\s*(\d{6,})", text, re.IGNORECASE)
            if m_po:
                wb.invoice_ref = m_po.group(1)
