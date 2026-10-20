# -*- coding: utf-8 -*-
"""Operasyon Kokpiti veri okuma — mevcut kaynakları bağlar, mantığı değiştirmez."""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SmartClearance"
EVRIM_PATH = CONFIG_DIR / "evrim_live_data.json"
CSV_FALLBACK = ROOT / "Operasyon_Kokpiti.csv"


def _load_json(path: Path, default=None):
    if default is None:
        default = []
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _from_master_engine() -> List[Dict[str, Any]]:
    """MasterDataEngine Excel kayıtları (Windows/Excel varsa)."""
    try:
        from tools.dogruer_master_suite.engine.master_data_engine import MasterDataEngine

        engine = MasterDataEngine()
        if hasattr(engine, "fetch_excel_records"):
            recs = engine.fetch_excel_records() or []
            if recs:
                return list(recs)
        if getattr(engine, "records", None):
            return list(engine.records)
    except Exception:
        pass
    return []


def _from_evrim() -> List[Dict[str, Any]]:
    rows = _load_json(EVRIM_PATH, [])
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        kapandi = bool(r.get("kapanis") or r.get("kapandi"))
        hat = str(r.get("hat") or "").strip()
        tescil = str(r.get("tescil_no") or r.get("tescil_tarihi") or "").strip()
        is_tax = bool(r.get("is_tax_pending"))
        if kapandi:
            stage = "5_KAPANDI"
            stage_title = "Kapandı / Arşiv"
        elif "KIRMIZI" in hat.upper():
            stage = "3_MUAYENE"
            stage_title = "Kırmızı Hat (Muayenede)"
        elif tescil or r.get("beyanname_no"):
            stage = "3_TESCILDE"
            stage_title = "Tescilde / Tescil Oldu"
        else:
            stage = "1_EVRAK"
            stage_title = "Evrak / Açılış"
        out.append(
            {
                "dosya": str(r.get("dosya_no") or "").strip(),
                "ref": str(r.get("referans_no") or r.get("hankook_ref") or r.get("musteri_referans") or "").strip(),
                "bl": str(r.get("bl_no") or r.get("konsimento") or "").strip(),
                "stage": stage,
                "stage_title": stage_title,
                "hat": hat,
                "vergi_mail": "Vergi bekliyor" if is_tax else "",
                "is_tax_pending": is_tax,
                "bayi": str(r.get("musteri_unvan") or r.get("firma") or r.get("bayi") or "").strip(),
                "liman": str(r.get("liman") or r.get("gumruk") or "").strip(),
                "beyanname_no": str(r.get("beyanname_no") or "").strip(),
                "kapandi": kapandi,
                "kaynak": "evrim",
            }
        )
    return out


