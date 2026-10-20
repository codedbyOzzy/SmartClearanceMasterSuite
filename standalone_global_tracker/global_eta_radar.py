"""
================================================================================
DOĞRUER SMARTCLEARANCE — KÜRESEL KONTEYNER & CANLI ETA VARIŞ RADARI (v5.0)
================================================================================
Tasarım Dili   : Modern Denizcilik / Operasyon Kontrol Radarı (Maritime Cyber-Radar)
Özellikler     :
  - MSC Direkt TLS Motoru (< 1sn, 0 TL)
  - Hapag-Lloyd Resmi DCSA v2 API (< 0.5sn, 0 TL)
  - ONE & Diğer Armatörler Akıllı Prefix/DCSA Algılama
  - E (Acenta), F (B/L), T (Excel ETA), U (Konteyner) Sütun Haritası
  - Canlı ETA vs Excel ETA Sapma Radarı (Rötar / Erken / Zamanında)
  - Seçilebilir Saatlik/Günlük Otomatik Takip Periyodu (1 Saat - 24 Saat)
  - Toplu Konteyner & B/L Giriş Paneli (Dinamik Sayaçlı ve Kesintisiz Butonlu)
  - Canlı Özet Metrikleri (Toplam, Rötar, Erken, Zamanında sayaç kartları)
================================================================================
"""

import os
import sys
import json
import time
import threading
import re
import argparse
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# HTTP İstemcisi
try:
    from curl_cffi import requests
except ImportError:
    try:
        from curl_cffi import requests
    except ImportError:
        import urllib.request as requests

# Excel İşleme
try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
except ImportError:
    openpyxl = None


# ==============================================================================
# ARMATÖR VE PREFIX VERİTABANI
# ==============================================================================

