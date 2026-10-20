# -*- coding: utf-8 -*-
"""
service_supervisor.py — Arka Plan Servisleri Canlılık Nabzı (Heartbeat) ve Bekçi Köpeği (Watchdog)
Takip edilen servisler:
1. GTB Otonom Beyanname Takip Servisi
2. Kantar & DBA Otonom Takip Servisi
3. Telegram Mobil Asistanı
"""
import time
import threading
from datetime import datetime


class ServiceSupervisor:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ServiceSupervisor()
        return cls._instance

    def __init__(self):
        self._lock = threading.Lock()
        self.services = {
            "gtb": {
                "label": "GTB Takip",
                "icon": "🏛️",
                "last_beat": None,
                "status": "RUNNING",
                "cycle_count": 0,
                "detail": "Başlatıldı",
                "instance": None,
                "restart_fn": None,
                "restart_count": 0,
                "expected_interval": 600, # 10 dk
            },
            "kantar": {
                "label": "Kantar & DBA",
                "icon": "⚖️",
                "last_beat": None,
                "status": "RUNNING",
                "cycle_count": 0,
                "detail": "Başlatıldı",
                "instance": None,
                "restart_fn": None,
                "restart_count": 0,
                "expected_interval": 600, # 10 dk
            },
            "telegram": {
                "label": "Telegram Bot",
                "icon": "🤖",
                "last_beat": None,
                "status": "RUNNING",
                "cycle_count": 0,
                "detail": "Aktif",
                "instance": None,
                "restart_fn": None,
                "restart_count": 0,
                "expected_interval": 60,
            }
        }
        self.watchdog_running = False
        self.start_watchdog()

    def register_service(self, service_id, instance=None, restart_fn=None):
        with self._lock:
            if service_id in self.services:
                self.services[service_id]["instance"] = instance
                self.services[service_id]["restart_fn"] = restart_fn
                self.services[service_id]["last_beat"] = time.time()
                self.services[service_id]["status"] = "OK"

    def record_heartbeat(self, service_id, status="OK", detail="", inc_cycle=True):
        with self._lock:
            if service_id in self.services:
                s = self.services[service_id]
                s["last_beat"] = time.time()
                s["status"] = status
                if detail:
                    s["detail"] = detail
                if inc_cycle:
                    s["cycle_count"] += 1

    def get_status_summary(self):
        """
        Durum çubuğu için özet renk ve metin listesi döner.
        """
        summary = []
        now = time.time()
        with self._lock:
            for s_id, s in self.services.items():
                last = s["last_beat"]
                if last is None:
                    color = "#64748b" # gri (henüz döngü yapmadı)
                    txt = f"{s['icon']} {s['label']}: Başlatılıyor..."
                else:
                    diff = int(now - last)
                    mins = diff // 60
                    if mins < 1:
                        time_str = "Az önce"
                    elif mins < 60:
                        time_str = f"{mins} dk önce"
                    else:
                        time_str = f"{mins // 60} sa önce"

                    # Beklenen sürenin 2.5 katı geçtiyse sarı/kırmızıya dön
                    exp = s["expected_interval"]
                    if diff > exp * 2.5:
                        color = "#dc2626" # Kırmızı (Gecikti)
                        icon_led = "🔴"
                    elif diff > exp * 1.5:
                        color = "#d97706" # Sarı (Bekleniyor)
                        icon_led = "🟡"
                    else:
                        color = "#16a34a" # Yeşil (Canlı)
                        icon_led = "🟢"

                    cycle_str = f"(#{s['cycle_count']})" if s['cycle_count'] > 0 else ""
                    txt = f"{icon_led} {s['label']}: {time_str} {cycle_str}".strip()

                summary.append({
                    "id": s_id,
                    "label": s["label"],
                    "icon": s["icon"],
                    "color": color,
                    "text": txt,
                    "detail": s["detail"],
                    "cycles": s["cycle_count"],
                    "restarts": s["restart_count"]
                })
        return summary

    def start_watchdog(self):
        if self.watchdog_running:
            return
        self.watchdog_running = True
        t = threading.Thread(target=self._watchdog_loop, daemon=True, name="SupervisorWatchdog")
        t.start()

    def _watchdog_loop(self):
        while self.watchdog_running:
            time.sleep(30)
            with self._lock:
                for s_id, s in self.services.items():
                    inst = s.get("instance")
                    restart_fn = s.get("restart_fn")
                    if not inst or not restart_fn:
                        continue

                    # Worker thread canlı mı kontrol et
                    worker_thread = getattr(inst, "worker_thread", None)
                    if worker_thread is not None and not worker_thread.is_alive() and getattr(inst, "is_running", True):
                        print(f"[SUPERVISOR] ⚠️ Servis '{s['label']}' iş parçacığı sonlanmış! Otomatik diriltiliyor...")
                        try:
                            s["restart_count"] += 1
                            s["status"] = "RESTARTING"
                            s["detail"] = f"Diriltildi (#{s['restart_count']})"
                            restart_fn()
                            s["last_beat"] = time.time()
                            s["status"] = "OK"
                            print(f"[SUPERVISOR] ✅ Servis '{s['label']}' başarıyla yeniden başlatıldı.")
                        except Exception as e:
                            print(f"[SUPERVISOR] ❌ Servis '{s['label']}' yeniden başlatılamadı: {e}")
                            s["status"] = "ERROR"
                            s["detail"] = str(e)
                            try:
                                from tools.ops_log import exception as log_exc
                                log_exc("supervisor", "Servis yeniden başlatılamadı: " + s["label"], e)
                            except Exception:
                                pass


def get_supervisor():
    return ServiceSupervisor.get_instance()
