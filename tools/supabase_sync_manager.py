"""
tools/supabase_sync_manager.py
==============================
Doğruer MasterSuite - Supabase Canlı Senkronizasyon & Çoklu Kullanıcı Köprüsü
URL ve anon anahtar secrets.json / ortam değişkeninden okunur.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import threading
import datetime
import sqlite3
from typing import Dict, List, Any, Optional

try:
    from tools.secrets_store import get_secret
except Exception:
    try:
        from secrets_store import get_secret
    except Exception:
        get_secret = lambda name, default="": default

SUPABASE_URL = get_secret("supabase_url", "")
SUPABASE_KEY = get_secret("supabase_anon_key", "")
REST_URL = f"{SUPABASE_URL}/rest/v1"


def plan_hankook_board_writes(payload, remote_rows):
    """UNIQUE(referans) yoksa: mevcut id'ye PATCH, yeni satıra INSERT, çiftleri ayıkla."""
    by_ref = {}
    dup_ids = []
    for rem in remote_rows or []:
        ref = rem.get("referans")
        rid = rem.get("id")
        if not ref or rid is None:
            continue
        rid_s = str(rid)
        if ref in by_ref:
            try:
                keep, other = (rid_s, by_ref[ref]) if int(rid) > int(by_ref[ref]) else (by_ref[ref], rid_s)
            except (TypeError, ValueError):
                keep, other = by_ref[ref], rid_s
            by_ref[ref] = keep
            if other not in dup_ids:
                dup_ids.append(other)
        else:
            by_ref[ref] = rid_s

    patches = []
    inserts = []
    for row in payload or []:
        ref = row.get("referans")
        if not ref:
            continue
        existing = by_ref.get(ref)
        if existing:
            patches.append((existing, row))
        else:
            inserts.append(row)
            by_ref[ref] = None
    return patches, inserts, dup_ids


