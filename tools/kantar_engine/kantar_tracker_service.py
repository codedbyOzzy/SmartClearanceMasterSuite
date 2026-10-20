# -*- coding: utf-8 -*-
"""
kantar_tracker_service.py — Kantar & DBA Tike Otonom Takip ve PDF Yönetim Servisi
"""
import os
import json
import time
import threading
import datetime
import re
from typing import List, Dict, Optional, Callable

try:
    from .kantar_sorgu import kantar_otomatik_sorgula, kantar_pdf_indir
except Exception:
    try:
        from tools.kantar_engine.kantar_sorgu import kantar_otomatik_sorgula, kantar_pdf_indir
    except Exception:
        from kantar_sorgu import kantar_otomatik_sorgula, kantar_pdf_indir


try:
    from tools.supabase_sync_manager import get_supabase_manager
except Exception:
    try:
        from supabase_sync_manager import get_supabase_manager
    except Exception:
        get_supabase_manager = None

try:
    from tools.cloud_sync import is_tombstone, remote_is_newer, local_record_ts, utc_now_iso
except Exception:
    from cloud_sync import is_tombstone, remote_is_newer, local_record_ts, utc_now_iso

try:
    from tools.ops_log import exception as ops_exception
    from tools.storage_json import load_json, save_json_atomic
except Exception:
    from ops_log import exception as ops_exception
    from storage_json import load_json, save_json_atomic

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
KANTAR_STORAGE_FILE = os.path.join(CONFIG_DIR, "kantar_takip_storage.json")
KANTAR_EXCLUDED_FILE = os.path.join(CONFIG_DIR, "kantar_takip_excluded.json")
KANTAR_PDF_DIR = os.path.join(CONFIG_DIR, "Kantar_Tickets")


def _pretty_ts(val):
    s = str(val or "").strip()
    if not s or s in ("—", "-", "None", "null"):
        return "—"
    if "T" in s and s[:4].isdigit():
        try:
            raw = s.replace("Z", "")
            if "+" in raw[10:]:
                raw = raw[:10] + raw[10:].split("+", 1)[0]
            if "." in raw:
                main, frac = raw.split(".", 1)
                frac = "".join(c for c in frac if c.isdigit())[:6].ljust(6, "0")
                raw = f"{main}.{frac}"
            dt = datetime.datetime.fromisoformat(raw)
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return s.replace("T", " ")[:16]
    return s


