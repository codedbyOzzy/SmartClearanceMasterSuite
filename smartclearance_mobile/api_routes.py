# -*- coding: utf-8 -*-
"""
smartclearance_mobile.api_routes
Kurumsal Mobil REST API Uç Noktaları (FastAPI APIRouter)
"""

import os
import sys
import json
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["SmartClearance Mobile API"])

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
EVRIM_DATA_PATH = os.path.join(CONFIG_DIR, "evrim_live_data.json")
GTB_STORAGE_PATH = os.path.join(CONFIG_DIR, "gtb_takip_storage.json")
KANTAR_STORAGE_PATH = os.path.join(CONFIG_DIR, "kantar_takip_storage.json")
RADAR_CACHE_PATH = os.path.join(ROOT_DIR, "standalone_global_tracker", "radar_cache.json")


def _load_json_safe(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _resolve_vessel_flag(vessel_name: str, carrier: str = "") -> str:
    """Gemi adına veya acente desenine göre bayrak emojisi döndürür."""
    v = (vessel_name or "").upper()
    c = (carrier or "").upper()
    if any(k in v for k in ["TURK", "KEMAL", "MEHMET", "ISTANBUL", "IZMIR", "KAS", "DENIZ", "BORA", "EFE"]):
        return "🇹🇷"
    if "PANAMA" in v or "MSC" in c or "MSC" in v:
        return "🇵🇦"
    if "LIBERIA" in v or "MAERSK" in c or "CMA" in c:
        return "🇱🇷"
    if "HAPAG" in c or "EXPRESS" in v:
        return "🇩🇪"
    if "COSCO" in c or "CHINA" in v:
        return "🇨🇳"
    if "EVER" in v or "EVERGREEN" in c:
        return "🇹🇼"
    if "ONE " in v or "ONE" in c:
        return "🇯🇵"
    return "🚢"


@router.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "SmartClearance Mobile Server",
        "timestamp": datetime.now().isoformat(),
        "version": "5.0.0-PRO"
    }


@router.get("/stats")
def get_stats():
    """Vercel/Apple tarzı üst KPI sayaçlarını hesaplar."""
    evrim_records = _load_json_safe(EVRIM_DATA_PATH, [])
    radar_cache = _load_json_safe(RADAR_CACHE_PATH, {})
    radar_items = radar_cache.get("items", []) if isinstance(radar_cache, dict) else []
    gtb_records = _load_json_safe(GTB_STORAGE_PATH, [])
    kantar_records = _load_json_safe(KANTAR_STORAGE_PATH, [])

    total_files = len(evrim_records)
    active_files = sum(1 for r in evrim_records if not r.get("kapanis") and not r.get("kapandi"))
    tax_pending = sum(1 for r in evrim_records if not r.get("kapanis") and r.get("is_tax_pending"))
    
    # Tescilde olanlar
    registered = sum(1 for r in evrim_records if not r.get("kapanis") and (r.get("tescil_no") or r.get("beyanname_no")))
    
    # Kırmızı hat
    red_line = 0
    for r in gtb_records:
        h = str(r.get("hat", "")).upper()
        if "KIRMIZI" in h or "MUAYENE" in str(r.get("durum", "")).upper():
            red_line += 1

    # Yoldaki aktif gemiler
    vessels = set()
    active_containers = 0
    for item in radar_items:
        if item.get("is_active", True):
            active_containers += 1
            v_name = item.get("vessel")
            if v_name and v_name not in ("—", "-", ""):
                vessels.add(v_name.strip())

    kantar_pending = sum(1 for k in kantar_records if not k.get("kilo") and not k.get("tartim_zamani"))

    return {
        "total_files": total_files,
        "active_files": active_files,
        "tax_pending": tax_pending,
        "registered": registered,
        "red_line": red_line,
        "active_containers": active_containers,
        "active_vessels": len(vessels),
        "kantar_pending": kantar_pending,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    }


