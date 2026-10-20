# -*- coding: utf-8 -*-
"""packing_list.py — Packing List sayfalarindan alan cikarma."""
import re
from dataclasses import dataclass, field
from typing import Optional

from tools.smart_clearance_engine.domain.models import LineItem
from tools.smart_clearance_engine.parsers.common import search, to_number, detect_origin, qty_raw_with_unit

# Kore sablonu: "3002384  315/70R22.5,20,AH31,L,B,Z,HK  49 EA  2,940.588 KG  2,940.588 KG  KR"
# Macaristan sablonunda menşe harfi (KR) yok — bu yuzden o kisim opsiyonel.
ITEM_LINE_RE = re.compile(
    r"^(\d{6,8})\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s*EA\s+([\d,]+\.\d+)\s*KG\s+"
    r"([\d,]+\.\d+)\s*KG(?:\s+([A-Z]{2}))?\s*$",
    re.MULTILINE,
)

# Cin sablonu: "1036203 ... 20 PCS 169.580 KGS 169.580 KGS"
ITEM_LINE_CN_RE = re.compile(
    r"^(\d{6,8})\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s*PCS\s+([\d,]+\.\d+)\s*KGS\s+([\d,]+\.\d+)\s*KGS\s*$",
    re.MULTILINE,
)


@dataclass
class PackingList:
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    lc_no: Optional[str] = None
    order_no: Optional[str] = None
    po_no: Optional[str] = None
    ctr_no: Optional[str] = None
    carrier: Optional[str] = None
    pack_range: Optional[str] = None
    origin_country: Optional[str] = None
    items: list = field(default_factory=list)
    sub_total_qty: Optional[float] = None
    sub_total_net: Optional[float] = None
    sub_total_gross: Optional[float] = None


def parse_packing_list(text: str) -> PackingList:
    pl = PackingList()
    pl.origin_country = detect_origin(text)
    pl.invoice_no = search(r"No\.?\s*&\s*Date\s*Of\s*(?:Invoice|Packing\s*List)\D*(\d{6,})", text)
    pl.invoice_date = search(r"(\d{6,})[, \t]+([A-Z]{3}\.\d{2}\.\d{4})", text, group=2)
    if not pl.invoice_date:
        pl.invoice_date = search(r"(\d{6,})[, \t]+(\d{4}\.\d{2}\.\d{2})", text, group=2)
    if not pl.invoice_date:
        pl.invoice_date = search(r"Date\s*:\s*(\d{4}\.\d{2}\.\d{2})", text)
    pl.lc_no = search(r"(TR_KOR_[A-Z0-9_]+)", text)
    pl.order_no = search(r"ORDER\s*NO\.?\s*:\s*(\d+)", text)
    pl.po_no = search(r"PO\s*No\.?\s*:\s*(\d{6,})", text)
    pl.ctr_no = search(r"CTR\s*No\.?\s*:\s*([A-Z]{4}\d+)", text)
    pl.pack_range = search(r"PACK\s*NO\.\s*([\d,\-\s]+)", text)

    for m in ITEM_LINE_RE.finditer(text):
        code, desc, qty, net_w, gross_w, origin = m.groups()
        pl.items.append(LineItem(
            code=code, description=desc.strip(), quantity=to_number(qty),
            quantity_raw=qty_raw_with_unit(qty, m.group(0)),
            net_weight=to_number(net_w), gross_weight=to_number(gross_w), origin=origin,
        ))

    for m in ITEM_LINE_CN_RE.finditer(text):
        code, desc, qty, net_w, gross_w = m.groups()
        pl.items.append(LineItem(
            code=code, description=desc.strip(), quantity=to_number(qty),
            quantity_raw=qty_raw_with_unit(qty, m.group(0), unit="PCS"),
            net_weight=to_number(net_w), gross_weight=to_number(gross_w),
            origin=pl.origin_country or "CHINA"
        ))

    # 1. Once nihai TOTAL kontrol et (Cin ve coklu siparisler)
    m = re.search(
        r"^(?:Grand\s+)?TOTAL\s+([\d,]+(?:\.\d+)?)\s*(?:EA|PCS)\s+([\d,]+\.\d+)\s*KGS?\s+([\d,]+\.\d+)\s*KGS?",
        text, re.IGNORECASE | re.MULTILINE
    )
    if not m:
        m = re.search(
            r"SUB\s*TOTAL\s*:?\s*([\d,]+(?:\.\d+)?)\s*(?:EA|PCS)\s+([\d,]+\.\d+)\s*KGS?\s+([\d,]+\.\d+)\s*KGS?",
            text, re.IGNORECASE,
        )
    if m:
        pl.sub_total_qty = to_number(m.group(1))
        pl.sub_total_net = to_number(m.group(2))
        pl.sub_total_gross = to_number(m.group(3))
    return pl