def _make_dosya_stamp_pdf_bytes(label: str, page_width: float = 595.0, page_height: float = 842.0) -> bytes:
    """Sağ üst köşede dosya numarası etiketi içeren minimal bir PDF damga üretir.

    Herhangi bir ek kütüphane gerektirmez — saf PDF yapısıyla oluşturulur.
    pypdf'nin merge_page() metoduyla orijinal PDF sayfasına bindirilmek üzere
    tasarlanmıştır.

    Args:
        label:       Etiket metni, örn. "D: 2024/1234"
        page_width:  Hedef sayfanın genişliği (punto cinsinden).
        page_height: Hedef sayfanın yüksekliği (punto cinsinden).

    Returns:
        Bellekte oluşturulmuş tek sayfalık PDF içeriği (bytes).
    """
    # Yalnızca latin-1 ile güvenle kodlanabilen karakterlere izin ver
    safe_label = ""
    for ch in label:
        try:
            ch.encode("latin-1")
            safe_label += ch
        except UnicodeEncodeError:
            safe_label += "?"

    # Tahmini metin genişliği: Helvetica-Bold 8pt ≈ 5.2 birim/karakter
    font_size = 8
    char_w = font_size * 0.52
    text_w = max(50.0, len(safe_label) * char_w)

    # Konum: sağ üst köşe, 6pt iç dolgu, 10pt sağ kenar boşluğu
    pad = 4.0
    margin_right = 10.0
    margin_top = 10.0
    box_w = text_w + pad * 2
    box_h = font_size + pad * 2
    box_x = page_width - box_w - margin_right
    box_y = page_height - box_h - margin_top
    text_x = box_x + pad
    text_y = box_y + pad

    # PDF içerik akışı
    stream_lines = [
        "q",
        # Beyaz dolgu kutusu
        "1 1 1 rg",
        f"{box_x:.2f} {box_y:.2f} {box_w:.2f} {box_h:.2f} re f",
        # Mavi-gri çerçeve
        "0.29 0.45 0.78 RG",
        "0.6 w",
        f"{box_x:.2f} {box_y:.2f} {box_w:.2f} {box_h:.2f} re S",
        # Metin
        "BT",
        f"/F1 {font_size} Tf",
        "0.10 0.20 0.60 rg",
        f"{text_x:.2f} {text_y:.2f} Td",
        f"({safe_label}) Tj",
        "ET",
        "Q",
    ]
    stream_str = "\n".join(stream_lines) + "\n"
    stream_bytes = stream_str.encode("latin-1")
    stream_len = len(stream_bytes)

    # --- Minimal PDF nesne yapısı ---
    obj_data = {}
    obj_data[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj_data[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj_data[3] = (
        f"<< /Type /Page /Parent 2 0 R "
        f"/MediaBox [0 0 {page_width:.2f} {page_height:.2f}] "
        f"/Contents 4 0 R "
        f"/Resources << /Font << /F1 5 0 R >> >> >>"
    ).encode("latin-1")
    obj_data[4] = (
        f"<< /Length {stream_len} >>\nstream\n"
    ).encode("latin-1") + stream_bytes + b"\nendstream"
    obj_data[5] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

    buf = bytearray()
    buf += b"%PDF-1.4\n"
    offsets: dict = {}

    for oid in sorted(obj_data.keys()):
        offsets[oid] = len(buf)
        buf += f"{oid} 0 obj\n".encode()
        buf += obj_data[oid]
        buf += b"\nendobj\n"

    xref_pos = len(buf)
    n_objs = len(obj_data) + 1  # +1 için boş nesne (0)
    buf += b"xref\n"
    buf += f"0 {n_objs}\n".encode()
    buf += b"0000000000 65535 f \n"
    for oid in sorted(obj_data.keys()):
        buf += f"{offsets[oid]:010d} 00000 n \n".encode()

    buf += b"trailer\n"
    buf += f"<< /Size {n_objs} /Root 1 0 R >>\n".encode()
    buf += b"startxref\n"
    buf += f"{xref_pos}\n".encode()
    buf += b"%%EOF\n"

    return bytes(buf)


class KantarTrackerService:
    def __init__(self, data_engine=None, telegram_service=None, on_status_change_callback: Optional[Callable] = None):
        self.data_engine = data_engine
        self.telegram_service = telegram_service
        self.on_status_change_callback = on_status_change_callback

        self.storage_file = KANTAR_STORAGE_FILE
        self.pdf_dir = KANTAR_PDF_DIR
        os.makedirs(self.pdf_dir, exist_ok=True)

        self.records: List[Dict] = []
        self.excluded: set = set()
        self.lock = threading.RLock()
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.is_scanning = False
        self.last_scan_time = "Henüz Yapılmadı"
        self.check_interval_seconds = 600  # 10 dakika
        self._pull_done = threading.Event()
        self._cloud_tombstones = set()

        self._load_storage()
        self._load_excluded()
        if get_supabase_manager:
            self._sync_from_supabase_async()
        else:
            self._pull_done.set()

    
    
    def _delete_from_supabase_async(self, c_no: str):
        self._tombstone_on_supabase_async([c_no])

    def _delete_multiple_from_supabase_async(self, c_list: list):
        self._tombstone_on_supabase_async(c_list)

    def _tombstone_on_supabase_async(self, c_list: list):
        if not get_supabase_manager:
            return
        def _run():
            try:
                sb = get_supabase_manager()
                sb.tombstone_kantar(c_list)
            except Exception as e:
                ops_exception("kantar", "Supabase kantar tombstone başarısız", e)
        threading.Thread(target=_run, daemon=True).start()

    def _clear_all_from_supabase_async(self):
        if not get_supabase_manager:
            return
        keys = []
        with self.lock:
            keys = list(self.excluded)
        def _run():
            try:
                sb = get_supabase_manager()
                if keys:
                    sb.tombstone_kantar(keys)
                else:
                    sb.clear_all_kantar()
            except Exception as e:
                ops_exception("kantar", "Supabase kantar tam temizlik başarısız", e)
        threading.Thread(target=_run, daemon=True).start()

    def _sync_to_supabase_async(self, item=None):
        if not get_supabase_manager:
            return
        def _run():
            try:
                self._pull_done.wait(timeout=20)
                sb = get_supabase_manager()
                skip = set(self.excluded) | set(self._cloud_tombstones)
                if item:
                    c_no = re.sub(r"[^A-Z0-9]", "", str(item.get("konteyner_no") or "").upper())
                    if c_no and c_no not in skip and not is_tombstone(item):
                        sb.upsert_kantar_record(item)
                    return
                with self.lock:
                    recs = [r for r in self.records if r.get("konteyner_no") not in skip and not is_tombstone(r)]
                payload = [{
                    "konteyner_no": r.get("konteyner_no"),
                    "dosya_no": r.get("dosya_no"),
                    "firma": r.get("firma"),
                    "kilo": r.get("agirlik", ""),
                    "dba_no": r.get("dba", ""),
                    "tartim_tarihi": r.get("tarih", ""),
                    "durum": r.get("durum", "İzleniyor"),
                    "kaynak": r.get("kaynak", ""),
                    "pdf_url": r.get("pdf_url") or "",
                } for r in recs if r.get("konteyner_no")]
                if hasattr(sb, "upsert_kantar_records"):
                    sb.upsert_kantar_records(payload)
                else:
                    for rec in payload:
                        sb.upsert_kantar_record(rec)
            except Exception as e:
                ops_exception("kantar", "Supabase kantar gönderimi başarısız", e)
        threading.Thread(target=_run, daemon=True).start()

    def _sync_from_supabase_async(self):
        if not get_supabase_manager:
            self._pull_done.set()
            return
        def _run():
            try:
                sb = get_supabase_manager()
                remote_recs = sb.fetch_all_kantar()
                changed = False
                with self.lock:
                    tombs = set()
                    local_map = {r.get("konteyner_no"): r for r in self.records if r.get("konteyner_no")}
                    for rem in remote_recs or []:
                        c_no = re.sub(r"[^A-Z0-9]", "", str(rem.get("konteyner_no") or "").upper())
                        if not c_no:
                            continue
                        if is_tombstone(rem):
                            tombs.add(c_no)
                            self.excluded.add(c_no)
                            if c_no in local_map:
                                self.records = [r for r in self.records if r.get("konteyner_no") != c_no]
                                local_map.pop(c_no, None)
                                changed = True
                            continue
                        if c_no in self.excluded:
                            continue
                        if c_no not in local_map:
                            new_rec = {
                                "konteyner_no": c_no,
                                "dosya_no": rem.get("dosya_no", "—"),
                                "ref": "—",
                                "firma": rem.get("firma", "WH-HANKOOK"),
                                "kaynak": rem.get("kaynak", "supabase"),
                                "durum": rem.get("durum", "⏳ Tartım Bekliyor"),
                                "hazir": bool(rem.get("kilo")),
                                "tartim_no": rem.get("dba_no", ""),
                                "tarih": rem.get("tartim_tarihi", ""),
                                "plaka": "",
                                "dba": rem.get("dba_no", ""),
                                "agirlik": rem.get("kilo", ""),
                                "pdf_url": rem.get("pdf_url"),
                                "yerel_pdf_yolu": None,
                                "son_kontrol": _pretty_ts(rem.get("updated_at") or rem.get("son_kontrol") or "—"),
                                "degisim_tarihi": _pretty_ts(rem.get("updated_at") or "—"),
                                "updated_at": rem.get("updated_at") or utc_now_iso(),
                                "bildirim_gonderildi": False,
                                "aktif": True
                            }
                            self.records.append(new_rec)
                            local_map[c_no] = new_rec
                            changed = True
                        elif remote_is_newer(rem, local_record_ts(local_map[c_no])):
                            loc = local_map[c_no]
                            loc["dosya_no"] = rem.get("dosya_no") or loc.get("dosya_no")
                            loc["firma"] = rem.get("firma") or loc.get("firma")
                            loc["kaynak"] = rem.get("kaynak") or loc.get("kaynak")
                            loc["durum"] = rem.get("durum") or loc.get("durum")
                            loc["dba"] = rem.get("dba_no") or loc.get("dba")
                            loc["agirlik"] = rem.get("kilo") or loc.get("agirlik")
                            loc["tarih"] = rem.get("tartim_tarihi") or loc.get("tarih")
                            loc["pdf_url"] = rem.get("pdf_url") or loc.get("pdf_url")
                            loc["hazir"] = bool(loc.get("agirlik") or loc.get("hazir"))
                            loc["updated_at"] = rem.get("updated_at") or loc.get("updated_at")
                            loc["son_kontrol"] = _pretty_ts(rem.get("updated_at") or loc.get("son_kontrol"))
                            changed = True
                    self._cloud_tombstones = tombs
                    if tombs:
                        self._save_excluded()
                if changed:
                    self._save_storage(sync_cloud=False)
                    if self.on_status_change_callback:
                        self.on_status_change_callback()
            except Exception as e:
                ops_exception("kantar", "Supabase kantar çekimi başarısız", e)
            finally:
                self._pull_done.set()
        threading.Thread(target=_run, daemon=True).start()

    def _load_storage(self):
        with self.lock:
            data = load_json(self.storage_file, default=[])
            self.records = data if isinstance(data, list) else []
            if self.excluded:
                self.records = [r for r in self.records if r.get("konteyner_no") not in self.excluded]

    def _load_excluded(self):
        with self.lock:
            data = load_json(KANTAR_EXCLUDED_FILE, default=[])
            if isinstance(data, list):
                self.excluded = {re.sub(r"[^A-Z0-9]", "", str(x).upper()) for x in data if x}
            else:
                self.excluded = set()
            if self.records:
                before = len(self.records)
                self.records = [r for r in self.records if r.get("konteyner_no") not in self.excluded]
                if len(self.records) != before:
                    self._save_storage(sync_cloud=False)

    def _save_excluded(self):
        try:
            with self.lock:
                payload = sorted(self.excluded)
            save_json_atomic(KANTAR_EXCLUDED_FILE, payload)
        except Exception as e:
            ops_exception("kantar", "Kantar hariç listesi yazılamadı", e)

    def _mark_excluded(self, cntr_list):
        added = False
        with self.lock:
            for c in cntr_list:
                clean = re.sub(r"[^A-Z0-9]", "", str(c or "").upper())
                if clean and clean not in self.excluded:
                    self.excluded.add(clean)
                    added = True
        if added:
            self._save_excluded()

    def _unexclude(self, konteyner_no: str):
        clean = re.sub(r"[^A-Z0-9]", "", str(konteyner_no or "").upper())
        with self.lock:
            if clean in self.excluded:
                self.excluded.discard(clean)
                self._cloud_tombstones.discard(clean)
                self._save_excluded()

    def _save_storage(self, sync_cloud: bool = True):
        try:
            save_json_atomic(self.storage_file, self.records, snapshot_lock=self.lock)
        except Exception as e:
            ops_exception("kantar", "Kantar yerel depo yazılamadı", e)
        if sync_cloud:
            self._sync_to_supabase_async()

    def list_tracked(self, only_active: bool = True) -> List[Dict]:
        with self.lock:
            if only_active:
                return [r for r in self.records if r.get("aktif", True)]
            return list(self.records)

    def add_to_tracking(self, konteyner_no: str, dosya_no: str = "—", ref: str = "—",
                        kaynak: str = "otomatik", firma: str = "WH-HANKOOK") -> Dict:
        clean_no = re.sub(r"[^A-Z0-9]", "", str(konteyner_no or "").upper())
        if not clean_no or len(clean_no) < 4:
            return {"success": False, "error": "Geçersiz konteyner numarası."}

        self._unexclude(clean_no)

        with self.lock:
            for r in self.records:
                if r.get("konteyner_no") == clean_no:
                    r["aktif"] = True
                    if dosya_no != "—": r["dosya_no"] = dosya_no
                    if ref != "—": r["ref"] = ref
                    if firma != "—": r["firma"] = firma
                    self._save_storage()
                    return {"success": True, "created": False, "record": r}

            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            new_rec = {
                "konteyner_no": clean_no,
                "dosya_no": dosya_no,
                "ref": ref,
                "firma": firma,
                "kaynak": kaynak,
                "durum": "⏳ Tartım Bekliyor",
                "hazir": False,
                "tartim_no": "",
                "tarih": "",
                "plaka": "",
                "dba": "",
                "agirlik": "",
                "pdf_url": None,
                "yerel_pdf_yolu": None,
                "son_kontrol": "—",
                "degisim_tarihi": now_str,
                "bildirim_gonderildi": False,
                "aktif": True
            }
            self.records.insert(0, new_rec)
            self._save_storage()

        return {"success": True, "created": True, "record": new_rec}

    def remove_multiple_from_tracking(self, cntr_list: List[str]) -> int:
        clean_set = {re.sub(r"[^A-Z0-9]", "", str(b).upper()) for b in cntr_list if b}
        removed_count = 0
        with self.lock:
            orig_len = len(self.records)
            self.records = [r for r in self.records if r.get("konteyner_no") not in clean_set]
            removed_count = orig_len - len(self.records)
            if removed_count > 0:
                self._save_storage(sync_cloud=False)
                self._mark_excluded(list(clean_set))
                self._delete_multiple_from_supabase_async(list(clean_set))
        return removed_count

    def clear_all_tracking(self) -> int:
        with self.lock:
            c = len(self.records)
            gone = [r.get("konteyner_no") for r in self.records if r.get("konteyner_no")]
            self.records = []
            self._save_storage(sync_cloud=False)
        if gone:
            self._mark_excluded(gone)
            self._clear_all_from_supabase_async()
        return c

    def auto_sync_from_evrim_and_excel(self, evrim_records: List[Dict] = None, excel_records: List[Dict] = None) -> int:
        """Excel U sütunundaki ve Evrim'deki tüm konteynerleri kantar takip havuzuna aktarır."""
        added_count = 0
        pool_records = []
        if excel_records:
            pool_records.extend(excel_records)
        elif self.data_engine and hasattr(self.data_engine, "records") and self.data_engine.records:
            pool_records.extend(self.data_engine.records)

        if evrim_records:
            for ev in evrim_records:
                if not any(r.get("dosya") == ev.get("dosya_no") for r in pool_records):
                    pool_records.append(ev)

        with self.lock:
            existing_map = {r.get("konteyner_no"): r for r in self.records}
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

            for rec in pool_records:
                cntrs = []
                c_raw = rec.get("konteyner") or rec.get("konteyner_no") or rec.get("Konteyner")
                if isinstance(c_raw, list):
                    cntrs.extend(c_raw)
                elif isinstance(c_raw, str):
                    for part in re.split(r"[\s,;+/]+", c_raw):
                        if part.strip():
                            cntrs.append(part.strip())

                for c in cntrs:
                    clean_c = re.sub(r"[^A-Z0-9]", "", c.upper())
                    if len(clean_c) >= 6:
                        if clean_c in self.excluded:
                            continue
                        dosya = rec.get("dosya") or rec.get("dosya_no") or "—"
                        ref = rec.get("ref") or rec.get("hankook_ref") or "—"
                        firma = rec.get("bayi") or rec.get("yurt_disi_firma") or "WH-HANKOOK"
                        
                        liman_raw = str(rec.get("liman") or rec.get("Liman") or rec.get("gumruk") or rec.get("Gumruk") or "").upper()
                        detected_kaynak = "otomatik"
                        if "YILPORT" in liman_raw or "DILOVASI" in liman_raw or "DİLOVASI" in liman_raw:
                            detected_kaynak = "Yılport"
                        elif "EVYAP" in liman_raw or "KORFEZ" in liman_raw or "KÖRFEZ" in liman_raw:
                            detected_kaynak = "Körfez"
                        elif "YARIMCA" in liman_raw or "DPW" in liman_raw or "DP WORLD" in liman_raw:
                            detected_kaynak = "Yarımca"

                        if clean_c in existing_map:
                            ex = existing_map[clean_c]
                            ex["aktif"] = True
                            if dosya != "—": ex["dosya_no"] = dosya
                            if ref != "—": ex["ref"] = ref
                            if not ex.get("hazir") and ex.get("kaynak") == "otomatik" and detected_kaynak != "otomatik":
                                ex["kaynak"] = detected_kaynak
                        else:
                            new_rec = {
                                "konteyner_no": clean_c,
                                "dosya_no": dosya,
                                "ref": ref,
                                "firma": firma,
                                "kaynak": detected_kaynak,
                                "durum": "⏳ Tartım Bekliyor",
                                "hazir": False,
                                "tartim_no": "",
                                "tarih": "",
                                "plaka": "",
                                "dba": "",
                                "agirlik": "",
                                "pdf_url": None,
                                "yerel_pdf_yolu": None,
                                "son_kontrol": "—",
                                "degisim_tarihi": now_str,
                                "bildirim_gonderildi": False,
                                "aktif": True
                            }
                            self.records.insert(0, new_rec)
                            existing_map[clean_c] = new_rec
                            added_count += 1

            self._save_storage()

        return added_count

    def query_single_now(self, konteyner_no: str) -> Dict:
        """Kullanıcı butona bastığında veya Telegram'dan tek bir konteyneri anlık tartar."""
        clean_no = re.sub(r"[^A-Z0-9]", "", str(konteyner_no or "").upper())
        res = kantar_otomatik_sorgula(clean_no)
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        if res.get("success"):
            hazir = res.get("hazir", False)
            t_no = res.get("tartim_no", "")
            t_dt = res.get("tarih", "")
            plaka = res.get("plaka", "")
            firma = res.get("firma", "")
            dba = res.get("dba", "")
            pdf_u = res.get("pdf_url")

            # Eğer tike hazırsa yerel PDF'i otomatik indir
            local_pdf = res.get("yerel_pdf_yolu")
            if not local_pdf or not os.path.exists(local_pdf):
                if hazir and pdf_u:
                    clean_t = re.sub(r"[^A-Za-z0-9]", "_", str(t_no or "tike"))[:25]
                    local_pdf = os.path.join(self.pdf_dir, f"Kantar_{clean_no}_{clean_t}.pdf")
                    kantar_pdf_indir(pdf_u, local_pdf)

            with self.lock:
                for r in self.records:
                    if r.get("konteyner_no") == clean_no:
                        r["durum"] = "🟢 Tartım Hazır" if hazir else "⏳ Tartım Bekliyor"
                        r["kaynak"] = res.get("kaynak") if hazir else "otomatik"
                        r["hazir"] = hazir
                        r["tartim_no"] = t_no
                        r["tarih"] = t_dt
                        r["plaka"] = plaka
                        if firma: r["firma"] = firma
                        r["dba"] = dba
                        r["agirlik"] = res.get("agirlik") or dba
                        r["pdf_url"] = pdf_u
                        if local_pdf: r["yerel_pdf_yolu"] = local_pdf
                        r["son_kontrol"] = now_str
                        break
                self._save_storage()

            if self.on_status_change_callback:
                try:
                    self.on_status_change_callback()
                except Exception as e:
                    ops_exception("kantar", "Durum değişim callback hatası", e)

            res["yerel_pdf_yolu"] = local_pdf
        return res

    def download_and_get_pdf(self, konteyner_no: str) -> Optional[str]:
        """Konteynerin PDF'ini indirir ve yerel dosya yolunu döner."""
        clean_no = re.sub(r"[^A-Z0-9]", "", str(konteyner_no or "").upper())
        rec = None
        with self.lock:
            for r in self.records:
                if r.get("konteyner_no") == clean_no:
                    rec = r
                    break

        if not rec:
            res = self.query_single_now(clean_no)
            return res.get("yerel_pdf_yolu")

        if rec.get("yerel_pdf_yolu") and os.path.exists(rec.get("yerel_pdf_yolu")):
            return rec.get("yerel_pdf_yolu")

        pdf_u = rec.get("pdf_url")
        if not pdf_u:
            res = self.query_single_now(clean_no)
            return res.get("yerel_pdf_yolu")

        clean_t = re.sub(r"[^A-Za-z0-9]", "_", str(rec.get('tartim_no') or 'tike'))[:25]
        local_pdf = os.path.join(self.pdf_dir, f"Kantar_{clean_no}_{clean_t}.pdf")
        if kantar_pdf_indir(pdf_u, local_pdf):
            with self.lock:
                rec["yerel_pdf_yolu"] = local_pdf
                self._save_storage()
            return local_pdf

        return None

    def download_pdf_tike(self, konteyner_no: str) -> Optional[str]:
        """Konteynerin PDF'ini indirir ve yerel dosya yolunu döner (download_and_get_pdf alias)."""
        return self.download_and_get_pdf(konteyner_no)

    def merge_all_pdfs(
        self,
        output_path: str,
        konteyner_list: Optional[List[str]] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict:
        """Takip havuzundaki hazır tike PDF'lerini tek bir dosyada birleştirir.

        Args:
            output_path:     Çıktı PDF'inin tam dosya yolu.
            konteyner_list:  Sadece bu konteynerleri işle. None ise tablodaki
                             sırayla tüm hazır kayıtlar kullanılır.
            on_progress:     İlerleme geri çağrısı (tamamlanan, toplam, cntr_no).

        Returns:
            {
                "success": bool,
                "merged_path": str | None,
                "total": int,          # birleştirilen PDF sayısı
                "skipped": int,        # PDF'i olmayan / atlanılan sayı
                "error": str | None,
            }
        """
        fitz_module = None
        try:
            import pymupdf as fitz_module
        except ImportError:
            try:
                import fitz as fitz_module
            except ImportError:
                pass

        pypdf_module = None
        try:
            import pypdf as pypdf_module
        except ImportError:
            pass

        if not fitz_module and not pypdf_module:
            return {"success": False, "error": "PDF birleştirme için pymupdf veya pypdf kütüphanesi bulunamadı.", "total": 0, "skipped": 0, "merged_path": None}

        with self.lock:
            all_records = [r for r in self.records if r.get("aktif", True)]

        # Filtrele: sadece istenen konteynerler veya tümü
        if konteyner_list is not None:
            clean_set = {re.sub(r"[^A-Z0-9]", "", str(c).upper()) for c in konteyner_list if c}
            # Tablodaki sırayı koru — sadece istenen konteynerleri filtrele
            records_to_process = [r for r in all_records if r.get("konteyner_no") in clean_set]
        else:
            # Seçim yok → tüm hazır olanlar (tabloda göründüğü sırayla)
            records_to_process = [r for r in all_records if r.get("hazir") or r.get("pdf_url")]

        if not records_to_process:
            return {"success": False, "error": "Birleştirilecek hazır PDF tikesi bulunamadı.", "total": 0, "skipped": 0, "merged_path": None}

        merged_count = 0
        skipped_count = 0
        total = len(records_to_process)

        # PyMuPDF (fitz) ile hızlı ve kayıpsız birleştirme
        if fitz_module:
            merged_doc = fitz_module.open()
            for idx, rec in enumerate(records_to_process):
                cntr = rec.get("konteyner_no", "?")
                if on_progress:
                    try: on_progress(idx, total, cntr)
                    except Exception: pass

                local_path = rec.get("yerel_pdf_yolu")
                if not local_path or not os.path.exists(local_path):
                    local_path = self.download_and_get_pdf(cntr)

                if not local_path or not os.path.exists(local_path):
                    skipped_count += 1
                    continue

                try:
                    doc = fitz_module.open(local_path)
                    dosya_no = rec.get("dosya_no", "")
                    if not dosya_no or str(dosya_no).strip() in ("—", "-", "None", "null", ""):
                        dosya_no = self._find_dosya_no_from_excel(cntr) or ""

                    stamp_label = f"D: {dosya_no} | {cntr}" if dosya_no and str(dosya_no).strip() not in ("—", "-", "None", "null", "") else cntr

                    for page in doc:
                        try:
                            pw = page.rect.width
                            box_w = max(90, len(stamp_label) * 6 + 12)
                            box_x = pw - box_w - 10
                            page.draw_rect(fitz_module.Rect(box_x, 10, pw - 10, 26), color=(0.29, 0.45, 0.78), fill=(1, 1, 1), width=0.6)
                            page.insert_text(fitz_module.Point(box_x + 6, 21), stamp_label, fontsize=8, fontname="helv", color=(0.10, 0.20, 0.60))
                        except Exception as se:
                            pass
                    merged_doc.insert_pdf(doc)
                    doc.close()
                    merged_count += 1
                except Exception as e:
                    ops_exception("kantar", f"PDF birleştirme okunamadı ({cntr})", e)
                    skipped_count += 1

            if merged_count == 0:
                merged_doc.close()
                return {"success": False, "error": "Hiçbir PDF tikesi okunamadı veya henüz mevcut değil.", "total": 0, "skipped": skipped_count, "merged_path": None}

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            merged_doc.save(output_path)
            merged_doc.close()

        elif pypdf_module:
            writer = pypdf_module.PdfWriter()
            for idx, rec in enumerate(records_to_process):
                cntr = rec.get("konteyner_no", "?")
                if on_progress:
                    try: on_progress(idx, total, cntr)
                    except Exception: pass

                local_path = rec.get("yerel_pdf_yolu")
                if not local_path or not os.path.exists(local_path):
                    local_path = self.download_and_get_pdf(cntr)

                if not local_path or not os.path.exists(local_path):
                    skipped_count += 1
                    continue

                try:
                    reader = pypdf_module.PdfReader(local_path)
                    for page in reader.pages:
                        writer.add_page(page)
                    merged_count += 1
                except Exception as e:
                    skipped_count += 1

            if merged_count == 0:
                return {"success": False, "error": "Hiçbir PDF tikesi okunamadı.", "total": 0, "skipped": skipped_count, "merged_path": None}

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as out_f:
                writer.write(out_f)

        return {
            "success": True,
            "merged_path": output_path,
            "total": merged_count,
            "skipped": skipped_count,
            "error": None,
        }

    def remove_from_tracking(self, konteyner_no: str) -> bool:
        """Tek bir konteyneri takip havuzundan siler."""
        return self.remove_multiple_from_tracking([konteyner_no]) > 0

    def run_full_cycle(self) -> Dict:
        """Tüm takip listesini çok iş parçacıklı (multi-threading) hızlı tarar ve hazır olanları bildirir."""
        if self.is_scanning:
            return {"status": "already_running"}

        self.is_scanning = True
        active_list = self.list_tracked(only_active=True)
        # Sadece henüz tartılmamış olanları tara
        pending_list = [r for r in active_list if not r.get("hazir")]
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        self.last_scan_time = now_str

        changed_count = 0
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _scan_single(item):
            cntr = item.get("konteyner_no")
            kaynak = item.get("kaynak", "otomatik")
            # Liman belirtilmemişse 'otomatik' modda tüm limanları sırayla tara
            if not kaynak or str(kaynak).lower() in ("otomatik", "manuel", "supabase", "—", "", "none"):
                kaynak = "otomatik"
            res = kantar_otomatik_sorgula(cntr, kaynak)
            return cntr, res, item

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(_scan_single, item): item for item in pending_list}
            for future in as_completed(futures):
                cntr, res, item = future.result()

                if res.get("success") and res.get("hazir"):
                    t_no = res.get("tartim_no", "")
                    t_dt = res.get("tarih", "")
                    plaka = res.get("plaka", "")
                    firma = res.get("firma", "")
                    dba = res.get("dba", "")
                    pdf_u = res.get("pdf_url")

                    local_pdf = res.get("yerel_pdf_yolu")
                    if not local_pdf or not os.path.exists(local_pdf):
                        if pdf_u:
                            clean_t = re.sub(r"[^A-Za-z0-9]", "_", str(t_no or "tike"))[:25]
                            local_pdf = os.path.join(self.pdf_dir, f"Kantar_{cntr}_{clean_t}.pdf")
                            kantar_pdf_indir(pdf_u, local_pdf)

                    with self.lock:
                        for r in self.records:
                            if r.get("konteyner_no") == cntr:
                                r["durum"] = "🟢 Tartım Hazır"
                                r["hazir"] = True
                                if res.get("kaynak"): r["kaynak"] = res.get("kaynak")
                                r["tartim_no"] = t_no
                                r["tarih"] = t_dt
                                r["plaka"] = plaka
                                if firma: r["firma"] = firma
                                r["dba"] = dba
                                r["agirlik"] = res.get("agirlik") or dba
                                r["pdf_url"] = pdf_u
                                if local_pdf: r["yerel_pdf_yolu"] = local_pdf
                                r["son_kontrol"] = now_str
                                r["degisim_tarihi"] = now_str
                                break
                        self._save_storage()

                    changed_count += 1

                    # Telegram Push Alarmı Fırlat
                    if self.telegram_service and not item.get("bildirim_gonderildi"):
                        try:
                            self._send_telegram_kantar_alert(cntr, t_no, t_dt, plaka, firma, dba, local_pdf)
                            with self.lock:
                                for r in self.records:
                                    if r.get("konteyner_no") == cntr:
                                        r["bildirim_gonderildi"] = True
                                        break
                                self._save_storage()
                        except Exception as e:
                            print(f"[KANTAR-TELEGRAM-ALERT-ERROR] {e}")

                else:
                    # Tartım henüz hazır değilse de son kontrol zamanını güncelle
                    with self.lock:
                        for r in self.records:
                            if r.get("konteyner_no") == cntr:
                                r["son_kontrol"] = now_str
                                if not r.get("hazir"):
                                    r["durum"] = "⏳ Tartım Bekliyor"
                                    # Henüz tartılmamış konteyner tek limana kilitlenmesin
                                    r["kaynak"] = "otomatik"
                                break
                        self._save_storage()

        self.is_scanning = False
        if self.on_status_change_callback:
            try:
                self.on_status_change_callback()
            except Exception as e:
                ops_exception("kantar", "Durum degisim callback hatasi", e)

        return {"total_checked": len(pending_list), "changed_count": changed_count}

    def _find_dosya_no_from_excel(self, cntr: str) -> str:
        """Excel data engine'den konteyner numarasına göre dosya no'yu bulur."""
        if not cntr:
            return ""
        try:
            # data_engine doğrudan mevcut
            engine = self.data_engine
            # Yoksa telegram_service üzerinden dene
            if engine is None and self.telegram_service:
                engine = getattr(self.telegram_service, "data_engine", None)
            if engine is None:
                return ""
            records = getattr(engine, "records", []) or []
            cntr_clean = cntr.strip().upper()
            for rec in records:
                raw = str(rec.get("konteyner") or "").upper()
                # Hücrede birden fazla konteyner olabilir, boşluk/virgül ile ayrılmış
                parts = [p.strip() for p in raw.replace(",", " ").split()]
                if cntr_clean in parts:
                    return str(rec.get("dosya") or "").strip()
        except Exception as e:
            print(f"[KANTAR-DOSYA-LOOKUP] {e}")
        return ""

    def _send_telegram_kantar_alert(self, cntr: str, tartim_no: str, tarih: str, plaka: str,
                                    firma: str, dba: str, pdf_path: Optional[str]):
        # Excel'den Dosya No'yu bul
        dosya_no = self._find_dosya_no_from_excel(cntr)
        dosya_satiri = f"📁 <b>Dosya No:</b> <code>{dosya_no}</code>\n" if dosya_no else ""

        # Windows Masaüstü Toast Bildirimi Fırlat
        try:
            from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
            toast_title = f"⚖️ DP World Kantar: {cntr}"
            toast_msg = f"Tartım No: {tartim_no or '—'} | Plaka: {plaka or '—'}\nFirma: {firma or 'WH-HANKOOK'}"
            send_desktop_notification(toast_title, toast_msg)
        except Exception:
            pass

        msg = (
            f"⚖️ 🟢 <b>[KANTAR TİKESİ HAZIR!]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{dosya_satiri}"
            f"📦 <b>Konteyner:</b> <code>{cntr}</code>\n"
            f"🧾 <b>Tartım No:</b> <code>{tartim_no or '—'}</code>\n"
            f"📅 <b>Tarih:</b> {tarih or 'Bugün'}\n"
            f"🚛 <b>Plaka:</b> <code>{plaka or '—'}</code>\n"
            f"🏢 <b>Firma:</b> {firma or 'WH-HANKOOK'}\n"
            f"⚖️ <b>DBA (VGM):</b> {dba or '—'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Kantar tikesi otonom olarak indirildi ve ekte sunulmuştur.</i>"
        )
        chat_ids = []
        if self.telegram_service:
            chat_ids = list(self.telegram_service.config.get("authorized_chat_ids") or [])
        if not chat_ids:
            return
        if self.telegram_service:
            for cid in chat_ids:
                try:
                    if pdf_path and os.path.exists(pdf_path) and hasattr(self.telegram_service, "send_document"):
                        self.telegram_service.send_document(cid, pdf_path, caption=msg)
                    else:
                        self.telegram_service.send_message(cid, msg)
                except Exception as e:
                    print(f"[KANTAR-TELEGRAM-ALERT-ERROR] {e}")

        # Teams kanalına da gönder (PDF eki dahil)
        try:
            import sys as _sys, os as _os
            _sys.path.append(_os.path.join(_os.path.dirname(__file__), ".."))
            from teams_bridge.teams_bridge import get_teams_bridge
            teams_body = (
                f"{'Dosya No: ' + dosya_no + chr(10) if dosya_no else ''}"
                f"Konteyner: {cntr}\n"
                f"Tartim No: {tartim_no or '-'}\n"
                f"Tarih: {tarih or 'Bugun'}\n"
                f"Plaka: {plaka or '-'}\n"
                f"Firma: {firma or 'WH-HANKOOK'}\n"
                f"DBA (VGM): {dba or '-'}"
            )
            # PDF varsa ek olarak ekle
            ekler = []
            if pdf_path and _os.path.exists(str(pdf_path)):
                ekler.append(str(pdf_path))
            get_teams_bridge().send_to_teams(
                f"Kantar Tikesi Hazir - {cntr}" + (f" | Dosya: {dosya_no}" if dosya_no else ""),
                teams_body,
                attachment_paths=ekler if ekler else None
            )
        except Exception as te:
            print(f"[KANTAR-TEAMS-ALERT-ERROR] {te}")

    def start_worker(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        print("[INFO] Kantar & DBA Otonom Takip Servisi Başlatıldı (10 Dk Döngü)!")

    def stop_worker(self):
        self.is_running = False

    def _worker_loop(self):
        time.sleep(15)  # Başlangıçta GUI yüklenmesini bekle
        while self.is_running:
            try:
                try:
                    from tools.dogruer_master_suite.service_supervisor import get_supervisor
                    get_supervisor().record_heartbeat("kantar", status="RUNNING", detail="Kantar taraması başladı", inc_cycle=True)
                except Exception:
                    pass
                self.run_full_cycle()
                try:
                    from tools.dogruer_master_suite.service_supervisor import get_supervisor
                    get_supervisor().record_heartbeat("kantar", status="OK", detail="Kantar taraması tamamlandı", inc_cycle=False)
                except Exception:
                    pass
            except Exception as e:
                print(f"[KANTAR-WORKER-ERROR] {e}")
                try:
                    from tools.dogruer_master_suite.service_supervisor import get_supervisor
                    get_supervisor().record_heartbeat("kantar", status="ERROR", detail=str(e), inc_cycle=False)
                except Exception:
                    pass

            for _ in range(self.check_interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)


_kantar_tracker_instance = None

def get_kantar_tracker_service(data_engine=None, telegram_service=None, on_status_change_callback=None) -> KantarTrackerService:
    global _kantar_tracker_instance
    if _kantar_tracker_instance is None:
        _kantar_tracker_instance = KantarTrackerService(
            data_engine=data_engine,
            telegram_service=telegram_service,
            on_status_change_callback=on_status_change_callback
        )
    else:
        if data_engine and not _kantar_tracker_instance.data_engine:
            _kantar_tracker_instance.data_engine = data_engine
        if telegram_service and not _kantar_tracker_instance.telegram_service:
            _kantar_tracker_instance.telegram_service = telegram_service
        if on_status_change_callback and not _kantar_tracker_instance.on_status_change_callback:
            _kantar_tracker_instance.on_status_change_callback = on_status_change_callback
    return _kantar_tracker_instance