CARRIER_PREFIX_MAP = {
    # MSC
    "MSNU": "MSC", "MEDU": "MSC", "MSCU": "MSC", "CSGU": "MSC",
    "TRHU": "MSC", "DRYU": "MSC", "KKFU": "MSC", "FFAU": "MSC",
    "TGHU": "MSC", "TTNU": "MSC", "GLDU": "MSC",

    # HAPAG-LLOYD
    "HLCU": "HAPAG", "HLBU": "HAPAG", "HLXU": "HAPAG", "HAMU": "HAPAG",
    "BMOU": "HAPAG", "SEGU": "HAPAG", "UACU": "HAPAG", "TCNU": "HAPAG",
    "NIDU": "HAPAG", "FCIU": "HAPAG", "UASU": "HAPAG", "FSCU": "HAPAG",
    "CAIU": "HAPAG", "CPSU": "HAPAG",

    # ONE (Ocean Network Express)
    "ONEU": "ONE", "NYKU": "ONE", "MOLU": "ONE", "KKLU": "ONE",
    "TGBU": "ONE",

    # CMA CGM
    "CMAU": "CMA-CGM", "APZU": "CMA-CGM", "ANLU": "CMA-CGM", "ECMU": "CMA-CGM",
    "SEKU": "CMA-CGM", "TLLU": "CMA-CGM", "TGCU": "CMA-CGM", "UETU": "CMA-CGM", "GCXU": "CMA-CGM",

    # MAERSK
    "MAEU": "MAERSK", "MSKU": "MAERSK", "MRKU": "MAERSK", "SUDU": "MAERSK",
    "PONU": "MAERSK",

    # COSCO
    "COSU": "COSCO", "CBHU": "COSCO", "CCLU": "COSCO",

    # EVERGREEN
    "EGLU": "EVERGREEN", "EGSU": "EVERGREEN", "EMCU": "EVERGREEN"
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar_config.json")
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar_cache.json")


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_cache(data, last_check_time=""):
    try:
        payload = {
            "last_check": last_check_time or datetime.now().strftime("%d.%m.%Y %H:%M"),
            "items": data
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_config():
    default_cfg = {
        "hapag_client_id": "af0e2d34-0000-415f-9b38-161f97d18c4a",
        "hapag_client_secret": "",
        "one_api_key": "",
        "cma_session_cookie": "",
        "cma_token": "",
        "default_excel_path": r"\\Dgfile01\ithalat\ITH28\Halit ENGELEK",
        "auto_sync_enabled": True,
        "auto_sync_interval_hours": 2  # Varsayılan 2 saatte bir kontrol
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_cfg.update(saved)
        except Exception:
            pass
    return default_cfg


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def resolve_excel_path(path_or_dir):
    """Verilen dosya veya klasör yolundaki en güncel Excel dosyasını tespit eder."""
    if not path_or_dir or not os.path.exists(path_or_dir):
        return ""
    if os.path.isfile(path_or_dir):
        return path_or_dir
    if os.path.isdir(path_or_dir):
        try:
            candidates = [
                os.path.join(path_or_dir, f) for f in os.listdir(path_or_dir)
                if f.lower().endswith(('.xlsx', '.xls')) and not f.startswith('~$')
            ]
            if not candidates:
                return ""
            rapor_files = [c for c in candidates if any(k in os.path.basename(c).upper() for k in ["RAPOR", "TAKİP", "HANKOOK", "LİSTE"])]
            if rapor_files:
                return max(rapor_files, key=os.path.getmtime)
            return max(candidates, key=os.path.getmtime)
        except Exception:
            pass
    return ""


def parse_date(val):
    """Farklı formatlardaki tarih verilerini date objesine dönüştürür."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    val_s = str(val).strip()
    if not val_s or val_s.upper() in ("NONE", "NULL", "—", "-", "", "NAN"):
        return None

    # T veya boşlukla ayrılmış saat kısmını ayıkla
    val_clean = val_s.split("T")[0].strip()
    parts = val_clean.split()
    if not parts:
        return None
    val_str = parts[0].strip()
    if not val_str:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y", "%Y.%m.%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except Exception:
            pass
    return None


def compute_eta_diff(excel_eta_val, live_eta_val):
    """Excel'deki T sütunu ile Canlı ETA arasındaki sapmayı hesaplar."""
    d_excel = parse_date(excel_eta_val)
    d_live = parse_date(live_eta_val)

    if not d_excel or not d_live:
        ex_str = d_excel.strftime("%d.%m.%Y") if d_excel else str(excel_eta_val or "—")
        return {
            "excel_eta_str": ex_str,
            "diff_days": None,
            "diff_text": "—",
            "diff_tag": "tag_normal"
        }

    diff = (d_live - d_excel).days  # Pozitifse gecikme, negatifse erken
    ex_formatted = d_excel.strftime("%d.%m.%Y")

    if diff == 0:
        return {
            "excel_eta_str": ex_formatted,
            "diff_days": 0,
            "diff_text": "✅ Aynı Gün",
            "diff_tag": "tag_ontime"
        }
    elif diff > 0:
        return {
            "excel_eta_str": ex_formatted,
            "diff_days": diff,
            "diff_text": f"🔴 +{diff}g Rötar",
            "diff_tag": "tag_delayed"
        }
    else:
        abs_diff = abs(diff)
        return {
            "excel_eta_str": ex_formatted,
            "diff_days": diff,
            "diff_text": f"🟢 -{abs_diff}g Erken",
            "diff_tag": "tag_early"
        }


def parse_batch_input(raw_text):
    """Kullanıcının çoklu yapıştırdığı metinden konteyner ve B/L'leri akıllıca ayıklar."""
    tokens = re.split(r'[\r\n,;\t\s]+', raw_text.strip())
    results = []
    seen = set()

    for tok in tokens:
        clean = tok.strip().upper()
        if not clean or len(clean) < 5 or clean in seen:
            continue

        seen.add(clean)
        kind = "B/L"
        carrier = "UNKNOWN"

        if len(clean) == 11 and clean[:4].isalpha() and clean[4:].isdigit():
            kind = "Konteyner"
            prefix = clean[:4]
            carrier = CARRIER_PREFIX_MAP.get(prefix, "UNKNOWN")
        elif clean.startswith("HLCU"):
            carrier = "HAPAG"
            kind = "B/L"
        elif clean.startswith("SELG"):
            carrier = "ONE"
            kind = "B/L"
        elif clean.startswith("MEDU"):
            carrier = "MSC"
            kind = "B/L"
        elif clean[:4] in CARRIER_PREFIX_MAP:
            carrier = CARRIER_PREFIX_MAP[clean[:4]]

        results.append({
            "number": clean,
            "type": kind,
            "carrier": carrier
        })

    return results


# ==============================================================================
# CARRIER ENGINE ADAPTÖRLERİ
# ==============================================================================

class MSCAdapter:
    """MSC Canlı Takip Motoru (Doğrudan TLS Engine)."""

    BASE_URL = "https://www.msc.com/en/track-a-shipment"
    API_URL = "https://www.msc.com/api/feature/tools/TrackingInfo"

    def __init__(self):
        try:
            self.session = requests.Session(impersonate="chrome124")
        except Exception:
            self.session = requests.Session()
        self.token = ""
        self._initialized = False

    def init_session(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8"
        }
        try:
            r = self.session.get(self.BASE_URL, headers=headers, timeout=15)
            if r.status_code == 200:
                self._initialized = True
                m = re.search(r'name=["\']__RequestVerificationToken["\']\s+type=["\']hidden["\']\s+value=["\']([^"\']+)["\']', r.text)
                if not m:
                    m = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']__RequestVerificationToken["\']', r.text)
                if m:
                    self.token = m.group(1)
                return True
        except Exception:
            pass
        return False

    def track(self, number, excel_eta=None):
        if not self._initialized:
            self.init_session()

        clean_num = str(number).strip().upper()
        payload = {"trackingNumber": clean_num, "trackingMode": "0"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.msc.com",
            "Referer": self.BASE_URL
        }
        if self.token:
            headers["__RequestVerificationToken"] = self.token

        try:
            resp = self.session.post(self.API_URL, json=payload, headers=headers, timeout=15)
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}

            data = resp.json()
            if not data.get("IsSuccess") or not data.get("Data"):
                return {"success": False, "error": data.get("Message") or "MSC kaydı bulunamadı"}

            return self._parse(clean_num, data["Data"], excel_eta=excel_eta)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse(self, query, raw, excel_eta=None):
        bols = raw.get("BillOfLadings", [])
        today = datetime.now().date()
        results = []

        for b in bols:
            bl_no = b.get("BillOfLadingNumber") or "—"
            gen = b.get("GeneralTrackingInfo") or {}
            pol = gen.get("PortOfLoad") or "—"
            pod = gen.get("PortOfDischarge") or "—"
            containers = b.get("ContainersInfo") or []

            for c in containers:
                cntr_no = c.get("ContainerNumber") or query
                eta_val = c.get("PodEtaDate") or gen.get("FinalPodEtaDate") or ""
                vessel = "—"
                voyage = "—"
                trans = []

                for ev in c.get("Events") or []:
                    desc = str(ev.get("Description") or "")
                    det = ev.get("Detail") or []
                    if "Estimated Time of Arrival" in desc or "ETA" in desc:
                        if ev.get("Date"):
                            eta_val = ev.get("Date")
                        if det and len(det) >= 1:
                            vessel = det[0]
                        if det and len(det) >= 2:
                            voyage = det[1]
                    for port_call in ev.get("IntermediaryPortCalls") or []:
                        loc = port_call.get("LocationName")
                        if loc and loc not in trans:
                            trans.append(loc)

                kalan_gun_str = "—"
                if eta_val:
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
                        try:
                            dt = datetime.strptime(eta_val.split()[0], fmt).date()
                            diff = (dt - today).days
                            if diff == 0:
                                kalan_gun_str = "Bugün Varış"
                            elif diff > 0:
                                kalan_gun_str = f"{diff} Gün Kaldı"
                            else:
                                kalan_gun_str = f"Gecikti ({abs(diff)}g)"
                            break
                        except Exception:
                            pass

                # ETA Sapma Analizi
                eta_diff_info = compute_eta_diff(excel_eta, eta_val)

                results.append({
                    "carrier": "MSC",
                    "container_no": cntr_no,
                    "bl_no": bl_no,
                    "excel_eta": eta_diff_info["excel_eta_str"],
                    "live_eta": eta_val,
                    "eta_diff": eta_diff_info["diff_text"],
                    "diff_tag": eta_diff_info["diff_tag"],
                    "vessel": f"{vessel} ({voyage})" if voyage != "—" else vessel,
                    "pol": pol,
                    "pod": pod,
                    "kalan_gun": kalan_gun_str,
                    "transshipments": " -> ".join(trans) if trans else "Direkt",
                    "source": "MSC Direct Engine"
                })

        return {"success": True, "items": results}


class HapagLloydAdapter:
    """Hapag-Lloyd Resmi DCSA Track & Trace API Motoru (0 TL, Yüksek Hızlı)."""

    BASE_URL = "https://api.hlag.com/hlag/external/v2/events/"

    def __init__(self, client_id="", client_secret=""):
        self.client_id = client_id
        self.client_secret = client_secret

    def track(self, number, excel_eta=None):
        if not self.client_id or not self.client_secret:
            return {"success": False, "error": "Hapag-Lloyd Client ID veya Secret eksik."}

        clean_num = str(number).strip().upper()
        param = "equipmentReference" if len(clean_num) == 11 and clean_num[:4].isalpha() and clean_num[4:].isdigit() else "transportDocumentReference"
        url = f"{self.BASE_URL}?{param}={clean_num}"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-IBM-Client-ID": self.client_id,
            "X-IBM-Client-Secret": self.client_secret,
            "User-Agent": "Mozilla/5.0"
        }

        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 204:
                    return {"success": False, "error": f"Hapag-Lloyd'da kayıt bulunamadı ({clean_num})"}
                data = json.loads(resp.read().decode('utf-8'))
                if not data or not isinstance(data, list):
                    return {"success": False, "error": "Hapag-Lloyd kaydı bulunamadı"}
                # --- DEBUG: Ham API yanıtını kaydet ---
                self._save_debug(clean_num, data)
                return self._parse(clean_num, data, excel_eta=excel_eta)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {"success": False, "error": "Hapag API: Yetkilendirme hatası (Client ID / Secret geçersiz)"}
            return {"success": False, "error": f"Hapag API HTTP {e.code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_debug(self, cntr_no: str, raw_events: list):
        """Ham Hapag API yanıtını JSON dosyasına yazar (tanı amaçlı)."""
        try:
            debug_dir = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "SmartClearance", "hapag_debug"
            )
            os.makedirs(debug_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = os.path.join(debug_dir, f"{cntr_no}_{ts}.json")
            # Özet: her event için kritik alanları göster
            summary = []
            for ev in raw_events:
                loc = ev.get("eventLocation") or {}
                tc = ev.get("transportCall") or {}
                vessel = (tc.get("vessel") or {}).get("vesselName", "")
                summary.append({
                    "eventClassifierCode": ev.get("eventClassifierCode"),
                    "transportEventTypeCode": ev.get("transportEventTypeCode"),
                    "equipmentEventTypeCode": ev.get("equipmentEventTypeCode"),
                    "eventDateTime": ev.get("eventDateTime"),
                    "locationName": loc.get("locationName"),
                    "UNLocationCode": loc.get("UNLocationCode"),
                    "vesselName": vessel,
                    "equipmentReference": ev.get("equipmentReference"),
                })
            with open(fname, "w", encoding="utf-8") as f:
                json.dump({"container": cntr_no, "event_count": len(raw_events),
                           "events": summary, "raw": raw_events}, f,
                          indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _parse(self, query, events, excel_eta=None):
        today = datetime.now().date()
        bl_no = "—"
        cntr_no = query

        sorted_events = []
        for ev in events:
            dt_str = ev.get("eventDateTime") or ""
            sorted_events.append((dt_str, ev))
        sorted_events.sort(key=lambda x: x[0])

        pol = "—"
        pod = "—"
        vessels = []
        transshipments = []
        final_eta = ""
        actual_arrival = ""
        actual_disc = ""
        planned_eta = ""
        planned_tr_disc = ""
        empty_return_date = "—"
        empty_return_address = "—"

        for dt_str, ev in sorted_events:
            for doc in ev.get("documentReferences") or []:
                if doc.get("documentReferenceType") in ("BKG", "TRD", "CBR"):
                    val = doc.get("documentReferenceValue")
                    if val and bl_no == "—":
                        bl_no = val

            c_ref = ev.get("equipmentReference")
            if c_ref and cntr_no == query:
                cntr_no = c_ref

            loc_info = ev.get("eventLocation") or {}
            loc_name = loc_info.get("locationName") or ""
            unloc = loc_info.get("UNLocationCode") or ""

            t_call = ev.get("transportCall") or {}
            v_info = t_call.get("vessel") or {}
            v_name = v_info.get("vesselName")

            if v_name and v_name not in vessels:
                vessels.append(v_name)

            type_code = ev.get("equipmentEventTypeCode") or ev.get("transportEventTypeCode") or ""
            classifier = ev.get("eventClassifierCode") or ""

            if not pol or pol == "—":
                if loc_name and (classifier == "ACT" or type_code in ("LOAD", "DEPA")):
                    pol = f"{loc_name} ({unloc})" if unloc else loc_name

            is_tr_port = unloc.startswith("TR") or any(k in (loc_name or "").upper() for k in [
                "IZMIT", "GEBZE", "EVYAP", "AMBARLI", "DERINCE", "ISTANBUL", "HAYDARPASA",
                "YARIMCA", "KORFEZ", "KOCAELI", "TUZLA", "ALIAGA", "MARPORT", "FILPORT",
                "ASYAPORT", "NEMRUT", "GEMPORT", "BOTAS", "CEYHAN", "MERSIN", "ISKENDERUN",
                "IZMIR", "BANDIRMA", "TEKIRDAG", "TRABZON", "SAMSUN", "ANTALYA"
            ])

            if is_tr_port and type_code != "GTIN":
                pod = f"{loc_name} ({unloc})" if unloc else loc_name

            # 1. Gerçekleşen Varış & Tahliye (ACT)
            if classifier == "ACT":
                if is_tr_port:
                    if type_code == "ARRI":
                        actual_arrival = dt_str
                    elif type_code == "DISC":
                        actual_disc = dt_str
            # 2. Planlanan Gemi Varışı / Tahliyesi (PLN / EST)
            elif classifier in ("PLN", "EST"):
                if is_tr_port and type_code in ("DISC", "ARRI"):
                    planned_tr_disc = dt_str
                elif type_code in ("ARRI", "DISC") and not planned_eta:
                    planned_eta = dt_str
                elif type_code == "GTIN":
                    empty_return_date = dt_str.split("T")[0] if "T" in dt_str else dt_str
                    empty_return_address = loc_name or unloc or "GEBZE"

            if loc_name and loc_name not in transshipments and loc_name != pol:
                transshipments.append(loc_name)

        if planned_tr_disc:
            planned_eta = planned_tr_disc

        if not pod or pod == "—":
            if transshipments:
                pod = transshipments[-1]

        # -----------------------------------------------------------------------
        # Asıl Taşıma Gemisini Belirle:
        # Öncelik: ACT ARRI (Türkiye limanına fiilen yanaşan gemi) >
        #          ACT LOAD (yükleme limanında konteyner bindiren gemi) >
        #          ACT DISC > Kronolojik olarak ilk görülen gemi
        # DÜZELTME: vessels[-1] yerine gerçek taşıma gemisini seçiyoruz.
        # -----------------------------------------------------------------------
        _arri_vessel = None
        _disc_vessel = None
        _load_vessel = None
        for _dt, _ev in sorted_events:
            _tc = _ev.get("transportCall") or {}
            _vi = _tc.get("vessel") or {}
            _vn = _vi.get("vesselName")
            _tc2 = _ev.get("equipmentEventTypeCode") or _ev.get("transportEventTypeCode") or ""
            _cl = _ev.get("eventClassifierCode") or ""
            _li = _ev.get("eventLocation") or {}
            _ln = _li.get("locationName") or ""
            _ul = _li.get("UNLocationCode") or ""
            _tr = _ul.startswith("TR") or any(k in (_ln or "").upper() for k in [
                "IZMIT", "GEBZE", "EVYAP", "AMBARLI", "DERINCE", "ISTANBUL", "HAYDARPASA",
                "YARIMCA", "KORFEZ", "KOCAELI", "TUZLA", "ALIAGA", "MARPORT", "FILPORT",
                "ASYAPORT", "NEMRUT", "GEMPORT", "BOTAS", "CEYHAN", "MERSIN", "ISKENDERUN",
                "IZMIR", "BANDIRMA", "TEKIRDAG", "TRABZON", "SAMSUN", "ANTALYA"
            ])
            if _vn:
                if _cl == "ACT" and _tr and _tc2 == "ARRI":
                    _arri_vessel = _vn
                elif _cl == "ACT" and _tr and _tc2 == "DISC":
                    _disc_vessel = _vn
                elif _cl == "ACT" and _tc2 == "LOAD":
                    _load_vessel = _vn
        final_vessel = _arri_vessel or _load_vessel or _disc_vessel or (vessels[0] if vessels else "—")

        # Canlı Tarih & Kalan Gün Analizi
        kalan_gun_str = "—"
        already_arrived = False
        if actual_arrival or actual_disc:
            target_dt = actual_arrival or actual_disc
            clean_eta = target_dt.split("T")[0] if "T" in target_dt else target_dt
            kalan_gun_str = "Limana İndi"
            already_arrived = True
        elif planned_eta:
            clean_eta = planned_eta.split("T")[0] if "T" in planned_eta else planned_eta
            try:
                dt = datetime.strptime(clean_eta.split()[0], "%Y-%m-%d").date()
                diff = (dt - today).days
                if diff == 0:
                    kalan_gun_str = "Bugün Varış"
                elif diff > 0:
                    kalan_gun_str = f"{diff} Gün Kaldı"
                else:
                    # Planlanan tarih geçmiş ama ACT olayı yoksa → büyük olasılıkla varmış
                    kalan_gun_str = "Limana İndi"
                    already_arrived = True
            except Exception:
                pass
        else:
            clean_eta = "—"

        trans_str = " -> ".join(transshipments) if transshipments else "Direkt"

        # -----------------------------------------------------------------------
        # ETA Sapma Analizi:
        # Yük zaten limana gelmiş ise rötar hesaplama YAPMA — "✅ Varmış" göster.
        # Bu şekilde "19.09.2026'da geldi, ETA 25.09 görünüyor → +6g Rötar"
        # yanlışlığının önüne geçilmiş olur.
        # -----------------------------------------------------------------------
        if already_arrived:
            d_excel = parse_date(excel_eta)
            excel_eta_str = d_excel.strftime("%d.%m.%Y") if d_excel else (str(excel_eta)[:10] if excel_eta else "—")
            eta_diff_info = {
                "excel_eta_str": excel_eta_str,
                "diff_days": 0,
                "diff_text": "✅ Varmış",
                "diff_tag": "tag_arrived"
            }
        else:
            eta_diff_info = compute_eta_diff(excel_eta, clean_eta)

        return {
            "success": True,
            "items": [{
                "carrier": "HAPAG-LLOYD",
                "container_no": cntr_no,
                "bl_no": bl_no,
                "excel_eta": eta_diff_info["excel_eta_str"],
                "live_eta": clean_eta,
                "eta_diff": eta_diff_info["diff_text"],
                "diff_tag": eta_diff_info["diff_tag"],
                "vessel": final_vessel,
                "pol": pol,
                "pod": pod,
                "kalan_gun": kalan_gun_str,
                "transshipments": trans_str,
                "empty_return_date": empty_return_date,
                "empty_return_address": empty_return_address,
                "source": "Hapag-Lloyd Official DCSA API"
            }]
        }


class CMACGMAdapter:
    """CMA CGM Resmi API Motoru - Gelişmiş B/L Caching (Kota Dostu)."""

    BASE_URL = "https://apis.cma-cgm.net/operation/trackandtrace/v1/events"

    def __init__(self, cookie_str="", token=""):
        self.api_key = cookie_str.strip() if cookie_str else "UovvlLGBlrdPnnOmT61VJywdygirD0VI"
        # B/L bazlı raw API yanıtlarını bellekte tutarak aynı seansta tekrar API'ye gitmeyi engeller (Kota tasarrufu)
        self.api_bl_cache = {}

    def update_credentials(self, cookie_str, token=""):
        self.api_key = cookie_str.strip() if cookie_str else self.api_key

    def track(self, number, excel_eta=None, bl_hint=""):
        if not self.api_key:
            return {"success": False, "error": "CMA CGM API Anahtarı eksik."}

        clean_num = str(number).strip().upper()
        clean_bl = str(bl_hint).strip().upper() if bl_hint and bl_hint != "—" else ""
        
        # 1. AKILLI KOTA MEKANİZMASI: Eğer bu B/L daha önce sorgulanmışsa, API'ye gitmeden bellekten oku!
        if clean_bl and clean_bl in self.api_bl_cache:
            raw_data = self.api_bl_cache[clean_bl]
            return self._parse(clean_num, raw_data, excel_eta, clean_bl)

        # 2. Eğer B/L verilmişse (Çoğu durumda Excel'de var), doğrudan B/L ile API'ye git (En güvenlisi)
        if clean_bl:
            url = f"{self.BASE_URL}?transportDocumentReference={clean_bl}"
            res_raw = self._fetch_api(url, clean_bl)
            
            if res_raw.get("success"):
                # Gelen B/L verisini belleğe kaydet (Sonraki konteynerler API'ye gitmesin)
                self.api_bl_cache[clean_bl] = res_raw["data"]
                return self._parse(clean_num, res_raw["data"], excel_eta, clean_bl)
            elif "Yetkisiz" in res_raw.get("error", "") or "Too Many Requests" in res_raw.get("error", ""):
                # Kota veya yetki hatasıysa direkt dön, konteynerle denemeye gerek yok
                return {"success": False, "error": res_raw["error"]}

        # 3. Eğer Excel'de B/L yoksa veya B/L sorgusu bulunamadı döndüyse, mecburen konteyner no ile dene
        url_cntr = f"{self.BASE_URL}?equipmentReference={clean_num}"
        res_raw_cntr = self._fetch_api(url_cntr, clean_num)
        
        if res_raw_cntr.get("success"):
            return self._parse(clean_num, res_raw_cntr["data"], excel_eta, clean_bl)
            
        return {"success": False, "error": res_raw_cntr.get("error", "Kayıt bulunamadı")}

    def _fetch_api(self, url, ref):
        import urllib.request
        import urllib.error
        import json
        
        headers = {
            "Accept": "application/json",
            "KeyId": self.api_key
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 204:
                    return {"success": False, "error": f"Kayıt bulunamadı ({ref})"}
                data = json.loads(resp.read().decode('utf-8'))
                if not data or not isinstance(data, list):
                    return {"success": False, "error": "Boş yanıt"}
                return {"success": True, "data": data}
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, 'code'):
                if e.code == 401:
                    err_msg = "Yetkisiz (API Anahtarı geçersiz)"
                elif e.code == 429:
                    err_msg = "Saatlik Kota Aşıldı (Too Many Requests)"
                elif e.code == 403:
                    err_msg = "Erişim Engellendi (403)"
            return {"success": False, "error": f"CMA API: {err_msg}"}

    def _parse(self, query, events, excel_eta, expected_bl):
        from datetime import datetime, date
        today = date.today()
        bl_no = expected_bl if expected_bl else "—"
        vessel = "—"
        pod = "—"
        live_eta_str = "—"
        live_eta_dt = None
        trans = []
        
        def get_date(ev):
            # API'deki en güvenilir tarih eventDateTime'dır.
            return ev.get("eventDateTime") or ev.get("eventCreatedDateTime") or ""
            
        # Filtreleme: Eğer API B/L ile çağrıldıysa, tüm konteynerlerin eventleri gelir.
        # Sadece bizim aradığımız konteynere ait eventleri filtrelemeliyiz.
        filtered_events = []
        for ev in events:
            is_match = False
            for ref in ev.get("references", []):
                if ref.get("referenceType") == "EQ" and ref.get("referenceValue", "").upper() == query:
                    is_match = True
                    break
            # Eğer referans yoksa veya eşleşiyorsa (bazen genel event olabilir)
            if is_match or not ev.get("references"):
                filtered_events.append(ev)
                
        # Eğer özel event bulamadıysa (örneğin B/L geneli ise) hepsini kullan
        target_events = filtered_events if filtered_events else events
        
        events_sorted = sorted(target_events, key=get_date)
        
        for ev in events_sorted:
            # B/L numarasını event içinden de teyit edebiliriz
            for doc in ev.get("documentReferences", []):
                if doc.get("documentReferenceType") in ("BKG", "BL"):
                    bl_no = doc.get("documentReferenceValue", bl_no)
            
            tc = ev.get("transportCall") or {}
            loc = tc.get("location") or {}
            loc_name = loc.get("locationName") or loc.get("UNLocationCode")
            
            # Gemi adı (varsa)
            ves = tc.get("vessel") or {}
            if ves.get("vesselName"):
                vessel = ves.get("vesselName")
            
            if loc_name and ev.get("transportEventTypeCode") in ("ARRI", "DEPA"):
                if loc_name not in trans:
                    trans.append(loc_name)
                    
            # DOĞRU ETA MANTIĞI: (Sadece Planlanan ve Tahmini Varışları dikkate al)
            if ev.get("eventClassifierCode") in ("PLN", "EST"):
                dt_str = get_date(ev)
                if dt_str:
                    try:
                        clean_dt = dt_str.split("T")[0]
                        temp_dt = datetime.strptime(clean_dt, "%Y-%m-%d").date()
                        # En ileri tarihi (Final POD) ETA olarak kabul et
                        if not live_eta_dt or temp_dt > live_eta_dt:
                            live_eta_dt = temp_dt
                            live_eta_str = live_eta_dt.strftime("%d.%m.%Y")
                            if loc_name:
                                pod = loc_name
                    except Exception:
                        pass
        
        kalan_gun_str = "—"
        if live_eta_dt:
            diff = (live_eta_dt - today).days
            if diff == 0:
                kalan_gun_str = "Bugün Varış"
            elif diff > 0:
                kalan_gun_str = f"{diff} Gün Kaldı"
            else:
                kalan_gun_str = f"{abs(diff)} Gün Önce Geldi"
                
        res = {
            "container_no": query if len(query) == 11 else "—",
            "bl_no": bl_no,
            "vessel": vessel,
            "pod": pod,
            "live_eta": live_eta_str,
            "eta_diff": "Bekleniyor",
            "diff_tag": "tag_pending",
            "kalan_gun": kalan_gun_str,
            "transshipments": " -> ".join(trans[-2:]) if trans else "—",
            "source": "CMA CGM (Akıllı API)"
        }
        
        # Eğer konteyner numarası bulunamadıysa eventlerden çıkarmaya çalış
        if res["container_no"] == "—":
            for ev in events:
                for ref in ev.get("references", []):
                    if ref.get("referenceType") == "EQ":
                        res["container_no"] = ref.get("referenceValue")
                        break
        
        if excel_eta and live_eta_str != "—":
            from standalone_global_tracker.global_eta_radar import compute_eta_diff
            diff_res = compute_eta_diff(excel_eta, live_eta_str)
            res["eta_diff"] = diff_res["diff_text"]
            res["diff_tag"] = diff_res["diff_tag"]
            
        return {"success": True, "items": [res]}

class COSCOAdapter:
    """COSCO Canlı Takip Motoru (COP API veya 3PL İçin Hazırlık)."""

    def __init__(self, api_key=""):
        self.api_key = api_key

    def track(self, number, excel_eta=None):
        clean_num = str(number).strip().upper()
        # Not: COSCO açık bir API sağlamadığı için burada resmi COP (Open Platform) 
        # veya 3. parti (TrackingMore, JSONCargo) API bağlantısı yapılmalıdır.
        
        # Şimdilik API entegrasyonu olmadığı için Excel verisini döner.
        return {
            "success": True,
            "items": [{
                "container_no": clean_num,
                "bl_no": "—",
                "vessel": "COSCO Gemi (API Gerekli)",
                "pod": "—",
                "live_eta": excel_eta if excel_eta else "—",
                "eta_diff": "Planlı Sefer",
                "kalan_gun": "Seferde",
                "transshipments": "—",
                "source": "COSCO (API Entegrasyonu Bekleniyor)"
            }]
        }



def normalize_turkish(text):
    if not text:
        return ""
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return str(text).translate(tr_map).upper().strip()

class GlobalTrackingRouter:
    """Tüm sorguları doğru armatör motoruna yönlendiren koordinatör."""

    def __init__(self, config=None):
        self.cosco_adapter = COSCOAdapter()
        self.config = config or load_config()
        self.msc_adapter = MSCAdapter()
        self.hapag_adapter = HapagLloydAdapter(
            client_id=self.config.get("hapag_client_id", ""),
            client_secret=self.config.get("hapag_client_secret", "")
        )
        self.cma_adapter = CMACGMAdapter(
            cookie_str=self.config.get("cma_session_cookie", ""),
            token=self.config.get("cma_token", "")
        )

    def detect_carrier(self, number, acenta_hint="", bl_hint="", gemi_hint=""):
        clean_num = str(number).strip().upper()
        clean_hint = normalize_turkish(acenta_hint)
        clean_bl = str(bl_hint or "").strip().upper()
        clean_gemi = normalize_turkish(gemi_hint)

        # 1. Konşimento (B/L) Önceliği — Kiralık konteynerler bile B/L koduna bağlıdır!
        if clean_bl:
            if clean_bl.startswith(("COEU", "COSU", "CCLU", "CBHU")):
                return "COSCO"
            if clean_bl.startswith("BUP"):
                return "CMA-CGM"
            if clean_bl.startswith("MEDU"):
                return "MSC"
            if clean_bl.startswith("HLCU"):
                return "HAPAG"
            if clean_bl.startswith(("SELG", "ONEY", "SH6SJ", "SELGH", "SELGE")):
                return "ONE"
            if clean_bl.startswith("GLVS"):
                return "MSC"
            if clean_bl.startswith(("MAEU", "MSKU")):
                return "MAERSK"
            if clean_bl.startswith("EGLU"):
                return "EVERGREEN"

        # 2. Acenta / Armatör Metin İpucu
        if "MSC" in clean_hint or "GLOVIS" in clean_hint:
            return "MSC"
        if "HAPAG" in clean_hint:
            return "HAPAG"
        if "ONE" in clean_hint or "OCEAN NETWORK" in clean_hint:
            return "ONE"
        if "CMA" in clean_hint or "APL" in clean_hint or "CNC" in clean_hint:
            return "CMA-CGM"
        if "COSCO" in clean_hint:
            return "COSCO"
        if "MAERSK" in clean_hint:
            return "MAERSK"
        if "EVERGREEN" in clean_hint:
            return "EVERGREEN"

        # 3. Gemi Adı İpucu
        if "COSCO" in clean_gemi:
            return "COSCO"
        if "MSC " in clean_gemi or clean_gemi.startswith("MSC"):
            return "MSC"
        if "CMA CGM" in clean_gemi or "CMA " in clean_gemi:
            return "CMA-CGM"
        if "MAERSK" in clean_gemi:
            return "MAERSK"
        if "ONE " in clean_gemi:
            return "ONE"

        # 4. Sorgulanan Numara B/L ise
        if clean_num.startswith(("COEU", "COSU", "CCLU", "CBHU")):
            return "COSCO"
        if clean_num.startswith("BUP"):
            return "CMA-CGM"
        if clean_num.startswith("HLCU"):
            return "HAPAG"
        if clean_num.startswith(("SELG", "ONEY")):
            return "ONE"
        if clean_num.startswith("MEDU"):
            return "MSC"
        if clean_num.startswith("GLVS"):
            return "MSC"

        # 5. Konteyner ISO Prefix (Yalnızca yukarıdakilerden hiçbiri yoksa son çare)
        prefix = clean_num[:4]
        if prefix in CARRIER_PREFIX_MAP:
            return CARRIER_PREFIX_MAP[prefix]

        return "UNKNOWN"

    def track(self, number, acenta_hint="", excel_eta=None, bl_hint="", gemi_hint=""):
        carrier = self.detect_carrier(number, acenta_hint, bl_hint=bl_hint, gemi_hint=gemi_hint)

        # 1. Tier: MSC (Doğrudan Ücretsiz TLS Motoru)
        if carrier == "MSC":
            return self.msc_adapter.track(number, excel_eta=excel_eta)

        # 2. Tier: Hapag-Lloyd (Resmi DCSA API Motoru)
        if carrier == "HAPAG":
            return self.hapag_adapter.track(number, excel_eta=excel_eta)

        # 3. Tier: CMA CGM (Canlı Oturum Web Motoru)
        if carrier == "CMA-CGM":
            return self.cma_adapter.track(number, excel_eta=excel_eta, bl_hint=bl_hint)

        # 4. Tier: COSCO (Manuel e-Services veya 3PL Motoru)
        if carrier == "COSCO":
            return self.cosco_adapter.track(number, excel_eta=excel_eta)

        # Fallback
        return {
            "success": False,
            "error": f"[{carrier}] hattı için henüz API anahtarı veya canlı motor tanımlı değil."
        }


# ==============================================================================
# SİBER DENİZCİLİK RADARI ARAYÜZÜ (MODERN CYBER-RADAR GUI)
# ==============================================================================

class GlobalRadarGUI:
    """Küresel Konteyner ve Canlı ETA Takip Radarı v5.0."""

    THEME = {
        "bg_dark": "#080e1a",       # En koyu arka plan
        "panel_bg": "#0f172a",      # Kontrol panelleri
        "card_bg": "#1e293b",       # Kartlar ve kutular
        "accent_cyan": "#00f0ff",   # Radar camgöbeği
        "accent_blue": "#38bdf8",   # Bilgi mavisi
        "accent_green": "#10b981",  # Başarı / Erken
        "accent_red": "#f43f5e",    # Rötar / Uyarı
        "accent_amber": "#f59e0b",  # Dikkat
        "text_main": "#f8fafc",     # Ana açık metin
        "text_muted": "#94a3b8"     # Soluk gri metin
    }

    INTERVAL_OPTIONS = [
        ("30 Dakika", 0.5),
        ("1 Saat", 1),
        ("2 Saat", 2),
        ("4 Saat", 4),
        ("6 Saat", 6),
        ("12 Saat", 12),
        ("24 Saat (1 Gün)", 24)
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("🛰️ DOĞRUER SMARTCLEARANCE — KÜRESEL CANLI ETA TAKİP RADARI v5.0")
        self.root.geometry("1480x840")
        self.root.minsize(1100, 680)
        try:
            self.root.state("zoomed")
        except Exception:
            pass
        self.root.configure(bg=self.THEME["bg_dark"])

        self.config = load_config()
        self.router = GlobalTrackingRouter(self.config)
        self.results_data = []

        self._last_mtime = 0
        self._watcher_running = True
        self._sync_in_progress = False

        self._setup_styles()
        self._setup_ui()
        self._load_cached_state()
        self._start_watcher_thread()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Radar.Treeview",
            background="#ffffff",
            foreground="#0f172a",
            fieldbackground="#ffffff",
            font=("Segoe UI", 9),
            rowheight=28
        )
        style.configure(
            "Radar.Treeview.Heading",
            background="#1e293b",
            foreground="#00f0ff",
            font=("Segoe UI", 9, "bold"),
            relief="flat"
        )
        style.map("Radar.Treeview.Heading", background=[("active", "#334155")])

    def _setup_ui(self):
        # 1. Üst Radar Başlık & Sayaç Metrikleri
        header = tk.Frame(self.root, bg=self.THEME["panel_bg"], padx=20, pady=12)
        header.pack(fill=tk.X)

        h_left = tk.Frame(header, bg=self.THEME["panel_bg"])
        h_left.pack(side=tk.LEFT, fill=tk.Y)

        lbl_logo = tk.Label(
            h_left, text="🛰️ KÜRESEL KONTEYNER & CANLI ETA RADARI",
            font=("Segoe UI", 16, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["panel_bg"]
        )
        lbl_logo.pack(anchor="w")

        lbl_desc = tk.Label(
            h_left,
            text="Doğruer Liman & Acenta Canlı Takip Radarı | MSC (Direkt Engine) & Hapag-Lloyd (Resmi DCSA)",
            font=("Segoe UI", 9), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Sağ Taraf: Metrik Sayaç Kartları ve Ayarlar
        h_right = tk.Frame(header, bg=self.THEME["panel_bg"])
        h_right.pack(side=tk.RIGHT)

        # Kartlar: Toplam, Rötar, Erken, Zamanında
        self.card_total = self._create_metric_card(h_right, "TOPLAM YÜK", "0", self.THEME["accent_blue"])
        self.card_delayed = self._create_metric_card(h_right, "🔴 RÖTAR / GECİKME", "0", self.THEME["accent_red"])
        self.card_early = self._create_metric_card(h_right, "🟢 ERKEN VARIŞ", "0", self.THEME["accent_green"])
        self.card_ontime = self._create_metric_card(h_right, "✅ ZAMANINDA", "0", self.THEME["accent_cyan"])

        btn_settings = tk.Button(
            h_right, text="⚙️ Acenta API Ayarları", font=("Segoe UI", 9, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff",
            relief=tk.FLAT, padx=12, pady=6, cursor="hand2", command=self.open_settings_dialog
        )
        btn_settings.pack(side=tk.LEFT, padx=(12, 0))

        # 2. Ana Kontrol Paneli (Komuta Çubuğu)
        ctrl_bar = tk.Frame(self.root, bg=self.THEME["bg_dark"], padx=16, pady=8)
        ctrl_bar.pack(fill=tk.X)

        # 2.1. Üst Satır: Excel Klasör Seçimi ve Periyodik Canlı İzleme
        f_top = tk.Frame(ctrl_bar, bg=self.THEME["panel_bg"], padx=14, pady=8, bd=1, relief=tk.SOLID)
        f_top.pack(fill=tk.X, pady=(0, 6))

        lbl_path = tk.Label(
            f_top, text="📁 İş Takip Excel / Klasör Yolu:",
            font=("Segoe UI", 9, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["panel_bg"]
        )
        lbl_path.pack(side=tk.LEFT, padx=(0, 8))

        self.txt_excel_path = tk.Entry(
            f_top, font=("Segoe UI", 10), bg="#1e293b", fg="#ffffff",
            insertbackground="#00f0ff", bd=1, relief=tk.SOLID
        )
        self.txt_excel_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=3)
        self.txt_excel_path.insert(0, self.config.get("default_excel_path", ""))

        btn_browse = tk.Button(
            f_top, text="📂 Gözat...", font=("Segoe UI", 9, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569",
            relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self.browse_excel_path
        )
        btn_browse.pack(side=tk.LEFT, padx=(0, 10))

        btn_scan = tk.Button(
            f_top, text="⚡ Excel'i Oku & Eşitle", font=("Segoe UI", 9, "bold"),
            bg="#10b981", fg="#ffffff", activebackground="#059669",
            relief=tk.FLAT, padx=11, pady=4, cursor="hand2", command=self.scan_excel
        )
        btn_scan.pack(side=tk.LEFT, padx=(0, 6))

        btn_refresh_mem = tk.Button(
            f_top, text="🔄 Canlı ETA'ları Tazele", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1",
            relief=tk.FLAT, padx=11, pady=4, cursor="hand2", command=self.refresh_live_from_memory
        )
        btn_refresh_mem.pack(side=tk.LEFT, padx=(0, 10))

        # Periyot Seçici ve Canlı Senkron
        sep1 = tk.Frame(f_top, bg="#334155", width=1, height=24)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self.chk_auto_sync_var = tk.BooleanVar(value=self.config.get("auto_sync_enabled", True))
        chk_sync = tk.Checkbutton(
            f_top, text="🟢 Canlı Otomatik Takip", variable=self.chk_auto_sync_var,
            font=("Segoe UI", 9, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["panel_bg"],
            selectcolor="#1e293b", activebackground=self.THEME["panel_bg"], cursor="hand2",
            command=self._on_toggle_sync
        )
        chk_sync.pack(side=tk.LEFT, padx=(6, 6))

        tk.Label(
            f_top, text="Aralık:", font=("Segoe UI", 9), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]
        ).pack(side=tk.LEFT)

        self.cmb_interval = ttk.Combobox(
            f_top, values=[opt[0] for opt in self.INTERVAL_OPTIONS],
            state="readonly", width=14, font=("Segoe UI", 9)
        )
        # Seçili olanı bul
        cur_h = self.config.get("auto_sync_interval_hours", 2)
        sel_idx = 2
        for idx, opt in enumerate(self.INTERVAL_OPTIONS):
            if opt[1] == cur_h:
                sel_idx = idx
                break
        self.cmb_interval.current(sel_idx)
        self.cmb_interval.bind("<<ComboboxSelected>>", self._on_interval_change)
        self.cmb_interval.pack(side=tk.LEFT, padx=(4, 0))

        sep2 = tk.Frame(f_top, bg="#334155", width=1, height=24)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self.chk_only_active_var = tk.BooleanVar(value=self.config.get("only_active_shipments", True))
        chk_active = tk.Checkbutton(
            f_top, text="🎯 Sadece Aktif Yükler (Bugün & Gelecek)", variable=self.chk_only_active_var,
            font=("Segoe UI", 9, "bold"), fg=self.THEME["accent_green"], bg=self.THEME["panel_bg"],
            selectcolor="#1e293b", activebackground=self.THEME["panel_bg"], cursor="hand2",
            command=self._on_toggle_active_filter
        )
        chk_active.pack(side=tk.LEFT, padx=(4, 6))

        # 2.2. Alt Satır: Manuel Giriş, Hızlı Arama, Rapor ve Temizle
        f_bot = tk.Frame(ctrl_bar, bg=self.THEME["bg_dark"])
        f_bot.pack(fill=tk.X)

        btn_batch = tk.Button(
            f_bot, text="✍️ Manuel Çoklu Ekle (Toplu Giriş)", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1",
            relief=tk.FLAT, padx=14, pady=5, cursor="hand2", command=self.open_manual_batch_dialog
        )
        btn_batch.pack(side=tk.LEFT, padx=(0, 14))

        # Tekil Arama
        lbl_q = tk.Label(f_bot, text="Hızlı Sorgu:", font=("Segoe UI", 9, "bold"), fg=self.THEME["text_muted"], bg=self.THEME["bg_dark"])
        lbl_q.pack(side=tk.LEFT, padx=(0, 4))

        self.txt_query = tk.Entry(
            f_bot, font=("Segoe UI", 10, "bold"), width=16, bg="#1e293b", fg="#ffffff",
            insertbackground="#00f0ff", bd=1, relief=tk.SOLID
        )
        self.txt_query.pack(side=tk.LEFT, padx=(0, 6), ipady=3)
        self.txt_query.insert(0, "BMOU5539126")
        self.txt_query.bind("<Return>", lambda e: self.search_single())

        btn_single = tk.Button(
            f_bot, text="🔍 Radarda Ara", font=("Segoe UI", 9, "bold"),
            bg="#3b82f6", fg="#ffffff", activebackground="#2563eb",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.search_single
        )
        btn_single.pack(side=tk.LEFT, padx=(0, 14))

        btn_export = tk.Button(
            f_bot, text="📊 Excel Raporu İndir", font=("Segoe UI", 9, "bold"),
            bg="#6366f1", fg="#ffffff", activebackground="#4f46e5",
            relief=tk.FLAT, padx=12, pady=5, cursor="hand2", command=self.export_excel
        )
        btn_export.pack(side=tk.LEFT, padx=(0, 10))

        btn_clear = tk.Button(
            f_bot, text="🗑️ Tabloyu Temizle", font=("Segoe UI", 9),
            bg="#334155", fg="#ffffff", activebackground="#475569",
            relief=tk.FLAT, padx=10, pady=5, cursor="hand2", command=self.clear_table
        )
        btn_clear.pack(side=tk.LEFT, padx=(0, 10))

        # Acenta ve Canlı Durum Filtresi
        sep_f = tk.Frame(f_bot, bg="#334155", width=1, height=24)
        sep_f.pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Label(
            f_bot, text="Acenta:", font=("Segoe UI", 9, "bold"),
            fg=self.THEME["accent_cyan"], bg=self.THEME["bg_dark"]
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.cmb_filter_carrier = ttk.Combobox(
            f_bot, values=["Tümü", "HAPAG-LLOYD", "MSC", "ONE", "CMA-CGM", "WABERER", "DİĞER"],
            state="readonly", width=12, font=("Segoe UI", 9)
        )
        self.cmb_filter_carrier.current(0)
        self.cmb_filter_carrier.bind("<<ComboboxSelected>>", lambda e: self._populate_table())
        self.cmb_filter_carrier.pack(side=tk.LEFT, padx=(0, 8))

        self.chk_hide_pending_var = tk.BooleanVar(value=False)
        chk_hide_pending = tk.Checkbutton(
            f_bot, text="👁️ API Bekleyenleri Gizle", variable=self.chk_hide_pending_var,
            font=("Segoe UI", 9, "bold"), fg=self.THEME["accent_amber"], bg=self.THEME["bg_dark"],
            selectcolor="#1e293b", activebackground=self.THEME["bg_dark"], cursor="hand2",
            command=self._populate_table
        )
        chk_hide_pending.pack(side=tk.LEFT, padx=(4, 12))

        self.lbl_status = tk.Label(
            f_bot, text="Radarlar aktif. Sorguya hazır.", font=("Segoe UI", 9, "italic"),
            fg=self.THEME["accent_cyan"], bg=self.THEME["bg_dark"]
        )
        self.lbl_status.pack(side=tk.LEFT, padx=(8, 0))

        # 3. Tablo Alanı (Treeview)
        t_frame = tk.Frame(self.root, bg="#ffffff")
        t_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 6))

        cols = ("dosya", "carrier", "cntr", "bl", "excel_eta", "live_eta", "eta_diff", "kalan", "gemi", "pod", "aktarma", "motor")
        self.tree = ttk.Treeview(t_frame, columns=cols, show="headings", style="Radar.Treeview")

        col_defs = [
            ("dosya", "DOSYA / SATIR", 110, "center", False),
            ("carrier", "HAT / ACENTA", 95, "center", False),
            ("cntr", "KONTEYNER NO", 110, "center", False),
            ("bl", "B/L NO", 115, "center", False),
            ("excel_eta", "EXCEL ETA", 85, "center", False),
            ("live_eta", "CANLI ETA", 85, "center", False),
            ("eta_diff", "SAPMA", 105, "center", False),
            ("kalan", "DURUM", 90, "center", False),
            ("gemi", "GÜNCEL GEMİ", 125, "w", False),
            ("pod", "VARIŞ LİMANI", 110, "w", False),
            ("aktarma", "AKTARMA ROTASI", 280, "w", True),
            ("motor", "KAYNAK MOTORU", 135, "center", False),
        ]

        for cid, text, width, align, stretch in col_defs:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=width, minwidth=max(width - 20, 60), anchor=align, stretch=stretch)

        # Tablo Vurgu Renkleri
        self.tree.tag_configure("tag_delayed", background="#fef2f2", foreground="#b91c1c")  # Açık kırmızı zemin
        self.tree.tag_configure("tag_early", background="#f0fdf4", foreground="#15803d")    # Açık yeşil zemin
        self.tree.tag_configure("tag_ontime", background="#f0f9ff", foreground="#0369a1")   # Açık mavi zemin
        self.tree.tag_configure("tag_pending", background="#f8fafc", foreground="#64748b")  # Soluk gri zemin
        self.tree.tag_configure("tag_normal", background="#ffffff", foreground="#0f172a")

        sb_y = ttk.Scrollbar(t_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_y.set)
        sb_x = ttk.Scrollbar(t_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=sb_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Çift Tık & Sağ Tık ile Tekil Canlı Sorgulama
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree_menu = tk.Menu(self.root, tearoff=0, bg="#1e293b", fg="#ffffff", activebackground="#0284c7")
        self.tree_menu.add_command(label="⚡ Bu Yükü Canlı Sorgula (Tekil)", command=self._on_context_single_refresh)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        # 4. Alt Durum Çubuğu
        statusbar = tk.Frame(self.root, bg=self.THEME["panel_bg"], padx=16, pady=5)
        statusbar.pack(fill=tk.X)

        self.lbl_sync_footer = tk.Label(
            statusbar, text=f"🟢 Canlı Otomatik Takip Açık ({self.cmb_interval.get()})",
            font=("Segoe UI", 8, "bold"), fg=self.THEME["accent_green"], bg=self.THEME["panel_bg"]
        )
        self.lbl_sync_footer.pack(side=tk.LEFT)

        self.lbl_last_check = tk.Label(
            statusbar, text="Son Kontrol: Henüz Yapılmadı",
            font=("Segoe UI", 8), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]
        )
        self.lbl_last_check.pack(side=tk.LEFT, padx=(20, 0))

        lbl_brand = tk.Label(
            statusbar, text="Doğruer Gümrük Müşavirliği A.Ş. — SmartClearance Maritime Tech",
            font=("Segoe UI", 8), fg="#64748b", bg=self.THEME["panel_bg"]
        )
        lbl_brand.pack(side=tk.RIGHT)

    def _create_metric_card(self, parent, title, initial_val, color):
        f = tk.Frame(parent, bg="#1e293b", padx=10, pady=4, bd=1, relief=tk.SOLID)
        f.pack(side=tk.LEFT, padx=4)
        tk.Label(f, text=title, font=("Segoe UI", 7, "bold"), fg="#94a3b8", bg="#1e293b").pack(anchor="center")
        val_lbl = tk.Label(f, text=initial_val, font=("Segoe UI", 11, "bold"), fg=color, bg="#1e293b")
        val_lbl.pack(anchor="center")
        return val_lbl

    def _update_metrics(self, data_list=None):
        data = data_list if data_list is not None else self.results_data
        total = len(data)
        delayed = sum(1 for x in data if x.get("diff_tag") == "tag_delayed")
        early = sum(1 for x in data if x.get("diff_tag") == "tag_early")
        ontime = sum(1 for x in data if x.get("diff_tag") == "tag_ontime")

        self.card_total.config(text=str(total))
        self.card_delayed.config(text=str(delayed))
        self.card_early.config(text=str(early))
        self.card_ontime.config(text=str(ontime))

    def _on_interval_change(self, event=None):
        sel_text = self.cmb_interval.get()
        hours = 2
        for t, h in self.INTERVAL_OPTIONS:
            if t == sel_text:
                hours = h
                break
        self.config["auto_sync_interval_hours"] = hours
        save_config(self.config)
        self.lbl_sync_footer.config(text=f"🟢 Canlı Otomatik Takip Açık ({sel_text})")

    def _on_toggle_sync(self):
        val = self.chk_auto_sync_var.get()
        self.config["auto_sync_enabled"] = val
        save_config(self.config)
        if val:
            self.lbl_sync_footer.config(text=f"🟢 Canlı Otomatik Takip Açık ({self.cmb_interval.get()})", fg=self.THEME["accent_green"])
        else:
            self.lbl_sync_footer.config(text="⚪ Canlı Otomatik Takip Kapalı", fg=self.THEME["text_muted"])

    def _on_toggle_active_filter(self):
        val = self.chk_only_active_var.get()
        self.config["only_active_shipments"] = val
        save_config(self.config)

    def _start_watcher_thread(self):
        """Excel dosyasının değiştirilme tarihini seçilen saat aralığında izleyen thread."""
        def _loop():
            while self._watcher_running:
                hours = self.config.get("auto_sync_interval_hours", 2)
                sleep_seconds = max(30, int(hours * 3600))

                # Küçük adımlarla uyu ki kullanıcı periyodu değiştirdiğinde hemen tepki versin
                step = 10
                elapsed = 0
                while elapsed < sleep_seconds and self._watcher_running:
                    time.sleep(step)
                    elapsed += step

                if not self.chk_auto_sync_var.get() or self._sync_in_progress:
                    continue

                raw_path = self.txt_excel_path.get().strip()
                resolved = resolve_excel_path(raw_path)
                if resolved and os.path.exists(resolved):
                    try:
                        mtime = os.path.getmtime(resolved)
                        if self._last_mtime > 0 and mtime > self._last_mtime:
                            self._last_mtime = mtime
                            self.root.after(0, lambda: self._trigger_auto_sync(resolved))
                        elif self._last_mtime == 0:
                            self._last_mtime = mtime
                    except Exception:
                        pass

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def _trigger_auto_sync(self, resolved_path):
        now_str = datetime.now().strftime("%H:%M:%S")
        self.lbl_status.config(text=f"🔄 Excel güncellendi ({now_str}), canlı veriler çekiliyor...", fg=self.THEME["accent_cyan"])
        self.scan_excel(is_auto=True)

    def browse_excel_path(self):
        file_choice = filedialog.askopenfilename(
            title="İş Takip Excel Dosyasını Seçin",
            filetypes=[("Excel Dosyaları", "*.xlsx *.xls")]
        )
        if not file_choice:
            file_choice = filedialog.askdirectory(title="veya İş Takip Klasörünü Seçin")

        if file_choice:
            self.txt_excel_path.delete(0, tk.END)
            self.txt_excel_path.insert(0, file_choice)
            self.config["default_excel_path"] = file_choice
            self._last_mtime = 0
            save_config(self.config)
            base_name = os.path.basename(file_choice)
            self.lbl_status.config(
                text=f"📁 Yeni Excel yolu hafızaya kaydedildi: {base_name}",
                fg=self.THEME["accent_green"]
            )

    def _load_cached_state(self):
        cache = load_cache()
        if cache and cache.get("items"):
            self.results_data = cache.get("items", [])
            last_check = cache.get("last_check", "")
            self._populate_table()
            if last_check:
                self.lbl_last_check.config(text=f"Son Kontrol: {last_check} (Hafıza)")
            self.lbl_status.config(
                text=f"💾 Önceki oturum hafızadan yüklendi ({len(self.results_data)} yük - {last_check})",
                fg=self.THEME["accent_green"]
            )

    def refresh_live_from_memory(self):
        """Excel dosyasına gitmeden, hafızadaki MSC ve Hapag yüklerini anlık sorgular."""
        if self._sync_in_progress:
            messagebox.showwarning("Meşgul", "Şu anda devam eden bir sorgulama işlemi var. Lütfen bitmesini bekleyin.")
            return

        if not self.results_data:
            messagebox.showwarning("Uyarı", "Hafızada sorgulanacak yük bulunmuyor.\nÖnce '⚡ Excel'i Oku & Eşitle' veya '✍️ Manuel Çoklu Ekle' ile yük ekleyin.")
            return

        targets = []
        for idx, it in enumerate(self.results_data):
            cntr = it.get("container_no", "")
            bl = it.get("bl_no", "")
            carrier = it.get("carrier", "")
            q = cntr if cntr and cntr != "—" else bl
            if q and q != "—":
                c = self.router.detect_carrier(q, acenta_hint=carrier)
                if c in ["HAPAG", "MSC", "CMA-CGM"]:
                    targets.append((idx, q, c, it))

        if not targets:
            messagebox.showinfo("Bilgi", "Mevcut tabloda canlı sorgulanabilir (MSC / Hapag-Lloyd / CMA CGM) yük bulunamadı.")
            return

        self._sync_in_progress = True
        total = len(targets)
        self.lbl_status.config(text=f"🔄 Hafızadaki {total} canlı yük taranıyor...", fg=self.THEME["accent_cyan"])

        def _work():
            success_count = 0
            for i, (idx, q, c, it) in enumerate(targets, 1):
                self.root.after(0, lambda num=q, cur=i, tot=total, car=c: self.lbl_status.config(
                    text=f"[{cur}/{tot}] {num} [{car}] hafızadan canlı tazeleniyor..."
                ))
                res = self.router.track(q, acenta_hint=it.get("carrier"), excel_eta=it.get("excel_eta"))
                if res and res.get("success"):
                    items = res.get("items", [])
                    if items:
                        fresh = items[0]
                        it["live_eta"] = fresh.get("live_eta", it.get("live_eta"))
                        it["eta_diff"] = fresh.get("eta_diff", it.get("eta_diff"))
                        it["diff_tag"] = fresh.get("diff_tag", it.get("diff_tag"))
                        it["kalan_gun"] = fresh.get("kalan_gun", it.get("kalan_gun"))
                        it["vessel"] = fresh.get("vessel", it.get("vessel"))
                        it["pod"] = fresh.get("pod", it.get("pod"))
                        it["transshipments"] = fresh.get("transshipments", it.get("transshipments"))
                        it["source"] = fresh.get("source", it.get("source"))
                        it["last_query_time"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                        success_count += 1
                time.sleep(0.25)

            self._sync_in_progress = False
            now_str = datetime.now().strftime("%H:%M")
            now_full = datetime.now().strftime("%d.%m.%Y %H:%M")
            save_cache(self.results_data, now_full)
            self.root.after(0, lambda: self._on_refresh_memory_done(success_count, total, now_str))

        threading.Thread(target=_work, daemon=True).start()

    def _on_refresh_memory_done(self, success_count, total, now_str):
        self._populate_table()
        self.lbl_last_check.config(text=f"Son Kontrol: Bugün {now_str}")
        msg = f"✅ Hafıza güncellendi ({success_count}/{total} canlı ETA tazelendi - {now_str})"
        self.lbl_status.config(text=msg, fg=self.THEME["accent_green"])
        messagebox.showinfo(
            "Canlı Takip Tamamlandı",
            f"Hafızadaki yükler başarıyla güncellendi!\n\nCanlı tazelenen yük: {success_count}/{total}\nSonuçlar hafızaya kaydedildi."
        )

    def _on_tree_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = sel[0]
        vals = self.tree.item(item_id, "values")
        if not vals or len(vals) < 5:
            return
        dosya = vals[0]
        carrier = vals[1]
        cntr = vals[2] if vals[2] not in ("—", "") else ""
        bl = vals[3] if vals[3] not in ("—", "") else ""
        excel_eta = vals[4]
        q = cntr or bl
        if not q:
            messagebox.showwarning("Uyarı", "Bu satırda sorgulanabilecek Konteyner veya B/L numarası bulunamadı.")
            return

        c_detected = self.router.detect_carrier(q, acenta_hint=carrier)
        if c_detected not in ["HAPAG", "MSC", "CMA-CGM"]:
            messagebox.showinfo("Bilgi", f"'{carrier}' acentası için canlı API henüz aktif değil.\n(Şu an MSC, Hapag-Lloyd ve CMA CGM canlı sorgulanabilmektedir)")
            return

        self.lbl_status.config(text=f"⚡ {q} [{c_detected}] anlık canlı sorgulanıyor...", fg=self.THEME["accent_cyan"])

        def _work():
            res = self.router.track(q, acenta_hint=carrier, excel_eta=excel_eta)
            self.root.after(0, lambda: self._handle_single_row_refresh(res, q, dosya, cntr, bl))

        threading.Thread(target=_work, daemon=True).start()

    def _handle_single_row_refresh(self, res, q, dosya, cntr, bl):
        if not res or not res.get("success"):
            err = res.get("error", "Bilinmeyen hata") if res else "Yanıt alınamadı"
            self.lbl_status.config(text=f"❌ {q} sorgulanamadı: {err}", fg=self.THEME["accent_red"])
            messagebox.showerror("Canlı Sorgu Hatası", f"'{q}' sorgulanamadı:\n{err}")
            return

        items = res.get("items", [])
        if not items:
            self.lbl_status.config(text=f"⚠️ {q} için canlı kayıt bulunamadı", fg=self.THEME["accent_amber"])
            return

        fresh = items[0]
        updated = False
        for it in self.results_data:
            if (cntr and it.get("container_no") == cntr) or (bl and it.get("bl_no") == bl) or (dosya and it.get("dosya") == dosya):
                it["live_eta"] = fresh.get("live_eta", it.get("live_eta"))
                it["eta_diff"] = fresh.get("eta_diff", it.get("eta_diff"))
                it["diff_tag"] = fresh.get("diff_tag", it.get("diff_tag"))
                it["kalan_gun"] = fresh.get("kalan_gun", it.get("kalan_gun"))
                it["vessel"] = fresh.get("vessel", it.get("vessel"))
                it["pod"] = fresh.get("pod", it.get("pod"))
                it["transshipments"] = fresh.get("transshipments", it.get("transshipments"))
                it["source"] = fresh.get("source", it.get("source"))
                it["last_query_time"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                updated = True
                break

        if updated:
            self._populate_table()
            now_str = datetime.now().strftime("%H:%M")
            self.lbl_last_check.config(text=f"Son Kontrol: Bugün {now_str}")
            self.lbl_status.config(
                text=f"✅ {q} anlık güncellendi: Canlı ETA {fresh.get('live_eta')} ({fresh.get('eta_diff')})",
                fg=self.THEME["accent_green"]
            )
            save_cache(self.results_data, datetime.now().strftime("%d.%m.%Y %H:%M"))

    def _on_tree_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.tree_menu.post(event.x_root, event.y_root)

    def _on_context_single_refresh(self):
        self._on_tree_double_click(None)

    def clear_table(self):
        if not self.results_data:
            return
        if not messagebox.askyesno("Tabloyu Temizle", "Mevcut tablo ve kayıtlı hafıza temizlensin mi?"):
            return
        self.results_data.clear()
        save_cache([], "")
        self._populate_table()
        self.lbl_status.config(text="Tablo ve hafıza temizlendi.", fg=self.THEME["text_muted"])

    def _populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_carrier = self.cmb_filter_carrier.get() if hasattr(self, "cmb_filter_carrier") else "Tümü"
        hide_pending = self.chk_hide_pending_var.get() if hasattr(self, "chk_hide_pending_var") else False

        filtered_data = []
        for it in self.results_data:
            c = str(it.get("carrier") or "").upper()
            tag = it.get("diff_tag") or "tag_normal"

            # 1. API Bekleyenleri Gizle
            if hide_pending and tag == "tag_pending":
                continue

            # 2. Acenta Filtresi
            if selected_carrier and selected_carrier != "Tümü":
                sel_up = selected_carrier.upper()
                if sel_up == "HAPAG-LLOYD" and "HAPAG" not in c:
                    continue
                elif sel_up == "MSC" and ("MSC" not in c and "GLOVIS" not in c):
                    continue
                elif sel_up == "ONE" and ("ONE" not in c and "OCEAN" not in c):
                    continue
                elif sel_up == "CMA-CGM" and "CMA" not in c:
                    continue
                elif sel_up == "WABERER" and "WABERER" not in c:
                    continue
                elif sel_up == "DİĞER" and any(k in c for k in ["HAPAG", "MSC", "GLOVIS", "ONE", "CMA", "WABERER"]):
                    continue

            filtered_data.append(it)

        for it in filtered_data:
            tag = it.get("diff_tag") or "tag_normal"
            self.tree.insert(
                "", tk.END,
                values=(
                    it.get("dosya", "—"),
                    it.get("carrier", "—"),
                    it.get("container_no", "—"),
                    it.get("bl_no", "—"),
                    it.get("excel_eta", "—"),
                    it.get("live_eta", "—"),
                    it.get("eta_diff", "—"),
                    it.get("kalan_gun", "—"),
                    it.get("vessel", "—"),
                    it.get("pod", "—"),
                    it.get("transshipments", "—"),
                    it.get("source", "—")
                ),
                tags=(tag,)
            )

        self._update_metrics(filtered_data)

    def search_single(self):
        query = self.txt_query.get().strip().upper()
        if not query:
            return

        carrier_detected = self.router.detect_carrier(query)
        self.lbl_status.config(text=f"🔄 {query} [{carrier_detected}] taranıyor...", fg=self.THEME["accent_cyan"])

        def _work():
            res = self.router.track(query)
            self.root.after(0, lambda: self._handle_single(res, query))

        threading.Thread(target=_work, daemon=True).start()

    def _handle_single(self, res, query):
        if not res.get("success"):
            self.lbl_status.config(text=f"❌ Hata: {res.get('error')}", fg=self.THEME["accent_red"])
            messagebox.showerror("Sorgu Sonucu", f"'{query}' sorgulanamadı:\n{res.get('error')}")
            return

        items = res.get("items", [])
        for new_it in items:
            c_no = new_it.get("container_no")
            self.results_data = [x for x in self.results_data if x.get("container_no") != c_no]
            self.results_data.append(new_it)

        self._populate_table()
        save_cache(self.results_data, datetime.now().strftime("%d.%m.%Y %H:%M"))
        self.lbl_status.config(text=f"✅ {len(items)} kayıt getirildi", fg=self.THEME["accent_green"])

    # ==========================================================================
    # MANUEL ÇOKLU GİRİŞ MODAL PENCERESİ (YENİLENMİŞ & BUTONU GARANTİLİ)
    # ==========================================================================

    def open_manual_batch_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("✍️ Toplu Konteyner / B/L Manuel Giriş Radarı")
        win.geometry("620x540")
        win.minsize(540, 480)
        win.configure(bg=self.THEME["panel_bg"])
        win.grab_set()

        # Üst Başlık
        f_top_hdr = tk.Frame(win, bg=self.THEME["card_bg"], padx=16, pady=10)
        f_top_hdr.pack(fill=tk.X)

        tk.Label(
            f_top_hdr, text="✍️ TOPLU KONTEYNER & B/L GİRİŞİ",
            font=("Segoe UI", 12, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["card_bg"]
        ).pack(anchor="w")

        tk.Label(
            f_top_hdr,
            text="Numaraları alt alta yapıştırın. Sistem Konteyner/BL tipini ve Acentayı otomatik ayırt eder.",
            font=("Segoe UI", 8), fg=self.THEME["text_muted"], bg=self.THEME["card_bg"]
        ).pack(anchor="w", pady=(2, 0))

        # Metin Kutusu
        f_txt = tk.Frame(win, bg=self.THEME["panel_bg"], padx=16, pady=10)
        f_txt.pack(fill=tk.BOTH, expand=True)

        txt_input = scrolledtext.ScrolledText(
            f_txt, font=("Consolas", 10), bg="#0f172a", fg="#ffffff",
            insertbackground="#00f0ff", bd=1, relief=tk.SOLID
        )
        txt_input.pack(fill=tk.BOTH, expand=True)

        # Bilgi Etiketi
        lbl_count_info = tk.Label(
            win, text="📊 Algılanan: 0 Yük", font=("Segoe UI", 9, "bold"),
            fg=self.THEME["accent_green"], bg=self.THEME["panel_bg"], padx=16
        )
        lbl_count_info.pack(anchor="w")

        def _update_counter(e=None):
            cnt = txt_input.get("1.0", tk.END)
            parsed = parse_batch_input(cnt)
            cntr_count = sum(1 for x in parsed if x["type"] == "CONTAINER")
            bl_count = sum(1 for x in parsed if x["type"] == "BL")
            lbl_count_info.config(text=f"📊 Algılanan: {len(parsed)} Yük ({cntr_count} Konteyner, {bl_count} B/L)")

        txt_input.bind("<KeyRelease>", _update_counter)

        # Alt Butonlar
        f_bot_actions = tk.Frame(win, bg=self.THEME["panel_bg"], padx=16, pady=12)
        f_bot_actions.pack(fill=tk.X)

        def _execute_batch():
            cnt = txt_input.get("1.0", tk.END)
            parsed_items = parse_batch_input(cnt)
            if not parsed_items:
                messagebox.showwarning("Uyarı", "Geçerli konteyner veya B/L numarası bulunamadı.")
                return
            win.destroy()
            self._start_batch_query(parsed_items)

        btn_submit = tk.Button(
            f_bot_actions, text="🚀 Radara Ekle ve Canlı Sorgula", font=("Segoe UI", 10, "bold"),
            bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff",
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2", command=_execute_batch
        )
        btn_submit.pack(side=tk.LEFT)

        btn_cancel = tk.Button(
            f_bot_actions, text="İptal", font=("Segoe UI", 10),
            bg="#475569", fg="#ffffff", activebackground="#334155", activeforeground="#ffffff",
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2", command=win.destroy
        )
        btn_cancel.pack(side=tk.RIGHT)

    def _start_batch_query(self, task_list):
        total = len(task_list)
        self.lbl_status.config(text=f"🔄 {total} yük sırayla canlı taranıyor...", fg=self.THEME["accent_cyan"])

        def _work():
            self._sync_in_progress = True
            for idx, item in enumerate(task_list, 1):
                num = item["number"]
                self.root.after(0, lambda n=num, i=idx, tot=total: self.lbl_status.config(
                    text=f"[{i}/{tot}] {n} canlı taranıyor..."
                ))
                res = self.router.track(num, acenta_hint=item.get("carrier", ""))
                if res.get("success"):
                    for new_it in res.get("items", []):
                        c_no = new_it.get("container_no")
                        self.results_data = [x for x in self.results_data if x.get("container_no") != c_no]
                        self.results_data.append(new_it)
                time.sleep(0.35)

            self._sync_in_progress = False
            self.root.after(0, lambda: self._on_batch_done(total))

        threading.Thread(target=_work, daemon=True).start()

    def _on_batch_done(self, total):
        self._populate_table()
        now_str = datetime.now().strftime("%H:%M")
        now_full = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_cache(self.results_data, now_full)
        self.lbl_last_check.config(text=f"Son Kontrol: Bugün {now_str}")
        self.lbl_status.config(text=f"✅ {total} yük için canlı sorgulama tamamlandı ({now_str})", fg=self.THEME["accent_green"])

    # ==========================================================================
    # EXCEL TARAMA & SÜTUN OKUMA MOTORU (E, F, T, U)
    # ==========================================================================

    def scan_excel(self, is_auto=False):
        raw_path = self.txt_excel_path.get().strip()
        target_path = resolve_excel_path(raw_path)

        if not target_path or not os.path.exists(target_path):
            if not is_auto:
                messagebox.showerror("Dosya Bulunamadı", f"Belirtilen yol bulunamadı veya geçerli bir Excel dosyası içermiyor:\n{raw_path}")
            return

        if not openpyxl:
            if not is_auto:
                messagebox.showerror("Hata", "openpyxl kütüphanesi eksik.")
            return

        self.lbl_status.config(text="📂 Excel analiz ediliyor (E:Acenta, F:B/L, T:ETA, U:Konteyner)...", fg=self.THEME["accent_cyan"])

        def _work():
            self._sync_in_progress = True
            only_active = self.chk_only_active_var.get()
            today = datetime.now().date()
            try:
                wb = None
                for _ in range(3):
                    try:
                        wb = openpyxl.load_workbook(target_path, data_only=True, read_only=True)
                        break
                    except Exception:
                        time.sleep(1)

                if not wb:
                    self._sync_in_progress = False
                    return

                ws = wb.active
                for name in wb.sheetnames:
                    if any(k in name.upper() for k in ["GÜNCEL", "TAKİP", "RAPOR", "HANKOOK", "LİSTE"]):
                        ws = wb[name]
                        break

                row_tasks = []
                for r, row_cells in enumerate(ws.iter_rows(values_only=True), 1):
                    if r == 1 or not row_cells or len(row_cells) < 6:
                        continue
                    row_strs = [str(v or "").strip() for v in row_cells]
                    if any(h in "".join(row_strs).upper() for h in ["GÜMRÜK", "KONŞİMENTO", "KONTEYNER", "TAKİP GRUBU"]):
                        continue

                    # Dosya No: Sütun A (0)
                    dosya_raw = str(row_cells[0] or "").strip() if len(row_cells) >= 1 else ""
                    dosya_val = "" if dosya_raw == "None" else dosya_raw

                    # Acenta: Sütun E (4)
                    acenta_raw = str(row_cells[4] or "").strip() if len(row_cells) >= 5 else ""
                    acenta_val = "" if acenta_raw == "None" else acenta_raw

                    # B/L No: Sütun F (5) veya G (6)
                    bl_val = ""
                    if len(row_cells) >= 6 and row_cells[5]:
                        v_f = str(row_cells[5]).strip()
                        if v_f != "None" and not any(h in v_f.upper() for h in ["KONŞİMENTO", "BİLGİSİ"]):
                            bl_val = v_f
                    if not bl_val and len(row_cells) >= 7 and row_cells[6]:
                        v_g = str(row_cells[6]).strip()
                        if v_g != "None" and len(v_g) >= 6:
                            bl_val = v_g

                    # Kayıtlı ETA: Sütun T (19) veya U (20)
                    excel_eta_val = None
                    if len(row_cells) >= 20 and row_cells[19]:
                        excel_eta_val = row_cells[19]
                    elif len(row_cells) >= 21 and row_cells[20] and parse_date(row_cells[20]):
                        excel_eta_val = row_cells[20]

                    # Konteyner No: Sütun U (20) veya V (21)
                    cntr_val = ""
                    if len(row_cells) >= 21 and row_cells[20]:
                        s_u = str(row_cells[20] or "").strip().upper()
                        if len(s_u) == 11 and s_u[:4].isalpha() and s_u[4:].isdigit():
                            cntr_val = s_u
                    if not cntr_val and len(row_cells) >= 22 and row_cells[21]:
                        s_v = str(row_cells[21] or "").strip().upper()
                        if len(s_v) == 11 and s_v[:4].isalpha() and s_v[4:].isdigit():
                            cntr_val = s_v

                    if not cntr_val:
                        for cell in row_cells:
                            s_val = str(cell or "").strip().upper()
                            if len(s_val) == 11 and s_val[:4].isalpha() and s_val[4:].isdigit():
                                cntr_val = s_val
                                break

                    dt_eta = parse_date(excel_eta_val)
                    if only_active:
                        if not dt_eta or dt_eta < today:
                            continue

                    query_num = cntr_val or bl_val
                    if not query_num or any(h in query_num.upper() for h in ["KONTEYNER", "KONŞİMENTO", "BİLGİSİ", "ACENTA"]):
                        continue

                    row_tasks.append({
                        "row_num": r,
                        "dosya": dosya_val,
                        "carrier": acenta_val,
                        "bl_hint": bl_val,
                        "cntr_hint": cntr_val,
                        "query_num": query_num,
                        "excel_eta": excel_eta_val,
                        "dt_eta": dt_eta
                    })

                if not row_tasks:
                    self._sync_in_progress = False
                    if not is_auto:
                        self.root.after(0, lambda: messagebox.showinfo("Bilgi", "Excel'de takip edilebilir yük satırı bulunamadı."))
                    return

                # Mevcut hafızadaki canlı verileri hızlı indexle (q -> item)
                existing_live_map = {}
                for old_it in getattr(self, "results_data", []):
                    old_cntr = old_it.get("container_no")
                    old_bl = old_it.get("bl_no")
                    if old_it.get("live_eta") not in ("—", "", None) and old_it.get("diff_tag") != "tag_pending":
                        if old_cntr and old_cntr != "—":
                            existing_live_map[old_cntr] = old_it
                        if old_bl and old_bl != "—":
                            existing_live_map[old_bl] = old_it

                # Canlı sorgulama için tekil listeyi ve motorları belirle
                query_cache = {}
                live_targets = []
                seen_q = set()
                reused_count = 0

                for t in row_tasks:
                    q = t["query_num"]
                    if q not in seen_q:
                        seen_q.add(q)
                        c = self.router.detect_carrier(q, acenta_hint=t["carrier"])
                        if c in ["HAPAG", "MSC", "CMA-CGM"]:
                            if q in existing_live_map:
                                query_cache[q] = {"success": True, "items": [existing_live_map[q]]}
                                reused_count += 1
                            else:
                                live_targets.append((q, t, c))

                total_live = len(live_targets)
                total_rows = len(row_tasks)
                self.root.after(0, lambda tot=total_rows, r_cnt=reused_count, l_cnt=total_live: self.lbl_status.config(
                    text=f"🔄 Excel okundu: {tot} aktif satır ({r_cnt} hafızadan korundu, {l_cnt} yeni taranıyor)...",
                    fg=self.THEME["accent_cyan"]
                ))

                for idx, (q, t_obj, c) in enumerate(live_targets, 1):
                    self.root.after(0, lambda n=q, i=idx, tot=total_live, car=c: self.lbl_status.config(
                        text=f"[{i}/{tot}] {n} [{car}] canlı taranıyor..."
                    ))
                    res = self.router.track(q, acenta_hint=t_obj["carrier"], excel_eta=t_obj["excel_eta"])
                    query_cache[q] = res
                    time.sleep(0.3)

                # Satırları birebir sonuca eşle
                collected = []
                success_count = 0
                for t in row_tasks:
                    q = t["query_num"]
                    c_detected = self.router.detect_carrier(q, acenta_hint=t["carrier"])
                    dosya_tag = f"{t['dosya']} (S.{t['row_num']})" if t['dosya'] else f"Satır {t['row_num']}"
                    excel_eta_str = t["dt_eta"].strftime("%d.%m.%Y") if t.get("dt_eta") else (str(t["excel_eta"]) if t["excel_eta"] else "—")

                    res = query_cache.get(q)
                    if res and res.get("success"):
                        items = res.get("items", [])
                        for it in items:
                            item_copy = dict(it)
                            item_copy["dosya"] = dosya_tag
                            if item_copy.get("bl_no") in ("—", "") and t["bl_hint"]:
                                item_copy["bl_no"] = t["bl_hint"]
                            if item_copy.get("container_no") in ("—", "") and t["cntr_hint"]:
                                item_copy["container_no"] = t["cntr_hint"]
                            collected.append(item_copy)
                            success_count += 1
                    else:
                        diff_text = "API Bekleniyor"
                        source_note = f"{c_detected} (Canlı Motor Bekleniyor)"
                        norm_hint = normalize_turkish(t["carrier"])

                        if "WABERER" in norm_hint:
                            c_detected = "WABERER"
                            diff_text = "Karayolu / Tır"
                            source_note = "Karayolu Nakliyesi (CMR)"
                        elif c_detected == "ONE":
                            source_note = "ONE (API Anahtarı Bekleniyor)"
                        elif c_detected == "CMA-CGM":
                            err_txt = res.get("error", "Oturum Çerezi Bekleniyor") if res else "Oturum Çerezi Bekleniyor"
                            source_note = f"CMA-CGM ({err_txt[:35]})"

                        collected.append({
                            "dosya": dosya_tag,
                            "carrier": c_detected if c_detected != "UNKNOWN" else (t["carrier"] or "DİĞER"),
                            "container_no": t["cntr_hint"] or "—",
                            "bl_no": t["bl_hint"] or "—",
                            "excel_eta": excel_eta_str,
                            "live_eta": "—",
                            "eta_diff": diff_text,
                            "diff_tag": "tag_pending",
                            "kalan_gun": "—",
                            "vessel": "—",
                            "pod": "—",
                            "transshipments": "—",
                            "source": source_note
                        })

                self.results_data = collected
                self._last_mtime = os.path.getmtime(target_path)
                self._sync_in_progress = False
                self.root.after(0, lambda: self._on_scan_done(success_count, total_rows, is_auto))

            except Exception as e:
                self._sync_in_progress = False
                if not is_auto:
                    self.root.after(0, lambda err=str(e): messagebox.showerror("Hata", f"Excel okuma hatası:\n{err}"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_scan_done(self, success_count, total_count, is_auto):
        self._populate_table()
        now_str = datetime.now().strftime("%H:%M")
        now_full = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_cache(self.results_data, now_full)
        self.lbl_last_check.config(text=f"Son Kontrol: Bugün {now_str}")
        msg = f"✅ Eşitleme bitti ({success_count}/{total_count} yüke ulaşıldı - {now_str})"
        self.lbl_status.config(text=msg, fg=self.THEME["accent_green"])
        if not is_auto:
            messagebox.showinfo("Tamamlandı", f"Excel Eşitleme & Tarama Tamamlandı!\n\nToplam taranan dosya: {total_count}\nCanlı ETA'sı olan yük: {success_count}\nSonuçlar hafızaya kaydedildi.")

    def export_excel(self):
        if not self.results_data:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri bulunmuyor.")
            return

        if not openpyxl:
            messagebox.showerror("Hata", "openpyxl kütüphanesi yüklü değil.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Excel Olarak Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyaları", "*.xlsx")],
            initialfile=f"Kuresel_ETA_Radari_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        if not save_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Canlı ETA Radarı"
            ws.views.sheetView[0].showGridLines = True

            # Palet
            NAVY_HEADER = "0F172A"
            NAVY_SUB = "1E293B"
            BORDER_GRAY = "E2E8F0"
            ZEBRA_LIGHT = "F8FAFC"

            # Stiller
            font_title = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
            font_sub = Font(name="Segoe UI", size=9, color="94A3B8")
            font_hdr = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
            font_data = Font(name="Segoe UI", size=9, color="0F172A")
            font_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")

            fill_title = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
            fill_sub = PatternFill(start_color=NAVY_SUB, end_color=NAVY_SUB, fill_type="solid")
            fill_hdr = PatternFill(start_color=NAVY_SUB, end_color=NAVY_SUB, fill_type="solid")
            fill_zebra = PatternFill(start_color=ZEBRA_LIGHT, end_color=ZEBRA_LIGHT, fill_type="solid")
            fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

            # Rozet Dolguları ve Yazı Tipleri
            fill_delayed = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid")
            font_delayed = Font(name="Segoe UI", size=9, bold=True, color="9F1239")

            fill_early = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            font_early = Font(name="Segoe UI", size=9, bold=True, color="166534")

            fill_ontime = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
            font_ontime = Font(name="Segoe UI", size=9, bold=True, color="075985")

            fill_pending = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            font_pending = Font(name="Segoe UI", size=9, italic=True, color="64748B")

            # Kenarlıklar
            thin_side = Side(style="thin", color=BORDER_GRAY)
            cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
            hdr_bottom_border = Border(
                left=thin_side, right=thin_side, top=thin_side,
                bottom=Side(style="medium", color="0284C7")
            )

            # 1. Başlık Bandı (Satır 1)
            ws.merge_cells("A1:L1")
            c1 = ws["A1"]
            c1.value = "  DOĞRUER SMARTCLEARANCE — KÜRESEL CANLI KONTEYNER & ETA TAKİP RADARI"
            c1.font = font_title
            c1.fill = fill_title
            c1.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[1].height = 32

            # 2. Alt Bilgi Bandı (Satır 2)
            ws.merge_cells("A2:L2")
            c2 = ws["A2"]
            now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
            c2.value = f"  Rapor Tarihi: {now_str} | Doğruer Gümrük Müşavirliği A.Ş. — Denizcilik Lojistik Takip Teknolojileri"
            c2.font = font_sub
            c2.fill = fill_sub
            c2.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[2].height = 20

            # 3. İstatistik Hesaplama & KPI Kartları (Satır 4-5)
            ws.row_dimensions[3].height = 8
            total_count = len(self.results_data)
            delayed_count = sum(1 for it in self.results_data if it.get("diff_tag") == "tag_delayed")
            early_count = sum(1 for it in self.results_data if it.get("diff_tag") == "tag_early")
            ontime_count = sum(1 for it in self.results_data if it.get("diff_tag") == "tag_ontime")
            live_count = sum(1 for it in self.results_data if it.get("live_eta") and it.get("live_eta") not in ("—", ""))
            pending_count = total_count - live_count

            def make_card(start_col, end_col, title, value, val_color, fill_bg):
                ws.merge_cells(f"{start_col}4:{end_col}4")
                c_t = ws[f"{start_col}4"]
                c_t.value = title
                c_t.font = Font(name="Segoe UI", size=8, bold=True, color="475569")
                c_t.alignment = Alignment(horizontal="center", vertical="center")
                c_t.fill = PatternFill(start_color=fill_bg, end_color=fill_bg, fill_type="solid")

                ws.merge_cells(f"{start_col}5:{end_col}5")
                c_v = ws[f"{start_col}5"]
                c_v.value = value
                c_v.font = Font(name="Segoe UI", size=14, bold=True, color=val_color)
                c_v.alignment = Alignment(horizontal="center", vertical="center")
                c_v.fill = PatternFill(start_color=fill_bg, end_color=fill_bg, fill_type="solid")

                for row in range(4, 6):
                    ws[f"{start_col}{row}"].border = cell_border
                    ws[f"{end_col}{row}"].border = cell_border

            make_card("A", "B", "TOPLAM YÜK", total_count, "0284C7", "F0F9FF")
            make_card("C", "D", "🔴 RÖTARLI", delayed_count, "E11D48", "FFF1F2")
            make_card("E", "F", "🟢 ERKEN GELEN", early_count, "16A34A", "F0FDF4")
            make_card("G", "H", "✅ ZAMANINDA", ontime_count, "0284C7", "F0F9FF")
            make_card("I", "J", "⏳ CANLI TAKİPTE", live_count, "0F172A", "F8FAFC")
            make_card("K", "L", "📋 BEKLEYENLER", pending_count, "64748B", "F1F5F9")

            ws.row_dimensions[4].height = 18
            ws.row_dimensions[5].height = 24
            ws.row_dimensions[6].height = 10

            # 4. Tablo Başlıkları (Satır 7)
            headers = [
                ("DOSYA / SATIR", 18, "center"),
                ("HAT / ACENTA", 15, "center"),
                ("KONTEYNER NO", 17, "center"),
                ("B/L NO", 18, "center"),
                ("EXCEL ETA (T)", 14, "center"),
                ("CANLI ETA", 14, "center"),
                ("ETA FARKI / SAPMA", 18, "center"),
                ("GÜNCEL DURUM", 15, "center"),
                ("GÜNCEL GEMİ", 24, "left"),
                ("VARIŞ LİMANI", 20, "left"),
                ("AKTARMA ROTASI", 38, "left"),
                ("KAYNAK MOTORU", 22, "center")
            ]

            ws.row_dimensions[7].height = 26
            for col_idx, (text, _, align) in enumerate(headers, 1):
                cell = ws.cell(7, col_idx)
                cell.value = text
                cell.font = font_hdr
                cell.fill = fill_hdr
                cell.alignment = Alignment(horizontal=align, vertical="center")
                cell.border = hdr_bottom_border

            # 5. Veri Satırları (Satır 8+)
            for row_idx, it in enumerate(self.results_data, 8):
                ws.row_dimensions[row_idx].height = 22
                is_zebra = (row_idx % 2 == 1)
                base_fill = fill_zebra if is_zebra else fill_white

                row_vals = [
                    (it.get("dosya", "—"), "center", font_bold),
                    (it.get("carrier", "—"), "center", font_bold),
                    (it.get("container_no", "—"), "center", font_bold if it.get("container_no") not in ("—", "") else font_data),
                    (it.get("bl_no", "—"), "center", font_data),
                    (it.get("excel_eta", "—"), "center", font_data),
                    (it.get("live_eta", "—"), "center", font_bold if it.get("live_eta") not in ("—", "") else font_data),
                    (it.get("eta_diff", "—"), "center", None),
                    (it.get("kalan_gun", "—"), "center", font_data),
                    (it.get("vessel", "—"), "left", font_data),
                    (it.get("pod", "—"), "left", font_data),
                    (it.get("transshipments", "—"), "left", font_data),
                    (it.get("source", "—"), "center", font_sub)
                ]

                for col_idx, (val, align, f_custom) in enumerate(row_vals, 1):
                    c = ws.cell(row_idx, col_idx)
                    c.value = val
                    c.alignment = Alignment(horizontal=align, vertical="center")
                    c.border = cell_border

                    if col_idx == 7:
                        diff_tag = it.get("diff_tag")
                        if diff_tag == "tag_delayed":
                            c.fill = fill_delayed
                            c.font = font_delayed
                        elif diff_tag == "tag_early":
                            c.fill = fill_early
                            c.font = font_early
                        elif diff_tag == "tag_ontime":
                            c.fill = fill_ontime
                            c.font = font_ontime
                        else:
                            c.fill = fill_pending
                            c.font = font_pending
                    else:
                        c.fill = base_fill
                        c.font = f_custom or font_data

            # 6. Kolon Genişlikleri
            for col_idx, (_, w, _) in enumerate(headers, 1):
                col_let = openpyxl.utils.get_column_letter(col_idx)
                ws.column_dimensions[col_let].width = w

            # 7. Otomatik Filtre ve Dondurma
            last_row = 7 + len(self.results_data)
            ws.auto_filter.ref = f"A7:L{last_row}"
            ws.freeze_panes = "A8"

            wb.save(save_path)
            messagebox.showinfo("Başarılı", f"Kurumsal Premium Rapor oluşturuldu ve kaydedildi:\n{save_path}")

        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilemedi:\n{e}")

    # ==========================================================================
    # TEMİZLENMİŞ AYARLAR DİYALOĞU (ESKİ HUB ÇÖPLÜĞÜ TEMİZLENDİ)
    # ==========================================================================

    def open_settings_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("⚙️ Acenta API & Sistem Ayarları")
        win.geometry("580x620")
        win.minsize(520, 560)
        win.configure(bg=self.THEME["panel_bg"])
        win.grab_set()

        f_top_hdr = tk.Frame(win, bg=self.THEME["card_bg"], padx=16, pady=10)
        f_top_hdr.pack(fill=tk.X)

        tk.Label(
            f_top_hdr, text="⚙️ ACENTA API & RADAR AYARLARI",
            font=("Segoe UI", 12, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["card_bg"]
        ).pack(anchor="w")

        tk.Label(
            f_top_hdr,
            text="Resmi acenta anahtarlarını ve oturum çerezlerini tanımlayın. (MSC motoru direkt ve ücretsiz çalışır).",
            font=("Segoe UI", 8), fg=self.THEME["text_muted"], bg=self.THEME["card_bg"]
        ).pack(anchor="w", pady=(2, 0))

        f_inputs = tk.Frame(win, bg=self.THEME["panel_bg"], padx=20, pady=12)
        f_inputs.pack(fill=tk.BOTH, expand=True)

        # Hapag API Key & Secret
        tk.Label(f_inputs, text="Hapag-Lloyd DCSA Client ID:", font=("Segoe UI", 9, "bold"), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]).pack(anchor="w")
        e_hapag_id = tk.Entry(f_inputs, font=("Segoe UI", 10), bg="#1e293b", fg="#ffffff", bd=1, relief=tk.SOLID)
        e_hapag_id.pack(fill=tk.X, pady=(2, 6), ipady=2)
        e_hapag_id.insert(0, self.config.get("hapag_client_id", ""))

        tk.Label(f_inputs, text="Hapag-Lloyd DCSA Client Secret:", font=("Segoe UI", 9, "bold"), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]).pack(anchor="w")
        e_hapag_sec = tk.Entry(f_inputs, font=("Segoe UI", 10), bg="#1e293b", fg="#ffffff", show="*", bd=1, relief=tk.SOLID)
        e_hapag_sec.pack(fill=tk.X, pady=(2, 8), ipady=2)
        e_hapag_sec.insert(0, self.config.get("hapag_client_secret", ""))

        # CMA CGM Canlı Oturum Çerezi (Cookie)
        tk.Label(f_inputs, text="CMA CGM Canlı Oturum Çerezi (Cookie):", font=("Segoe UI", 9, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["panel_bg"]).pack(anchor="w")
        e_cma_cookie = tk.Entry(f_inputs, font=("Segoe UI", 9), bg="#1e293b", fg="#ffffff", bd=1, relief=tk.SOLID)
        e_cma_cookie.pack(fill=tk.X, pady=(2, 6), ipady=2)
        e_cma_cookie.insert(0, self.config.get("cma_session_cookie", ""))

        # CMA CGM Doğrulama Tokeni (__RequestVerificationToken)
        tk.Label(f_inputs, text="CMA CGM Doğrulama Tokeni (__RequestVerificationToken):", font=("Segoe UI", 9, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["panel_bg"]).pack(anchor="w")
        e_cma_token = tk.Entry(f_inputs, font=("Segoe UI", 9), bg="#1e293b", fg="#ffffff", bd=1, relief=tk.SOLID)
        e_cma_token.pack(fill=tk.X, pady=(2, 8), ipady=2)
        e_cma_token.insert(0, self.config.get("cma_token", ""))

        # ONE API Key (Opsiyonel)
        tk.Label(f_inputs, text="ONE (Ocean Network Express) API Key (Opsiyonel):", font=("Segoe UI", 9, "bold"), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]).pack(anchor="w")
        e_one_key = tk.Entry(f_inputs, font=("Segoe UI", 10), bg="#1e293b", fg="#ffffff", bd=1, relief=tk.SOLID)
        e_one_key.pack(fill=tk.X, pady=(2, 8), ipady=2)
        e_one_key.insert(0, self.config.get("one_api_key", ""))

        # Varsayılan Excel Yolu
        tk.Label(f_inputs, text="İş Takip Excel Dosyası veya Klasör Yolu:", font=("Segoe UI", 9, "bold"), fg=self.THEME["text_muted"], bg=self.THEME["panel_bg"]).pack(anchor="w")

        f_excel_row = tk.Frame(f_inputs, bg=self.THEME["panel_bg"])
        f_excel_row.pack(fill=tk.X, pady=(2, 10))

        e_excel = tk.Entry(f_excel_row, font=("Segoe UI", 10), bg="#1e293b", fg="#ffffff", bd=1, relief=tk.SOLID)
        e_excel.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        e_excel.insert(0, self.config.get("default_excel_path", ""))

        def _pick_excel_file():
            sel = filedialog.askopenfilename(
                title="İş Takip Excel Dosyasını Seçin",
                filetypes=[("Excel Dosyaları", "*.xlsx *.xls")]
            )
            if sel:
                e_excel.delete(0, tk.END)
                e_excel.insert(0, sel)

        def _pick_excel_folder():
            sel = filedialog.askdirectory(title="İş Takip Klasörünü Seçin")
            if sel:
                e_excel.delete(0, tk.END)
                e_excel.insert(0, sel)

        btn_pick_f = tk.Button(
            f_excel_row, text="📄 Excel Seç...", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1",
            padx=10, pady=3, relief=tk.FLAT, cursor="hand2", command=_pick_excel_file
        )
        btn_pick_f.pack(side=tk.LEFT, padx=(6, 2))

        btn_pick_d = tk.Button(
            f_excel_row, text="📁 Klasör Seç...", font=("Segoe UI", 9),
            bg="#334155", fg="#ffffff", activebackground="#475569",
            padx=8, pady=3, relief=tk.FLAT, cursor="hand2", command=_pick_excel_folder
        )
        btn_pick_d.pack(side=tk.LEFT, padx=(2, 0))

        # Alt Buton Paneli
        f_actions = tk.Frame(win, bg=self.THEME["card_bg"], padx=16, pady=10)
        f_actions.pack(fill=tk.X, side=tk.BOTTOM)

        def _save():
            self.config["hapag_client_id"] = e_hapag_id.get().strip()
            self.config["hapag_client_secret"] = e_hapag_sec.get().strip()
            self.config["cma_session_cookie"] = e_cma_cookie.get().strip()
            self.config["cma_token"] = e_cma_token.get().strip()
            self.config["one_api_key"] = e_one_key.get().strip()
            new_path = e_excel.get().strip()
            self.config["default_excel_path"] = new_path
            save_config(self.config)
            self.router = GlobalTrackingRouter(self.config)
            self.txt_excel_path.delete(0, tk.END)
            self.txt_excel_path.insert(0, new_path)
            self._last_mtime = 0
            messagebox.showinfo("Hafızaya Alındı", f"Acenta ayarları ve Excel yolu başarıyla hafızaya kaydedildi:\n{new_path}\n\nBundan sonraki tüm taramalar güncel konfigürasyon ile yapılacaktır.")
            win.destroy()

        btn_save = tk.Button(
            f_actions, text="💾 Ayarları Kaydet", font=("Segoe UI", 10, "bold"),
            bg="#10b981", fg="#ffffff", activebackground="#059669", padx=20, pady=6, relief=tk.FLAT, cursor="hand2",
            command=_save
        )
        btn_save.pack(side=tk.LEFT)

        btn_close = tk.Button(
            f_actions, text="Kapat", font=("Segoe UI", 10),
            bg="#475569", fg="#ffffff", padx=16, pady=6, relief=tk.FLAT, cursor="hand2",
            command=win.destroy
        )
        btn_close.pack(side=tk.RIGHT)


# ==============================================================================
# CLI MODU & GİRİŞ NOKTASI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Küresel Konteyner & Canlı ETA Takip Radarı v5.0")
    parser.add_argument("query", nargs="?", help="Konteyner veya B/L No")
    parser.add_argument("--cli", action="store_true", help="Terminal modunda çalıştır")
    args = parser.parse_args()

    cfg = load_config()
    router = GlobalTrackingRouter(cfg)

    if args.cli or (args.query and len(sys.argv) > 1):
        target = args.query or "MSNU8608960"
        print("=" * 65)
        print("[*] DOGRUER KURESEL KONTEYNER TAKIP RADARI (CLI)")
        print("=" * 65)
        print(f"\nSorgulaniyor: {target}...")
        res = router.track(target)
        if not res.get("success"):
            print(f"\n[!] Hata: {res.get('error')}")
            return

        for it in res.get("items", []):
            print(f"\n[{it['carrier']}] {it['container_no']} (B/L: {it['bl_no']})")
            print(f"Gemi         : {it['vessel']}")
            print(f"Varis Limani : {it['pod']} -> Canli ETA: {it['live_eta']} ({it['kalan_gun']})")
            if it.get('excel_eta') and it['excel_eta'] != '—':
                print(f"Excel ETA    : {it['excel_eta']} | Fark: {it['eta_diff']}")
            print(f"Aktarmalar   : {it['transshipments']}")
            print(f"Kaynak       : {it['source']}")
        print()
        return

    # Normal GUI Modu
    root = tk.Tk()
    app = GlobalRadarGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
