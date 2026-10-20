# -*- coding: utf-8 -*-
"""
tools/gtb_engine/gtb_tracker_service.py
GTB Otonom Beyanname Takip & Arka Plan İzleme Servisi v2.0
Firma: Doğruer Gümrük Müşavirliği A.Ş.
"""

import os
import json
import time
import threading
import datetime
import re
from typing import List, Dict, Optional, Callable

try:
    from .gtb_sorgu import gtb_beyanname_sorgula
except Exception:
    try:
        from tools.gtb_engine.gtb_sorgu import gtb_beyanname_sorgula
    except Exception:
        from gtb_sorgu import gtb_beyanname_sorgula


try:
    from tools.supabase_sync_manager import get_supabase_manager
except Exception:
    try:
        from supabase_sync_manager import get_supabase_manager
    except Exception:
        get_supabase_manager = None

try:
    from tools.ops_log import exception as ops_exception, error as ops_error
    from tools.storage_json import load_json, save_json_atomic
except Exception:
    from ops_log import exception as ops_exception, error as ops_error
    from storage_json import load_json, save_json_atomic

try:
    from tools.cloud_sync import is_tombstone, remote_is_newer, local_record_ts, utc_now_iso
except Exception:
    from cloud_sync import is_tombstone, remote_is_newer, local_record_ts, utc_now_iso

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
GTB_STORAGE_PATH = os.path.join(CONFIG_DIR, "gtb_takip_storage.json")
GTB_EXCLUDED_FILE = os.path.join(CONFIG_DIR, "gtb_takip_excluded.json")

os.makedirs(CONFIG_DIR, exist_ok=True)

