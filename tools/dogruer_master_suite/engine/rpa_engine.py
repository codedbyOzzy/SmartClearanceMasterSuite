# -*- coding: utf-8 -*-
"""
Doğruer Master Suite - Otonom RPA Motoru (Evrim Automation Engine)
Evrim Gümrük Yazılımı için 3 Robotlu (Beyanname, Excel Aktarım, PL4) RPA Yürütücü ve Kalibrasyon Motoru.
"""

import os
import sys
import json
import time
import threading
import ctypes
from ctypes import wintypes
from typing import List, Dict, Any, Optional, Callable

import pyautogui
import keyboard
import pyperclip

from tools.dogruer_master_suite.engine.rpa_field_values import (
    DEFAULT_SABIT_DEGERLER,
    queue_item_from_record,
    resolve_beyanname_item_values,
)
from tools.dogruer_master_suite.engine import rpa_win32

rpa_win32.enable_dpi_awareness()

# Köşe failsafe + kısa durak; acil durdurma stop_requested ile kesilir
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03

_AYAR_KLASORU = r"C:\OTONOMAKTARIM_AYARLAR"
os.makedirs(_AYAR_KLASORU, exist_ok=True)

KOOR_BEYANNAME_P1 = os.path.join(_AYAR_KLASORU, "beyanname_koordinatlar.json")
KOOR_BEYANNAME_P2 = os.path.join(_AYAR_KLASORU, "beyanname_koordinatlar_profil2.json")
KOOR_AKTARIM = os.path.join(_AYAR_KLASORU, "aktarim_koordinatlar.json")
KOOR_PL4 = os.path.join(_AYAR_KLASORU, "pl4_koordinatlar.json")

BEYANNAME_ALANLAR = [
    ("dosya_no_ara", "1. Dosya No Ara (Üst menü kutusu)"),
    ("ara_butonu", "2. Ara Butonu"),
    ("degistir_butonu", "3. Değiştir Butonu"),
    ("beyan_4000", "4. 1 Beyan (4000 kutusu)"),
    ("tarife_evet", "5. Tarife Çalıştır -> Evet"),
    ("giris_gumruk", "6. 29 Giriş/Çıkış Gümrük İdaresi (18)"),
    ("fatura_bedeli", "7. 22 Fatura Bedeli (F4)"),
    ("banka_bilgisi", "8. 28 Banka Bilgisi (14661)"),
    ("odeme_sekli", "9. Ödeme Şekli (F4 + 7 ok)"),
    ("odeme_kisa", "10. Ödeme yanı kısa kutu (71)"),
    ("sinirdaki_25", "11. 25 Sınırdaki (10)"),
    ("dahili_26", "12. 26 Dahili (10)"),
    ("t19_kntynr", "13. T19 Kntynr (1)"),
    ("tir_knt_sayisi", "14. Tır-Knt Sayısı (1)"),
    ("teslim_sekli", "15. 20 Teslim Şekli (CIP)"),
    ("teslim_sehri", "16. 20 Teslim Şehri (KOCAELİ)"),
    ("tasit_kimligi", "17. 21 Taşıt Kimliği 1 (GEMİ - Gemi Adı)"),
    ("tasit_kimligi_2", "18. Taşıt Kimliği 2 (GEMİ - Gemi Adı)"),
    ("liman_kutu", "19. Liman kutusu (DP)"),
    ("ek_bilgi_44", "20. 44 Ek Bilgi Notu"),
    ("sayfa_3_sekmesi", "21. Sayfa 3 Sekmesi"),
    ("edi_karne", "22. EDI Karne Sahibi (30)"),
    ("hesapla_sayfasi", "23. Hesapla Butonu"),
    ("diger_kutu", "24. Diğer Giderler (3000)"),
    ("diger_aciklama", "25. Diğer Açıklama (Y.ICI)"),
    ("liman_gider_kutu", "26. Liman Giderleri (5000)"),
    ("liman_gider_aciklama", "27. Liman Gider Açıklama (.)"),
    ("tamam_butonu", "28. Tamam / Kaydet Butonu"),
    ("sayfa_1_sekmesi", "29. Sayfa 1 Sekmesine Dön")
]

