# -*- coding: utf-8 -*-
"""
app.py — Doğruer SmartClearance MasterSuite Ana Koordinatör & Uygulama Sınıfı
Modüler Mimari Koordinatörü
"""
import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Root path ayarı
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tools.dogruer_master_suite.engine import (
    MasterDataEngine, load_app_config, save_app_config, DEFAULT_CONFIG,
    load_evrim_cached_data, save_evrim_cached_data, load_talep_queue, save_talep_queue
)
from tools.dogruer_master_suite.components import (
    MasterSuiteSidebar, MasterSuiteHeader, MasterSuiteStatusBar
)
from tools.dogruer_master_suite.views import (
    CockpitView, ActivityHubView, GTBView, KantarView, ETAView,
    EvrimView, ShieldView, PortalsView, SummaryView, SettingsView, UsersView,
    QNBPortalView, GLPPortalView, DogruerPortalView, TalepPortalView, RPAStationView,
    AIAssistantView
)
from tools.dogruer_master_suite.sc_native_views import (
    NativeExcelAktarimView, NativeMasterKontrolView
)
from tools.dogruer_master_suite.service_supervisor import get_supervisor
from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
from tools.dogruer_master_suite.app_lifecycle import prepare_shutdown, report_critical

# Opsiyonel servisler
try:
    from tools.auth_manager import get_auth_manager
except Exception:
    get_auth_manager = None

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


