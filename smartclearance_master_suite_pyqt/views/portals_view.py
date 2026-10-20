# -*- coding: utf-8 -*-
from __future__ import annotations
"""
portals_view.py — Entegre Portallar & WebEngine Görünümleri (PyQt6 - Dark Obsidian)
1. QNB eSolutions Portal & Fatura Eşleştirici:
   - PopupWebEngineView & SilentWebEnginePage (Temiz popup ve printToPdf desteği)
   - InvoicePdfMerger (Seçilen faturaları arka planda tek PDF'te birleştirme)
   - loadFinished: Otomatik şifre doldurma, __ALL_EVRIM_DATA enjeksiyonu, fatura_eslestirici.js çalıştırma
   - titleChanged: PT_QUEUE_EXPORT (Para Talep kuyruğuna aktarım & Supabase logu) & PDF_MERGE_EXPORT
2. Hankook GLP Global Lojistik Portalı
3. Doğruer Online & Canlı Evrim Portalı (dogruer_sync.js)
4. Doğruer Online Para Talep Portalı & QNB Fatura Kuyruğu
"""

import os
import sys
import json
import re
import tempfile
import datetime
import webbrowser
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal, QObject, QMarginsF
from PyQt6.QtGui import QKeySequence, QShortcut, QPageLayout, QPageSize

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import (
        QWebEngineProfile, QWebEngineScript, QWebEnginePage,
        QWebEngineDownloadRequest
    )
    HAS_WEBENGINE = True
except (ImportError, Exception):
    HAS_WEBENGINE = False
    QWebEngineView = QWidget
    QWebEngineProfile = None
    QWebEngineScript = None
    QWebEnginePage = None
    QWebEngineDownloadRequest = Any

from .base_view import BaseView

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
TALEP_QUEUE_PATH = os.path.join(CONFIG_DIR, "talep_queue.json")
EVRIM_DATA_PATH = os.path.join(CONFIG_DIR, "evrim_live_data.json")
DOGRUER_ONLINE_URL = "https://dogruer.online"