@router.get("/cockpit")
def get_cockpit(
    q: str = Query("", description="Arama terimi"),
    filter_type: str = Query("all", description="Filtre: all, active, tax, tescil, red, closed"),
    limit: int = Query(100, ge=1, le=500)
):
    """Mobil operasyon kokpiti için dosya listesi."""
    records = _load_json_safe(EVRIM_DATA_PATH, [])
    gtb_map = {str(g.get("beyanname_no") or ""): g for g in _load_json_safe(GTB_STORAGE_PATH, []) if g.get("beyanname_no")}

    res = []
    q_clean = q.strip().upper()

    for idx, r in enumerate(records):
        dosya = str(r.get("dosya_no") or "").strip()
        ref = str(r.get("referans_no") or "").strip()
        musteri = str(r.get("musteri_unvan") or r.get("firma") or "HANKOOK LASTİKLERİ A.Ş.").strip()
        beyanname = str(r.get("beyanname_no") or "").strip()
        tescil = str(r.get("tescil_no") or r.get("tescil_tarihi") or "").strip()
        kapandi = bool(r.get("kapanis") or r.get("kapandi"))
        is_tax = bool(r.get("is_tax_pending"))

        # GTB eşleşmesi varsa canlı hat bilgisini al
        gtb_item = gtb_map.get(beyanname, {})
        hat = gtb_item.get("hat") or r.get("hat") or ""
        durum = gtb_item.get("durum") or r.get("durum") or ("Kapandı" if kapandi else "İşlemde")

        # Filtreleme
        if filter_type == "active" and kapandi:
            continue
        if filter_type == "closed" and not kapandi:
            continue
        if filter_type == "tax" and not is_tax:
            continue
        if filter_type == "tescil" and not (tescil or beyanname):
            continue
        if filter_type == "red" and "KIRMIZI" not in hat.upper():
            continue

        # Arama
        if q_clean:
            searchable = f"{dosya} {ref} {musteri} {beyanname} {tescil} {hat} {durum}".upper()
            if q_clean not in searchable:
                continue

        res.append({
            "id": idx + 1,
            "dosya_no": dosya,
            "referans_no": ref,
            "musteri": musteri,
            "beyanname_no": beyanname,
            "tescil_no": tescil,
            "hat": hat,
            "durum": durum,
            "kapandi": kapandi,
            "is_tax_pending": is_tax,
            "mail_badge": r.get("mail_badge", ""),
            "eta": r.get("eta", ""),
            "gumruk": r.get("gumruk", "Erenköy Gümrük Md."),
            "rejim": r.get("rejim", "İthalat (4000)"),
            "kalem_sayisi": r.get("kalem_sayisi", 1),
            "fatura_tutar": r.get("fatura_tutar", ""),
            "fatura_doviz": r.get("fatura_doviz", "EUR"),
            "aciklama": r.get("aciklama", "")
        })

        if len(res) >= limit:
            break

    return {"count": len(res), "items": res}


@router.get("/horizon")
def get_horizon(
    q: str = Query("", description="Arama terimi"),
    carrier: str = Query("all", description="Acente filtresi"),
    active_only: bool = Query(True),
    limit: int = Query(80, ge=1, le=300)
):
    """Horizon canlı gemi, AIS koordinatı ve konteyner radar listesi."""
    cache = _load_json_safe(RADAR_CACHE_PATH, {})
    items = cache.get("items", []) if isinstance(cache, dict) else []

    res = []
    q_clean = q.strip().upper()
    carrier_filter = carrier.strip().upper()

    for it in items:
        is_act = bool(it.get("is_active", True))
        if active_only and not is_act:
            continue

        c = str(it.get("carrier") or "").upper()
        if carrier_filter != "ALL" and carrier_filter not in c:
            continue

        cntr = str(it.get("container_no") or "").strip()
        bl = str(it.get("bl_no") or "").strip()
        vessel = str(it.get("vessel") or "").strip()
        dosya = str(it.get("dosya") or "").strip()

        if q_clean:
            combined = f"{cntr} {bl} {vessel} {dosya} {c}".upper()
            if q_clean not in combined:
                continue

        # Koordinat ve rota analizi
        lat = it.get("lat")
        lng = it.get("lng")
        coords = None
        if lat is not None and lng is not None:
            try:
                coords = [float(lat), float(lng)]
            except (ValueError, TypeError):
                coords = None

        if not coords:
            # Örnek Akdeniz/Marmara koordinatları
            coords = [40.965, 28.685] if "AMBARLI" in str(it.get("pod", "")).upper() else [35.5, 25.0]

        flag = _resolve_vessel_flag(vessel, c)

        res.append({
            "container_no": cntr,
            "bl_no": bl,
            "dosya": dosya,
            "carrier": c,
            "vessel": vessel,
            "flag": flag,
            "pol": it.get("pol", "—"),
            "pod": it.get("pod", "—"),
            "live_eta": it.get("live_eta", "—"),
            "excel_eta": it.get("excel_eta", "—"),
            "kalan_gun": it.get("kalan_gun", "—"),
            "diff_tag": it.get("diff_tag", ""),
            "status": it.get("status", "Yolda"),
            "is_active": is_act,
            "coords": coords,
            "has_route": bool(it.get("route_geojson"))
        })

        if len(res) >= limit:
            break

    return {
        "count": len(res),
        "last_check": cache.get("last_check", ""),
        "items": res
    }


@router.get("/kantar")
def get_kantar():
    """DP World Kantar & DBA takip verileri."""
    records = _load_json_safe(KANTAR_STORAGE_PATH, [])
    return {"count": len(records), "items": records}


@router.get("/gtb")
def get_gtb():
    """Ticaret Bakanlığı GTB beyanname takip havuzu."""
    records = _load_json_safe(GTB_STORAGE_PATH, [])
    return {"count": len(records), "items": records}