class SupabaseSyncManager:
    def delete_gtb_record(self, beyanname_no: str) -> bool:
        clean_no = (beyanname_no or "").strip().upper()
        res = self._request("DELETE", f"ms_gtb_takip?beyanname_no=eq.{urllib.parse.quote(clean_no)}")
        return res is not None

    def delete_gtb_multiple(self, beyanname_list: list) -> bool:
        clean_list = [b.strip().upper() for b in beyanname_list if b]
        if not clean_list: return True
        in_query = f"in.({','.join(clean_list)})"
        res = self._request("DELETE", f"ms_gtb_takip?beyanname_no={in_query}")
        return res is not None

    def clear_all_gtb(self) -> bool:
        res = self._request("DELETE", "ms_gtb_takip?id=gt.0")
        return res is not None

    def delete_kantar_record(self, konteyner_no: str) -> bool:
        clean_no = (konteyner_no or "").strip().upper()
        res = self._request("DELETE", f"ms_kantar_takip?konteyner_no=eq.{urllib.parse.quote(clean_no)}")
        return res is not None

    def delete_kantar_multiple(self, cntr_list: list) -> bool:
        clean_list = [c.strip().upper() for c in cntr_list if c]
        if not clean_list: return True
        in_query = "in.(" + ",".join(f'"{c}"' for c in clean_list) + ")"
        res = self._request("DELETE", f"ms_kantar_takip?konteyner_no={in_query}")
        return res is not None

    def clear_all_kantar(self) -> bool:
        res = self._request("DELETE", "ms_kantar_takip?id=gt.0")
        return res is not None

    """MasterSuite için hafif ve güvenilir Supabase REST & Senkronizasyon İstemcisi."""
    
    def __init__(self, url: str = None, key: str = None):
        self.url = (url or get_secret("supabase_url", "")).rstrip("/")
        self.key = key or get_secret("supabase_anon_key", "")
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates"
        }
        self.current_user = os.environ.get("USERNAME", "Bilinmeyen Kullanici")
        self._lock = threading.Lock()
        
        # Yerel SQLite Aktivite & Not Veritabanı
        db_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
        os.makedirs(db_dir, exist_ok=True)
        self.sqlite_path = os.path.join(db_dir, "activity_notes.db")
        self._init_sqlite()
        
        # Başlangıçta Supabase senkronizasyonunu tetikle
        self.sync_activity_logs()

    def _request(self, method: str, endpoint: str, data: Optional[Any] = None, extra_headers: Optional[Dict] = None) -> Optional[Any]:
        url = f"{self.rest_url}/{endpoint}"
        headers = self.headers.copy()
        if extra_headers:
            headers.update(extra_headers)

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    resp_data = resp.read().decode("utf-8")
                    if resp_data:
                        return json.loads(resp_data)
                    return True
            except urllib.error.HTTPError as e:
                if e.code == 206:
                    try:
                        resp_data = e.read().decode("utf-8")
                        return json.loads(resp_data) if resp_data else True
                    except Exception:
                        return None
                # Geçici sunucu/ağ gecikmeleri (429, 502, 503, 504) için bekle ve tekrar dene
                if e.code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                err_msg = e.read().decode("utf-8", errors="ignore")
                try:
                    from tools.ops_log import error as ops_error
                    ops_error("supabase", f"{method} {endpoint} -> {e.code}: {err_msg[:300]}")
                except Exception:
                    pass
                return None
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                try:
                    from tools.ops_log import exception as ops_exception
                    ops_exception("supabase", f"{method} {endpoint}", e)
                except Exception:
                    pass
                return None
        return None

    def fetch_all_rows(self, table: str, order: str = "updated_at.desc", page_size: int = 1000, max_rows: int = 20000) -> List[Dict[str, Any]]:
        """PostgREST varsayılan 1000 satır tavanını aşmak için Range ile çeker."""
        rows: List[Dict[str, Any]] = []
        offset = 0
        while offset < max_rows:
            last = offset + page_size - 1
            chunk = self._request(
                "GET",
                f"{table}?select=*&order={order}",
                extra_headers={"Range": f"{offset}-{last}", "Range-Unit": "items"},
            )
            if not isinstance(chunk, list) or not chunk:
                if offset == 0:
                    fallback = self._request("GET", f"{table}?select=*&order={order}")
                    return fallback if isinstance(fallback, list) else []
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            offset += page_size
        return rows

    def tombstone_kantar(self, cntr_list: list) -> bool:
        from tools.cloud_sync import TOMBSTONE
        keys = [(c or "").strip().upper() for c in cntr_list if c]
        if not keys:
            return True
        payload = [{"konteyner_no": k, "durum": TOMBSTONE, "kaynak": "tombstone"} for k in keys]
        return self.upsert_kantar_records(payload)

    def tombstone_gtb(self, beyanname_list: list) -> bool:
        from tools.cloud_sync import TOMBSTONE
        keys = [(b or "").strip().upper() for b in beyanname_list if b]
        if not keys:
            return True
        payload = [{"beyanname_no": k, "gtb_durum": TOMBSTONE, "hat": ""} for k in keys]
        return self.upsert_gtb_records(payload)

    # ── KANTAR & DBA SENKRONİZASYONU ──────────────────────────────────────────
    def upsert_kantar_record(self, item: Dict[str, Any]) -> bool:
        """Kantar takibindeki bir konteyneri Supabase'e kaydeder / günceller."""
        payload = {
            "konteyner_no": (item.get("konteyner_no") or "").strip().upper(),
            "dosya_no": item.get("dosya_no", ""),
            "firma": item.get("firma", ""),
            "liman": item.get("liman", ""),
            "kilo": str(item.get("kilo", "")),
            "dba_no": item.get("dba_no", ""),
            "tartim_tarihi": item.get("tartim_tarihi", ""),
            "pdf_url": item.get("pdf_url", ""),
            "durum": item.get("durum", "İzleniyor"),
            "kaynak": item.get("kaynak", ""),
            "guncelleyen": self.current_user,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        res = self._request("POST", "ms_kantar_takip?on_conflict=konteyner_no", data=payload)
        return res is not None

    def upsert_kantar_records(self, items: List[Dict[str, Any]]) -> bool:
        if not items:
            return True
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = []
        for item in items:
            payload.append({
                "konteyner_no": (item.get("konteyner_no") or "").strip().upper(),
                "dosya_no": item.get("dosya_no", ""),
                "firma": item.get("firma", ""),
                "liman": item.get("liman", ""),
                "kilo": str(item.get("kilo", "")),
                "dba_no": item.get("dba_no", ""),
                "tartim_tarihi": item.get("tartim_tarihi", ""),
                "pdf_url": item.get("pdf_url", ""),
                "durum": item.get("durum", "İzleniyor"),
                "kaynak": item.get("kaynak", ""),
                "guncelleyen": self.current_user,
                "updated_at": now,
            })
        res = self._request("POST", "ms_kantar_takip?on_conflict=konteyner_no", data=payload)
        return res is not None

    def fetch_all_kantar(self) -> List[Dict[str, Any]]:
        return self.fetch_all_rows("ms_kantar_takip")

    # ── GTB BAKANLIK BEYANNAME SENKRONİZASYONU ─────────────────────────────────
    def upsert_gtb_record(self, item: Dict[str, Any]) -> bool:
        """Beyanname takip kaydını Supabase'e kaydeder / günceller."""
        payload = {
            "beyanname_no": (item.get("beyanname_no") or "").strip().upper(),
            "dosya_no": item.get("dosya_no", ""),
            "ref_no": item.get("ref_no", ""),
            "firma": item.get("firma", ""),
            "gtb_durum": item.get("gtb_durum", item.get("durum", "İzleniyor")),
            "hat": item.get("hat", ""),
            "son_sorgu_zamani": item.get("son_sorgu_zamani", ""),
            "guncelleyen": self.current_user,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        res = self._request("POST", "ms_gtb_takip?on_conflict=beyanname_no", data=payload)
        return res is not None

    def upsert_gtb_records(self, items: List[Dict[str, Any]]) -> bool:
        if not items:
            return True
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = []
        for item in items:
            bno = (item.get("beyanname_no") or "").strip().upper()
            if not bno:
                continue
            payload.append({
                "beyanname_no": bno,
                "dosya_no": item.get("dosya_no", ""),
                "ref_no": item.get("ref_no", ""),
                "firma": item.get("firma", ""),
                "gtb_durum": item.get("gtb_durum", item.get("durum", "İzleniyor")),
                "hat": item.get("hat", ""),
                "son_sorgu_zamani": item.get("son_sorgu_zamani", ""),
                "guncelleyen": self.current_user,
                "updated_at": now,
            })
        if not payload:
            return True
        res = self._request("POST", "ms_gtb_takip?on_conflict=beyanname_no", data=payload)
        return res is not None

    def fetch_all_gtb(self) -> List[Dict[str, Any]]:
        return self.fetch_all_rows("ms_gtb_takip")

    # ── EVRİM MERKEZİ SENKRONİZASYONU ──────────────────────────────────────────
    def upsert_evrim_bulk(self, records: List[Dict[str, Any]]) -> bool:
        """Doğruer Online'dan çekilen tüm Evrim kayıtlarını topluca buluta aktarır."""
        if not records:
            return True
        payload = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for r in records:
            dosya_no = r.get("dosya_no") or r.get("A") or r.get("dosya")
            if dosya_no:
                payload.append({
                    "dosya_no": str(dosya_no).strip(),
                    "data": r,
                    "guncelleyen": self.current_user,
                    "updated_at": now_str
                })
        if payload:
            res = self._request("POST", "ms_evrim_live?on_conflict=dosya_no", data=payload)
            return res is not None
        return True

    def fetch_all_evrim(self) -> Dict[str, Dict[str, Any]]:
        res = self.fetch_all_rows("ms_evrim_live", order="updated_at.desc")
        return {item["dosya_no"]: item["data"] for item in res if isinstance(item, dict) and item.get("dosya_no")}

    # ── CANLI KULLANICI VARLIĞI & DOSYA KİLİDİ (PRESENCE) ───────────────────────
    def heartbeat(self, active_file: str = "", active_tab: str = "") -> bool:
        """Kullanıcının aktif olduğunu ve hangi dosyada çalıştığını bildirir."""
        payload = {
            "user_name": self.current_user,
            "active_file": active_file,
            "active_tab": active_tab,
            "last_seen": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        res = self._request("POST", "ms_presence?on_conflict=user_name", data=payload)
        return res is not None

    def get_active_users(self) -> List[Dict[str, Any]]:
        """Son 2 dakika içinde aktif olan tüm kullanıcıları ve çalıştıkları dosyaları döner."""
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)).isoformat()
        res = self._request("GET", f"ms_presence?last_seen=gte.{cutoff}&order=last_seen.desc")
        return res if isinstance(res, list) else []

    def sync_hankook_board(self, records: List[Dict[str, Any]], prune_missing: bool = True) -> bool:
        """Hankook panosunu satır güncelle/ekle ile yazar; ON CONFLICT (referans) gerektirmez."""
        try:
            payload = []
            incoming_refs = []
            for r in records:
                dosya_no = str(r.get("dosya", "")).strip()
                ref_no = str(r.get("ref", "")).strip()
                combo_ref = f"{dosya_no} / {ref_no}".strip(" /")
                if not combo_ref:
                    continue
                kont_no = str(r.get("konteyner", "")).strip()
                bl_no = str(r.get("bl", "")).strip()
                combo_kont = f"{kont_no} / {bl_no}".strip(" /")
                incoming_refs.append(combo_ref)
                payload.append({
                    "referans": combo_ref,
                    "gemi": str(r.get("gemi", "")),
                    "konteyner": combo_kont,
                    "eta": str(r.get("eta", "")),
                    "statu": str(r.get("stage_title", "İşlemde")),
                    "durum_notu": str(r.get("aciklama", "")),
                })

            remote = self.fetch_all_rows("ms_hankook_board", order="id.desc")
            patches, inserts, dup_ids = plan_hankook_board_writes(payload, remote)
            patch_ok = True
            for rid, row in patches:
                res = self._request(
                    "PATCH",
                    f"ms_hankook_board?id=eq.{urllib.parse.quote(str(rid), safe='')}",
                    data=row,
                    extra_headers={"Prefer": "return=minimal"},
                )
                if res is None:
                    patch_ok = False
            if inserts:
                res = self._request(
                    "POST",
                    "ms_hankook_board",
                    data=inserts,
                    extra_headers={"Prefer": "return=minimal"},
                )
                if res is None:
                    patch_ok = False
            extra_delete = list(dup_ids)
            if prune_missing:
                incoming = set(incoming_refs)
                for rem in remote:
                    ref = rem.get("referans")
                    rid = rem.get("id")
                    if rid is None:
                        continue
                    if ref not in incoming:
                        extra_delete.append(str(rid))
            seen = set()
            stale_ids = []
            for sid in extra_delete:
                if sid in seen:
                    continue
                seen.add(sid)
                stale_ids.append(sid)
            for i in range(0, len(stale_ids), 40):
                chunk = stale_ids[i:i + 40]
                in_q = "in.(" + ",".join(chunk) + ")"
                self._request("DELETE", f"ms_hankook_board?id={in_q}")
            return patch_ok
        except Exception as e:
            print(f"[SupabaseSync] Hankook Board sync hatası: {e}")
            return False

    # ── DOSYA NOTLARI & AKTİVİTE LOGLARI (HİBRİT: SQLITE + SUPABASE) ───────────
    def _init_sqlite(self):
        """Yerel SQLite aktivite log veritabanını başlatır."""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        remote_id INTEGER,
                        dosya_no TEXT,
                        ref_no TEXT,
                        beyanname_no TEXT,
                        islem_tipi TEXT,
                        baslik TEXT,
                        icerik TEXT,
                        kullanici TEXT,
                        etiket TEXT DEFAULT 'Normal',
                        metadata TEXT,
                        created_at TEXT,
                        synced INTEGER DEFAULT 0
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_act_dosya ON activity_logs(dosya_no);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_act_tip ON activity_logs(islem_tipi);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_act_created ON activity_logs(created_at DESC);")
                try:
                    cur.execute("ALTER TABLE activity_logs ADD COLUMN is_deleted INTEGER DEFAULT 0")
                except Exception:
                    pass
                try:
                    cur.execute("ALTER TABLE activity_logs ADD COLUMN deleted_at TEXT")
                except Exception:
                    pass
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS deleted_tombstones (
                        remote_id INTEGER PRIMARY KEY,
                        dosya_no TEXT,
                        deleted_at TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[SupabaseSync] SQLite init hatası: {e}")

    def soft_delete_activity_log(self, log_id: int) -> bool:
        """Kaydı fiziksel olarak silmek yerine is_deleted = 1 yapar (Soft-delete)."""
        try:
            now_str = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE activity_logs SET is_deleted = 1, deleted_at = ?, synced = 0 WHERE id = ?", (now_str, log_id))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"[SupabaseSync] Soft delete error: {e}")
            return False

    def restore_activity_log(self, log_id: int) -> bool:
        """Silinmiş bir notu veya işlemi geri yükler (Restore / Undo)."""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT remote_id FROM activity_logs WHERE id = ?", (log_id,))
                r_row = cur.fetchone()
                if r_row and r_row[0]:
                    cur.execute("DELETE FROM deleted_tombstones WHERE remote_id = ?", (r_row[0],))
                cur.execute("UPDATE activity_logs SET is_deleted = 0, deleted_at = NULL, synced = 0 WHERE id = ?", (log_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"[SupabaseSync] Restore log error: {e}")
            return False

    def empty_trash(self) -> int:
        """Çöp kutusundaki (is_deleted = 1) tüm kayıtları hem yerel SQLite'tan hem de Supabase bulutundan kalıcı olarak temizler."""
        purged_count = 0
        remote_ids = []
        now_str = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                # 1. Uzak Supabase ID'lerini ve dosya no'ları topla
                cur.execute("SELECT remote_id, dosya_no FROM activity_logs WHERE is_deleted = 1 AND remote_id IS NOT NULL")
                rows = cur.fetchall()
                for r_id, d_no in rows:
                    if r_id:
                        remote_ids.append(r_id)
                        cur.execute(
                            "INSERT OR IGNORE INTO deleted_tombstones (remote_id, dosya_no, deleted_at) VALUES (?, ?, ?)",
                            (r_id, d_no, now_str)
                        )

                # 2. Yerel tablodan fiziksel sil
                cur.execute("DELETE FROM activity_logs WHERE is_deleted = 1")
                conn.commit()
                purged_count = cur.rowcount

            # 3. Supabase bulutundan da kalıcı olarak sil
            if remote_ids:
                def _purge_remote(ids_to_del):
                    try:
                        chunk_size = 30
                        for i in range(0, len(ids_to_del), chunk_size):
                            chunk = ids_to_del[i:i + chunk_size]
                            in_expr = f"in.({','.join(str(x) for x in chunk)})"
                            self._request("DELETE", f"ms_activity_logs?id={in_expr}")
                    except Exception as ex:
                        print(f"[SupabaseSync] Empty trash Supabase silme hatası: {ex}")

                threading.Thread(target=_purge_remote, args=(remote_ids,), daemon=True).start()

        except Exception as e:
            print(f"[SupabaseSync] Empty trash error: {e}")
        return purged_count

    def add_activity_log(
        self,
        dosya_no: str,
        ref_no: str = "",
        beyanname_no: str = "",
        islem_tipi: str = "NOT",
        baslik: str = "",
        icerik: str = "",
        etiket: str = "Normal",
        metadata: Optional[Dict] = None,
        kullanici: Optional[str] = None
    ) -> int:
        """Yeni bir dosya notu veya sistem işlem kaydı ekler.
        Önce yerel SQLite'a kaydeder, ardından arka planda Supabase'e iletir.
        """
        user = kullanici or self.current_user
        now_str = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        dosya_clean = (dosya_no or "").strip()
        ref_clean = (ref_no or "").strip()
        beyan_clean = (beyanname_no or "").strip()

        local_id = -1
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO activity_logs (
                        dosya_no, ref_no, beyanname_no, islem_tipi, baslik, icerik,
                        kullanici, etiket, metadata, created_at, is_deleted, synced
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """, (dosya_clean, ref_clean, beyan_clean, islem_tipi, baslik, icerik, user, etiket, meta_str, now_str))
                conn.commit()
                local_id = cur.lastrowid
        except Exception as e:
            print(f"[SupabaseSync] Local log kaydetme hatası: {e}")

        # Arka planda Supabase'e gönder
        def _push():
            payload = {
                "dosya_no": dosya_clean,
                "ref_no": ref_clean,
                "beyanname_no": beyan_clean,
                "islem_tipi": islem_tipi,
                "baslik": baslik,
                "icerik": icerik,
                "kullanici": user,
                "etiket": etiket,
                "metadata": metadata or {},
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            res = self._request("POST", "ms_activity_logs", data=payload)
            if res and local_id > 0:
                try:
                    with sqlite3.connect(self.sqlite_path) as conn:
                        cur = conn.cursor()
                        remote_id = res[0].get("id") if (isinstance(res, list) and res and "id" in res[0]) else None
                        cur.execute("UPDATE activity_logs SET synced = 1, remote_id = ? WHERE id = ?", (remote_id, local_id))
                        conn.commit()
                except Exception:
                    pass

        threading.Thread(target=_push, daemon=True).start()
        return local_id

    def fetch_activity_logs(
        self,
        dosya_no: Optional[str] = None,
        islem_tipi: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: int = 200,
        include_deleted: bool = False,
        only_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Filtrelenmiş aktivite loglarını yerel SQLite'tan anında çeker."""
        query = "SELECT id, remote_id, dosya_no, ref_no, beyanname_no, islem_tipi, baslik, icerik, kullanici, etiket, metadata, created_at, is_deleted, deleted_at, synced FROM activity_logs WHERE 1=1"
        params = []

        if only_deleted:
            query += " AND is_deleted = 1"
        elif not include_deleted:
            query += " AND (is_deleted IS NULL OR is_deleted = 0)"

        if dosya_no:
            query += " AND (dosya_no LIKE ? OR ref_no LIKE ? OR beyanname_no LIKE ?)"
            d_param = f"%{dosya_no.strip()}%"
            params.extend([d_param, d_param, d_param])

        if islem_tipi and islem_tipi.upper() != "TÜMÜ" and islem_tipi.upper() != "TUMU":
            query += " AND islem_tipi = ?"
            params.append(islem_tipi)

        if date_from:
            query += " AND created_at >= ?"
            params.append(f"{date_from} 00:00:00")

        if date_to:
            query += " AND created_at <= ?"
            params.append(f"{date_to} 23:59:59")

        if search_term:
            query += " AND (dosya_no LIKE ? OR ref_no LIKE ? OR beyanname_no LIKE ? OR baslik LIKE ? OR icerik LIKE ? OR kullanici LIKE ?)"
            s_param = f"%{search_term.strip()}%"
            params.extend([s_param, s_param, s_param, s_param, s_param, s_param])

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = []
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append(dict(row))
        except Exception as e:
            print(f"[SupabaseSync] Fetch logs hatası: {e}")
        return results

    def sync_activity_logs(self):
        """Supabase ile çift yönlü senkronizasyon:
        1) Gönderilmemiş yerel kayıtları Supabase'e aktarır.
        2) Supabase'deki yeni uzak kayıtları yerel SQLite'a çeker.
        """
        def _worker():
            # 1. Yerelde gönderilmemişleri gönder
            try:
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM activity_logs WHERE synced = 0 LIMIT 50")
                    unsynced = [dict(r) for r in cur.fetchall()]

                payloads = []
                row_ids = []
                for row in unsynced:
                    meta = {}
                    try:
                        meta = json.loads(row.get("metadata") or "{}")
                    except Exception:
                        pass
                    payloads.append({
                        "dosya_no": row.get("dosya_no", ""),
                        "ref_no": row.get("ref_no", ""),
                        "beyanname_no": row.get("beyanname_no", ""),
                        "islem_tipi": row.get("islem_tipi", "NOT"),
                        "baslik": row.get("baslik", ""),
                        "icerik": row.get("icerik", ""),
                        "kullanici": row.get("kullanici", ""),
                        "etiket": row.get("etiket", "Normal"),
                        "metadata": meta,
                        "created_at": row.get("created_at", "")
                    })
                    row_ids.append(row["id"])

                if payloads:
                    res = self._request("POST", "ms_activity_logs", data=payloads)
                    if res:
                        with sqlite3.connect(self.sqlite_path) as conn:
                            cur = conn.cursor()
                            for i, rid in enumerate(row_ids):
                                rem_id = None
                                if isinstance(res, list) and i < len(res) and isinstance(res[i], dict):
                                    rem_id = res[i].get("id")
                                cur.execute(
                                    "UPDATE activity_logs SET synced = 1, remote_id = ? WHERE id = ?",
                                    (rem_id, rid),
                                )
                            conn.commit()
                    else:
                        for row, payload in zip(unsynced, payloads):
                            one = self._request("POST", "ms_activity_logs", data=payload)
                            if one:
                                rem_id = one[0].get("id") if (isinstance(one, list) and one and "id" in one[0]) else None
                                with sqlite3.connect(self.sqlite_path) as conn:
                                    cur = conn.cursor()
                                    cur.execute(
                                        "UPDATE activity_logs SET synced = 1, remote_id = ? WHERE id = ?",
                                        (rem_id, row["id"]),
                                    )
                                    conn.commit()
            except Exception:
                pass

            # 2. Supabase'deki son kayıtları çekip yerelle eşle
            try:
                remote_logs = self.fetch_all_rows("ms_activity_logs", order="created_at.desc", page_size=200, max_rows=2000)
                if isinstance(remote_logs, list):
                    with sqlite3.connect(self.sqlite_path) as conn:
                        cur = conn.cursor()
                        for rlog in remote_logs:
                            rem_id = rlog.get("id")
                            if not rem_id:
                                continue

                            # Eğer bu kayıt yerelde çöpten kalıcı olarak silinmişse (tombstone), Supabase'e geri alma ve Supabase'den sil
                            cur.execute("SELECT 1 FROM deleted_tombstones WHERE remote_id = ? LIMIT 1", (rem_id,))
                            if cur.fetchone():
                                try:
                                    self._request("DELETE", f"ms_activity_logs?id=eq.{rem_id}")
                                except Exception:
                                    pass
                                continue

                            cur.execute(
                                "SELECT id FROM activity_logs WHERE remote_id = ? OR (dosya_no = ? AND baslik = ? AND created_at = ?) LIMIT 1",
                                (rem_id, rlog.get("dosya_no", ""), rlog.get("baslik", ""), rlog.get("created_at", ""))
                            )
                            existing = cur.fetchone()
                            if existing:
                                cur.execute("UPDATE activity_logs SET remote_id = ?, synced = 1 WHERE id = ? AND (remote_id IS NULL OR remote_id = '')", (rem_id, existing[0]))
                            else:
                                cur.execute("""
                                    INSERT INTO activity_logs (
                                        remote_id, dosya_no, ref_no, beyanname_no, islem_tipi, baslik, icerik, kullanici, etiket, metadata, created_at, is_deleted, synced
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
                                """, (
                                    rem_id,
                                    rlog.get("dosya_no", ""),
                                    rlog.get("ref_no", ""),
                                    rlog.get("beyanname_no", ""),
                                    rlog.get("islem_tipi", "NOT"),
                                    rlog.get("baslik", ""),
                                    rlog.get("icerik", ""),
                                    rlog.get("kullanici", ""),
                                    rlog.get("etiket", "Normal"),
                                    json.dumps(rlog.get("metadata") or {}, ensure_ascii=False),
                                    rlog.get("created_at", "")
                                ))
                        conn.commit()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

# Global Tekil Örnek (Singleton)
_client: Optional[SupabaseSyncManager] = None

def get_supabase_manager() -> SupabaseSyncManager:
    global _client
    if _client is None:
        _client = SupabaseSyncManager()
    return _client