def _from_csv() -> List[Dict[str, Any]]:
    if not CSV_FALLBACK.exists():
        return []
    out = []
    try:
        with open(CSV_FALLBACK, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                stage_title = (row.get("Aşama") or row.get("Asama") or "").strip()
                stage = "1_EVRAK"
                st_u = stage_title.upper()
                if "KAPAND" in st_u:
                    stage = "5_KAPANDI"
                elif "KIRMIZI" in st_u or "MUAYENE" in st_u:
                    stage = "3_MUAYENE"
                elif "TESCİL" in st_u or "TESCIL" in st_u:
                    stage = "3_TESCILDE"
                elif "ORDİNO" in st_u or "ORDINO" in st_u or "TAREKS" in st_u:
                    stage = "2_ORDINO_TAREKS"
                vergi = (row.get("Vergi Maili") or "").strip()
                out.append(
                    {
                        "dosya": (row.get("Dosya No") or "").strip(),
                        "ref": (row.get("Referans No") or "").strip(),
                        "bl": (row.get("Konşimento") or row.get("Konsimento") or "").strip(),
                        "stage": stage,
                        "stage_title": stage_title,
                        "hat": (row.get("Hat") or "").strip(),
                        "vergi_mail": vergi,
                        "is_tax_pending": "BEKLE" in vergi.upper() or "VERGİ" in vergi.upper() or "VERGI" in vergi.upper(),
                        "bayi": (row.get("Bayi / Alıcı") or row.get("Bayi / Alici") or "").strip(),
                        "liman": (row.get("Liman") or "").strip(),
                        "beyanname_no": "",
                        "kapandi": stage == "5_KAPANDI",
                        "kaynak": "csv",
                    }
                )
    except Exception:
        return []
    return out


def load_cockpit_records(q: str = "", filter_type: str = "all", limit: int = 200) -> Dict[str, Any]:
    """Öncelik: Excel motor → Evrim JSON → Operasyon_Kokpiti.csv."""
    source = "empty"
    records = _from_master_engine()
    if records:
        source = "excel"
        # MasterDataEngine alan adlarını normalize et
        normalized = []
        for r in records:
            stage = str(r.get("stage") or "")
            stage_title = str(r.get("stage_title") or r.get("asama") or "")
            kapandi = stage.startswith("5") or bool(r.get("kapandi"))
            normalized.append(
                {
                    "dosya": str(r.get("dosya") or r.get("dosya_no") or "").strip(),
                    "ref": str(r.get("ref") or r.get("referans_no") or "").strip(),
                    "bl": str(r.get("bl") or r.get("konsimento") or "").strip(),
                    "stage": stage or "1_EVRAK",
                    "stage_title": stage_title,
                    "hat": str(r.get("hat") or "").strip(),
                    "vergi_mail": str(r.get("vergi_mail") or r.get("mail_badge") or "").strip(),
                    "is_tax_pending": bool(r.get("is_tax_pending")),
                    "bayi": str(r.get("bayi") or r.get("firma") or "").strip(),
                    "liman": str(r.get("liman") or "").strip(),
                    "beyanname_no": str(r.get("beyanname_no") or r.get("beyan_no") or "").strip(),
                    "kapandi": kapandi,
                    "kaynak": "excel",
                }
            )
        records = normalized
    else:
        records = _from_evrim()
        if records:
            source = "evrim"
        else:
            records = _from_csv()
            if records:
                source = "csv"

    q_clean = (q or "").strip().upper()
    ft = (filter_type or "all").strip().lower()
    filtered: List[Dict[str, Any]] = []
    for r in records:
        kapandi = bool(r.get("kapandi"))
        hat = str(r.get("hat") or "").upper()
        is_tax = bool(r.get("is_tax_pending"))
        stage = str(r.get("stage") or "")

        if ft == "active" and kapandi:
            continue
        if ft == "closed" and not kapandi:
            continue
        if ft == "tax" and not is_tax:
            continue
        if ft == "tescil" and not (stage.startswith("3") or r.get("beyanname_no")):
            continue
        if ft == "red" and "KIRMIZI" not in hat and "MUAYENE" not in str(r.get("stage_title") or "").upper():
            continue
        if ft == "ordino" and not stage.startswith("2"):
            continue

        if q_clean:
            blob = " ".join(
                str(r.get(k) or "")
                for k in ("dosya", "ref", "bl", "bayi", "liman", "beyanname_no", "stage_title", "hat")
            ).upper()
            if q_clean not in blob:
                continue
        filtered.append(r)
        if len(filtered) >= limit:
            break

    stats = {
        "total": len(records),
        "active": sum(1 for r in records if not r.get("kapandi")),
        "tax": sum(1 for r in records if r.get("is_tax_pending")),
        "closed": sum(1 for r in records if r.get("kapandi")),
    }
    return {"source": source, "count": len(filtered), "stats": stats, "items": filtered}


def extract_beyanname_candidates(text: str) -> List[str]:
    """Metinden 16 haneli beyanname numaralarını ayıklar."""
    found = []
    for part in re.split(r"[\s,;/\n\r]+", text or ""):
        clean = re.sub(r"[^A-Z0-9]", "", part.upper())
        if len(clean) >= 15:
            found.append(clean)
    return found
