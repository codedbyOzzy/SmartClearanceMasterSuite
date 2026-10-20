# -*- coding: utf-8 -*-
"""
declaration_rules.py — 0887 Transfer Bildirim Formu kararini 2017/20 sayili
Genelge'ye gore verir. Mantik AYNEN eski sistemden tasindi (dogrulanmis,
regresyon testleri var), sadece config yolu bizim config.py'ye baglandi.

Kritik davranis: belirsizlikte "gerekli degil" DEMEZ, "indeterminate"
(fail-closed) doner — kullaniciyi kanit gostermeye zorlar.
"""
import json
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Optional

from tools.smart_clearance_engine.config import REGULATIONS_DIR

RULE_PATH = REGULATIONS_DIR / "transfer_notification_2017_20.json"


@lru_cache(maxsize=1)
def transfer_notification_rule() -> dict:
    rule = json.loads(RULE_PATH.read_text(encoding="utf-8"))
    required = {"rule_id", "version", "document_code", "source_url", "required_when"}
    missing = sorted(required - set(rule))
    if missing:
        raise ValueError(f"0887 kural dosyasi eksik alan iceriyor: {', '.join(missing)}")
    return rule


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def evaluate_transfer_notification(
    *,
    form_present: bool,
    payment_transferred: Optional[bool] = None,
    transfer_date: Any = None,
    registration_date: Any = None,
    payment_method: Optional[str] = None,
) -> dict:
    """0887 kararini kanit ve tarihe gore, belirsizlikte fail-closed verir."""
    rule = transfer_notification_rule()
    base = {
        "rule_id": rule["rule_id"],
        "rule_version": rule["version"],
        "document_code": rule["document_code"],
        "source_url": rule["source_url"],
        "payment_method": payment_method,
    }
    if form_present:
        return {**base, "status": "present", "required": None, "message": "0887 belge kodu beyannamede mevcut."}
    if payment_transferred is False:
        return {
            **base,
            "status": "not_required",
            "required": False,
            "message": "Esya bedelinin henuz transfer edilmedigi dogrulandi; 0887 bu kosulda aranmadi.",
        }

    transferred = _as_date(transfer_date)
    registered = _as_date(registration_date)
    if payment_transferred is True and transferred and registered:
        required = transferred <= registered
        return {
            **base,
            "status": "required" if required else "not_required",
            "required": required,
            "message": (
                "Transfer tescil tarihinde/tescilden once yapilmis; 0887 gereklidir."
                if required
                else "Transfer tescil tarihinden sonra yapilmis; 0887 bu zaman kosuluyla aranmadi."
            ),
        }

    return {
        **base,
        "status": "indeterminate",
        "required": None,
        "message": (
            "0887 gerekliligi yalnizca odeme sekli adindan belirlenemez. "
            "Transferin yapilip yapilmadigini ve transfer/tescil tarihlerini kanitla dogrulayin."
        ),
    }
