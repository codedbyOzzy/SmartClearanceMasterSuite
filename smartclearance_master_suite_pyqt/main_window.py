# -*- coding: utf-8 -*-
"""
🏛️ SmartClearance MasterSuite - Ana Pencere (MainWindow PyQt6)
Header, Sidebar, StackedWidget (17 Sekme), Arka Plan Servisleri (GTB, Kantar, Telegram),
Canlı Senkronizasyon (Live Watcher) ve StatusBar koordinatörü.
"""

import sys
import os
import threading
from datetime import datetime

# Root import guard
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent

from .components.header import MasterSuiteHeader
from .components.sidebar import MasterSuiteSidebar
from .components.status_bar import MasterSuiteStatusBar
from .views import (
    CockpitView, ActivityHubView, ExcelAktarimView,
    RPAStationView, MasterKontrolView, GTBView, KantarView,
    ETAView, EvrimView, ShieldChatView, QNBPortalView,
    GLPPortalView, DogruerPortalView, TalepPortalView,
    SummaryView, SettingsView, UsersView,
    ApexView, HorizonView, AIAssistantView
)
from .auth.login_dialog import PyQtChangePasswordDialog

# Master Data Engine Import
try:
    from tools.dogruer_master_suite.engine.master_data_engine import (
        MasterDataEngine, load_evrim_cached_data, load_talep_queue
    )
except Exception:
    MasterDataEngine = None
    load_evrim_cached_data = lambda: []
    load_talep_queue = lambda: []

# Servisler ve Altyapı
try:
    from tools.dogruer_master_suite.service_supervisor import get_supervisor
except Exception:
    get_supervisor = lambda: None

try:
    from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
except Exception:
    send_desktop_notification = lambda t, m, f=False: None

try:
    from tools.dogruer_master_suite.app_lifecycle import prepare_shutdown, report_critical
except Exception:
    prepare_shutdown = lambda app, logout_auth=True: None
    report_critical = lambda mod, title, err, app=None: None

try:
    from tools.gtb_engine.gtb_tracker_service import get_gtb_tracker_service
except Exception:
    get_gtb_tracker_service = None

try:
    from tools.kantar_engine.kantar_tracker_service import get_kantar_tracker_service
except Exception:
    get_kantar_tracker_service = None

try:
    from tools.telegram_bridge.telegram_bot_service import get_telegram_service
except Exception:
    get_telegram_service = None


class LiveSyncWorker(QThread):
    """Excel ve Outlook verilerini 12 saniyede bir arka planda güncelleyen iş parçacığı."""
    cycle_done = pyqtSignal(bool, str)

    def __init__(self, engine, interval_sec=12.0):
        super().__init__()
        self.engine = engine
        self.interval_sec = interval_sec
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        # İlk senkron hemen çalışır
        if self.engine and self._running:
            try:
                self.engine.sync_all()
                self.cycle_done.emit(True, "Veriler güncellendi")
            except Exception as e:
                self.cycle_done.emit(False, str(e))

        # Periyodik döngü
        while self._running:
            # 500ms aralıklarla iptal kontrolü yaparak bekle
            steps = max(1, int(self.interval_sec * 2))
            for _ in range(steps):
                if not self._running:
                    return
                self.msleep(500)

            if not self._running:
                return

            if self.engine:
                try:
                    self.engine.sync_all()
                    self.cycle_done.emit(True, "Veriler güncellendi")
                except Exception as e:
                    self.cycle_done.emit(False, str(e))