def load_talep_queue() -> List[Dict[str, Any]]:
    if os.path.exists(TALEP_QUEUE_PATH):
        try:
            with open(TALEP_QUEUE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def load_evrim_cached_data() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(EVRIM_DATA_PATH):
            with open(EVRIM_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []


def get_autofill_js() -> str:
    """QNB eSolutions giriş alanlarını config.json'daki bilgilerle doldurur."""
    config_path = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("qnb_autofill", True):
                    u = cfg.get("qnb_user", "").replace('\\', '\\\\').replace('"', '\\"')
                    p = cfg.get("qnb_pass", "").replace('\\', '\\\\').replace('"', '\\"')
                    if u and p:
                        return f"""
                        (function() {{
                            function tryFill() {{
                                let uField = document.getElementById('userid') || document.querySelector("input[name='userid']");
                                let pField = document.getElementById('password') || document.querySelector("input[name='password']");
                                if (uField && pField) {{
                                    if (!uField.value) {{
                                        uField.value = "{u}";
                                        uField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        uField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    if (!pField.value) {{
                                        pField.value = "{p}";
                                        pField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        pField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}
                            }}
                            tryFill();
                            setTimeout(tryFill, 800);
                            setTimeout(tryFill, 1800);
                        }})();
                        """
        except Exception:
            pass
    return ""


def get_dogruer_autofill_js() -> str:
    """Doğruer Online giriş alanlarını config.json'daki bilgilerle doldurur."""
    config_path = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("dogruer_autofill", True):
                    u = cfg.get("dogruer_user", "").replace('\\', '\\\\').replace('"', '\\"')
                    p = cfg.get("dogruer_pass", "").replace('\\', '\\\\').replace('"', '\\"')
                    if u and p:
                        return f"""
                        (function() {{
                            function tryFill() {{
                                let uField = document.getElementById('UserName') || document.getElementById('Email') || document.querySelector("input[name='UserName']") || document.querySelector("input[type='email']") || document.querySelector("input[name*='User']");
                                let pField = document.getElementById('Password') || document.querySelector("input[name='Password']") || document.querySelector("input[type='password']");
                                let rField = document.getElementById('RememberMe') || document.querySelector("input[name*='Remember']");
                                if (rField && !rField.checked) {{
                                    rField.checked = true;
                                    rField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                }}
                                if (uField && pField) {{
                                    if (!uField.value) {{
                                        uField.value = "{u}";
                                        uField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        uField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    if (!pField.value) {{
                                        pField.value = "{p}";
                                        pField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        pField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}
                            }}
                            tryFill();
                            setTimeout(tryFill, 800);
                            setTimeout(tryFill, 1800);
                        }})();
                        """
        except Exception:
            pass
    return ""


def get_glp_autofill_js() -> str:
    """Hankook GLP giriş alanlarını config.json'daki bilgilerle doldurur."""
    config_path = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("glp_autofill", True):
                    u = cfg.get("glp_user", "").replace('\\', '\\\\').replace('"', '\\"')
                    p = cfg.get("glp_pass", "").replace('\\', '\\\\').replace('"', '\\"')
                    if u and p:
                        return f"""
                        (function() {{
                            function tryFill() {{
                                let uField = document.getElementById('userId') || document.getElementById('user_id') || document.querySelector("input[name='userId']") || document.querySelector("input[name='user_id']") || document.querySelector("input[name*='user']");
                                let pField = document.getElementById('password') || document.getElementById('passwd') || document.querySelector("input[name='password']") || document.querySelector("input[type='password']");
                                if (uField && pField) {{
                                    if (!uField.value) {{
                                        uField.value = "{u}";
                                        uField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        uField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    if (!pField.value) {{
                                        pField.value = "{p}";
                                        pField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        pField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}
                            }}
                            tryFill();
                            setTimeout(tryFill, 800);
                            setTimeout(tryFill, 1800);
                        }})();
                        """
        except Exception:
            pass
    return ""


if HAS_WEBENGINE:
    class SilentWebEnginePage(QWebEnginePage):
        """Konsol mesajlarını susturan sayfa bileşeni."""
        def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
            pass


    class PopupWebEngineView(QWebEngineView):
        """Popup pencereleri temiz izole profilde açan ve printToPdf destekleyen tarayıcı."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.popups = []

        def createWindow(self, type):
            popup = QWebEngineView()
            clean_popup_profile = QWebEngineProfile(f"QNB_PopupProfile_{id(popup)}", popup)
            popup_page = SilentWebEnginePage(clean_popup_profile, popup)
            popup.setPage(popup_page)
            popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            popup.resize(800, 700)
            popup.setMinimumSize(600, 500)
            popup.setWindowTitle("e-Fatura Görüntüleyici")
            popup.titleChanged.connect(
                lambda t: popup.setWindowTitle(f"e-Fatura: {t}" if t and t != "about:blank" else "e-Fatura")
            )

            # JS'den window.print() çağrıldığında tetiklenir
            def handle_print():
                file_path, _ = QFileDialog.getSaveFileName(popup, "PDF Kaydet", "Fatura.pdf", "PDF Dosyaları (*.pdf)")
                if file_path:
                    def on_pdf_done(file_path_res, success):
                        if success:
                            QMessageBox.information(popup, "Başarılı", "PDF başarıyla kaydedildi!")
                            try:
                                os.startfile(file_path)
                            except Exception:
                                pass
                            popup.close()

                    layout = QPageLayout(
                        QPageSize(QPageSize.PageSizeId.A4),
                        QPageLayout.Orientation.Portrait,
                        QMarginsF(0, 0, 0, 0)
                    )
                    popup.page().printToPdf(file_path, layout)
                    popup.page().pdfPrintingFinished.connect(on_pdf_done)

            popup.page().printRequested.connect(handle_print)
            popup.show()
            self.popups.append(popup)
            return popup


    class InvoicePdfMerger(QObject):
        """Seçilen faturaları arka planda tek bir PDF dosyasında birleştiren motor."""
        finished = pyqtSignal(str, bool, str)

        def __init__(self, invoices: list, output_path: str, profile=None, parent=None):
            super().__init__(parent)
            self.invoices = invoices
            self.output_path = output_path
            self.temp_dir = tempfile.mkdtemp(prefix="qnb_invoices_")
            self.temp_pdfs = []
            self.current_idx = 0
            self.clean_profile = QWebEngineProfile(f"QNB_PdfMerger_{id(self)}", self)
            self.page = SilentWebEnginePage(self.clean_profile, self)
            self.page.pdfPrintingFinished.connect(self._on_pdf_printed)

        def start(self):
            self._process_current()

        def _process_current(self):
            if self.current_idx >= len(self.invoices):
                self._merge_all()
                return

            inv = self.invoices[self.current_idx]
            temp_pdf = os.path.join(self.temp_dir, f"inv_{self.current_idx}.pdf")
            self.temp_pdfs.append(temp_pdf)

            raw_html = inv.get("html", "")
            no_panel_style = """
            <style>
                #gumruk-eslestirici-panel,
                #gumruk-sonuc-modal,
                .gumruk-no-print,
                [id^="gumruk-"] {
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                }
            </style>
            """
            if "</head>" in raw_html:
                clean_html = raw_html.replace("</head>", f"{no_panel_style}</head>")
            else:
                clean_html = f"{no_panel_style}{raw_html}"

            def _on_loaded(ok):
                try:
                    self.page.loadFinished.disconnect(_on_loaded)
                except Exception:
                    pass
                layout = QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Portrait,
                    QMarginsF(0, 0, 0, 0)
                )
                self.page.printToPdf(temp_pdf, layout)

            self.page.loadFinished.connect(_on_loaded)
            self.page.setHtml(clean_html, QUrl("https://portal.qnbesolutions.com.tr/"))

        def _on_pdf_printed(self, file_path, success):
            self.current_idx += 1
            self._process_current()

        def _merge_all(self):
            try:
                valid_pdfs = [p for p in self.temp_pdfs if os.path.exists(p) and os.path.getsize(p) > 0]
                if not valid_pdfs:
                    raise Exception("Birleştirilecek geçerli PDF dosyası bulunamadı.")

                merged_successfully = False
                last_err = ""

                # 1. Yöntem: pypdf
                try:
                    from pypdf import PdfWriter
                    writer = PdfWriter()
                    for p in valid_pdfs:
                        writer.append(p)
                    with open(self.output_path, "wb") as f:
                        writer.write(f)
                    writer.close()
                    merged_successfully = True
                except Exception as e:
                    last_err = str(e)

                # 2. Yöntem: PyPDF2
                if not merged_successfully:
                    try:
                        from PyPDF2 import PdfMerger
                        merger = PdfMerger()
                        for p in valid_pdfs:
                            merger.append(p)
                        merger.write(self.output_path)
                        merger.close()
                        merged_successfully = True
                    except Exception as e:
                        last_err = str(e)

                # 3. Yöntem: PyMuPDF (fitz)
                if not merged_successfully:
                    try:
                        try:
                            import pymupdf as fitz
                        except ImportError:
                            import fitz
                        merged = fitz.open()
                        for p in valid_pdfs:
                            doc = fitz.open(p)
                            merged.insert_pdf(doc)
                            doc.close()
                        merged.save(self.output_path)
                        merged.close()
                        merged_successfully = True
                    except Exception as e:
                        last_err = str(e)

                # Geçici dosyaları temizle
                for p in self.temp_pdfs:
                    try: os.remove(p)
                    except Exception: pass
                try: os.rmdir(self.temp_dir)
                except Exception: pass

                if merged_successfully and os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                    self.finished.emit(self.output_path, True, "")
                else:
                    self.finished.emit(self.output_path, False, f"PDF birleştirme başarısız oldu: {last_err}")
            except Exception as e:
                self.finished.emit(self.output_path, False, str(e))
else:
    class SilentWebEnginePage(object): pass
    class PopupWebEngineView(object): pass
    class InvoicePdfMerger(object): pass


# ══════════════════════════════════════════════════════════════════════
# 1. QNB PORTAL & FATURA EŞLEŞTİRİCİ
# ══════════════════════════════════════════════════════════════════════
class QNBPortalView(BaseView):
    """Gömülü QNB eSolutions Portalı & Fatura Eşleştirici Görünümü (PyQt6 - Dark Obsidian)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.browser: Optional[PopupWebEngineView] = None
        self.current_merger: Optional[InvoicePdfMerger] = None
        self._page_loaded = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        # Üst Kontrol Barı (Dark Obsidian)
        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 4, 10, 4)
        tb_layout.setSpacing(8)

        lbl_title = QLabel("💳 QNB eSolutions Portalı & Fatura Eşleştirici (Doğrudan Gömülü)", top_bar)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #38bdf8; border: none;")
        tb_layout.addWidget(lbl_title)

        tb_layout.addStretch()

        # Zoom Kontrolleri
        btn_zm = QPushButton("🔍 -", top_bar)
        btn_zm.setToolTip("Küçült")
        btn_zm.setStyleSheet(self._btn_bar_style())
        btn_zm.setFixedWidth(32)
        btn_zm.clicked.connect(self._zoom_out)
        tb_layout.addWidget(btn_zm)

        btn_zr = QPushButton("100%", top_bar)
        btn_zr.setToolTip("Varsayılan Yakınlaştırma")
        btn_zr.setStyleSheet(self._btn_bar_style())
        btn_zr.setFixedWidth(44)
        btn_zr.clicked.connect(self._zoom_reset)
        tb_layout.addWidget(btn_zr)

        btn_zp = QPushButton("🔍 +", top_bar)
        btn_zp.setToolTip("Büyüt")
        btn_zp.setStyleSheet(self._btn_bar_style())
        btn_zp.setFixedWidth(32)
        btn_zp.clicked.connect(self._zoom_in)
        tb_layout.addWidget(btn_zp)

        btn_refresh = QPushButton("🔄 Yenile (F5)", top_bar)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #0369a1;
                border: 1px solid #38bdf8;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #0284c7; }
        """)
        btn_refresh.clicked.connect(self._reload_browser)
        tb_layout.addWidget(btn_refresh)

        btn_inject = QPushButton("🚀 Eşleştiriciyi Aç", top_bar)
        btn_inject.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                border: 1px solid #a78bfa;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #6d28d9; }
        """)
        btn_inject.clicked.connect(lambda: self._inject_eslestirici(silent=False))
        tb_layout.addWidget(btn_inject)

        btn_copy_bm = QPushButton("⭐ Kodu Kopyala", top_bar)
        btn_copy_bm.setStyleSheet("""
            QPushButton {
                background-color: #d97706;
                border: 1px solid #fbbf24;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #b45309; }
        """)
        btn_copy_bm.clicked.connect(self.copy_qnb_bookmarklet_code)
        tb_layout.addWidget(btn_copy_bm)

        btn_copy_bl = QPushButton("📋 Açık BL Kopyala", top_bar)
        btn_copy_bl.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                border: 1px solid #34d399;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        btn_copy_bl.clicked.connect(self.copy_active_bl_list)
        tb_layout.addWidget(btn_copy_bl)

        layout.addWidget(top_bar)

        # Tarayıcı Alanı
        if HAS_WEBENGINE:
            # Kalıcı Profil & Çerez/Giriş Bilgisi Depolama
            base_dir = os.path.join(CONFIG_DIR, "QNB_Profile")
            storage_dir = os.path.join(base_dir, "Storage")
            cache_dir = os.path.join(base_dir, "Cache")
            os.makedirs(storage_dir, exist_ok=True)
            os.makedirs(cache_dir, exist_ok=True)

            self.browser = PopupWebEngineView(self)
            self.profile = QWebEngineProfile("SmartClearance_QNB_Storage", self.browser)
            self.profile.setPersistentStoragePath(storage_dir)
            self.profile.setCachePath(cache_dir)
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
            self.page = SilentWebEnginePage(self.profile, self.browser)
            self.browser.setPage(self.page)

            # İndirme Yöneticisi
            self.page.profile().downloadRequested.connect(self.on_download_requested)

            # Dinleyiciler
            self.browser.loadFinished.connect(self.on_load_finished)
            self.browser.titleChanged.connect(self.on_title_changed)

            # Lazy load: Sayfa ilk kez sekme açıldığında (on_activate) yüklenecektir
            layout.addWidget(self.browser, stretch=1)
        else:
            lbl_err = QLabel("PyQt6 WebEngine bileşeni sistemde bulunamadı.", self)
            lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_err, stretch=1)

    def on_activate(self):
        """Sekme aktifleştiğinde sayfayı lazy load ile yükle."""
        if not getattr(self, "_page_loaded", False) and self.browser:
            self._page_loaded = True
            self.browser.setUrl(QUrl("https://portal.qnbesolutions.com.tr/yonetim/"))

        # Kısayol: F5
        sc_f5 = QShortcut(QKeySequence(Qt.Key.Key_F5), self)
        sc_f5.activated.connect(self._reload_browser)

    def _btn_bar_style(self) -> str:
        return """
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f1f5f9;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """

    def on_load_finished(self, ok: bool):
        """Sayfa yüklendiğinde otomatik doldurma, Evrim verisi ve eşleştiriciyi enjekte et."""
        if ok and self.browser:
            autofill_js = get_autofill_js()
            if autofill_js:
                self.browser.page().runJavaScript(autofill_js)

            self.browser.page().runJavaScript("window.__IS_PYQT_EMBED = true;")

            try:
                ev_data = load_evrim_cached_data()
                if ev_data:
                    clean_ev = [
                        {
                            "dosya_no": x.get("dosya_no") or x.get("dosya", ""),
                            "bl": x.get("bl", ""),
                            "ref": x.get("hankook_ref") or x.get("ref", ""),
                            "beyan": x.get("beyanname_no", "")
                        }
                        for x in ev_data if isinstance(x, dict)
                    ]
                    self.browser.page().runJavaScript(f"window.__ALL_EVRIM_DATA = {json.dumps(clean_ev)};")
            except Exception as e:
                print(f"Error injecting Evrim data: {e}")

            self._inject_eslestirici(silent=True)

    def on_title_changed(self, title: str):
        """Sayfa başlığı üzerinden gelen IPC komutlarını dinler."""
        if not title:
            return

        if title.startswith("PT_QUEUE_EXPORT:"):
            def on_queue_data(data_json):
                if data_json:
                    try:
                        os.makedirs(CONFIG_DIR, exist_ok=True)
                        with open(TALEP_QUEUE_PATH, "w", encoding="utf-8") as f:
                            f.write(data_json)

                        # Aktivite Günlüğüne kaydet
                        try:
                            from tools.supabase_sync_manager import get_supabase_manager
                            sm = get_supabase_manager()
                            items = json.loads(data_json)
                            if sm and isinstance(items, list):
                                for itm in items:
                                    d_no = itm.get("dosya_no") or itm.get("dosya", "")
                                    f_no = itm.get("fatura_no") or itm.get("fatura", "")
                                    tutar = itm.get("tutar") or ""
                                    sm.add_activity_log(
                                        dosya_no=d_no,
                                        islem_tipi="FATURA",
                                        baslik=f"Fatura Talep Kuyruğuna Eklendi ({f_no})",
                                        icerik=f"Fatura No: {f_no} | Tutar: {tutar} TL | Para Talep Kuyruğuna Aktarıldı",
                                        etiket="Tamamlandı",
                                        metadata=itm
                                    )
                        except Exception as ex:
                            print(f"Activity Hub log error: {ex}")

                        self.show_info(
                            "Talep Kuyruğu",
                            "✅ Faturalar başarıyla Para Talep Kuyruğuna aktarıldı ve Aktivite Günlüğü güncellendi!"
                        )
                    except Exception as e:
                        self.show_error("Hata", f"Talep kuyruğu kaydedilemedi: {e}")

            self.browser.page().runJavaScript("document.body.getAttribute('data-pt-queue')", on_queue_data)

        elif title.startswith("PDF_MERGE_EXPORT:"):
            def on_pdf_data(data_json):
                if not data_json:
                    self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                    return
                try:
                    invoices = json.loads(data_json)
                    if not invoices:
                        self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                        return

                    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    if len(invoices) == 1:
                        f_no = invoices[0].get("faturaNo", "Belge")
                        default_name = f"Fatura_{f_no}.pdf"
                    else:
                        default_name = f"Hankook_Toplu_Faturalar_{len(invoices)}_Adet_{now_str}.pdf"

                    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                    default_path = os.path.join(desktop_dir, default_name)

                    file_path, _ = QFileDialog.getSaveFileName(
                        self, "Tüm Faturaları Tek PDF Olarak Kaydet", default_path, "PDF Dosyaları (*.pdf)"
                    )
                    if not file_path:
                        self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                        return

                    self.current_merger = InvoicePdfMerger(invoices, file_path, self.profile, self)

                    def on_merge_done(out_path, success, err_msg):
                        self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(true);")
                        if success:
                            QMessageBox.information(
                                self, "Başarılı",
                                f"✅ Toplam {len(invoices)} adet fatura başarıyla tek PDF olarak birleştirildi!\n\nDosya Adı: {os.path.basename(out_path)}"
                            )
                            try:
                                os.startfile(out_path)
                            except Exception:
                                pass
                        else:
                            QMessageBox.critical(self, "Hata", f"PDF birleştirme hatası:\n{err_msg}")

                    self.current_merger.finished.connect(on_merge_done)
                    self.current_merger.start()
                except Exception as err:
                    self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                    self.show_error("Hata", f"PDF verisi işlenirken hata oluştu:\n{err}")

            self.browser.page().runJavaScript("document.body.getAttribute('data-pdf-queue')", on_pdf_data)

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.downloadFileName())
        file_path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", default_path)
        if file_path:
            download_item.setDownloadDirectory(os.path.dirname(file_path))
            download_item.setDownloadFileName(os.path.basename(file_path))
            download_item.accept()

    def _reload_browser(self):
        if self.browser:
            self.browser.reload()

    def _zoom_in(self):
        if self.browser:
            self.browser.setZoomFactor(self.browser.zoomFactor() + 0.1)

    def _zoom_out(self):
        if self.browser:
            self.browser.setZoomFactor(max(0.5, self.browser.zoomFactor() - 0.1))

    def _zoom_reset(self):
        if self.browser:
            self.browser.setZoomFactor(1.0)

    def _inject_eslestirici(self, silent: bool = False):
        if not self.browser:
            return
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidates = [
            os.path.join(root_dir, "tools", "qnb_fatura_eslestirici", "fatura_eslestirici.js"),
            os.path.join(os.getcwd(), "tools", "qnb_fatura_eslestirici", "fatura_eslestirici.js")
        ]
        p = next((x for x in candidates if os.path.exists(x)), candidates[0])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                js_code = f.read()
            self.browser.page().runJavaScript("window.__IS_PYQT_EMBED = true;")
            self.browser.page().runJavaScript(js_code)
            if not silent:
                self.show_info("Fatura Eşleştirici", "🚀 QNB Fatura Eşleştirici betiği başarıyla enjekte edildi!")
        else:
            if not silent:
                self.show_warning("Bulunamadı", f"fatura_eslestirici.js dosyası bulunamadı:\n{p}")

    def copy_qnb_bookmarklet_code(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidates = [
            os.path.join(root_dir, "tools", "qnb_fatura_eslestirici", "fatura_eslestirici.js"),
            os.path.join(os.getcwd(), "tools", "qnb_fatura_eslestirici", "fatura_eslestirici.js")
        ]
        p = next((x for x in candidates if os.path.exists(x)), candidates[0])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            bookmarklet = "javascript:" + code.replace("\n", " ")
            self.copy_to_clipboard(bookmarklet)
            self.show_info("Kopyalandı", "⭐ QNB Fatura Eşleştirici bookmarklet kodu panoya kopyalandı!")
        else:
            self.show_warning("Bulunamadı", f"fatura_eslestirici.js dosyası bulunamadı:\n{p}")

    def copy_active_bl_list(self):
        rows = []
        seen = set()
        records = getattr(self.main_window.engine, "records", []) if self.main_window and hasattr(self.main_window, "engine") else []
        for r in records:
            bl = str(r.get("bl") or "").strip()
            if not r.get("kapanis") and bl and len(bl) >= 5:
                if bl not in seen:
                    seen.add(bl)
                    d_no = str(r.get("dosya_no") or r.get("dosya") or "").strip()
                    ref_no = str(r.get("hankook_ref") or r.get("ref") or "").strip()
                    if d_no or ref_no:
                        rows.append(f"{d_no}\t{ref_no}\t{bl}")
                    else:
                        rows.append(bl)

        if rows:
            self.copy_to_clipboard("\n".join(rows))
            self.show_info("Panoya Kopyalandı", f"✅ Toplam {len(rows)} adet açık iş (Dosya No, Referans, Konşimento) panoya kopyalandı!\n\nŞimdi QNB ekranındaki kutucuğa yapıştırıp (Ctrl+V) taratabilirsiniz.")
        else:
            self.show_warning("Uyarı", "Açık konşimento bulunamadı.")


# ══════════════════════════════════════════════════════════════════════
# 2. GLP PORTAL
# ══════════════════════════════════════════════════════════════════════
class GLPPortalView(BaseView):
    """Gömülü Hankook GLP Global Lojistik Portalı Görünümü (PyQt6 - Dark Obsidian)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.browser: Optional[QWebEngineView] = None
        self._page_loaded = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 4, 10, 4)
        tb_layout.setSpacing(8)

        lbl_info = QLabel("🚛 Hankook GLP Lojistik Portalı (glp.hankooktech.com)", top_bar)
        lbl_info.setStyleSheet("font-size: 12px; font-weight: 800; color: #38bdf8; border: none;")
        tb_layout.addWidget(lbl_info)

        tb_layout.addStretch()

        btn_zm = QPushButton("🔍 -", top_bar); btn_zm.setFixedWidth(32); btn_zm.clicked.connect(self._zoom_out)
        btn_zm.setStyleSheet(self._btn_bar_style())
        btn_zr = QPushButton("100%", top_bar); btn_zr.setFixedWidth(44); btn_zr.clicked.connect(self._zoom_reset)
        btn_zr.setStyleSheet(self._btn_bar_style())
        btn_zp = QPushButton("🔍 +", top_bar); btn_zp.setFixedWidth(32); btn_zp.clicked.connect(self._zoom_in)
        btn_zp.setStyleSheet(self._btn_bar_style())
        tb_layout.addWidget(btn_zm); tb_layout.addWidget(btn_zr); tb_layout.addWidget(btn_zp)

        btn_refresh = QPushButton("🔄 Yenile (F5)", top_bar)
        btn_refresh.setStyleSheet(self._btn_bar_style())
        btn_refresh.clicked.connect(self._reload_browser)
        tb_layout.addWidget(btn_refresh)

        btn_open_ext = QPushButton("🌐 Harici Tarayıcıda Aç", top_bar)
        btn_open_ext.setStyleSheet(self._btn_bar_style())
        btn_open_ext.clicked.connect(lambda: webbrowser.open("https://glp.hankooktech.com/login.html?redirectUrl=%2FMAIN%2Fmain.html%3Flang%3Dko"))
        tb_layout.addWidget(btn_open_ext)

        btn_copy_bl = QPushButton("📋 Açık BL Kopyala", top_bar)
        btn_copy_bl.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                border: 1px solid #34d399;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        btn_copy_bl.clicked.connect(self.copy_active_bl_list)
        tb_layout.addWidget(btn_copy_bl)

        layout.addWidget(top_bar)

        if HAS_WEBENGINE:
            self.browser = QWebEngineView(self)
            self.page = SilentWebEnginePage(self.browser)
            self.browser.setPage(self.page)
            self.browser.loadFinished.connect(self._on_glp_load_finished)
            layout.addWidget(self.browser, stretch=1)
        else:
            layout.addWidget(QLabel("GLP Portalı WebEngine hazır değil."))

    def on_activate(self):
        """Sekme aktifleştiğinde sayfayı lazy load ile yükle."""
        if not getattr(self, "_page_loaded", False) and self.browser:
            self._page_loaded = True
            self.browser.setUrl(QUrl("https://glp.hankooktech.com/login.html?redirectUrl=%2FMAIN%2Fmain.html%3Flang%3Dko"))

    def _on_glp_load_finished(self, ok: bool):
        if ok and self.browser:
            autofill_js = get_glp_autofill_js()
            if autofill_js:
                self.browser.page().runJavaScript(autofill_js)

    def _btn_bar_style(self) -> str:
        return """
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f1f5f9;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """

    def _reload_browser(self):
        if self.browser: self.browser.reload()

    def _zoom_in(self):
        if self.browser: self.browser.setZoomFactor(self.browser.zoomFactor() + 0.1)

    def _zoom_out(self):
        if self.browser: self.browser.setZoomFactor(max(0.5, self.browser.zoomFactor() - 0.1))

    def _zoom_reset(self):
        if self.browser: self.browser.setZoomFactor(1.0)

    def copy_active_bl_list(self):
        bl_list = []
        records = getattr(self.main_window.engine, "records", []) if self.main_window and hasattr(self.main_window, "engine") else []
        for r in records:
            bl = str(r.get("bl") or "").strip()
            if not r.get("kapanis") and len(bl) >= 5 and bl not in bl_list:
                bl_list.append(bl)

        if bl_list:
            self.copy_to_clipboard("\n".join(bl_list))
            self.show_info("Panoya Kopyalandı", f"✅ Toplam {len(bl_list)} adet açık Konşimento (B/L) numarası kopyalandı!")
        else:
            self.show_warning("Uyarı", "Açık konşimento bulunamadı.")


# ══════════════════════════════════════════════════════════════════════
# 3. DOĞRUER ONLINE PORTAL
# ══════════════════════════════════════════════════════════════════════
class DogruerPortalView(BaseView):
    """Gömülü Doğruer Online & Canlı Evrim Portalı Görünümü (PyQt6 - Dark Obsidian)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.browser: Optional[QWebEngineView] = None
        self._page_loaded = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 4, 10, 4)
        tb_layout.setSpacing(8)

        lbl_info = QLabel("🌐 Doğruer Online Portalı (dogruer.online) - Evrim Canlı Entegrasyon", top_bar)
        lbl_info.setStyleSheet("font-size: 12px; font-weight: 800; color: #38bdf8; border: none;")
        tb_layout.addWidget(lbl_info)

        tb_layout.addStretch()

        self.btn_auto_login = QPushButton("⚡ Otomatik Giriş & Çek", top_bar)
        self.btn_auto_login.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                border: 1px solid #34d399;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self.btn_auto_login.clicked.connect(self.trigger_auto_login)
        tb_layout.addWidget(self.btn_auto_login)

        btn_sync = QPushButton("🔄 Sayfaları Tara & Çek", top_bar)
        btn_sync.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        btn_sync.clicked.connect(self.trigger_dogruer_sync)
        tb_layout.addWidget(btn_sync)

        btn_copy_open = QPushButton("📋 Açık Dosyaları Kopyala", top_bar)
        btn_copy_open.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f1f5f9;
                font-weight: 600;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        btn_copy_open.clicked.connect(self.copy_all_open_dosya_nos)
        tb_layout.addWidget(btn_copy_open)

        btn_copy_bm = QPushButton("⭐ Kodu Kopyala", top_bar)
        btn_copy_bm.setStyleSheet("""
            QPushButton {
                background-color: #d97706;
                border: 1px solid #fbbf24;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 8px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #b45309; }
        """)
        btn_copy_bm.clicked.connect(self.copy_dogruer_bookmarklet_code)
        tb_layout.addWidget(btn_copy_bm)

        btn_ext = QPushButton("🌐 Harici Aç", top_bar)
        btn_ext.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f1f5f9;
                font-weight: 600;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        btn_ext.clicked.connect(lambda: webbrowser.open(DOGRUER_ONLINE_URL))
        tb_layout.addWidget(btn_ext)

        layout.addWidget(top_bar)

        # Durum Çubuğu
        self.lbl_auto_status = QLabel("", self)
        self.lbl_auto_status.setStyleSheet("font-size: 11px; color: #94a3b8; padding-left: 4px;")
        layout.addWidget(self.lbl_auto_status)

        if HAS_WEBENGINE:
            self.browser = QWebEngineView(self)
            self.page = SilentWebEnginePage(self.browser)
            self.browser.setPage(self.page)
            self.browser.loadFinished.connect(self._on_dogruer_load_finished)
            self.browser.titleChanged.connect(self._on_dogruer_title_changed)
            layout.addWidget(self.browser, stretch=1)
        else:
            layout.addWidget(QLabel("Doğruer Online WebEngine hazır değil."))

    def on_activate(self):
        """Sekme aktifleştiğinde sayfayı lazy load ile yükle."""
        if not getattr(self, "_page_loaded", False) and self.browser:
            self._page_loaded = True
            self.browser.setUrl(QUrl(DOGRUER_ONLINE_URL))

    def _on_dogruer_load_finished(self, ok: bool):
        if ok and self.browser:
            autofill_js = get_dogruer_autofill_js()
            if autofill_js:
                self.browser.page().runJavaScript(autofill_js)

    def _on_dogruer_title_changed(self, title: str):
        """dogruer_sync.js'in document.title uzerinden gonderdigi senkronizasyon tamamlandi sinyalini yakalar."""
        if not title:
            return
        if "DOGRUER_SYNC_DONE:" in title:
            self.lbl_auto_status.setText("📥 Evrim verileri alındı, yerel veritabanına işleniyor...")
            self.lbl_auto_status.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 600; padding-left: 4px;")
            self.browser.page().runJavaScript(
                "document.body.getAttribute('data-sync-result')",
                self._on_dogruer_sync_data_arrived
            )

    def _on_dogruer_sync_data_arrived(self, json_str):
        if json_str:
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0:
                    os.makedirs(CONFIG_DIR, exist_ok=True)
                    with open(EVRIM_DATA_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    self.lbl_auto_status.setText(f"✅ Başarılı! Toplam {len(data)} dosya Evrim'den çekildi ve kaydedildi.")
                    self.lbl_auto_status.setStyleSheet("font-size: 11px; color: #34d399; font-weight: 700; padding-left: 4px;")

                    if self.main_window:
                        self.main_window.evrim_records = data
                        if hasattr(self.main_window, "view_evrim") and self.main_window.view_evrim:
                            self.main_window.view_evrim.evrim_records = data
                            self.main_window.view_evrim.refresh_evrim_table()
                        if hasattr(self.main_window, "view_cockpit") and self.main_window.view_cockpit:
                            self.main_window.view_cockpit.refresh_cockpit_table()

                    self.show_info(
                        "Evrim Senkronizasyonu Başarılı",
                        f"🎉 Doğruer Online üzerinden {len(data)} dosya başarıyla çekildi!\n\n"
                        "Evrim Veri Merkezi ve Operasyon Masası canlı olarak güncellendi."
                    )
            except Exception as e:
                self.lbl_auto_status.setText(f"❌ Senkronizasyon hatası: {e}")
                self.lbl_auto_status.setStyleSheet("font-size: 11px; color: #ef4444; font-weight: 700; padding-left: 4px;")

    def trigger_auto_login(self):
        if not self.browser: return
        self.lbl_auto_status.setText("🔐 Otomatik giriş komutu gönderildi...")
        self.lbl_auto_status.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 600; padding-left: 4px;")
        autofill_js = get_dogruer_autofill_js()
        if autofill_js:
            self.browser.page().runJavaScript(autofill_js)

        # Buton tıklama JS'i
        click_js = """
        (function() {
            let btn = document.getElementById('btnLogin') || document.querySelector("button[type='submit']") || document.querySelector("input[type='submit']");
            if (btn) btn.click();
        })();
        """
        self.browser.page().runJavaScript(click_js)

        # 2FA Outlook COM kontrolü
        def _check_otp():
            try:
                from tools.dogruer_online_bridge.evrim_imap_reader import EvrimImapReader
                reader = EvrimImapReader()
                code = reader.fetch_latest_otp(timeout_seconds=6, on_progress=lambda m: None)
                if code:
                    fill_otp_js = f"""
                    (function() {{
                        let inp = document.querySelector("input[name*='Otp'], input[name*='Code'], input[name*='Dogrulama']");
                        if (inp) {{
                            inp.value = '{code}';
                            inp.dispatchEvent(new Event('input', {{bubbles:true}}));
                            inp.dispatchEvent(new Event('change', {{bubbles:true}}));
                            let sub = document.querySelector("button[type='submit']");
                            if (sub) sub.click();
                        }}
                    }})();
                    """
                    self.browser.page().runJavaScript(fill_otp_js)
            except Exception:
                pass

        import threading
        threading.Thread(target=_check_otp, daemon=True).start()
        QTimer.singleShot(2500, self.trigger_dogruer_sync)

    def trigger_dogruer_sync(self):
        if not self.browser: return
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        p = os.path.join(root_dir, "tools", "dogruer_online_bridge", "dogruer_sync.js")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            self.lbl_auto_status.setText("⏳ Evrim verileri taranıyor, lütfen bekleyin...")
            self.browser.page().runJavaScript(code)
        else:
            self.show_warning("Bulunamadı", f"dogruer_sync.js dosyası bulunamadı:\n{p}")

    def copy_all_open_dosya_nos(self):
        records = getattr(self.main_window, "evrim_records", []) if self.main_window else []
        dosyalar = [r.get("dosya_no") for r in records if r.get("dosya_no")]
        if dosyalar:
            self.copy_to_clipboard("\n".join(str(d) for d in dosyalar[:50]))
            self.show_info("Kopyalandı", f"📋 {min(len(dosyalar), 50)} adet dosya numarası panoya kopyalandı!")

    def copy_dogruer_bookmarklet_code(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        p = os.path.join(root_dir, "tools", "dogruer_online_bridge", "dogruer_sync.js")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            self.copy_to_clipboard("javascript:" + code.replace("\n", " "))
            self.show_info("Kopyalandı", "⭐ Doğruer Online Senkronizasyon bookmarklet kodu panoya kopyalandı!")


# ══════════════════════════════════════════════════════════════════════
# 4. PARA TALEP PORTALI
# ══════════════════════════════════════════════════════════════════════
class TalepPortalView(BaseView):
    """Gömülü Doğruer Online Para Talep Portalı Görünümü (PyQt6 - Dark Obsidian)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.browser: Optional[QWebEngineView] = None
        self._page_loaded = False
        self.talep_queue = load_talep_queue()
        self.talep_queue_idx = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        # Üst Bar
        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 4, 10, 4)
        tb_layout.setSpacing(8)

        lbl_title = QLabel("💸 Doğruer Online Para Talep Portalı (Gömülü Arayüz)", top_bar)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #38bdf8; border: none;")
        tb_layout.addWidget(lbl_title)

        tb_layout.addStretch()

        btn_refresh = QPushButton("🔄 Sayfayı Yenile", top_bar)
        btn_refresh.setStyleSheet(self._btn_bar_style())
        btn_refresh.clicked.connect(self.reload_talep_page)
        tb_layout.addWidget(btn_refresh)

        btn_copy_bm = QPushButton("⭐ Kodu Kopyala", top_bar)
        btn_copy_bm.setStyleSheet("""
            QPushButton {
                background-color: #d97706;
                border: 1px solid #fbbf24;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 8px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #b45309; }
        """)
        btn_copy_bm.clicked.connect(self.copy_talep_bookmarklet_code)
        tb_layout.addWidget(btn_copy_bm)

        layout.addWidget(top_bar)

        # QNB Fatura Kuyruk Kontrol Barı (Dark Obsidian)
        self.f_talep_queue_bar = QFrame(self)
        self.f_talep_queue_bar.setStyleSheet("""
            QFrame {
                background-color: #0b1e36;
                border: 1px solid #0284c7;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        qb_layout = QHBoxLayout(self.f_talep_queue_bar)
        qb_layout.setContentsMargins(10, 4, 10, 4)
        qb_layout.setSpacing(8)

        self.lbl_q_status = QLabel("📦 QNB Fatura Kuyruğu: Yükleniyor...", self.f_talep_queue_bar)
        self.lbl_q_status.setStyleSheet("font-weight: 700; color: #38bdf8; border: none; font-size: 11px;")
        qb_layout.addWidget(self.lbl_q_status, stretch=1)

        self.btn_q_prev = QPushButton("⏮️ Önceki", self.f_talep_queue_bar)
        self.btn_q_prev.setStyleSheet(self._btn_bar_style())
        self.btn_q_prev.clicked.connect(self.prev_queue_item)
        qb_layout.addWidget(self.btn_q_prev)

        self.btn_q_next = QPushButton("⏭️ Sonraki", self.f_talep_queue_bar)
        self.btn_q_next.setStyleSheet(self._btn_bar_style())
        self.btn_q_next.clicked.connect(self.skip_queue_item)
        qb_layout.addWidget(self.btn_q_next)

        self.btn_q_clear = QPushButton("🗑️ Temizle", self.f_talep_queue_bar)
        self.btn_q_clear.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                border: 1px solid #ef4444;
                color: #ffffff;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #991b1b; }
        """)
        self.btn_q_clear.clicked.connect(self.clear_talep_queue)
        qb_layout.addWidget(self.btn_q_clear)

        self.btn_q_fill = QPushButton("▶️ Form Doldur", self.f_talep_queue_bar)
        self.btn_q_fill.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                color: #ffffff;
                font-weight: 700;
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_q_fill.clicked.connect(self.fill_current_queue_item)
        qb_layout.addWidget(self.btn_q_fill)

        layout.addWidget(self.f_talep_queue_bar)

        # WebEngine Browser
        if HAS_WEBENGINE:
            self.browser = QWebEngineView(self)
            self.page = SilentWebEnginePage(self.browser)
            self.browser.setPage(self.page)
            self.browser.loadFinished.connect(self._on_talep_load_finished)
            layout.addWidget(self.browser, stretch=1)
        else:
            layout.addWidget(QLabel("Para Talep WebEngine hazır değil."))

        self.update_talep_queue_ui()

    def _btn_bar_style(self) -> str:
        return """
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f1f5f9;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """

    def on_activate(self):
        """Sekme aktifleştiğinde talep kuyruğunu yenile ve sayfayı lazy load ile yükle."""
        self.talep_queue = load_talep_queue()
        self.update_talep_queue_ui()
        if not getattr(self, "_page_loaded", False) and self.browser:
            self._page_loaded = True
            self.browser.setUrl(QUrl("https://dogruer.online/ACC/MoneyRequest/Add"))

    def reload_talep_page(self):
        if self.browser:
            self.browser.setUrl(QUrl("https://dogruer.online/ACC/MoneyRequest/Add"))

    def _on_talep_load_finished(self, ok: bool):
        if ok and self.browser:
            autofill_js = get_dogruer_autofill_js()
            if autofill_js:
                self.browser.page().runJavaScript(autofill_js)

            # Para talep doldurucu scripti
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            p = os.path.join(root_dir, "tools", "dogruer_para_talep", "dogruer_para_talep_doldurucu.js")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    self.browser.page().runJavaScript(f.read())

    def resolve_exact_referance_for_talep(self, item: dict) -> str:
        dosya = str(item.get("dosyaNo") or "").strip()
        ref = str(item.get("ref") or "").strip()
        bl = str(item.get("blNo") or item.get("bl") or "").strip()
        beyan = str(item.get("beyanNo") or item.get("beyanname_no") or "").strip()

        if re.match(r"^26-\d{5,7}$", dosya):
            return dosya

        records = getattr(self.main_window, "evrim_records", []) if self.main_window else []
        for ev in records:
            ev_dosya = ev.get("dosya_no", "").strip()
            ev_beyan = ev.get("beyanname_no", "").strip()
            ev_ref = ev.get("hankook_ref", "").strip()
            if beyan and ev_beyan and (beyan in ev_beyan or ev_beyan in beyan):
                return ev_dosya or ev_ref
            if bl and ((ev_ref and bl in ev_ref) or (ev_beyan and bl in ev_beyan)):
                return ev_dosya or ev_ref
            if ref and ev_ref and (ref in ev_ref or ev_ref in ref):
                return ev_dosya or ev_ref

        return dosya or ref or bl

    def update_talep_queue_ui(self):
        if not hasattr(self, "lbl_q_status"): return

        if self.talep_queue and len(self.talep_queue) > 0:
            if self.talep_queue_idx >= len(self.talep_queue):
                self.talep_queue_idx = 0
            if self.talep_queue_idx < 0:
                self.talep_queue_idx = len(self.talep_queue) - 1

            cur = self.talep_queue_idx
            item = self.talep_queue[cur]
            f_no = item.get("faturaNo", "—")
            tutar = item.get("tutar", "0")
            dosya = self.resolve_exact_referance_for_talep(item)
            note = item.get("aciklama", "FATURA")

            self.lbl_q_status.setText(f"📦 Kuyruk: {cur + 1} / {len(self.talep_queue)} | Fatura: {f_no} ({note}) | Tutar: {tutar} TL | Referans: {dosya}")
            self.btn_q_fill.setText(f"▶️ {cur + 1}. Formu Doldur ({note})")
            self.btn_q_fill.setEnabled(True)
            self.btn_q_next.setEnabled(True)
            self.btn_q_prev.setEnabled(True)
            self.btn_q_clear.setEnabled(True)
            self.f_talep_queue_bar.setStyleSheet("""
                QFrame {
                    background-color: #06281e;
                    border: 1px solid #059669;
                    border-radius: 8px;
                    padding: 6px 10px;
                }
            """)
        else:
            self.lbl_q_status.setText("📦 QNB Fatura Kuyruğu: Boş (QNB'de bulunan faturaları aktararak buraya gönderebilirsiniz)")
            self.btn_q_fill.setText("▶️ Form Doldur")
            self.btn_q_fill.setEnabled(False)
            self.btn_q_next.setEnabled(False)
            self.btn_q_prev.setEnabled(False)
            self.btn_q_clear.setEnabled(False)
            self.f_talep_queue_bar.setStyleSheet("""
                QFrame {
                    background-color: #111827;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    padding: 6px 10px;
                }
            """)

    def fill_current_queue_item(self):
        if not self.talep_queue: return
        if self.talep_queue_idx >= len(self.talep_queue): self.talep_queue_idx = 0

        item = self.talep_queue[self.talep_queue_idx]
        resolved_ref = self.resolve_exact_referance_for_talep(item)
        payload = dict(item)
        payload["dosyaNo"] = resolved_ref
        payload["ref"] = resolved_ref

        if self.browser:
            json_str = json.dumps(payload, ensure_ascii=False)
            fill_js = f"""
            (function() {{
                let data = {json_str};
                window.__LAST_TALEP_DATA = data;
                if (typeof window.fillMoneyRequestForm === 'function') {{
                    window.fillMoneyRequestForm(data);
                }}
            }})();
            """
            self.browser.page().runJavaScript(fill_js)
            self.show_info("Form Dolduruldu", f"✅ {resolved_ref} bilgileri Para Talep formuna aktarıldı!")

        self.talep_queue_idx = (self.talep_queue_idx + 1) % len(self.talep_queue)
        self.update_talep_queue_ui()

    def prev_queue_item(self):
        if self.talep_queue:
            self.talep_queue_idx = (self.talep_queue_idx - 1) % len(self.talep_queue)
            self.update_talep_queue_ui()

    def skip_queue_item(self):
        if self.talep_queue:
            self.talep_queue_idx = (self.talep_queue_idx + 1) % len(self.talep_queue)
            self.update_talep_queue_ui()

    def clear_talep_queue(self):
        self.talep_queue = []
        self.talep_queue_idx = 0
        if os.path.exists(TALEP_QUEUE_PATH):
            try: os.remove(TALEP_QUEUE_PATH)
            except Exception: pass
        self.update_talep_queue_ui()
        self.show_info("Temizlendi", "🗑️ Para Talep kuyruğu temizlendi.")

    def copy_talep_bookmarklet_code(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        p = os.path.join(root_dir, "tools", "dogruer_para_talep", "dogruer_para_talep_doldurucu.js")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            self.copy_to_clipboard("javascript:" + code.replace("\n", " "))
            self.show_info("Kopyalandı", "⭐ Para Talep doldurucu bookmarklet kodu panoya kopyalandı!")