AKTARIM_ALANLAR = [
    ("aktarimlar_sekmesi", "1) Evrim Menüsünde 'Aktarımlar' Sekmesi"),
    ("excelden_beyan_menu", "2) Açılan Listede 'Excelden Beyannameye Aktar'"),
    ("excel_dosya_kutusu", "3) Sarı Excel Dosyası Yolu Kutusu"),
    ("doviz_kutusu", "4) Döviz Kutusu (TL)"),
    ("atr_kutusu", "5) ATR Kutusu (KORE)"),
    ("alici_kutusu", "6) Alıcı Kutusu (9122)"),
    ("gonderen_kutusu", "7) Gönderen Kutusu"),
    ("kap_marka_kutusu", "8) Kap Marka Kutusu"),
    ("kap_no_kutusu", "9) Kap No Kutusu"),
    ("kap_cinsi_kutusu", "10) Kap Cinsi Kutusu"),
    ("adedi_kutusu", "11) Adedi Kutusu"),
    ("gumruk_kutusu", "12) Gümrük Kutusu (18)"),
    ("aktar_butonu", "13) 'Excel Dosyasına Aktar' Butonu"),
    ("kapat_butonu", "14) Formun X (Kapat) Butonu")
]

PL4_ALANLAR = [
    ("dosya_no_ara", "1) Dosya No Ara Kutusu"),
    ("ara_butonu", "2) Ara Butonu"),
    ("ekle_butonu", "3) Alt Kısımdaki Ekle Butonu"),
    ("bos_kutu", "4) PL4 Yazılacak Boş Kutucuk"),
    ("tamam_butonu", "5) Tamam / Onay Butonu")
]