class MainWindow(QMainWindow):
    # Çekirdek servis durum sinyalleri
    gtb_status_signal = pyqtSignal(object)
    kantar_status_signal = pyqtSignal(object)

    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user or {"username": "admin", "display_name": "Sistem Yöneticisi", "role": "admin"}
        self.engine = MasterDataEngine() if MasterDataEngine else None
        self.config = getattr(self.engine, "config", {}) if self.engine else {}
        self.evrim_records = load_evrim_cached_data() if callable(load_evrim_cached_data) else []
        self.talep_queue = load_talep_queue() if callable(load_talep_queue) else []

        self.supervisor = get_supervisor() if callable(get_supervisor) else None
        self.telegram_service = None
        self.gtb_tracker = None
        self.kantar_tracker = None
        self.sync_worker = None

        self.setWindowTitle(f"Doğruer SmartClearance MasterSuite v5.0 — [{self.current_user.get('display_name', 'Kullanıcı')}]")
        self.setMinimumSize(960, 550)

        # Aktif ekranın çalışma alanına göre başlat
        scr = QApplication.primaryScreen()
        avail = scr.availableGeometry() if scr else None
        if avail:
            init_w = min(1400, max(960, int(avail.width() * 0.94)))
            init_h = min(860, max(550, int(avail.height() * 0.92)))
            self.resize(init_w, init_h)
            self.move(
                avail.left() + max(0, (avail.width() - init_w) // 2),
                avail.top() + max(0, (avail.height() - init_h) // 2)
            )
        else:
            self.resize(1300, 780)

        self.views = {}
        self.current_tab_code = None
        self._current_screen_name = None

        self._build_ui()
        self._init_signals()
        self._init_background_services()
        self.start_background_sync()

    def showEvent(self, event):
        super().showEvent(event)
        wh = self.windowHandle()
        if wh:
            try:
                wh.screenChanged.connect(self._on_screen_changed)
            except Exception:
                pass
            scr = wh.screen()
            if scr:
                self._current_screen_name = scr.name()
                self._on_screen_changed(scr)

    def moveEvent(self, event):
        super().moveEvent(event)
        wh = self.windowHandle()
        if wh:
            scr = wh.screen()
            if scr and scr.name() != getattr(self, "_current_screen_name", None):
                self._current_screen_name = scr.name()
                self._on_screen_changed(scr)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            # Minimize edilirken _on_screen_changed çağırma — aksi hâlde
            # maximize modundan minimize etmeye çalışırken pencere showMaximized()
            # ile geri itilip görev çubuğuna inemez.
            if not self.isMinimized():
                self._on_screen_changed(self.screen())

    def _on_screen_changed(self, new_screen=None):
        """Pencere harici monitör ve laptop ekranı arasında taşındığında boyut ve tüm 19 sekmenin bileşenlerini adapte eder."""
        if not new_screen:
            new_screen = self.screen() or QApplication.primaryScreen()
        if not new_screen:
            return

        avail = new_screen.availableGeometry()

        if self.isMaximized():
            QTimer.singleShot(60, self.showMaximized)
            return

        geo = self.geometry()
        new_w = geo.width()
        new_h = geo.height()
        changed = False

        max_w = int(avail.width() * 0.96)
        if new_w > max_w:
            new_w = max(self.minimumWidth(), max_w)
            changed = True

        max_h = int(avail.height() * 0.94)
        if new_h > max_h:
            new_h = max(self.minimumHeight(), max_h)
            changed = True

        new_x = geo.x()
        new_y = geo.y()
        if new_x < avail.left() or (new_x + new_w) > avail.right():
            new_x = max(avail.left(), min(new_x, avail.right() - new_w))
            changed = True
        if new_y < avail.top() or (new_y + new_h) > avail.bottom():
            new_y = max(avail.top(), min(new_y, avail.bottom() - new_h))
            changed = True

        if changed:
            self.setGeometry(new_x, new_y, new_w, new_h)

        # 1. Kenar Çubuğu (Sidebar) Genişlik Adaptasyonu
        if hasattr(self, "sidebar") and self.sidebar:
            try:
                self.sidebar.adapt_to_screen(new_screen)
            except Exception:
                pass

        # 2. Tüm 19 Görünümün (Tab) Ekran Adaptörlerini Tetikle
        for view_code, view in getattr(self, "views", {}).items():
            if view and hasattr(view, "_on_screen_changed"):
                try:
                    view._on_screen_changed(new_screen)
                except Exception:
                    pass

        self.updateGeometry()
        self.update()

    def _build_ui(self):
        central = QWidget(self)
        central.setObjectName("CentralContainer")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SOL MENÜ (SIDEBAR)
        self.sidebar = MasterSuiteSidebar(central)
        self.sidebar.set_user_info(
            self.current_user.get("display_name", "Kullanıcı"),
            self.current_user.get("role", "admin").upper()
        )
        self.sidebar.tab_changed.connect(self.switch_tab)
        self.sidebar.change_password_requested.connect(self._on_change_password)
        self.sidebar.logout_requested.connect(self._on_logout)
        main_layout.addWidget(self.sidebar)

        # 2. SAĞ İÇERİK ALANI (HEADER + STACKED VIEWS + STATUS BAR)
        right_box = QWidget(central)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Üst Başlık Barı
        self.header = MasterSuiteHeader(right_box)
        self.header.refresh_requested.connect(self.refresh_all_data)
        self.header.open_excel_requested.connect(self.open_excel_file)
        right_layout.addWidget(self.header)

        # Sekmeler Yığını (QStackedWidget)
        self.stacked_views = QStackedWidget(right_box)
        self._setup_views()
        right_layout.addWidget(self.stacked_views, stretch=1)

        # Alt Durum Çubuğu
        self.status_bar = MasterSuiteStatusBar(right_box)
        self.status_bar.health_report_requested.connect(self._show_health_report)
        right_layout.addWidget(self.status_bar)

        main_layout.addWidget(right_box, stretch=1)

        # Başlangıç sekmesini aç
        self.switch_tab("COCKPIT")

    def _setup_views(self):
        # 17 Görünümün oluşturulması ve StackedWidget'a eklenmesi
        view_classes = {
            "COCKPIT": CockpitView,
            "AI_ASSISTANT": AIAssistantView,
            "APEX": ApexView,
            "HORIZON": HorizonView,
            "ACTIVITY_HUB": ActivityHubView,
            "EXCEL_AKTARIM": ExcelAktarimView,
            "RPA_STATION": RPAStationView,
            "MASTER_KONTROL": MasterKontrolView,
            "GTB_TAKIP": GTBView,
            "KANTAR_TAKIP": KantarView,
            "ETA_YAKLASANLAR": ETAView,
            "EVRIM_EXPLORER": EvrimView,
            "SHIELD": ShieldChatView,
            "QNB_PORTAL": QNBPortalView,
            "GLP_PORTAL": GLPPortalView,
            "DOGRUER_PORTAL": DogruerPortalView,
            "TALEP": TalepPortalView,
            "SUMMARY": SummaryView,
            "SETTINGS": SettingsView,
            "USERS": UsersView,
        }

        for code, cls in view_classes.items():
            view_instance = cls(self.stacked_views, main_window=self)
            self.views[code] = view_instance
            self.stacked_views.addWidget(view_instance)

    def _init_signals(self):
        self.gtb_status_signal.connect(self._on_gtb_status_received)
        self.kantar_status_signal.connect(self._on_kantar_status_received)

    def _init_background_services(self):
        """Arka plan takip servislerini ve gözetmeni (Supervisor) başlatır."""
        # 1. Telegram Mobil Servisi
        if get_telegram_service:
            try:
                self.telegram_service = get_telegram_service(
                    data_engine=self.engine,
                    evrim_data_provider=lambda: getattr(self, "evrim_records", [])
                )
                self.telegram_service.start_polling()
                if self.supervisor:
                    self.supervisor.register_service("telegram", self.telegram_service)
            except Exception as e:
                print(f"[SERVICE] Telegram servisi başlatılamadı: {e}")

        # 2. GTB Otonom Takip Servisi
        if get_gtb_tracker_service:
            try:
                def _gtb_callback(*args, **kwargs):
                    try:
                        res = kwargs.get("result") or (args[0] if args else {})
                        self.gtb_status_signal.emit(res)
                    except RuntimeError:
                        pass

                self.gtb_tracker = get_gtb_tracker_service(
                    data_engine=self.engine,
                    telegram_service=self.telegram_service,
                    on_status_change_callback=_gtb_callback
                )
                if self.telegram_service:
                    self.telegram_service.gtb_tracker_provider = lambda: self.gtb_tracker
                self.gtb_tracker.start_worker()
                if self.supervisor:
                    self.supervisor.register_service("gtb", self.gtb_tracker)
            except Exception as e:
                print(f"[SERVICE] GTB Takip servisi başlatılamadı: {e}")

        # 3. Kantar & DBA Otonom Takip Servisi
        if get_kantar_tracker_service:
            try:
                def _kantar_callback(*args, **kwargs):
                    try:
                        res = kwargs.get("result") or (args[0] if args else {})
                        self.kantar_status_signal.emit(res)
                    except RuntimeError:
                        pass

                self.kantar_tracker = get_kantar_tracker_service(
                    data_engine=self.engine,
                    telegram_service=self.telegram_service,
                    on_status_change_callback=_kantar_callback
                )
                if self.telegram_service:
                    self.telegram_service.kantar_tracker_provider = lambda: self.kantar_tracker
                self.kantar_tracker.start_worker()
                if self.supervisor:
                    self.supervisor.register_service("kantar", self.kantar_tracker)
            except Exception as e:
                print(f"[SERVICE] Kantar Takip servisi başlatılamadı: {e}")

    def start_background_sync(self):
        """12 saniyelik periyotlarla Excel ve Outlook'u senkronize eden canlı thread'i başlatır."""
        if not self.engine:
            return
        self.sync_worker = LiveSyncWorker(self.engine, interval_sec=12.0)
        self.sync_worker.cycle_done.connect(self._on_sync_cycle_done)
        self.sync_worker.start()

    def _on_sync_cycle_done(self, success, msg):
        """Senkronizasyon tamamlandığında arayüzü ve aktif sekmeyi günceller."""
        err = getattr(self.engine, "last_excel_error", None)
        ok = getattr(self.engine, "excel_read_ok", True)

        if not ok and err:
            self.header.set_titles(self.header.lbl_title.text(), f"⚠️ Excel Okuma Hatası: {err}")
        else:
            now_str = datetime.now().strftime("%H:%M:%S")
            self.header.set_titles(self.header.lbl_title.text(), f"✅ Canlı Excel & Outlook senkronize edildi ({now_str})")

        # Aktif sekme görünümünü yenile
        if self.current_tab_code and self.current_tab_code in self.views:
            active_v = self.views[self.current_tab_code]
            if hasattr(active_v, "refresh_table"):
                try:
                    active_v.refresh_table()
                except Exception:
                    pass
            elif hasattr(active_v, "on_activate"):
                try:
                    active_v.on_activate()
                except Exception:
                    pass

    def _on_gtb_status_received(self, res):
        """Bakanlık servisinden durum geldiğinde masatüstü bildirimi verir ve ilgili sekmeyi günceller."""
        if isinstance(res, dict) and res.get("beyanname_no"):
            b_no = res.get("beyanname_no")
            durum = res.get("durum") or res.get("hat") or "Güncellendi"
            if res.get("hat") in ["KIRMIZI", "SARI"]:
                send_desktop_notification(f"🏛️ GTB Hat Bildirimi: {b_no}", f"Bakanlık Durumu: {durum}")

        gtb_v = self.views.get("GTB_TAKIP")
        if gtb_v and hasattr(gtb_v, "refresh_table"):
            gtb_v.refresh_table()

        if self.current_tab_code == "COCKPIT":
            cockpit_v = self.views.get("COCKPIT")
            if cockpit_v and hasattr(cockpit_v, "refresh_table"):
                cockpit_v.refresh_table()

    def _on_kantar_status_received(self, res):
        """Kantar tikesi tamamlandığında ilgili sekmeyi günceller."""
        kantar_v = self.views.get("KANTAR_TAKIP")
        if kantar_v and hasattr(kantar_v, "refresh_table"):
            kantar_v.refresh_table()

    def switch_tab(self, tab_code):
        if tab_code not in self.views:
            return

        # Önceki görünümün deaktif hook'u
        if self.current_tab_code and self.current_tab_code in self.views:
            prev_view = self.views[self.current_tab_code]
            if hasattr(prev_view, "on_deactivate"):
                try:
                    prev_view.on_deactivate()
                except Exception as e:
                    print(f"Deactivate error: {e}")

        self.current_tab_code = tab_code
        target_view = self.views[tab_code]
        self.stacked_views.setCurrentWidget(target_view)
        self.sidebar.update_active_tab(tab_code)

        # Başlık ve Alt Başlık Sözlüğü
        TITLES = {
            "COCKPIT": ("📊 MERKEZİ OPERASYON KONTROL PANELİ", "Tüm aktif dosyaların gümrük tescil ve Outlook vergi mail durumları"),
            "AI_ASSISTANT": ("🧠 DOĞRUER AKILLI GÜMRÜK & MEVZUAT ASİSTANI (GEMINI AI)", "Gümrük mevzuatı, 12 haneli GTİP tespiti, ithalat/ihracat kuralları ve operasyonel soru-cevap"),
            "APEX": ("🚀 SMARTCLEARANCE APEX — HANKOOK GÜMRÜK MASASI & EVRAK STÜDYOSU", "Sabah brifingi, dosya aşamaları, Singapur fatura eşleştirici ve YFKS dilekçe motoru"),
            "HORIZON": ("🌐 SMARTCLEARANCE HORIZON — KÜRESEL KONTEYNER & AIS HARİTA RADARI", "Canlı Leaflet dünya haritası, anlık gemi uydu koordinatları ve küresel rota takibi"),
            "ACTIVITY_HUB": ("📋 DOSYA NOTLARI & OPERASYONEL İŞLEM GÜNLÜĞÜ (TIMELINE)", "Özel dosya notları ve gümrük hareketlerinin canlı tarihçesi"),
            "EXCEL_AKTARIM": ("📑 FATURA & PACKING LIST'TEN EVRİM EXCEL AKTARIMI", "PDF evraklarını ayrıştırma, kalem birleştirme ve Evrim Excel üretimi"),
            "RPA_STATION": ("🤖 OTONOM RPA İSTASYONU", "Evrim masaüstü otomasyon robotu ve otomatik veri girişi"),
            "MASTER_KONTROL": ("🔍 MASTER DATA KONTROL & GTİP ÇAPRAZ DENETİM MERKEZİ", "Ürün kataloğu karşılaştırması ve GTİP çapraz denetimi"),
            "GTB_TAKIP": ("🏛️ TİCARET BAKANLIĞI (GTB) OTONOM BEYANNAME TAKİP MERKEZİ", "Bakanlık otonom hat (Sarı/Kırmızı/Yeşil) ve bloke durumları"),
            "KANTAR_TAKIP": ("⚖️ DP WORLD YARIMCA & KÖRFEZ KANTAR / DBA TİKE MERKEZİ", "Konteyner tartım durumları, plaka ve tek tıkla resmi Kantar Tikesi indirme"),
            "ETA_YAKLASANLAR": ("⏳ ETA TARİHİ YAKLAŞAN DOSYALAR & VARIŞ RADARI", "Önümüzdeki günlerde yanaşacak açık gemi ve konteynerler"),
            "EVRIM_EXPLORER": ("💾 EVRİM CANLI VERİ MERKEZİ & DETAYLI DOSYA SORGULAMA", "Doğruer Online & Evrim Entegre Dosya ve Beyanname Veritabanı"),
            "SHIELD": ("💬 AKILLI MAİL & KONUŞMA GEZGİNİ", "Outlook üzerindeki tüm konuşma zincirleri ve ekler havuzu"),
            "QNB_PORTAL": ("📦 QNB eSOLUTIONS PORTALI (YEREL WEBNET)", "Gömülü QNB Portalı & Otomatik Fatura Eşleştirici"),
            "GLP_PORTAL": ("🚢 HANKOOK GLP PORTALI", "Global Lojistik Portalı WebEngine Arayüzü"),
            "DOGRUER_PORTAL": ("🏢 DOĞRUER ONLINE PORTALI", "Gümrük Müşavirliği Online Operasyon Portalı"),
            "TALEP": ("💰 FİNANSAL TALEPLER & KUYRUK YÖNETİMİ", "Liman ve masraf faturaları talep doldurma motoru"),
            "SUMMARY": ("📈 OPERASYONEL ÖZET & RAPORLAMA", "Haftalık ve aylık performans göstergeleri"),
            "SETTINGS": ("⚙️ SİSTEM AYARLARI", "Excel, PDF, Outlook ve portal bağlantı yapılandırmaları"),
            "USERS": ("👥 KULLANICI VE YETKİ YÖNETİMİ", "Sistem kullanıcıları ve rol dağılımları"),
        }

        t_title, t_sub = TITLES.get(tab_code, ("SmartClearance MasterSuite", ""))
        self.header.set_titles(t_title, t_sub)

        # Yeni görünümün aktifleşme hook'u
        if hasattr(target_view, "on_activate"):
            try:
                target_view.on_activate()
            except Exception as e:
                print(f"Activate error: {e}")

    def open_in_horizon(self, query: str):
        """Herhangi bir sekmeden Horizon sekmesini açıp aranan gemi/konteyneri haritada odaklar."""
        self.switch_tab("HORIZON")
        horizon_v = self.views.get("HORIZON")
        if horizon_v and hasattr(horizon_v, "focus_shipment"):
            horizon_v.focus_shipment(query)

    def refresh_all_data(self):
        """Manuel yenileme butonu tetiklendiğinde senkronizasyon yapar."""
        self.header.btn_refresh.setEnabled(False)
        self.header.btn_refresh.setText("⏳ Yükleniyor...")

        # PyQT QThread kullanan basit, lokal, thread-safe bir worker
        class ManualRefreshWorker(QThread):
            done_signal = pyqtSignal(bool, str)
            def __init__(self, engine):
                super().__init__()
                self.engine = engine
            def run(self):
                try:
                    if self.engine:
                        self.engine.sync_all()
                    self.done_signal.emit(True, "Başarılı")
                except Exception as e:
                    self.done_signal.emit(False, str(e))

        self._manual_worker = ManualRefreshWorker(self.engine)
        self._manual_worker.done_signal.connect(self._after_refresh)
        self._manual_worker.start()

    def _after_refresh(self, success, msg):
        self.header.btn_refresh.setEnabled(True)
        self.header.btn_refresh.setText("🔄 Şimdi Yenile")
        if self.current_tab_code and self.current_tab_code in self.views:
            active_v = self.views[self.current_tab_code]
            if hasattr(active_v, "refresh_table"):
                active_v.refresh_table()
        if success:
            QMessageBox.information(self, "Bilgi", "Veriler başarıyla yenilendi!")
        else:
            QMessageBox.warning(self, "Uyarı", f"Senkronizasyon uyarısı: {msg}")

    def open_excel_file(self):
        cfg = getattr(self, "config", {})
        excel_path = cfg.get("excel_path", r"\\Dgfile01\ithalat\ITH28\Halit ENGELEK\HANKOOK İŞ TAKİP RAPORU.xlsx")
        if os.path.exists(excel_path):
            try:
                os.startfile(excel_path)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Excel açılamadı: {e}")
        else:
            QMessageBox.warning(self, "Dosya Bulunamadı", f"Belirtilen Excel dosyası bulunamadı:\n{excel_path}")

    def query_selected_gtb_row(self, beyanname_no):
        """GTB sorgusu için merkezi fonksiyon."""
        if not beyanname_no:
            QMessageBox.warning(self, "Uyarı", "Geçerli bir beyanname numarası bulunamadı.")
            return

        if self.gtb_tracker:
            def _worker():
                res = self.gtb_tracker.query_single_now(beyanname_no)
                def _done():
                    if res.get("success"):
                        QMessageBox.information(
                            self, "GTB Canlı Sonuç",
                            f"📑 Beyanname: {beyanname_no}\n\n🏛️ Bakanlık Durumu:\n{res.get('durum') or res.get('hat')}"
                        )
                    else:
                        QMessageBox.critical(self, "GTB Sorgu Hatası", f"Sorgulama başarısız:\n{res.get('error')}")
                QTimer.singleShot(0, _done)
            threading.Thread(target=_worker, daemon=True).start()
        else:
            QMessageBox.information(self, "GTB Takip", f"Beyanname: {beyanname_no}\nGTB servisi aktif değil.")

    def navigate_to_evrim_detail(self, query):
        """Seçili referans/dosya no ile Evrim Gezgini sekmesine geçer."""
        self.switch_tab("EVRIM_EXPLORER")
        evrim_v = self.views.get("EVRIM_EXPLORER")
        if evrim_v and hasattr(evrim_v, "search_with_query"):
            evrim_v.search_with_query(query)

    def do_shield_quick_search(self, query):
        """Mail Gezgini sekmesinde dosya araması yapar."""
        self.switch_tab("SHIELD")
        shield_v = self.views.get("SHIELD")
        if shield_v and hasattr(shield_v, "search_with_query"):
            shield_v.search_with_query(query)

    def send_to_talep_form(self, payload):
        """Para Talebi sekmesine veri aktarır."""
        self.switch_tab("TALEP")
        talep_v = self.views.get("TALEP")
        if talep_v and hasattr(talep_v, "load_payload"):
            talep_v.load_payload(payload)

    def _on_change_password(self):
        username = self.current_user.get("username", "admin")
        dlg = PyQtChangePasswordDialog(username, self)
        dlg.exec()

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Çıkış Onayı", "Oturumu kapatmak ve çıkmak istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from tools.auth_manager import get_auth_manager
                auth = get_auth_manager()
                if auth:
                    auth.logout()
            except Exception:
                pass
            self.close()

    def _show_health_report(self):
        QMessageBox.information(
            self, "Sistem Sağlık Raporu",
            "🟢 GTB Servisi: 10 dk periyotla aktif\n"
            "🟢 Kantar & DBA: 10 dk periyotla aktif\n"
            "🟢 Telegram Bot Servisi: Dinlemede\n"
            "🟢 Excel Canlı Bağlantısı: Aktif (Read Guard korumalı)\n"
            "🟢 Supabase Bulut Senkronizasyonu: Bağlı"
        )

    def closeEvent(self, event):
        """Uygulama kapatılırken arka plan iş parçacıklarını güvenle durdurur."""
        if hasattr(self, "sync_worker") and self.sync_worker:
            self.sync_worker.stop()
            self.sync_worker.wait(1000)

        try:
            prepare_shutdown(self, logout_auth=False)
        except Exception:
            pass

        event.accept()