class GTBTrackerService:
    def __init__(self, data_engine=None, telegram_service=None, on_status_change_callback: Optional[Callable] = None):
        self.data_engine = data_engine
        self.telegram_service = telegram_service
        self.on_status_change_callback = on_status_change_callback
        self.is_running = False
        self.interval_seconds = 600  # 10 dakika
        self.worker_thread = None
        self.lock = threading.RLock()
        self.excluded: set = set()
        self._cloud_tombstones = set()
        self._pull_done = threading.Event()
        self.records: List[Dict] = self._load_storage()
        self._load_excluded()
        self.purge_invalid_records()
        if get_supabase_manager:
            self._sync_from_supabase_async()
        else:
            self._pull_done.set()
        self.last_scan_time = "—"
        self.is_scanning = False

    
    
    def _delete_from_supabase_async(self, b_no: str):
        self._tombstone_on_supabase_async([b_no])

    def _delete_multiple_from_supabase_async(self, b_list: list):
        self._tombstone_on_supabase_async(b_list)

    def _tombstone_on_supabase_async(self, b_list: list):
        if not get_supabase_manager:
            return
        def _run():
            try:
                sb = get_supabase_manager()
                sb.tombstone_gtb(b_list)
            except Exception as e:
                ops_exception("gtb", "Supabase GTB tombstone başarısız", e)
        threading.Thread(target=_run, daemon=True).start()

    def _clear_all_from_supabase_async(self):
        if not get_supabase_manager:
            return
        with self.lock:
            keys = list(self.excluded)
        def _run():
            try:
                sb = get_supabase_manager()
                if keys:
                    sb.tombstone_gtb(keys)
                else:
                    sb.clear_all_gtb()
            except Exception as e:
                ops_exception("gtb", "Supabase GTB tam temizlik başarısız", e)
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
                    b_no = re.sub(r"[^A-Z0-9]", "", str(item.get("beyanname_no") or "").upper())
                    if b_no and b_no not in skip and not is_tombstone(item):
                        sb.upsert_gtb_record(item)
                    return
                with self.lock:
                    recs = [r for r in self.records if r.get("beyanname_no") not in skip and not is_tombstone(r)]
                payload = [{
                    "beyanname_no": r.get("beyanname_no"),
                    "dosya_no": r.get("dosya_no"),
                    "ref_no": r.get("ref_no"),
                    "firma": r.get("firma"),
                    "gtb_durum": r.get("gtb_durum", r.get("durum", "İzleniyor")),
                    "hat": r.get("hat", ""),
                    "son_sorgu_zamani": r.get("son_sorgu_zamani", ""),
                } for r in recs]
                if hasattr(sb, "upsert_gtb_records"):
                    sb.upsert_gtb_records(payload)
                else:
                    for rec in payload:
                        sb.upsert_gtb_record(rec)
            except Exception as e:
                ops_exception("gtb", "Supabase GTB gönderimi başarısız", e)
        threading.Thread(target=_run, daemon=True).start()

    def _sync_from_supabase_async(self):
        if not get_supabase_manager:
            self._pull_done.set()
            return

        def _run():
            try:
                sb = get_supabase_manager()
                remote_recs = sb.fetch_all_gtb() or []
                changed = False
                with self.lock:
                    tombs = set()
                    local_map = {r.get("beyanname_no"): r for r in self.records if r.get("beyanname_no")}
                    for rem in remote_recs:
                        b_no = rem.get("beyanname_no")
                        if not b_no:
                            continue
                        clean_b = re.sub(r"[^A-Z0-9]", "", str(b_no).upper())
                        if clean_b.startswith("BEYAN") or len(clean_b) < 15:
                            continue
                        if is_tombstone(rem):
                            tombs.add(clean_b)
                            self.excluded.add(clean_b)
                            if clean_b in local_map:
                                self.records = [r for r in self.records if r.get("beyanname_no") != clean_b]
                                local_map.pop(clean_b, None)
                                changed = True
                            continue
                        if clean_b in self.excluded:
                            continue
                        if clean_b not in local_map:
                            new_rec = {
                                "beyanname_no": clean_b,
                                "dosya_no": rem.get("dosya_no", "—"),
                                "ref_no": rem.get("ref_no", "—"),
                                "firma": rem.get("firma", "WH-HANKOOK"),
                                "durum": rem.get("gtb_durum", "İzleniyor"),
                                "gtb_durum": rem.get("gtb_durum", "İzleniyor"),
                                "hat": rem.get("hat", "—"),
                                "son_sorgu_zamani": rem.get("son_sorgu_zamani", "—"),
                                "updated_at": rem.get("updated_at") or utc_now_iso(),
                                "hata_sayisi": 0,
                                "aktif": True,
                            }
                            self.records.append(new_rec)
                            local_map[clean_b] = new_rec
                            changed = True
                        elif remote_is_newer(rem, local_record_ts(local_map[clean_b])):
                            loc = local_map[clean_b]
                            loc["gtb_durum"] = rem.get("gtb_durum") or loc.get("gtb_durum")
                            loc["durum"] = loc["gtb_durum"]
                            if rem.get("hat"):
                                loc["hat"] = rem["hat"]
                            if rem.get("dosya_no"):
                                loc["dosya_no"] = rem["dosya_no"]
                            loc["son_sorgu_zamani"] = rem.get("son_sorgu_zamani") or loc.get("son_sorgu_zamani")
                            loc["updated_at"] = rem.get("updated_at") or loc.get("updated_at")
                            changed = True
                    self._cloud_tombstones = tombs
                    if tombs:
                        self._save_excluded()
                if changed:
                    self._save_storage(sync_cloud=False)
                    if self.on_status_change_callback:
                        self.on_status_change_callback()
            except Exception as e:
                ops_exception("gtb", "Supabase GTB çekimi başarısız", e)
            finally:
                self._pull_done.set()

        threading.Thread(target=_run, daemon=True).start()

    def purge_invalid_records(self) -> int:
        """BEYAN_ veya geçersiz formattaki tüm dummy kayıtları hem hafızadan hem depolamadan hem de Supabase'den temizler."""
        removed_count = 0
        invalid_keys = []
        with self.lock:
            valid = []
            for r in self.records:
                b = str(r.get("beyanname_no", "")).strip()
                c = re.sub(r"[^A-Z0-9]", "", b.upper())
                if b.startswith("BEYAN") or len(c) < 15:
                    invalid_keys.append(b)
                    removed_count += 1
                else:
                    valid.append(r)
            self.records = valid
        if removed_count > 0:
            self._save_storage(sync_cloud=False)
            if invalid_keys:
                self._delete_multiple_from_supabase_async(invalid_keys)
            if self.on_status_change_callback:
                self.on_status_change_callback()
        return removed_count

    def _load_storage(self) -> List[Dict]:
        data = load_json(GTB_STORAGE_PATH, default=[])
        valid = []
        for r in (data or []):
            b = str(r.get("beyanname_no", "")).strip()
            c = re.sub(r"[^A-Z0-9]", "", b.upper())
            if b and not b.startswith("BEYAN") and len(c) >= 15:
                valid.append(r)
        return valid

    def _load_excluded(self):
        data = load_json(GTB_EXCLUDED_FILE, default=[])
        if isinstance(data, list):
            self.excluded = {re.sub(r"[^A-Z0-9]", "", str(x).upper()) for x in data if x}
        else:
            self.excluded = set()
        if self.records:
            self.records = [r for r in self.records if r.get("beyanname_no") not in self.excluded]

    def _save_excluded(self):
        try:
            save_json_atomic(GTB_EXCLUDED_FILE, sorted(self.excluded))
        except Exception as e:
            ops_exception("gtb", "GTB hariç listesi yazılamadı", e)

    def _mark_excluded(self, b_list):
        added = False
        with self.lock:
            for b in b_list:
                clean = re.sub(r"[^A-Z0-9]", "", str(b or "").upper())
                if clean and clean not in self.excluded:
                    self.excluded.add(clean)
                    added = True
        if added:
            self._save_excluded()

    def _unexclude(self, beyanname_no: str):
        clean = re.sub(r"[^A-Z0-9]", "", str(beyanname_no or "").upper())
        with self.lock:
            if clean in self.excluded:
                self.excluded.discard(clean)
                self._cloud_tombstones.discard(clean)
                self._save_excluded()

    def _save_storage(self, sync_cloud: bool = True):
        try:
            save_json_atomic(GTB_STORAGE_PATH, self.records, snapshot_lock=self.lock)
        except Exception as e:
            ops_exception("gtb", "GTB yerel depo yazılamadı", e)
        if sync_cloud:
            self._sync_to_supabase_async()

    def list_tracked(self, only_active: bool = True) -> List[Dict]:
        with self.lock:
            if only_active:
                return [r for r in self.records if r.get("aktif", True)]
            return list(self.records)

    def add_to_tracking(self, beyanname_no: str, dosya_no: str = "—", firma: str = "WH-HANKOOK", ref: str = "—") -> Dict:
        clean_no = re.sub(r"[^A-Z0-9]", "", str(beyanname_no).upper())
        if not clean_no or clean_no.startswith("BEYAN") or len(clean_no) < 15:
            return {"success": False, "error": "Geçersiz beyanname formatı (16 haneli gümrük beyanname no giriniz)."}

        self._unexclude(clean_no)

        with self.lock:
            existing = next((r for r in self.records if r.get("beyanname_no") == clean_no), None)
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

            if existing:
                existing["aktif"] = True
                if dosya_no and dosya_no != "—": existing["dosya_no"] = dosya_no
                if firma and firma != "WH-HANKOOK": existing["firma"] = firma
                if ref and ref != "—": existing["ref"] = ref
                self._save_storage()
                return {"success": True, "record": existing, "updated": True}

            new_rec = {
                "beyanname_no": clean_no,
                "dosya_no": dosya_no,
                "firma": firma,
                "ref": ref,
                "durum": "İzleniyor (İlk Sorgu Bekliyor)",
                "kapandi": False,
                "son_kontrol": "—",
                "degisim_tarihi": now_str,
                "aktif": True
            }
            self.records.insert(0, new_rec)
            self._save_storage()
            return {"success": True, "record": new_rec, "created": True}

    def remove_from_tracking(self, beyanname_no: str) -> bool:
        clean_no = re.sub(r"[^A-Z0-9]", "", str(beyanname_no).upper())
        with self.lock:
            orig_len = len(self.records)
            self.records = [r for r in self.records if r.get("beyanname_no") != clean_no]
            if len(self.records) < orig_len:
                self._save_storage(sync_cloud=False)
                self._mark_excluded([clean_no])
                self._delete_from_supabase_async(clean_no)
                return True
        return False


    def remove_multiple_from_tracking(self, beyanname_list: List[str]) -> int:
        """Birden fazla beyannameyi tek seferde hafızadan siler."""
        clean_set = {re.sub(r"[^A-Z0-9]", "", str(b).upper()) for b in beyanname_list if b}
        removed_count = 0
        with self.lock:
            orig_len = len(self.records)
            self.records = [r for r in self.records if r.get("beyanname_no") not in clean_set]
            removed_count = orig_len - len(self.records)
            if removed_count > 0:
                self._save_storage(sync_cloud=False)
                self._mark_excluded(list(clean_set))
                self._delete_multiple_from_supabase_async(list(clean_set))
        return removed_count

    def clear_all_tracking(self) -> int:
        """Tüm takip havuzunu sıfırlar."""
        with self.lock:
            count = len(self.records)
            gone = [r.get("beyanname_no") for r in self.records if r.get("beyanname_no")]
            self.records = []
            self._save_storage(sync_cloud=False)
        if gone:
            self._mark_excluded(gone)
            self._clear_all_from_supabase_async()
        return count

    def auto_sync_from_evrim_and_excel(self, evrim_records: List[Dict]) -> int:
        """Evrim ve Excel'deki 16 haneli beyannameleri toplu olarak optimize şekilde takip havuzuna aktarır."""
        added_count = 0
        if not evrim_records:
            return 0

        with self.lock:
            existing_map = {r.get("beyanname_no"): r for r in self.records}
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

            for ev in evrim_records:
                beyan = ev.get("beyanname_no") or ev.get("gumruk_beyanname_no")
                clean_no = re.sub(r"[^A-Z0-9]", "", str(beyan or "").upper())
                if clean_no and len(clean_no) >= 15:
                    if clean_no in self.excluded:
                        continue
                    dosya = ev.get("dosya_no") or "—"
                    ref = ev.get("hankook_ref") or ev.get("musteri_referans") or "—"
                    firma = ev.get("yurt_disi_firma") or ev.get("bayi") or "WH-HANKOOK"

                    if clean_no in existing_map:
                        existing = existing_map[clean_no]
                        existing["aktif"] = True
                        if dosya != "—": existing["dosya_no"] = dosya
                        if ref != "—": existing["ref"] = ref
                    else:
                        new_rec = {
                            "beyanname_no": clean_no,
                            "dosya_no": dosya,
                            "firma": firma,
                            "ref": ref,
                            "durum": "İzleniyor (İlk Sorgu Bekliyor)",
                            "kapandi": False,
                            "son_kontrol": "—",
                            "degisim_tarihi": now_str,
                            "aktif": True
                        }
                        self.records.insert(0, new_rec)
                        existing_map[clean_no] = new_rec
                        added_count += 1

            self._save_storage()

        return added_count

    def start_worker(self):
        if self.is_running:
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        print("[INFO] GTB Otonom Beyanname Takip Servisi Başlatıldı (10 Dk Döngü)!")

    def stop_worker(self):
        self.is_running = False

    def _worker_loop(self):
        # Başlangıçta 5 saniye bekle
        time.sleep(5)
        while self.is_running:
            try:
                try:
                    from tools.dogruer_master_suite.service_supervisor import get_supervisor
                    get_supervisor().record_heartbeat("gtb", status="RUNNING", detail="Tarama başladı", inc_cycle=True)
                except Exception:
                    pass
                self.run_full_cycle()
                try:
                    from tools.dogruer_master_suite.service_supervisor import get_supervisor
                    get_supervisor().record_heartbeat("gtb", status="OK", detail="Tarama tamamlandı", inc_cycle=False)
                except Exception:
                    pass
            except Exception as e:
                print(f"[GTB-WORKER-CYCLE-ERROR] {e}")
                try:
                    from tools.dogruer_master_suite.service_supervisor import get_supervisor
                    get_supervisor().record_heartbeat("gtb", status="ERROR", detail=str(e), inc_cycle=False)
                except Exception:
                    pass

            # 10 dakika bekle (1 sn adımlarla çıkış kontrolü)
            for _ in range(self.interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)

    def run_full_cycle(self, on_progress_callback: Optional[Callable] = None) -> Dict:
        """Tüm aktif beyannameleri paralel çalışan (3 iş parçacığı) havuzla yüksek hızda sorgular."""
        if self.is_scanning:
            return {"success": False, "error": "Tarama zaten devam ediyor."}

        self.is_scanning = True
        active_list = self.list_tracked(only_active=True)
        changed_records = []
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        total_items = len(active_list)
        processed_count = 0

        def _query_item_task(rec):
            nonlocal processed_count
            b_no = rec.get("beyanname_no")
            old_status = rec.get("durum", "")
            old_kapandi = rec.get("kapandi", False)

            res = gtb_beyanname_sorgula(b_no)
            chk_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

            with self.lock:
                target = next((r for r in self.records if r.get("beyanname_no") == b_no), None)
                if target:
                    target["son_kontrol"] = chk_time
                    if res.get("success"):
                        new_status = res.get("durum", old_status)
                        new_kapandi = res.get("kapandi", old_kapandi)
                        target["durum"] = new_status
                        target["kapandi"] = new_kapandi

                        # Durum Değişti mi?
                        if (new_kapandi and not old_kapandi) or (new_status != old_status and "İzleniyor" not in old_status):
                            target["degisim_tarihi"] = chk_time
                            changed_records.append(target)
                            self._dispatch_status_alert(target, old_status, new_status)

                processed_count += 1
                cur_c = processed_count

            if on_progress_callback:
                try:
                    on_progress_callback(cur_c, total_items, b_no, res)
                except Exception:
                    pass

            return res

        try:
            from concurrent.futures import ThreadPoolExecutor
            if active_list:
                with ThreadPoolExecutor(max_workers=3) as executor:
                    list(executor.map(_query_item_task, active_list))

            with self.lock:
                self._save_storage()

            self.last_scan_time = now_str

            if self.on_status_change_callback:
                try:
                    self.on_status_change_callback()
                except Exception as e:
                    ops_exception("gtb", "Durum değişim callback hatası", e)

            return {
                "success": True,
                "total_checked": len(active_list),
                "changed_count": len(changed_records),
                "changed_records": changed_records,
                "scan_time": now_str
            }
        finally:
            self.is_scanning = False

    def query_single_now(self, beyanname_no: str) -> Dict:
        """Tek bir beyannameyi anlık sorgular ve veritabanındaki durumunu günceller."""
        clean_no = re.sub(r"[^A-Z0-9]", "", str(beyanname_no).upper())
        res = gtb_beyanname_sorgula(clean_no)
        chk_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        with self.lock:
            target = next((r for r in self.records if r.get("beyanname_no") == clean_no), None)
            if target and res.get("success"):
                old_status = target.get("durum", "")
                new_status = res.get("durum", old_status)
                new_kapandi = res.get("kapandi", False)

                target["son_kontrol"] = chk_time
                target["durum"] = new_status
                target["kapandi"] = new_kapandi
                if new_status != old_status and "İzleniyor" not in old_status:
                    target["degisim_tarihi"] = chk_time
                    self._dispatch_status_alert(target, old_status, new_status)
                self._save_storage()

        return res

    def _dispatch_status_alert(self, record: Dict, old_st: str, new_st: str):
        """Durum değişimini hem Operasyon Günlüğüne kaydeder hem de Telegram'a push basar."""
        b_no = record.get("beyanname_no")
        dosya = record.get("dosya_no") or "—"
        ref = record.get("ref") or "—"
        firma = record.get("firma") or "WH-HANKOOK"

        # 1. Otomatik Aktivite Günlüğüne (SQLite + Supabase) Kaydet
        try:
            from tools.supabase_sync_manager import get_supabase_manager
            sm = get_supabase_manager()
            if sm:
                is_closed = bool(record.get("kapandi"))
                title = f"GTB Statü: {new_st[:45]}"
                desc = f"Eski Durum: {old_st}\nYeni Canlı Durum: {new_st}\nFirma: {firma}"
                tag = "Tamamlandı" if is_closed else "Bilgi"
                sm.add_activity_log(
                    dosya_no=dosya if dosya != "—" else "",
                    ref_no=ref if ref != "—" else "",
                    beyanname_no=b_no,
                    islem_tipi="TESCIL",
                    baslik=title,
                    icerik=desc,
                    etiket=tag,
                    metadata={"old_status": old_st, "new_status": new_st, "firma": firma}
                )
        except Exception as log_err:
            print(f"[GTB-LOG-ERROR] {log_err}")

        # 1.5 Windows Masaüstü Toast Bildirimi Fırlat
        try:
            from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
            dosya_label = f"Dosya: {dosya}" if dosya != "—" else f"Ref: {ref}"
            toast_title = f"🏛️ GTB Tescil & Statü ({dosya_label})"
            toast_msg = f"Beyanname: {b_no}\nYeni Durum: {new_st}"
            send_desktop_notification(toast_title, toast_msg)
        except Exception:
            pass

        if not self.telegram_service:
            return

        badge = "🟢 BEYANNAME KAPANDI / TAMAMLANDI" if record.get("kapandi") else "🔄 GTB STATÜ DEĞİŞİKLİĞİ"
        msg = (
            f"<b>{badge}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📑 <b>Beyanname No:</b> <code>{b_no}</code>\n"
            f"📦 <b>Dosya / Ref:</b> {dosya} | <code>{ref}</code>\n"
            f"🏢 <b>Firma:</b> {firma}\n\n"
            f"📊 <b>Eski Durum:</b> <i>{old_st[:60]}</i>\n"
            f"⚡ <b>Yeni Canlı Durum:</b> <b>{new_st}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 <i>10 Dk Otonom GTB Motoru tarafından tespit edildi.</i>"
        )
        try:
            self.telegram_service.notify_critical_event("GTB BAKANLIK ALARMI", msg)
        except Exception as e:
            print(f"[GTB-ALERT-DISPATCH-ERROR] {e}")


# Singleton instance
_global_gtb_tracker = None

def get_gtb_tracker_service(data_engine=None, telegram_service=None, on_status_change_callback=None):
    global _global_gtb_tracker
    if _global_gtb_tracker is None:
        _global_gtb_tracker = GTBTrackerService(data_engine, telegram_service, on_status_change_callback)
    else:
        if data_engine and not _global_gtb_tracker.data_engine:
            _global_gtb_tracker.data_engine = data_engine
        if telegram_service and not _global_gtb_tracker.telegram_service:
            _global_gtb_tracker.telegram_service = telegram_service
        if on_status_change_callback and not _global_gtb_tracker.on_status_change_callback:
            _global_gtb_tracker.on_status_change_callback = on_status_change_callback
    return _global_gtb_tracker
