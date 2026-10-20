# -*- coding: utf-8 -*-
"""models.py — Belgelerden cikan verinin ortak veri yapilari."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineItem:
    code: str
    description: str
    quantity: float
    unit: str = "EA"
    quantity_raw: Optional[str] = None
    net_weight: Optional[float] = None
    gross_weight: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    origin: Optional[str] = None


@dataclass
class EvrakSeti:
    """Tek bir PDF'ten (veya birlestirilmis bir fatura grubundan) cikan
    Packing List + Invoice + Waybill uclusu."""
    source_pdf: str
    packing_list: Optional[object] = None
    invoice: Optional[object] = None
    waybill: Optional[object] = None
    files: list = field(default_factory=list)
