# -*- coding: utf-8 -*-
"""
merge_lines.py — Packing List ve Fatura kalemlerini SATIR SATIR (sirasina
gore) birlestirir.

ONEMLI: Ayni urun kodu bir faturada birden fazla kez gecebilir (orn. ayni
model 2 farkli partide sevk edilmis olabilir, her birinin miktari/agirligi
farkli). Bu yuzden kod bazinda BIRLESTIRME yapilmaz — Packing List ve
Fatura'daki her satir, kendi sirasindaki karsiligiyla eslenir ve KENDI
cikti satirini alir (SAP/Evrim export mantigi budur).

Packing List ve Fatura'nin ayni sirada, ayni sayida kalem listeledigi
varsayilir (gercek orneklerde hep boyle oldugu dogrulandi). Sayida fark
varsa, kisa olanin bittigi yerden sonraki satirlar icin o taraftan veri
gelmez (None) ve satir "eksik veri" olarak isaretlenir.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeclarationLine:
    code: Optional[str]
    description: Optional[str]
    quantity: Optional[float]
    amount: Optional[float]
    currency: Optional[str]
    gross_weight: Optional[float]
    net_weight: Optional[float]
    missing_price: bool = False
    missing_weight: bool = False


def build_declaration_lines(evrak):
    pl_items = evrak.packing_list.items if evrak.packing_list else []
    inv_items = evrak.invoice.items if evrak.invoice else []

    n = max(len(pl_items), len(inv_items))
    lines = []
    for i in range(n):
        pl_it = pl_items[i] if i < len(pl_items) else None
        inv_it = inv_items[i] if i < len(inv_items) else None

        code = (pl_it.code if pl_it else None) or (inv_it.code if inv_it else None)
        desc = (pl_it.description if pl_it else None) or (inv_it.description if inv_it else None)
        qty = (pl_it.quantity if pl_it else None)
        if qty is None:
            qty = inv_it.quantity if inv_it else None

        lines.append(DeclarationLine(
            code=code,
            description=desc,
            quantity=qty,
            amount=inv_it.amount if inv_it else None,
            currency=inv_it.currency if inv_it else None,
            gross_weight=pl_it.gross_weight if pl_it else None,
            net_weight=pl_it.net_weight if pl_it else None,
            missing_price=(inv_it is None or inv_it.amount is None),
            missing_weight=(pl_it is None or pl_it.gross_weight is None),
        ))
    return lines