class DogruerMasterSuiteApp:
    """Doğruer SmartClearance MasterSuite Ana Uygulama Koordinatörü."""

    def __init__(self, root, current_user=None):
        self.root = root
        self.current_user = current_user or {"username": "admin", "full_name": "Yönetici", "role": "admin"}
        self.config = load_app_config()
        self.engine = MasterDataEngine(config=self.config)

        self.root.title(f"Doğruer SmartClearance MasterSuite v4.0 — [{self.current_user.get('full_name', '')}]")
        self.root.configure(bg="#0f172a")
        self._fit_window_to_screen()

        self.current_tab = "COCKPIT"
        self.views = {}
        self._closed = False
        self._sync_stop = threading.Event()
        self.evrim_records = load_evrim_cached_data()
        self.talep_queue = load_talep_queue()

        # Servisler ve Supervisor
        self.supervisor = get_supervisor()
        self._init_background_services()

        # Arayüz kurulumu
        self.setup_styles()
        self.setup_layout()

        # Canlı izleme döngüsü
        self.start_background_sync()
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_close)
        try:
            self.root.report_callback_exception = self._on_tk_callback_exception
        except Exception:
            pass
        try:
            from tools.auth_manager import get_auth_manager as _get_am
            am = _get_am()
            am.set_ui_dispatcher(lambda fn: self._schedule_ui(fn))
        except Exception:
            pass

    def _fit_window_to_screen(self):
        """Pencereyi ekrana sığdırır, maksimize eder; küçük ekranda da yeniden boyutlanabilir."""
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        sw = int(self.root.winfo_screenwidth() or 1280)
        sh = int(self.root.winfo_screenheight() or 720)
        min_w = min(900, max(720, sw - 24))
        min_h = min(580, max(480, sh - 80))
        self.root.minsize(min_w, min_h)
        self.root.resizable(True, True)
        try:
            self.root.state("zoomed")
        except Exception:
            w = max(min_w, sw - 16)
            h = max(min_h, sh - 72)
            self.root.geometry(f"{w}x{h}+0+0")

    def _init_background_services(self):
        # 1. Telegram
        self.telegram_service = None
        if get_telegram_service:
            try:
                self.telegram_service = get_telegram_service(
                    data_engine=self.engine,
                    evrim_data_provider=lambda: self.evrim_records
                )
                self.telegram_service.start_polling()
                self.supervisor.register_service("telegram", self.telegram_service)
            except Exception as e:
                report_critical("telegram", "Telegram servisi başlatılamadı", e, app=self)

        # 2. GTB Tracker
        self.gtb_tracker = None
        if get_gtb_tracker_service:
            try:
                self.gtb_tracker = get_gtb_tracker_service(
                    data_engine=self.engine,
                    telegram_service=self.telegram_service,
                    on_status_change_callback=self.on_gtb_status_changed
                )
                if self.telegram_service:
                    self.telegram_service.gtb_tracker_provider = lambda: self.gtb_tracker
                self.gtb_tracker.start_worker()
                self.supervisor.register_service("gtb", self.gtb_tracker)
            except Exception as e:
                report_critical("gtb", "GTB takip servisi başlatılamadı", e, app=self)

        # 3. Kantar Tracker
        self.kantar_tracker = None
        if get_kantar_tracker_service:
            try:
                self.kantar_tracker = get_kantar_tracker_service(
                    data_engine=self.engine,
                    telegram_service=self.telegram_service,
                    on_status_change_callback=self.on_kantar_status_changed
                )
                if self.telegram_service:
                    self.telegram_service.kantar_tracker_provider = lambda: self.kantar_tracker
                self.kantar_tracker.start_worker()
                self.supervisor.register_service("kantar", self.kantar_tracker)
            except Exception as e:
                report_critical("kantar", "Kantar takip servisi başlatılamadı", e, app=self)

    def create_metric_widget(self, parent, title, val, subtitle, accent_color, command=None):
        card = tk.Frame(parent, bg="#ffffff", padx=12, pady=8, relief=tk.FLAT, bd=0, cursor="hand2" if command else "arrow")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

        top_strip = tk.Frame(card, bg=accent_color, height=3)
        top_strip.pack(fill=tk.X, pady=(0, 4))

        lbl_t = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff", cursor="hand2" if command else "arrow")
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(card, text=val, font=("Segoe UI", 15, "bold"), fg=accent_color, bg="#ffffff", cursor="hand2" if command else "arrow")
        lbl_v.pack(anchor="w")

        lbl_sub = tk.Label(card, text=subtitle, font=("Segoe UI", 8), fg="#94a3b8", bg="#ffffff", cursor="hand2" if command else "arrow")
        lbl_sub.pack(anchor="w")

        if command:
            for w in (card, top_strip, lbl_t, lbl_v, lbl_sub):
                w.bind("<Button-1>", lambda e, cmd=command: cmd())

        return {"card": card, "val_lbl": lbl_v, "title": title, "subtitle": subtitle, "color": accent_color}

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=30,
            background="#ffffff",
            fieldbackground="#ffffff",
            borderwidth=0
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#0f172a",
            foreground="#ffffff",
            padding=[8, 8],
            relief="flat"
        )
        self.style.map("Treeview.Heading", background=[("active", "#1e293b")])

    def setup_layout(self):
        # 1. En Alt Durum Çubuğu
        self.status_bar = MasterSuiteStatusBar(self.root, self)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 2. Sol Navigasyon Menüsü
        self.sidebar = MasterSuiteSidebar(self.root, self)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # 3. Ana İçerik Alanı
        self.content_frame = tk.Frame(self.root, bg="#f8fafc")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 4. Üst Başlık & Aksiyon Barı
        self.header = MasterSuiteHeader(self.content_frame, self)
        self.header.pack(fill=tk.X)

        # 5. Görünüm Konteyneri ve Sekmeler
        self.view_container = tk.Frame(self.content_frame, bg="#f8fafc", padx=16, pady=12)
        self.view_container.pack(fill=tk.BOTH, expand=True)

        self.setup_views()

        # İlk sekme açılışı
        self.switch_tab("COCKPIT")
        self.apply_role_permissions(self.current_user)
        self.status_bar.start_ticker()

    def setup_views(self):
        # Tüm modüler görünümleri oluştur ve kaydet
        self.views["COCKPIT"] = CockpitView(self.view_container, self)
        self.views["AI_ASSISTANT"] = AIAssistantView(self.view_container, self)
        self.views["ACTIVITY_HUB"] = ActivityHubView(self.view_container, self)
        self.views["EXCEL_AKTARIM"] = NativeExcelAktarimView(self.view_container, self)
        self.views["RPA_STATION"] = RPAStationView(self.view_container, self)
        self.views["MASTER_KONTROL"] = NativeMasterKontrolView(self.view_container, self)
        self.views["GTB_TAKIP"] = GTBView(self.view_container, self)
        self.views["KANTAR_TAKIP"] = KantarView(self.view_container, self)
        self.views["ETA_YAKLASANLAR"] = ETAView(self.view_container, self)
        self.views["EVRIM_EXPLORER"] = EvrimView(self.view_container, self)
        self.views["SHIELD"] = ShieldView(self.view_container, self)

        # Portallar
        self.views["QNB_PORTAL"] = QNBPortalView(self.view_container, self)
        self.views["GLP_PORTAL"] = GLPPortalView(self.view_container, self)
        self.views["DOGRUER_PORTAL"] = DogruerPortalView(self.view_container, self)
        self.views["TALEP"] = TalepPortalView(self.view_container, self)

        # Yönetim ve Ayarlar
        self.views["SUMMARY"] = SummaryView(self.view_container, self)
        self.views["SETTINGS"] = SettingsView(self.view_container, self)
        self.views["USERS"] = UsersView(self.view_container, self)

        # Geriye uyumluluk için app üzerindeki view referansları
        self.view_cockpit = self.views["COCKPIT"]
        self.view_ai_assistant = self.views["AI_ASSISTANT"]
        self.view_activity = self.views["ACTIVITY_HUB"]
        self.view_excel_aktarim = self.views["EXCEL_AKTARIM"]
        self.view_rpa = self.views["RPA_STATION"]
        self.view_master_kontrol = self.views["MASTER_KONTROL"]
        self.view_gtb_takip = self.views["GTB_TAKIP"]
        self.view_kantar_takip = self.views["KANTAR_TAKIP"]
        self.view_eta_takip = self.views["ETA_YAKLASANLAR"]
        self.view_evrim = self.views["EVRIM_EXPLORER"]
        self.view_shield = self.views["SHIELD"]
        self.view_qnb = self.views["QNB_PORTAL"]
        self.view_glp = self.views["GLP_PORTAL"]
        self.view_dogruer = self.views["DOGRUER_PORTAL"]
        self.view_talep = self.views["TALEP"]
        self.view_summary = self.views["SUMMARY"]
        self.view_settings = self.views["SETTINGS"]
        self.view_users = self.views["USERS"]

    @property
    def lbl_head_subtitle(self):
        return getattr(self.header, "lbl_head_subtitle", None) if hasattr(self, "header") else None

    def switch_tab(self, tab_code):
        # Önceki görünümün devre dışı bırakılma hook'unu çağır
        prev_view = self.views.get(self.current_tab)
        if prev_view and hasattr(prev_view, "on_deactivate"):
            try:
                prev_view.on_deactivate()
            except Exception as e:
                print(f"on_deactivate error ({self.current_tab}): {e}")

        # Ayarlar sekmesinden ayrılıyorsa girilen kutuları otomatik kaydet
        if self.current_tab == "SETTINGS" and tab_code != "SETTINGS":
            settings_v = self.views.get("SETTINGS")
            if settings_v and hasattr(settings_v, "_silent_save_settings_from_ui"):
                try:
                    settings_v._silent_save_settings_from_ui()
                except Exception:
                    pass

        self.current_tab = tab_code
        self.sidebar.update_active_tab(tab_code)

        # Tüm görünümleri gizle
        for code, view in self.views.items():
            view.pack_forget()

        titles = {
            "COCKPIT": ("📊 MERKEZİ OPERASYON KONTROL PANELİ", "Tüm aktif dosyaların gümrük tescil ve Outlook vergi mail durumları"),
            "AI_ASSISTANT": ("🧠 DOĞRUER AKILLI GÜMRÜK & MEVZUAT ASİSTANI (GEMINI AI)", "Gümrük mevzuatı, 12 haneli GTİP tespiti, ithalat/ihracat kuralları ve operasyonel soru-cevap"),
            "ACTIVITY_HUB": ("📋 DOSYA NOTLARI & OPERASYONEL İŞLEM GÜNLÜĞÜ (TIMELINE)", "Dosyalara ait özel notlar, GTB tescil, mail ve fatura hareketlerinin canlı tarihçesi"),
            "EXCEL_AKTARIM": ("📑 FATURA & PACKING LIST'TEN EVRİM EXCEL AKTARIMI", "PDF evraklarını ayrıştırma, kalem birleştirme ve Evrim sistemine aktarılabilir Excel üretimi"),
            "MASTER_KONTROL": ("🔍 MASTER DATA KONTROL & GTİP ÇAPRAZ DENETİM MERKEZİ", "Ürün kataloğu karşılaştırması, GTİP ve Türkçe tanım denetimi"),
            "GTB_TAKIP": ("🏛️ TİCARET BAKANLIĞI (GTB) OTONOM BEYANNAME TAKİP MERKEZİ", "10 dakikalık periyotlarla otonom taranan beyannamelerin canlı gümrük statüleri"),
            "KANTAR_TAKIP": ("⚖️ DP WORLD YARIMCA & KÖRFEZ KANTAR / DBA TİKE MERKEZİ", "Konteyner tartım durumları, plaka ve DBA bilgileri — Tek tıkla resmi Kantar Tikesi PDF indirme"),
            "ETA_YAKLASANLAR": ("⏳ ETA TARİHİ YAKLAŞAN DOSYALAR & VARIŞ RADARI", "Excel ETA / varış tarihine göre önümüzdeki günlerde yanaşacak açık dosyalar"),
            "EVRIM_EXPLORER": ("🏛️ EVRİM CANLI VERİ MERKEZİ & DETAYLI DOSYA SORGULAMA", "Doğruer Online & Evrim Entegre Dosya, Beyanname Tescil ve Durum Takip Sistemi"),
            "SHIELD": ("📧 AKILLI MAİL & KONUŞMA GEZGİNİ (ADIM ADIM SOHBET AKIŞI)", "Outlook üzerindeki tüm konuşma zincirleri, adım adım aşamalar ve ekler havuzu"),
            "QNB_PORTAL": ("🌐 QNB eSOLUTIONS PORTALI (GÖMÜLÜ ARAYÜZ)", "Doğrudan arayüz içinde çalışan QNB Portalı & Otomatik Evyap/DP World Eşleştirici"),
            "GLP_PORTAL": ("🚛 HANKOOK GLP GLOBAL LOJİSTİK PORTALI (GÖMÜLÜ)", "Hankook Global Logistics Portal (GLP) - Gömülü Yükleme & Konşimento Takibi"),
            "DOGRUER_PORTAL": ("🌐 DOĞRUER ONLİNE & EVRİM SİSTEMİ (GÖMÜLÜ)", "Doğruer Online Portalı, İş Takip Raporu & Tek Tıkla Canlı Veri Aktarımı"),
            "TALEP": ("💸 DOĞRUER ONLİNE PARA TALEP PORTALI (GÖMÜLÜ)", "Doğrudan arayüz içinde çalışan Doğruer Online Masraf ve Avans Talepleri Form Otomasyonu"),
            "SUMMARY": ("📈 GÜNLÜK İŞ & OPERASYON ÖZETİ", "Günlük tescil, gönderilen mailler ve bekleyen işler raporu"),
            "SETTINGS": ("⚙️ SİSTEM VE ENTEGRASYON AYARLARI", "Excel iş takip dosyası, PDF tarama klasörü ve e-posta tercihleri"),
            "USERS": ("👥 KULLANICI & YETKİ YÖNETİM MERKEZİ", "Sistem kullanıcıları, yetkilendirme (Admin/Operatör) ve canlı hesap yönetimi")
        }

        t_tuple = titles.get(tab_code, ("Doğruer MasterSuite", ""))
        self.header.set_title(t_tuple[0], t_tuple[1])

        active_view = self.views.get(tab_code)
        if active_view:
            active_view.pack(fill=tk.BOTH, expand=True)
            if hasattr(active_view, "on_activate"):
                active_view.on_activate()
            elif tab_code == "COCKPIT" and hasattr(active_view, "refresh_cockpit_table"):
                active_view.refresh_cockpit_table()
            elif tab_code == "ACTIVITY_HUB" and hasattr(active_view, "refresh_activity_hub"):
                active_view.refresh_activity_hub()
            elif tab_code == "GTB_TAKIP" and hasattr(active_view, "refresh_gtb_takip_table"):
                active_view.refresh_gtb_takip_table()
            elif tab_code == "KANTAR_TAKIP" and hasattr(active_view, "refresh_kantar_takip_table"):
                active_view.refresh_kantar_takip_table()
            elif tab_code == "ETA_YAKLASANLAR" and hasattr(active_view, "refresh_eta_yaklasanlar_table"):
                active_view.refresh_eta_yaklasanlar_table()
            elif tab_code == "SUMMARY" and hasattr(active_view, "update_summary_view"):
                active_view.update_summary_view()
            elif tab_code == "SETTINGS" and hasattr(active_view, "load_settings_into_ui"):
                active_view.load_settings_into_ui()
            elif tab_code == "USERS" and hasattr(active_view, "refresh_users_table"):
                active_view.refresh_users_table()

    def _ui_alive(self):
        if self._closed:
            return False
        try:
            return bool(self.root) and bool(self.root.winfo_exists())
        except Exception:
            return False

    def _schedule_ui(self, fn):
        if not self._ui_alive():
            return
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def start_background_sync(self):
        def loop():
            try:
                self.engine.sync_all()
                self._schedule_ui(self.on_sync_finished)
            except Exception as e:
                report_critical("sync", "İlk Excel/Outlook senkronu başarısız", e, app=self)

            while not self._sync_stop.wait(12.0):
                try:
                    self.engine.sync_all()
                    self._schedule_ui(self.on_sync_finished)
                except Exception as e:
                    report_critical("sync", "Arka plan senkronu başarısız", e, app=self)

        t = threading.Thread(target=loop, daemon=True, name="BackgroundSyncThread")
        t.start()

    def trigger_sync_async(self):
        self.set_header_subtitle("🔄 Excel ve Outlook verileri taranıyor...", fg="#2563eb")

        def work():
            try:
                self.engine.sync_all()
                def _done():
                    if not self._ui_alive():
                        return
                    self.on_sync_finished()
                    self._apply_sync_header_status(reset_after_ok=True)
                self._schedule_ui(_done)
            except Exception as e:
                print("Manual sync error:", e)
                report_critical("sync", "Manuel senkronizasyon hatası", e, app=self)
                self._schedule_ui(lambda: self.set_header_subtitle("⚠️ Senkronizasyon hatası!", fg="#dc2626") if self._ui_alive() else None)

        t = threading.Thread(target=work, daemon=True)
        t.start()

    def _apply_sync_header_status(self, reset_after_ok=False):
        if not self._ui_alive():
            return
        err = getattr(self.engine, "last_excel_error", None)
        ok = getattr(self.engine, "excel_read_ok", True)
        if not ok and err:
            self.set_header_subtitle("⚠️ " + str(err), fg="#dc2626")
            return
        self.set_header_subtitle("✅ Canlı Excel & Outlook verileri güncellendi", fg="#16a34a")
        if reset_after_ok:
            try:
                self.root.after(
                    4000,
                    lambda: self.set_header_subtitle(
                        "Tüm aktif dosyaların gümrük tescil ve Outlook vergi mail durumları"
                    ) if self._ui_alive() else None,
                )
            except Exception:
                pass

    def on_sync_finished(self):
        if not self._ui_alive():
            return
        self._apply_sync_header_status(reset_after_ok=False)
        curr_v = self.views.get(self.current_tab)
        if not curr_v:
            return
        try:
            if hasattr(curr_v, "is_alive") and not curr_v.is_alive():
                return
        except Exception:
            return
        try:
            if hasattr(curr_v, "refresh_cockpit_table"):
                curr_v.refresh_cockpit_table()
            elif hasattr(curr_v, "update_summary_view"):
                curr_v.update_summary_view()
            elif hasattr(curr_v, "on_activate"):
                curr_v.on_activate()
        except tk.TclError:
            return

    def set_header_subtitle(self, text, fg="#64748b"):
        if not self._ui_alive():
            return
        if hasattr(self, "header") and self.header and hasattr(self.header, "lbl_head_subtitle"):
            try:
                self.header.lbl_head_subtitle.config(text=text, fg=fg)
            except Exception:
                pass

    def query_selected_gtb_row(self, beyanname_no):
        gtb_v = self.views.get("GTB_TAKIP")
        if gtb_v and hasattr(gtb_v, "query_selected_gtb_row"):
            gtb_v.query_selected_gtb_row(beyanname_no)
        elif self.gtb_tracker:
            def _worker():
                res = self.gtb_tracker.query_single_now(beyanname_no)
                def _done():
                    if res.get("success"):
                        messagebox.showinfo("GTB Canlı Sonuç", f"📑 Beyanname: {beyanname_no}\n\n🏛️ Bakanlık Durumu:\n{res.get('durum')}")
                    else:
                        messagebox.showerror("GTB Sorgu Hatası", f"Sorgulama başarısız:\n{res.get('error')}")
                self._schedule_ui(_done)
            threading.Thread(target=_worker, daemon=True).start()
        else:
            messagebox.showinfo("GTB Sorgu", f"Beyanname No: {beyanname_no}")

    def send_to_talep_form(self, payload):
        self.switch_tab("TALEP")
        talep_v = self.views.get("TALEP")
        if talep_v and hasattr(talep_v, "send_to_talep_form"):
            talep_v.send_to_talep_form(payload)

    def do_shield_quick_search(self, query=None):
        self.switch_tab("SHIELD")
        shield_v = self.views.get("SHIELD")
        if shield_v:
            if query and hasattr(shield_v, "txt_shield_query"):
                shield_v.txt_shield_query.delete(0, tk.END)
                shield_v.txt_shield_query.insert(0, query)
            if hasattr(shield_v, "do_shield_quick_search"):
                shield_v.do_shield_quick_search()

    def navigate_to_evrim_detail(self, query):
        self.switch_tab("EVRIM_EXPLORER")
        evrim_v = self.views.get("EVRIM_EXPLORER")
        if evrim_v:
            if hasattr(evrim_v, "txt_ev_search"):
                evrim_v.txt_ev_search.delete(0, tk.END)
                evrim_v.txt_ev_search.insert(0, query)
            if hasattr(evrim_v, "apply_evrim_filters"):
                evrim_v.apply_evrim_filters()

    def open_excel_file(self):
        path = self.config.get("excel_path", "")
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Uyarı", f"Excel dosyası bulunamadı:\n{path}")

    def on_gtb_status_changed(self, *args, **kwargs):
        gtb_v = self.views.get("GTB_TAKIP")
        if gtb_v and hasattr(gtb_v, "refresh_gtb_takip_table"):
            self._schedule_ui(gtb_v.refresh_gtb_takip_table)

    def on_kantar_status_changed(self, *args, **kwargs):
        kantar_v = self.views.get("KANTAR_TAKIP")
        if kantar_v and hasattr(kantar_v, "refresh_kantar_takip_table"):
            self._schedule_ui(kantar_v.refresh_kantar_takip_table)

    def apply_role_permissions(self, user):
        role = user.get("role", "operator")
        if role != "admin":
            if hasattr(self.sidebar, "btn_nav_users"):
                self.sidebar.btn_nav_users.pack_forget()

    def show_change_password_dialog(self):
        # Şifre değiştirme modalı
        dlg = tk.Toplevel(self.root)
        dlg.title("🔑 Şifre Değiştir")
        dlg.geometry("380x260")
        dlg.configure(bg="#f8fafc")
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="Yeni Şifrenizi Belirleyin", font=("Segoe UI", 11, "bold"), bg="#f8fafc", fg="#0f172a").pack(pady=12)
        f = tk.Frame(dlg, bg="#f8fafc", padx=20)
        f.pack(fill=tk.BOTH, expand=True)

        tk.Label(f, text="Mevcut Şifre:", bg="#f8fafc", font=("Segoe UI", 9)).pack(anchor="w")
        txt_old = tk.Entry(f, show="*", font=("Segoe UI", 10))
        txt_old.pack(fill=tk.X, pady=(2, 8))

        tk.Label(f, text="Yeni Şifre:", bg="#f8fafc", font=("Segoe UI", 9)).pack(anchor="w")
        txt_new = tk.Entry(f, show="*", font=("Segoe UI", 10))
        txt_new.pack(fill=tk.X, pady=(2, 12))

        def save_pwd():
            old_p = txt_old.get().strip()
            new_p = txt_new.get().strip()
            if not old_p or not new_p:
                messagebox.showwarning("Uyarı", "Lütfen tüm alanları doldurun.")
                return
            if get_auth_manager:
                auth = get_auth_manager()
                changer = getattr(auth, "change_own_password", None) or getattr(auth, "change_password", None)
                ok, msg = changer(self.current_user["username"], old_p, new_p)
                if ok:
                    messagebox.showinfo("Başarılı", "✅ Şifreniz başarıyla değiştirildi!")
                    dlg.destroy()
                else:
                    messagebox.showerror("Hata", msg)
            else:
                dlg.destroy()

        tk.Button(f, text="💾 Şifreyi Güncelle", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#ffffff", padx=12, pady=6, relief=tk.FLAT, cursor="hand2", command=save_pwd).pack(fill=tk.X)

    def _on_tk_callback_exception(self, exc, val, tb):
        report_critical("ui", "Arayüz geri çağrısı hata verdi", val, app=self)
        try:
            import traceback
            traceback.print_exception(exc, val, tb)
        except Exception:
            pass

    def _shutdown_ui(self, logout_auth=True):
        prepare_shutdown(self, logout_auth=logout_auth)
        try:
            self.root.destroy()
        except Exception:
            pass

    def do_logout(self):
        if messagebox.askyesno("Çıkış Onayı", "Oturumu kapatmak istiyor musunuz?"):
            self._shutdown_ui(logout_auth=True)
            if get_auth_manager:
                try:
                    from tools.dogruer_master_suite.login_dialog import prompt_login_dialog
                    new_user = prompt_login_dialog()
                    if new_user:
                        new_root = tk.Tk()
                        app = DogruerMasterSuiteApp(new_root, current_user=new_user)
                        new_root.mainloop()
                except Exception as e:
                    report_critical("auth", "Yeniden giriş başarısız", e)

    def on_app_close(self):
        self._shutdown_ui(logout_auth=True)
