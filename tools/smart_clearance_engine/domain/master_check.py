# -*- coding: utf-8 -*-
"""
master_check.py — Fatura/Packing List kalemlerini master katalogla
karsilastirir: eslesti / tanim uyusmuyor / kod master'da yok.

Tanim karsilastirmasi toleranslidir: bosluk/buyuk-kucuk harf farklarini
ve fatura tanimindaki hiz/yuk endeksi ekini (orn. '96H') yok sayar,
cunku bu ek master'da olmayabilir.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

MATCHED = "matched"
DESCRIPTION_MISMATCH = "description_mismatch"
MISSING_CODE = "missing_code"

_SPEED_LOAD_SUFFIX_RE = re.compile(r"\s+\d{2,3}(/\d{2,3})?[A-Z]{0,2}$")


def _compare_key(value) -> str:
    return re.sub(r"\s+", "", str(value or "").upper())


def descriptions_match(invoice_desc: str, master_descs: list) -> bool:
    candidates = {_compare_key(invoice_desc)}
    trimmed = _SPEED_LOAD_SUFFIX_RE.sub("", " ".join(str(invoice_desc or "").split()))
    candidates.add(_compare_key(trimmed))
    candidates.discard("")
    for master_desc in master_descs:
        key = _compare_key(master_desc)
        if not key:
            continue
        for cand in candidates:
            if cand == key or cand in key or key in cand:
                return True
    return False


@dataclass
class MasterCheckRow:
    product_code: str
    invoice_description: str
    quantity: Optional[float]
    status: str
    master_description: Optional[str] = None
    master_turkish_description: Optional[str] = None
    master_gtip: Optional[str] = None
    master_origin: Optional[str] = None
    master_status: Optional[str] = None
    master_agreement_code: Optional[str] = None
    origin: Optional[str] = None  # bu urunun KENDI faturasindan tespit edilen mense (KOREA/HUNGARY) —
    # parti bazinda tek bir mense varsayan eski davranisin aksine, karisik mense partilerinde
    # her urun kendi kaynagini tasir (bkz. app/services/master_pipeline.py)


@dataclass
class MasterCheckResult:
    rows: list = field(default_factory=list)
    matched_count: int = 0
    mismatch_count: int = 0
    missing_count: int = 0


def check_items_against_master(items, katalog) -> MasterCheckResult:
    """items: LineItem listesi (app.domain.models). katalog: MasterKatalog."""
    result = MasterCheckResult()
    seen_codes = set()
    for item in items:
        code = str(item.code or "").strip()
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        master = katalog.rows_by_code.get(code)
        if master is None:
            status = MISSING_CODE
        elif descriptions_match(item.description, [master.description, master.turkish_description or ""]):
            status = MATCHED
        else:
            status = DESCRIPTION_MISMATCH

        result.rows.append(MasterCheckRow(
            product_code=code,
            invoice_description=item.description,
            quantity=item.quantity,
            status=status,
            master_description=master.description if master else None,
            master_turkish_description=master.turkish_description if master else None,
            master_gtip=master.gtip if master else None,
            master_origin=master.origin if master else None,
            master_status=master.status if master else None,
            master_agreement_code=master.agreement_code if master else None,
            origin=item.origin,
        ))

    result.matched_count = sum(1 for r in result.rows if r.status == MATCHED)
    result.mismatch_count = sum(1 for r in result.rows if r.status == DESCRIPTION_MISMATCH)
    result.missing_count = sum(1 for r in result.rows if r.status == MISSING_CODE)
    return result