class RPAEngine:
    """Evrim Otonom RPA Yürütücü ve Kalibrasyon Motoru"""

    def __init__(self):
        self.mode = "SEMI_AUTONOMOUS"  # 'FULL_AUTONOMOUS' veya 'SEMI_AUTONOMOUS'
        self.active_robot = "BEYANNAME"  # 'BEYANNAME', 'AKTARIM', 'PL4'
        self.status = "IDLE"  # 'IDLE', 'RUNNING', 'WAITING_APPROVAL', 'PAUSED', 'STOPPED'
        self.delay = 0.1

        # Kuyruklar
        self.queue: List[Dict[str, Any]] = []
        self.current_index = 0
        self.active_params = dict(DEFAULT_SABIT_DEGERLER)
        self.dry_run = False

        self.stop_requested = False
        self.pause_requested = False
        self.calibrating = False
        self._panic_armed = False
        self._hotkey_stop = False
        self.approval_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.last_evrim_hwnd: Optional[int] = None
        self.last_layout_fp = rpa_win32.display_fingerprint()

        # Koordinat haritaları (Her robot için ayrı)
        self.koor_beyan: Dict[str, Dict[str, int]] = {}
        self.koor_aktarim: Dict[str, Dict[str, int]] = {}
        self.koor_pl4: Dict[str, Dict[str, int]] = {}
        self.active_beyan_profile = "Profil 1 (Ana Ekran)"

        self.load_all_coordinates()

        # Callbacks
        self.on_status_change: Optional[Callable[[str, str], None]] = None
        self.on_queue_update: Optional[Callable[[int, Dict[str, Any]], None]] = None
        self.on_step_progress: Optional[Callable[[str, int, int], None]] = None
        self.on_approval_needed: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_finish: Optional[Callable[[bool, str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None

        # Acil fren: ESC ve F12 yalnızca robot/kalibrasyon açıkken; Ctrl+Alt+F12 her zaman
        try:
            keyboard.on_press_key("esc", lambda _: self._on_panic_key("ESC"))
            keyboard.on_press_key("f12", lambda _: self._on_panic_key("F12"))
        except Exception:
            pass
        threading.Thread(target=self._hotkey_loop, daemon=True).start()

    def log(self, msg: str):
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception:
                pass
        try:
            print(f"[RPAEngine] {msg}")
        except UnicodeEncodeError:
            try:
                clean_msg = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
                print(f"[RPAEngine] {clean_msg}")
            except Exception:
                pass
        except Exception:
            pass

    def _field_map(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out = {}
        for k, v in (data or {}).items():
            if str(k).startswith("_"):
                continue
            if isinstance(v, dict) and ("x" in v or "rx" in v):
                out[k] = v
        return out

    def load_all_coordinates(self):
        """3 robotun tüm koordinat dosyalarını diskten yükler."""
        p_path = KOOR_BEYANNAME_P2 if "2" in self.active_beyan_profile else KOOR_BEYANNAME_P1
        self.koor_beyan = self._field_map(self._read_json(p_path))
        self.koor_aktarim = self._field_map(self._read_json(KOOR_AKTARIM))
        self.koor_pl4 = self._field_map(self._read_json(KOOR_PL4))
        self._warn_if_layout_changed(p_path)

    def _read_json(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[RPAEngine] Okuma hatası ({path}): {e}")
        return {}

    def _save_json(self, path: str, data: Dict[str, Any]):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[RPAEngine] Kaydetme hatası ({path}): {e}")

    def set_beyan_profile(self, profile_name: str):
        self.active_beyan_profile = profile_name
        p_path = KOOR_BEYANNAME_P2 if "2" in profile_name else KOOR_BEYANNAME_P1
        self.koor_beyan = self._field_map(self._read_json(p_path))

    def _warn_if_layout_changed(self, sample_path: str):
        data = self._read_json(sample_path)
        meta = data.get("_meta") if isinstance(data, dict) else None
        saved_fp = (meta or {}).get("fingerprint")
        now_fp = rpa_win32.display_fingerprint()
        if saved_fp and saved_fp != now_fp:
            self.log(
                f"⚠️ Monitör düzeni değişmiş. Kayıt: {saved_fp} | Şimdi: {now_fp}. "
                "Göreli koordinat kullanılacak; isabet kayarsa bir kez F9 kalibrasyonu yenileyin."
            )

    def _dump_coords(self, path: str, fields: Dict[str, Any], hwnd: Optional[int] = None):
        payload = dict(fields)
        win = None
        if hwnd:
            left, top, w, h = rpa_win32.window_rect(hwnd)
            win = {"left": left, "top": top, "w": w, "h": h, "title": rpa_win32.window_title(hwnd)}
        payload["_meta"] = {
            "schema": 2,
            "fingerprint": rpa_win32.display_fingerprint(),
            "window": win,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save_json(path, payload)

    # -------------------------------------------------------------------------
    # Evrim Pencere Odaklama (süreç + başlık; Doğruer başlığını eleme)
    # -------------------------------------------------------------------------
    def find_evrim_window(self) -> Optional[int]:
        hwnd, title, notes = rpa_win32.find_evrim_hwnd()
        for n in notes:
            self.log(n)
        if hwnd:
            self.last_evrim_hwnd = hwnd
            self.log(f"✅ Evrim penceresi bulundu: [{title}]")
            return hwnd
        self.log("❌ Evrim penceresi algılanamadı. İthalat/İhracat (ithalsql/ihrsql) açık olsun.")
        return None

    def probe_evrim(self) -> bool:
        hwnd = self.find_evrim_window()
        if not hwnd:
            return False
        left, top, w, h = rpa_win32.window_rect(hwnd)
        self.log(f"Pencere konumu: {w}x{h} @ ({left},{top}) | Düzen: {rpa_win32.display_fingerprint()}")
        return True

    def focus_and_maximize_evrim(self) -> bool:
        hwnd = self.find_evrim_window()
        if not hwnd:
            return False
        ok = rpa_win32.focus_window(hwnd, maximize=False)
        time.sleep(0.25)
        return ok

    def _arm_panic(self, on: bool):
        self._panic_armed = bool(on)

    def _on_panic_key(self, src: str):
        if self._panic_armed or self.calibrating or self.status in ("RUNNING", "WAITING_APPROVAL", "PAUSED"):
            self.log(f"🚨 Acil fren tuşu: {src}")
            self.trigger_emergency_stop()

    def _hotkey_loop(self):
        """Ctrl+Alt+F12 — klavye kancası düşse bile Windows hotkey ile durur."""
        user32 = ctypes.windll.user32
        MOD_ALT, MOD_CONTROL = 0x0001, 0x0002
        VK_F12 = 0x7B
        try:
            if not user32.RegisterHotKey(None, 7711, MOD_ALT | MOD_CONTROL, VK_F12):
                return
        except Exception:
            return
        msg = wintypes.MSG()
        try:
            while not self._hotkey_stop:
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312:
                        self.log("🚨 Acil fren tuşu: Ctrl+Alt+F12")
                        self.trigger_emergency_stop()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.04)
        finally:
            try:
                user32.UnregisterHotKey(None, 7711)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Tıklama ve Yazma Temel Fonksiyonları
    # -------------------------------------------------------------------------
    def click_coord(self, koor_dict: Dict[str, Any], alan_adi: str, cift: bool = False, factor: float = 1.0) -> bool:
        if self.stop_requested:
            return False

        pt = koor_dict.get(alan_adi)
        if not pt or not isinstance(pt, dict):
            self.log(f"⚠️ Koordinat eksik: {alan_adi}")
            return False

        hwnd = self.last_evrim_hwnd or self.find_evrim_window()
        resolved = rpa_win32.resolve_point(hwnd, pt)
        if not resolved:
            self.log(f"⚠️ Koordinat çözülemedi: {alan_adi}")
            return False
        x, y = resolved

        if hwnd and not rpa_win32.point_inside_window(hwnd, x, y, margin=24):
            self.log(
                f"⚠️ {alan_adi} Evrim penceresinin dışında ({x},{y}). "
                "Monitör düzeni kaymış olabilir — kalibrasyonu yenileyin."
            )
            return False

        try:
            pyautogui.moveTo(x, y, duration=0.07)
            if self.stop_requested:
                return False
            if self.dry_run and alan_adi in ("tamam_butonu", "aktar_butonu"):
                self.log(f"[TEST] {alan_adi} tıklanmadı (kaydet/aktar atlandı).")
                return True
            if cift:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.click(x, y)
            time.sleep(self.delay * factor)
            return True
        except pyautogui.FailSafeException:
            self.trigger_emergency_stop()
            return False
        except Exception as e:
            self.log(f"Tıklama hatası ({alan_adi}): {e}")
            return False

    def write_text(self, text: str, clear_first: bool = True):
        if self.stop_requested:
            return
        if self.dry_run:
            self.log("[TEST] yazılmayacak: %s" % str(text)[:120])
            return
        if clear_first:
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.04)

        pyperclip.copy(str(text))
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(self.delay)

    # -------------------------------------------------------------------------
    # KALİBRASYON SİHİRBAZLARI (Her Robot İçin F9 ile Alan Tanıma)
    # -------------------------------------------------------------------------
    def run_calibration_wizard(self, robot_type: str, callback_step: Callable[[str, int, int], None], callback_done: Callable[[bool], None]):
        """Belirtilen robot için arka planda adım adım F9 kalibrasyonu çalıştırır."""
        def _worker():
            if robot_type == "BEYANNAME":
                alanlar = BEYANNAME_ALANLAR
                p_path = KOOR_BEYANNAME_P2 if "2" in self.active_beyan_profile else KOOR_BEYANNAME_P1
                target_dict = self.koor_beyan
            elif robot_type == "AKTARIM":
                alanlar = AKTARIM_ALANLAR
                p_path = KOOR_AKTARIM
                target_dict = self.koor_aktarim
            else:
                alanlar = PL4_ALANLAR
                p_path = KOOR_PL4
                target_dict = self.koor_pl4

            self.log(f"\n🎯 [{robot_type}] Kalibrasyonu Başlatıldı.")
            self.log("Evrim açık kalsın (zorla tam ekran yapılmaz). İmleci kutuya götürüp [F9]. İptal: [ESC].\n")

            hwnd = self.find_evrim_window()
            if hwnd:
                rpa_win32.focus_window(hwnd, maximize=False)
            else:
                self.log("Uyarı: Evrim henüz algılanamadı; F9 yine kaydeder ama göreli koordinat zayıf kalır.")

            time.sleep(0.8)
            total = len(alanlar)

            for idx, (alan_id, alan_adi) in enumerate(alanlar, 1):
                if self.stop_requested:
                    self.log("Kalibrasyon durduruldu.")
                    callback_done(False)
                    return

                if callback_step:
                    callback_step(alan_adi, idx, total)
                self.log(f"[{idx}/{total}] 📍 Gösterin: {alan_adi} -> [F9] bekliyor...")

                sonuc = [None]
                iptal = [False]

                def _f9():
                    sonuc[0] = pyautogui.position()

                def _esc():
                    iptal[0] = True

                f9_h = keyboard.on_press_key("f9", lambda _: _f9())
                esc_h = keyboard.on_press_key("esc", lambda _: _esc())

                while sonuc[0] is None and not iptal[0] and not self.stop_requested:
                    time.sleep(0.04)

                keyboard.unhook(f9_h)
                keyboard.unhook(esc_h)

                if iptal[0] or self.stop_requested:
                    self.log("❌ Kalibrasyon kullanıcı tarafından iptal edildi.")
                    callback_done(False)
                    return

                pt = sonuc[0]
                hwnd = self.last_evrim_hwnd or self.find_evrim_window()
                rec = rpa_win32.capture_point(hwnd, int(pt.x), int(pt.y))
                target_dict[alan_id] = rec
                self._dump_coords(p_path, target_dict, hwnd)
                extra = f" göreli=({rec.get('rx')}, {rec.get('ry')})" if rec.get("rx") is not None else ""
                self.log(f"   ✅ Kaydedildi: {alan_id} -> ({rec['x']}, {rec['y']}){extra}")
                time.sleep(0.2)

            self.log(f"🎉 [{robot_type}] Kalibrasyonu Eksiksiz Tamamlandı (pencere-göreli).")
            callback_done(True)

        self.stop_requested = False
        self.calibrating = True
        self._arm_panic(True)

        def _wrap():
            try:
                _worker()
            finally:
                self.calibrating = False
                self._arm_panic(False)

        threading.Thread(target=_wrap, daemon=True).start()

    def test_robot_coordinates(self, robot_type: str, callback_done: Callable[[bool], None]):
        """Koordinatları fareyle gezerek ekranda görsel olarak test eder."""
        def _worker():
            if not self.focus_and_maximize_evrim():
                self.log("Evrim penceresi bulunamadı!")
                callback_done(False)
                return

            if robot_type == "BEYANNAME":
                alanlar = BEYANNAME_ALANLAR
                target_dict = self.koor_beyan
            elif robot_type == "AKTARIM":
                alanlar = AKTARIM_ALANLAR
                target_dict = self.koor_aktarim
            else:
                alanlar = PL4_ALANLAR
                target_dict = self.koor_pl4

            self.log(f"👀 [{robot_type}] Koordinat Testi Başlıyor (ESC ile durdurabilirsiniz)...")
            time.sleep(1)

            for idx, (alan_id, alan_adi) in enumerate(alanlar, 1):
                if self.stop_requested:
                    break
                pt = target_dict.get(alan_id)
                resolved = rpa_win32.resolve_point(self.last_evrim_hwnd, pt) if pt else None
                if resolved:
                    x, y = resolved
                    self.log(f"[{idx}/{len(alanlar)}] -> {alan_adi} ({x}, {y})")
                    pyautogui.moveTo(x, y, duration=0.22)
                    time.sleep(0.25)

            self.log("Koordinat testi bitti.")
            callback_done(True)

        self.stop_requested = False
        self._arm_panic(True)

        def _wrap():
            try:
                _worker()
            finally:
                self._arm_panic(False)

        threading.Thread(target=_wrap, daemon=True).start()

    # -------------------------------------------------------------------------
    # 1. BEYANNAME DOLDURMA ROBOTU
    # -------------------------------------------------------------------------
    def set_queue(self, dosya_listesi: List[Dict[str, Any]]):
        self.queue = []
        fb_gemi = self.active_params.get("tasit_kimligi", "")
        for idx, item in enumerate(dosya_listesi):
            row = queue_item_from_record(item, fallback_gemi=fb_gemi)
            row["index"] = idx
            row["status"] = "BEKLIYOR"
            row["message"] = ""
            self.queue.append(row)
        self.current_index = 0

    def update_remaining_params(self, new_params: Dict[str, Any]):
        self.active_params.update(new_params)
        for i in range(self.current_index, len(self.queue)):
            if "tasit_kimligi" in new_params and new_params["tasit_kimligi"]:
                self.queue[i]["gemi"] = new_params["tasit_kimligi"]

    def start_beyanname_process(self, start_index: Optional[int] = None, dry_run: Optional[bool] = None):
        if self.status == "RUNNING":
            return
        if start_index is not None:
            self.current_index = start_index
        if dry_run is not None:
            self.dry_run = bool(dry_run)

        self.active_robot = "BEYANNAME"
        self.stop_requested = False
        self.pause_requested = False
        self.approval_event.clear()
        self.status = "RUNNING"
        self._arm_panic(True)

        if self.on_status_change:
            self.on_status_change(self.status, f"Beyanname Robotu Başlatıldı ({len(self.queue)} dosya)")

        self.worker_thread = threading.Thread(target=self._run_beyanname_loop, daemon=True)
        self.worker_thread.start()

    def _run_beyanname_loop(self):
        if not self.focus_and_maximize_evrim():
            self.status = "ERROR"
            self._arm_panic(False)
            if self.on_finish:
                self.on_finish(False, "Evrim penceresi bulunamadı! Lütfen önce Evrim'i açın.")
            return

        total = len(self.queue)
        completed_count = 0

        while self.current_index < total:
            if self.stop_requested:
                break
            if self.pause_requested:
                self.status = "PAUSED"
                if self.on_status_change:
                    self.on_status_change("PAUSED", f"İşlem duraklatıldı ({self.current_index}/{total})")
                return

            item = self.queue[self.current_index]
            dosya_no = item["dosya_no"]
            item["status"] = "YAZILIYOR"
            if self.on_queue_update:
                self.on_queue_update(self.current_index, item)

            success, err_msg = self._process_single_beyanname(dosya_no, item)

            if self.stop_requested:
                item["status"] = "DURDURULDU"
                item["message"] = "Acil fren ile durduruldu"
                if self.on_queue_update:
                    self.on_queue_update(self.current_index, item)
                break

            if not success:
                item["status"] = "HATA"
                item["message"] = err_msg
                if self.on_queue_update:
                    self.on_queue_update(self.current_index, item)
                self.status = "PAUSED"
                if self.on_status_change:
                    self.on_status_change("PAUSED", f"Hata: {err_msg}")
                return

            if self.mode == "SEMI_AUTONOMOUS" and (self.current_index < total - 1):
                self.status = "WAITING_APPROVAL"
                item["status"] = "ONAY_BEKLIYOR"
                if self.on_queue_update:
                    self.on_queue_update(self.current_index, item)
                if self.on_status_change:
                    self.on_status_change("WAITING_APPROVAL", f"{dosya_no} dolduruldu. Onay bekleniyor (Space/Enter)...")
                if self.on_approval_needed:
                    self.on_approval_needed(item)

                self.approval_event.wait()
                self.approval_event.clear()

                if self.stop_requested:
                    break

            item["status"] = "TAMAMLANDI"
            item["message"] = "Başarıyla dolduruldu"
            completed_count += 1
            if self.on_queue_update:
                self.on_queue_update(self.current_index, item)

            self.current_index += 1
            time.sleep(0.4)

        if self.stop_requested:
            self.status = "STOPPED"
            self._arm_panic(False)
            if self.on_finish:
                self.on_finish(False, f"İşlem durduruldu ({completed_count}/{total} bitti).")
        else:
            self.status = "IDLE"
            self._arm_panic(False)
            if self.on_finish:
                msg = f"Tüm dosyalar ({completed_count}/{total}) Evrim'e başarıyla yazıldı! 🎉"
                if self.dry_run:
                    msg = f"Test modu: {completed_count}/{total} dosya gezildi, Evrim'e yazılmadı."
                self.on_finish(True, msg)

    def _process_single_beyanname(self, dosya_no: str, item: Dict[str, Any]) -> (bool, str):
        vals = resolve_beyanname_item_values(item, self.active_params)
        gemi_adi = vals["gemi"]
        kd = self.koor_beyan

        if self.dry_run:
            self.log(
                "[TEST] %s | gemi=%s | liman=%s | fatura=%s | diğer=%s | liman gider=%s"
                % (dosya_no, gemi_adi, vals["liman_kutu"], vals["fatura_bedeli"], vals["diger_tutar"], vals["liman_gider_tutar"])
            )
            item["message"] = "Test: yazılmadı / Tamam basılmadı"
            return True, ""

        steps = [
            ("dosya_no_ara", lambda: self.write_text(dosya_no)),
            ("ara_butonu", lambda: time.sleep(0.4)),
            ("degistir_butonu", lambda: time.sleep(0.3)),
            ("beyan_4000", lambda: self.write_text(vals["beyan_4000"])),
            ("tarife_evet", lambda: time.sleep(0.3)),
            ("giris_gumruk", lambda: self.write_text(vals["giris_gumruk"])),
            ("fatura_bedeli", lambda: (pyautogui.press('f4'), time.sleep(0.2))),
            ("banka_bilgisi", lambda: self.write_text(vals["banka_bilgisi"])),
            ("odeme_sekli", lambda: (pyautogui.press('f4'), time.sleep(0.1), [pyautogui.press('down') for _ in range(7)], pyautogui.press('enter'))),
            ("odeme_kisa", lambda: self.write_text(vals["odeme_kisa"])),
            ("sinirdaki_25", lambda: self.write_text(vals["sinirdaki_25"])),
            ("dahili_26", lambda: self.write_text(vals["dahili_26"])),
            ("t19_kntynr", lambda: self.write_text(vals["t19_kntynr"])),
            ("tir_knt_sayisi", lambda: self.write_text(vals["tir_knt_sayisi"])),
            ("teslim_sekli", lambda: self.write_text(vals["teslim_sekli"])),
            ("teslim_sehri", lambda: self.write_text(vals["teslim_sehri"])),
            ("tasit_kimligi", lambda: self.write_text(f"GEMİ - {gemi_adi}")),
            ("tasit_kimligi_2", lambda: self.write_text(f"GEMİ - {gemi_adi}")),
            ("liman_kutu", lambda: self.write_text(vals["liman_kutu"])),
            ("ek_bilgi_44", lambda: self.write_text(vals["ek_bilgi_metin"], clear_first=False)),
            ("sayfa_3_sekmesi", lambda: time.sleep(0.3)),
            ("edi_karne", lambda: self.write_text(vals["edi_karne"])),
            ("hesapla_sayfasi", lambda: time.sleep(0.3)),
            ("diger_kutu", lambda: self.write_text(vals["diger_tutar"])),
            ("diger_aciklama", lambda: self.write_text(vals["diger_aciklama_metin"])),
            ("liman_gider_kutu", lambda: self.write_text(vals["liman_gider_tutar"])),
            ("liman_gider_aciklama", lambda: self.write_text(vals["liman_gider_aciklama_metin"])),
            ("tamam_butonu", lambda: time.sleep(0.4)),
            ("sayfa_1_sekmesi", lambda: time.sleep(0.3)),
        ]

        total_steps = len(steps)
        for idx, (alan_adi, action_fn) in enumerate(steps, 1):
            if self.stop_requested:
                return False, "Kullanıcı durdurdu"
            if self.on_step_progress:
                self.on_step_progress(alan_adi, idx, total_steps)
            if not self.click_coord(kd, alan_adi):
                return False, f"Koordinata tıklanamadı: {alan_adi}"
            try:
                action_fn()
            except Exception as e:
                return False, f"İşlem hatası ({alan_adi}): {e}"
            time.sleep(self.delay)

        return True, ""

    # -------------------------------------------------------------------------
    # 2. EXCEL AKTARIM ROBOTU (otonom_aktarim.py & arayüz mantığı)
    # -------------------------------------------------------------------------
    def start_aktarim_process(self, excel_dosyalari: List[str], test_modu: bool = False, f8_bekle: bool = True):
        """Excel dosyalarını sırayla Evrim'e aktarır."""
        if self.status == "RUNNING":
            return

        self.active_robot = "AKTARIM"
        self.stop_requested = False
        self.pause_requested = False
        self.status = "RUNNING"
        self._arm_panic(True)

        def _worker():
            if not self.focus_and_maximize_evrim():
                self.status = "ERROR"
                self._arm_panic(False)
                if self.on_finish:
                    self.on_finish(False, "Evrim penceresi bulunamadı!")
                return

            kd = self.koor_aktarim
            total = len(excel_dosyalari)
            self.log(f"📊 Excel Aktarım Robotu Başlatıldı. Toplam: {total} Dosya.")

            for idx, dosya_yolu in enumerate(excel_dosyalari, 1):
                if self.stop_requested:
                    break

                dosya_adi = os.path.basename(dosya_yolu)
                self.log(f"\n[{idx}/{total}] Sıradaki Dosya: {dosya_adi}")

                if f8_bekle:
                    self.log("   👉 Evrim sarı kutuya tıklayın ve hazır olunca [ F8 ] tuşuna basın...")
                    f8_basildi = [False]
                    h = keyboard.on_press_key("f8", lambda _: f8_basildi.__setitem__(0, True))
                    while not f8_basildi[0] and not self.stop_requested:
                        time.sleep(0.05)
                    keyboard.unhook(h)
                    if self.stop_requested:
                        break
                    time.sleep(0.2)

                # 1. Dosya yolu yapıştır
                self.click_coord(kd, "excel_dosya_kutusu", cift=True)
                self.write_text(dosya_yolu)
                time.sleep(0.2)

                # 2. Döviz (TL)
                self.click_coord(kd, "doviz_kutusu")
                self.write_text("TL")

                # 3. ATR (KORE)
                self.click_coord(kd, "atr_kutusu")
                self.write_text("KORE")

                # 4. Alıcı (9122)
                self.click_coord(kd, "alici_kutusu")
                self.write_text("9122")

                # 5. Gümrük (18)
                self.click_coord(kd, "gumruk_kutusu")
                self.write_text("18")

                # 6. Aktar butonu
                if not test_modu:
                    self.click_coord(kd, "aktar_butonu")
                    self.log(f"   ✅ {dosya_adi} Evrim'e aktarıldı!")
                else:
                    self.log(f"   [TEST MODU] {dosya_adi} formları dolduruldu, 'Aktar' basılmadı.")

                time.sleep(0.5)

            self.status = "IDLE"
            self._arm_panic(False)
            if self.on_finish:
                self.on_finish(True, "Excel aktarımı tamamlandı!")

        self.worker_thread = threading.Thread(target=_worker, daemon=True)
        self.worker_thread.start()

    # -------------------------------------------------------------------------
    # 3. TOPLU PL4 EKLEME ROBOTU (pl4_otonom_arayuz.py mantığı)
    # -------------------------------------------------------------------------
    def start_pl4_process(self, dosya_no_listesi: List[str], test_modu: bool = False):
        """Verilen dosya numaralarına Evrim'de PL4 ön izin kodunu seri ekler."""
        if self.status == "RUNNING":
            return

        self.active_robot = "PL4"
        self.stop_requested = False
        self.status = "RUNNING"
        self.dry_run = bool(test_modu)
        self._arm_panic(True)

        def _worker():
            if not self.focus_and_maximize_evrim():
                self.status = "ERROR"
                self._arm_panic(False)
                if self.on_finish:
                    self.on_finish(False, "Evrim penceresi bulunamadı!")
                return

            kd = self.koor_pl4
            total = len(dosya_no_listesi)
            self.log(f"🏷️ Toplu PL4 Robotu Başlatıldı. Toplam: {total} Dosya.")

            for idx, dosya_no in enumerate(dosya_no_listesi, 1):
                if self.stop_requested:
                    break

                if self.dry_run:
                    self.log(f"[TEST] [{idx}/{total}] {dosya_no} — PL4 yazılmayacak, Tamam basılmayacak.")
                    continue

                self.log(f"[{idx}/{total}] Dosya: {dosya_no} -> PL4 ekleniyor...")
                # 1. Dosya No Ara
                self.click_coord(kd, "dosya_no_ara")
                self.write_text(dosya_no)
                time.sleep(0.2)

                # 2. Ara Butonu
                self.click_coord(kd, "ara_butonu")
                time.sleep(0.4)

                # 3. Ekle Butonu
                self.click_coord(kd, "ekle_butonu")
                time.sleep(0.3)

                # 4. Boş Kutucuk (PL4 yaz)
                self.click_coord(kd, "bos_kutu")
                self.write_text("PL4")
                time.sleep(0.2)

                # 5. Tamam Butonu
                self.click_coord(kd, "tamam_butonu")
                time.sleep(0.4)

                self.log(f"   ✅ {dosya_no} için PL4 kaydedildi.")

            self.status = "IDLE"
            self._arm_panic(False)
            if self.on_finish:
                if self.dry_run:
                    self.on_finish(True, f"Test modu: {total} dosya listelendi, PL4 yazılmadı.")
                else:
                    self.on_finish(True, f"{total} dosya için PL4 ekleme işlemi tamamlandı!")

        self.worker_thread = threading.Thread(target=_worker, daemon=True)
        self.worker_thread.start()

    # -------------------------------------------------------------------------
    # Duraklatma, Onay & Acil Fren
    # -------------------------------------------------------------------------
    def approve_and_continue(self):
        self.approval_event.set()

    def pause(self):
        self.pause_requested = True

    def resume(self):
        if self.status in ("PAUSED", "STOPPED"):
            if self.active_robot == "BEYANNAME":
                self.start_beyanname_process(self.current_index)

    def trigger_emergency_stop(self):
        self.stop_requested = True
        self.pause_requested = True
        self.calibrating = False
        self._arm_panic(False)
        self.approval_event.set()

        try:
            pyautogui.mouseUp()
        except Exception:
            pass
        try:
            for key in ["ctrl", "alt", "shift", "tab", "enter", "space", "f4", "f8", "f9", "f12"]:
                pyautogui.keyUp(key)
        except Exception:
            pass

        self.status = "STOPPED"
        if self.on_status_change:
            try:
                self.on_status_change("STOPPED", "🚨 ACİL DURUM FRENİ: Robot donduruldu (ESC / F12 / Ctrl+Alt+F12).")
            except Exception:
                pass
