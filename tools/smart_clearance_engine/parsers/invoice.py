# -*- coding: utf-8 -*-
"""invoice.py — Commercial Invoice sayfalarindan alan cikarma."""
import re
from dataclasses import dataclass, field
from typing import Optional

from tools.smart_clearance_engine.domain.models import LineItem
from tools.smart_clearance_engine.parsers.common import search, to_number, detect_origin, qty_raw_with_unit

# Kore sablonu: "3002384 ... 49 EA TRY 13,525.88 TRY 662,768.12 KR"
INV_ITEM_LINE_RE = re.compile(
    r"^(\d{6,8})\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s*EA\s+([A-Z]{3})\s+([\d,]+\.\d+)\s+"
    r"([A-Z]{3})\s+([\d,]+\.\d+)\s+([A-Z]{2})\s*$",
    re.MULTILINE,
)

# Macaristan sablonu: "1023161 ... 60 EA 0 % 0 % 2,920.63 175,237.80 0 % 0.00 175,237.80"
INV_ITEM_LINE_HU_RE = re.compile(
    r"^(\d{6,8})\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s*EA\s+\d+\s*%\s+\d+\s*%\s+"
    r"([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+\d+\s*%\s+[\d,]+\.\d+\s+([\d,]+\.\d+)\s*$",
    re.MULTILINE,
)

# Cin sablonu: "1036203 205/60R16H... 20 PCS 1,358.07 TRY 27,161.40"
INV_ITEM_LINE_CN_RE = re.compile(
    r"^(\d{6,8})\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s*PCS\s+([\d,]+\.\d+)\s+([A-Z]{3})\s+([\d,]+\.\d+)\s*$",
    re.MULTILINE,
)


@dataclass
class Invoice:
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    lc_no: Optional[str] = None
    incoterm: Optional[str] = None
    incoterm_place: Optional[str] = None
    origin_country: Optional[str] = None
    items: list = field(default_factory=list)
    sub_total_qty: Optional[float] = None
    sub_total_amount: Optional[float] = None
    currency: Optional[str] = None
    net_amount: Optional[float] = None


def parse_invoice(text: str) -> Invoice:
    inv = Invoice()
    inv.origin_country = detect_origin(text)
    inv.invoice_no = search(r"No\.?\s*&\s*Date\s*of\s*Invoice\D*(\d{6,})", text)
    inv.invoice_date = search(r"(\d{6,})[, \t]+([A-Z]{3}\.\d{2}\.\d{4})", text, group=2)
    if not inv.invoice_date:
        inv.invoice_date = search(r"(\d{6,})[, \t]+(\d{4}\.\d{2}\.\d{2})", text, group=2)
    if not inv.invoice_date:
        inv.invoice_date = search(r"Date\s*:\s*(\d{4}\.\d{2}\.\d{2})", text)
    inv.lc_no = search(r"(TR_KOR_[A-Z0-9_]+)", text)

    m = re.search(r"\b(CIP|CIF|FOB|CFR|EXW|DAP|DDP)\b\s+([A-Za-z ]+?)\s*\n", text)
    if m:
        inv.incoterm, inv.incoterm_place = m.group(1), m.group(2).strip()

    _parse_items_kore(inv, text)
    if not inv.items:
        _parse_items_hungary(inv, text)
    if not inv.items:
        _parse_items_china(inv, text)

    _parse_totals(inv, text)
    return inv


def _parse_items_kore(inv, text):
    for m in INV_ITEM_LINE_RE.finditer(text):
        code, desc, qty, _cur1, unit_price, cur2, amount, origin = m.groups()
        inv.items.append(LineItem(
            code=code, description=desc.strip(), quantity=to_number(qty),
            quantity_raw=qty_raw_with_unit(qty, m.group(0)),
            unit_price=to_number(unit_price), amount=to_number(amount),
            currency=cur2, origin=origin,
        ))


def _parse_items_hungary(inv, text):
    for m in INV_ITEM_LINE_HU_RE.finditer(text):
        code, desc, qty, unit_price, _net_value, gross_value = m.groups()
        inv.items.append(LineItem(
            code=code, description=desc.strip(), quantity=to_number(qty),
            quantity_raw=qty_raw_with_unit(qty, m.group(0)),
            unit_price=to_number(unit_price), amount=to_number(gross_value),
        ))


def _parse_items_china(inv, text):
    for m in INV_ITEM_LINE_CN_RE.finditer(text):
        code, desc, qty, unit_price, curr, amount = m.groups()
        inv.items.append(LineItem(
            code=code, description=desc.strip(), quantity=to_number(qty),
            quantity_raw=qty_raw_with_unit(qty, m.group(0), unit="PCS"),
            unit_price=to_number(unit_price), amount=to_number(amount),
            currency=curr,
            origin=inv.origin_country or "CHINA"
        ))


def _parse_totals(inv, text):
    # 1. Once Grand Total / Final TOTAL kontrol et (Cin ve coklu siparisler)
    m = re.search(
        r"Grand\s*Total\s*:?\s*([\d,]+(?:\.\d+)?)\s*(?:EA|PCS)\s*(?:([A-Z]{3})\s+)?([\d,]+\.\d+)",
        text, re.IGNORECASE,
    )
    if m:
        inv.sub_total_qty = to_number(m.group(1))
        inv.currency = m.group(2) or "TRY"
        inv.sub_total_amount = to_number(m.group(3))
    else:
        # 2. Standart SUB TOTAL kontrolu
        m = re.search(
            r"SUB\s*TOTAL\s*:?\s*([\d,]+(?:\.\d+)?)\s*(?:EA|PCS)\s+([A-Z]{3})\s+([\d,]+\.\d+)",
            text, re.IGNORECASE,
        )
        if m:
            inv.sub_total_qty = to_number(m.group(1))
            inv.currency = m.group(2)
            inv.sub_total_amount = to_number(m.group(3))
        else:
            m = re.search(r"^Total\s+([\d,]+)\s*(?:EA|PCS)\s+([\d,]+\.\d+)\s*$", text, re.MULTILINE | re.IGNORECASE)
            if m:
                inv.sub_total_qty = to_number(m.group(1))
                inv.sub_total_amount = to_number(m.group(2))
            inv.currency = inv.currency or search(r"Currency\s*\n?\s*([A-Z]{3})", text)

    net = search(r"NET\s*AMOUNT\s*:\s*([\d,]+\.\d+)", text)
    if not net:
        net = search(r"Invoice Amount\s*\n?\s*([\d,]+\.\d+)", text)
    if not net and inv.sub_total_amount:
        net = str(inv.sub_total_amount)
    inv.net_amount = to_number(net)
