"""
================================================================================
SMARTCLEARANCE APEX — HANKOOK GÜMRÜK OPERASYON MASASI & EVRAK STÜDYOSU (v1.0 Pro)
================================================================================
Marka       : SmartClearance
Tasarım     : Seamless Linear / Dark Obsidian Architecture (Horizon Standard)
Teknoloji   : PyQt6 + QSplitter + OpenPyXL + PyMuPDF
================================================================================
"""

import os
import sys
import json
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QTabWidget, QFrame, QFileDialog, QMessageBox,
    QProgressBar, QMenu, QTextEdit, QScrollArea, QSizePolicy, QDialog, QComboBox,
    QStackedWidget, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QCursor

# Apex Modülleri
from apex_core.apex_notes_manager import ApexNotesManager
from apex_core.apex_data_engine import (
    ApexDataLoader, DataLoaderThread, Durum, DURUM_BILGILERI, DEFAULT_CONFIG_PATH
)
from apex_core.apex_stepper import ApexStepperWidget
from apex_core.apex_invoice_studio import ApexInvoiceStudioWidget
from apex_core.apex_morning_briefing import ApexMorningBriefingWidget


def load_config():
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"rapor_yolu": r"C:\Yeni klasör\HANKOOK İŞ TAKİP RAPORU.xlsx"}


def save_config(cfg):
    try:
        with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ==============================================================================
# LINEAR / HORIZON DARK QSS TEMASI (KUSURSUZ VE SEAMLESS)
# ==============================================================================

APEX_STYLESHEET = """
QWidget {
    background-color: #080b11;
    color: #e2e8f0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, system-ui, Arial, sans-serif;
    font-size: 12px;
}

/* Header */
#headerFrame {
    background-color: #0f1523;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 8px 16px;
}

#brandTitle {
    font-size: 16px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.3px;
}

#brandBadge {
    background-color: #0284c7;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.5px;
}

QPushButton#brandBadgeBtn {
    background-color: #0284c7;
    color: #ffffff;
    font-size: 10.5px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 5px;
    border: 1px solid #38bdf8;
    letter-spacing: 0.5px;
}
QPushButton#brandBadgeBtn:hover {
    background-color: #0369a1;
    border-color: #7dd3fc;
}

#statusPill {
    background-color: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
}

/* KPI Çubuğu & Kartları */
#kpiBar {
    background-color: #0a0e17;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.kpiCard {
    background-color: #111726;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    padding: 6px 12px;
}
.kpiCard:hover {
    background-color: #162035;
    border-color: rgba(255, 255, 255, 0.2);
}
.kpiTitle {
    color: #64748b;
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.kpiValue {
    font-size: 20px;
    font-weight: 800;
    color: #f8fafc;
    margin-top: 1px;
}

/* Butonlar */
QPushButton {
    background-color: #1a2336;
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: 600;
    font-size: 11.5px;
}
QPushButton:hover {
    background-color: #243049;
    border-color: rgba(255, 255, 255, 0.22);
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton#btnPrimary {
    background-color: #0284c7;
    border-color: #0369a1;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#btnPrimary:hover {
    background-color: #0369a1;
}

/* Arama Kutusu */
QLineEdit {
    background-color: #111726;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 5px 10px;
    color: #f8fafc;
    font-size: 11.5px;
}
QLineEdit:focus {
    border-color: #38bdf8;
    background-color: #141d30;
}

/* Filtre Hapları */
QPushButton.filterPill {
    background-color: transparent;
    color: #94a3b8;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton.filterPill:hover {
    color: #f8fafc;
    background-color: rgba(255, 255, 255, 0.05);
}
QPushButton.filterPill[selected="true"] {
    background-color: rgba(56, 189, 248, 0.16);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 0.45);
}

/* Tablo */
QTableWidget {
    background-color: #0b0f19;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.03);
    selection-background-color: rgba(56, 189, 248, 0.16);
    selection-color: #ffffff;
    outline: none;
    font-size: 11.5px;
}
QHeaderView::section {
    background-color: #101624;
    color: #94a3b8;
    font-weight: 700;
    font-size: 10.5px;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 0.04);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background-color: #151e32;
    color: #38bdf8;
}
QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

/* QSplitter */
QSplitter::handle {
    background-color: #0f172a;
    border-radius: 2px;
}
QSplitter::handle:hover {
    background-color: #38bdf8;
}
QSplitter::handle:horizontal {
    width: 6px;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.07);
    background-color: #0c111d;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background-color: #080b11;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 14px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    border: 1px solid transparent;
    margin-right: 3px;
}
QTabBar::tab:selected {
    color: #ffffff;
    background-color: #0c111d;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-bottom: 2px solid #38bdf8;
}
QTabBar::tab:hover:!selected {
    color: #ffffff;
    background-color: #111726;
}

/* ScrollBar */
QScrollBar:vertical {
    background: #080b11;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 3px;
    min-height: 25px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* Navigation Segmented Tab Buttons */
QPushButton[class="navTabBtn"] {
    background-color: #0b101c;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #94a3b8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
}
QPushButton[class="navTabBtn"]:hover {
    background-color: #172238;
    color: #f8fafc;
    border-color: rgba(56, 189, 248, 0.4);
}
QPushButton[class="navTabBtn"][selected="true"] {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
}

QPushButton[class="btnToggleExpand"] {
    background-color: #111a2d;
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38bdf8;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 5px;
}
QPushButton[class="btnToggleExpand"]:hover {
    background-color: #0284c7;
    color: #ffffff;
    border-color: #38bdf8;
}
"""


class ApexNoteEditDialog(QDialog):
    """Operasyon notunu düzenleme penceresi."""
    def __init__(self, parent, text, tag):
        super().__init__(parent)
        self.setWindowTitle("Operasyon Notunu Düzenle")
        self.setFixedSize(460, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1523;
                color: #ffffff;
                font-family: "Segoe UI", sans-serif;
            }
            QComboBox {
                background-color: #161f30;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QTextEdit {
                background-color: #111726;
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #38bdf8;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top_box = QHBoxLayout()
        lbl_tag = QLabel("Kategori / Etiket:")
        lbl_tag.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        top_box.addWidget(lbl_tag)

        self.cmb_tag = QComboBox()
        self.cmb_tag.addItems(["Banka ID", "Ordino", "TAREKS", "Beyanname", "Sevkiyat", "Özel Not"])
        self.cmb_tag.setCurrentText(tag if tag in ["Banka ID", "Ordino", "TAREKS", "Beyanname", "Sevkiyat", "Özel Not"] else "Özel Not")
        top_box.addWidget(self.cmb_tag)
        top_box.addStretch(1)
        layout.addLayout(top_box)

        self.txt_edit = QTextEdit()
        self.txt_edit.setText(text)
        layout.addWidget(self.txt_edit, 1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.addStretch(1)

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Değişiklikleri Kaydet")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self.accept)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def get_data(self):
        return self.txt_edit.toPlainText().strip(), self.cmb_tag.currentText()


class ApexDetachedWindow(QMainWindow):
    """Herhangi bir Apex modülünü bağımsız (çift monitör uyumlu) pencere yapan pencere çerçevesi."""
    def __init__(self, title, widget, on_close=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"SmartClearance Apex — {title}")
        self.resize(1200, 800)
        self.setStyleSheet(APEX_STYLESHEET)
        self.on_close = on_close
        self.setCentralWidget(widget)

    def closeEvent(self, event):
        if self.on_close:
            self.on_close(self.centralWidget())
        event.accept()


class SmartClearanceApex(QMainWindow):
    """SmartClearance Apex Ana Operasyon Kokpiti."""
    appSwitchRequested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartClearance Apex — Gümrük Operasyon Masası & Evrak Stüdyosu")
        self.setMinimumSize(960, 560)
        scr = QApplication.primaryScreen()
        avail = scr.availableGeometry() if scr else None
        if avail:
            self.resize(min(1480, max(960, int(avail.width() * 0.94))), min(880, max(560, int(avail.height() * 0.92))))
        else:
            self.resize(1360, 800)
        self.setStyleSheet(APEX_STYLESHEET)

        self.config = load_config()
        self.rapor_yolu = self.config.get("rapor_yolu", "")
        self.notes_mgr = ApexNotesManager()

        self.all_shipments = []
        self.filtered_shipments = []
        self.selected_item = None
        self.active_filter = "Tümü"
        self.search_query = ""

        # Çoklu Görünüm ve Pencere Yönetimi
        self.is_table_expanded = False
        self.saved_splitter_sizes = [770, 710]
        self.briefing_window = None
        self.studio_window = None
        self.briefing_placeholder = None
        self.studio_placeholder = None

        # Dosya İzleme (Watcher & Debounce)
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._start_data_load)

        self._setup_ui()
        self._attach_file_watcher()
        self._start_data_load()

    # --------------------------------------------------------------------------
    # ARAYÜZ KURULUMU
    # --------------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Üst Başlık & Görünüm Seçici (Header Bar + Nav Bar + Mini KPI)
        root_layout.addWidget(self._create_header_bar())

        # 2. Ana Çalışma Alanı (QStackedWidget ile 3 Ferah Görünüm)
        self.stacked_widget = QStackedWidget()

        # Sayfa 0: 🌅 Sabah Brifingi & Radar
        self.page_briefing = self._create_briefing_page()
        self.stacked_widget.addWidget(self.page_briefing)

        # Sayfa 1: 📋 Dosya Takip Masası & Kokpit
        self.page_table = self._create_table_page()
        self.stacked_widget.addWidget(self.page_table)

        # Sayfa 2: ⚡ Akıllı Evrak & Fatura Stüdyosu
        self.page_studio = self._create_studio_page()
        self.stacked_widget.addWidget(self.page_studio)

        root_layout.addWidget(self.stacked_widget, 1)

        # 3. Alt Durum Çubuğu
        root_layout.addWidget(self._create_status_bar())

    def _create_header_bar(self):
        hdr = QFrame()
        hdr.setObjectName("headerFrame")
        layout = QHBoxLayout(hdr)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(12)

        # 1. Marka Başlığı
        brand_box = QHBoxLayout()
        brand_box.setSpacing(8)

        lbl_logo = QLabel("SMARTCLEARANCE")
        lbl_logo.setObjectName("brandTitle")

        self.btn_app_switch = QPushButton("APEX ▾")
        self.btn_app_switch.setObjectName("brandBadgeBtn")
        self.btn_app_switch.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_app_switch.setToolTip("SmartClearance sistemleri arasında geçiş yap")
        self.btn_app_switch.clicked.connect(self._show_app_switch_menu)

        brand_box.addWidget(lbl_logo)
        brand_box.addWidget(self.btn_app_switch)
        layout.addLayout(brand_box)

        # 2. Segmented Nav Bar (3 Ana Görünüm)
        nav_box = QHBoxLayout()
        nav_box.setSpacing(6)

        self.btn_nav_briefing = QPushButton("🌅 1. Sabah Brifingi & Radar")
        self.btn_nav_briefing.setProperty("class", "navTabBtn")
        self.btn_nav_briefing.setProperty("selected", "true")
        self.btn_nav_briefing.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_nav_briefing.clicked.connect(lambda: self._switch_view_mode(0))

        self.btn_nav_table = QPushButton("📋 2. Dosya Takip Masası")
        self.btn_nav_table.setProperty("class", "navTabBtn")
        self.btn_nav_table.setProperty("selected", "false")
        self.btn_nav_table.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_nav_table.clicked.connect(lambda: self._switch_view_mode(1))

        self.btn_nav_studio = QPushButton("⚡ 3. Evrak & Fatura Stüdyosu")
        self.btn_nav_studio.setProperty("class", "navTabBtn")
        self.btn_nav_studio.setProperty("selected", "false")
        self.btn_nav_studio.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_nav_studio.clicked.connect(lambda: self._switch_view_mode(2))

        nav_box.addWidget(self.btn_nav_briefing)
        nav_box.addWidget(self.btn_nav_table)
        nav_box.addWidget(self.btn_nav_studio)
        layout.addLayout(nav_box)

        layout.addStretch(1)

        # 3. Mini KPI Rozetleri (Canlı ve Tıklanabilir)
        kpi_box = QHBoxLayout()
        kpi_box.setSpacing(5)

        self.kpi_cards = {}
        cards_info = [
            ("total",   "AÇIK",       "#f8fafc", "Tümü"),
            ("demuraj", "🚨 DEMURAJ", "#f43f5e", Durum.DEMURAJ_RISKI),
            ("banka",   "🏦 BANKA",   "#fb923c", Durum.BANKA_ID_BEKLER),
            ("tareks",  "🔬 TAREKS",  "#c084fc", Durum.TAREKS_DENETIM),
            ("ordino",  "⚓ ORDİNO",  "#facc15", Durum.ORDINO_BEKLER),
            ("eta",     "🚢 ETA ≤ 7", "#38bdf8", Durum.ETA_YAKLASAN),
        ]
        for key, title, color, filter_target in cards_info:
            btn_k = QPushButton(f"{title}: 0")
            btn_k.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_k.setStyleSheet(f"""
                QPushButton {{
                    background-color: #111726;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    color: {color};
                    font-size: 10.5px;
                    font-weight: 700;
                    padding: 3px 8px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: #1c263c;
                    border-color: {color};
                }}
            """)
            btn_k.clicked.connect(lambda checked, f=filter_target: self._go_to_table_with_filter(f))
            kpi_box.addWidget(btn_k)
            self.kpi_cards[key] = (btn_k, title)

        layout.addLayout(kpi_box)

        # 4. Dosya ve Canlı İzleme Kontrolleri
        file_box = QHBoxLayout()
        file_box.setSpacing(6)

        self.lbl_watch_status = QLabel("● Canlı")
        self.lbl_watch_status.setObjectName("statusPill")
        file_box.addWidget(self.lbl_watch_status)

        fname = os.path.basename(self.rapor_yolu) if self.rapor_yolu else "Rapor Seçilmedi"
        self.lbl_file_path = QLabel(f"📄 {fname}")
        self.lbl_file_path.setStyleSheet("color: #94a3b8; font-size: 11px; max-width: 170px;")
        self.lbl_file_path.setToolTip(self.rapor_yolu)
        file_box.addWidget(self.lbl_file_path)

        btn_browse = QPushButton("📁 Değiştir")
        btn_browse.clicked.connect(self._browse_report_file)
        file_box.addWidget(btn_browse)

        btn_refresh = QPushButton("🔄 Yenile")
        btn_refresh.setObjectName("btnPrimary")
        btn_refresh.clicked.connect(self._start_data_load)
        file_box.addWidget(btn_refresh)

        layout.addLayout(file_box)
        return hdr

    def _show_app_switch_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b111e;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 9px 20px;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11.5px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 8px;
            }
        """)
        a_apex = menu.addAction("⚡ SmartClearance APEX  (Aktif)")
        a_apex.setEnabled(False)
        menu.addSeparator()
        a_horizon = menu.addAction("🚢 SmartClearance HORIZON  (Canlı Konteyner Radarı)")

        pos = self.btn_app_switch.mapToGlobal(QPoint(0, self.btn_app_switch.height() + 4))
        act = menu.exec(pos)
        if act == a_horizon:
            self._trigger_app_switch("HORIZON")

    def _trigger_app_switch(self, target):
        if self.receivers(self.appSwitchRequested) > 0:
            self.appSwitchRequested.emit(target)
        else:
            try:
                import subprocess
                suite_script = os.path.join(os.path.dirname(__file__), "smartclearance_suite.py")
                subprocess.Popen([sys.executable, suite_script, "--system", target])
                self.close()
            except Exception as e:
                QMessageBox.warning(self, "Sistem Geçişi", f"SmartClearance Suite başlatılamadı:\n{e}")

    def _switch_view_mode(self, idx):
        self.stacked_widget.setCurrentIndex(idx)
        buttons = [self.btn_nav_briefing, self.btn_nav_table, self.btn_nav_studio]
        for i, btn in enumerate(buttons):
            btn.setProperty("selected", "true" if i == idx else "false")
            btn.setStyle(btn.style())

    def _go_to_table_with_filter(self, filter_target):
        self._switch_view_mode(1)
        self._set_filter(filter_target)

    def _on_briefing_shipment_selected(self, it):
        self._switch_view_mode(1)
        self._select_shipment_by_dict(it)

    def _on_briefing_filter_requested(self, code):
        self._switch_view_mode(1)
        self._set_filter(code)

    def _create_briefing_page(self):
        page = QWidget()
        self.briefing_container_layout = QVBoxLayout(page)
        self.briefing_container_layout.setContentsMargins(12, 10, 12, 10)
        self.briefing_container_layout.setSpacing(8)

        self.tab_briefing = ApexMorningBriefingWidget(self)
        self.tab_briefing.shipmentSelected.connect(self._on_briefing_shipment_selected)
        self.tab_briefing.filterRequested.connect(self._on_briefing_filter_requested)
        self.tab_briefing.gotoTableRequested.connect(lambda: self._switch_view_mode(1))
        self.tab_briefing.popoutRequested.connect(self._popout_briefing)

        self.briefing_container_layout.addWidget(self.tab_briefing, 1)
        return page

    def _create_table_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)

        # Sol Panel: Tablo & Süzgeçler
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(12, 10, 6, 10)
        left_layout.setSpacing(8)
        self._populate_left_panel(left_layout)
        self.main_splitter.addWidget(self.left_widget)

        # Sağ Panel: Kokpit, Stepper & Sekmeler
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(6, 10, 12, 10)
        right_layout.setSpacing(8)
        self._populate_right_panel(right_layout)
        self.main_splitter.addWidget(self.right_widget)

        self.main_splitter.setSizes([770, 710])
        layout.addWidget(self.main_splitter, 1)
        return page

    def _create_studio_page(self):
        page = QWidget()
        self.studio_container_layout = QVBoxLayout(page)
        self.studio_container_layout.setContentsMargins(12, 10, 12, 10)
        self.studio_container_layout.setSpacing(8)

        # Üst Araç Çubuğu
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #0f1523; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 6px 14px;")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 4, 8, 4)
        tb_lay.setSpacing(10)

        lbl_title = QLabel("⚡ AKILLI EVRAK & FATURA STÜDYOSU (CMMF & MASTER DATA EŞLEŞTİRME)")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        tb_lay.addWidget(lbl_title)
        tb_lay.addStretch(1)

        btn_back_table = QPushButton("📋 Dosya Takip Masasına Dön")
        btn_back_table.clicked.connect(lambda: self._switch_view_mode(1))
        tb_lay.addWidget(btn_back_table)

        btn_popout = QPushButton("↗ Ayrı Pencere Yap")
        btn_popout.setToolTip("Evrak stüdyosunu çift monitör kullanımı için bağımsız pencere yap")
        btn_popout.clicked.connect(self._popout_studio)
        tb_lay.addWidget(btn_popout)

        self.studio_container_layout.addWidget(top_bar)

        self.tab_studio = ApexInvoiceStudioWidget(self)
        self.studio_container_layout.addWidget(self.tab_studio, 1)
        return page

    def _toggle_table_expand(self):
        if self.is_table_expanded:
            self.right_widget.setVisible(True)
            self.main_splitter.setSizes(self.saved_splitter_sizes or [770, 710])
            self.btn_toggle_expand.setText("⛶ Tabloyu Genişlet (Tam Ekran)")
            self.is_table_expanded = False
        else:
            self.saved_splitter_sizes = self.main_splitter.sizes()
            self.right_widget.setVisible(False)
            self.main_splitter.setSizes([1000, 0])
            self.btn_toggle_expand.setText("⛶ Normale Dön (Bölünmüş Görünüm)")
            self.is_table_expanded = True

    def _popout_briefing(self):
        if self.briefing_window and self.briefing_window.isVisible():
            self.briefing_window.activateWindow()
            return

        self.briefing_container_layout.removeWidget(self.tab_briefing)

        self.briefing_placeholder = QFrame()
        self.briefing_placeholder.setStyleSheet("background-color: #0b0f19; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 40px;")
        p_lay = QVBoxLayout(self.briefing_placeholder)
        p_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info = QLabel("🌅 Sabah Brifingi & Radar bağımsız bir pencerede açık çalışıyor.")
        lbl_info.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: 700; margin-bottom: 8px;")
        btn_reembed = QPushButton("⬅ Pencereyi Ana Ekrana Geri Al")
        btn_reembed.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_reembed.setStyleSheet("background-color: #0284c7; color: white; padding: 8px 18px; font-weight: 700; border-radius: 6px;")
        btn_reembed.clicked.connect(self._reembed_briefing)
        p_lay.addWidget(lbl_info)
        p_lay.addWidget(btn_reembed)
        self.briefing_container_layout.addWidget(self.briefing_placeholder, 1)

        self.briefing_window = ApexDetachedWindow("Sabah Brifingi & Radar", self.tab_briefing, on_close=lambda w: self._reembed_briefing(), parent=self)
        self.briefing_window.show()

    def _reembed_briefing(self):
        if self.briefing_window:
            w = self.briefing_window.takeCentralWidget()
            self.briefing_window.close()
            self.briefing_window = None
            if self.briefing_placeholder:
                self.briefing_container_layout.removeWidget(self.briefing_placeholder)
                self.briefing_placeholder.deleteLater()
                self.briefing_placeholder = None
            self.briefing_container_layout.addWidget(self.tab_briefing, 1)

    def _popout_studio(self):
        if self.studio_window and self.studio_window.isVisible():
            self.studio_window.activateWindow()
            return

        self.studio_container_layout.removeWidget(self.tab_studio)

        self.studio_placeholder = QFrame()
        self.studio_placeholder.setStyleSheet("background-color: #0b0f19; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 40px;")
        p_lay = QVBoxLayout(self.studio_placeholder)
        p_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info = QLabel("⚡ Akıllı Evrak Stüdyosu bağımsız bir pencerede açık çalışıyor.")
        lbl_info.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: 700; margin-bottom: 8px;")
        btn_reembed = QPushButton("⬅ Pencereyi Ana Ekrana Geri Al")
        btn_reembed.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_reembed.setStyleSheet("background-color: #0284c7; color: white; padding: 8px 18px; font-weight: 700; border-radius: 6px;")
        btn_reembed.clicked.connect(self._reembed_studio)
        p_lay.addWidget(lbl_info)
        p_lay.addWidget(btn_reembed)
        self.studio_container_layout.addWidget(self.studio_placeholder, 1)

        self.studio_window = ApexDetachedWindow("Akıllı Evrak & Fatura Stüdyosu", self.tab_studio, on_close=lambda w: self._reembed_studio(), parent=self)
        self.studio_window.show()

    def _reembed_studio(self):
        if self.studio_window:
            w = self.studio_window.takeCentralWidget()
            self.studio_window.close()
            self.studio_window = None
            if self.studio_placeholder:
                self.studio_container_layout.removeWidget(self.studio_placeholder)
                self.studio_placeholder.deleteLater()
                self.studio_placeholder = None
            self.studio_container_layout.addWidget(self.tab_studio, 1)

    # --------------------------------------------------------------------------
    # SOL PANEL: FİLTRELER & TABLO
    # --------------------------------------------------------------------------

    def _populate_left_panel(self, layout):
        # Arama ve Filtre Hapları
        filter_box = QVBoxLayout()
        filter_box.setSpacing(6)

        # Üst Araç Çubuğu (Genişletme / Normale Dön butonu)
        tbl_top_bar = QHBoxLayout()
        tbl_top_bar.setSpacing(8)

        lbl_panel_title = QLabel("📁 SEVKİYAT İŞ LİSTESİ")
        lbl_panel_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #94a3b8; letter-spacing: 0.5px;")
        tbl_top_bar.addWidget(lbl_panel_title)
        tbl_top_bar.addStretch(1)

        self.btn_toggle_expand = QPushButton("⛶ Tabloyu Genişlet (Tam Ekran)")
        self.btn_toggle_expand.setProperty("class", "btnToggleExpand")
        self.btn_toggle_expand.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_expand.clicked.connect(self._toggle_table_expand)
        tbl_top_bar.addWidget(self.btn_toggle_expand)

        filter_box.addLayout(tbl_top_bar)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Dosya No, PO, Gemi, Liman veya Açıklama ile canlı ara...")
        self.txt_search.textChanged.connect(self._on_search_changed)
        filter_box.addWidget(self.txt_search)

        pills_box = QHBoxLayout()
        pills_box.setSpacing(4)

        self.pill_buttons = {}
        pills = [
            ("Tümü", "Tümü"),
            ("🌅 Sabah Görevleri", "SABAH_GOREVLERI"),
            ("📅 Hafta Sonu & Bugün", "HAFTA_SONU"),
            ("⏳ ETA Sıralı", "ETA_SIRALI"),
            ("🚨 Demuraj", Durum.DEMURAJ_RISKI),
            ("🏦 Banka ID", Durum.BANKA_ID_BEKLER),
            ("🔬 TAREKS", Durum.TAREKS_DENETIM),
            ("⚓ Ordino", Durum.ORDINO_BEKLER),
            ("🚢 ETA ≤ 7", Durum.ETA_YAKLASAN),
            ("⚪ Dosya Yok", Durum.DOSYA_YOK)
        ]

        for label, code in pills:
            btn = QPushButton(label)
            btn.setProperty("class", "filterPill")
            btn.setProperty("selected", "true" if label == "Tümü" else "false")
            btn.clicked.connect(lambda checked, c=code: self._set_filter(c))
            pills_box.addWidget(btn)
            self.pill_buttons[code] = btn

        pills_box.addStretch(1)
        filter_box.addLayout(pills_box)
        layout.addLayout(filter_box)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "DURUM", "DOSYA NO", "PO REF NO", "GEMİ ADI", "LİMAN", "VARIŞ / ETA", "GEÇEN", "NOT"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        # Kolon Genişlikleri (METİNLER KESİNLİKLE '...' İLE KESİLMEYECEK ŞEKİLDE)
        self.table.setColumnWidth(0, 140)  # Durum
        self.table.setColumnWidth(1, 105)  # Dosya No
        self.table.setColumnWidth(2, 105)  # PO
        self.table.setColumnWidth(3, 135)  # Gemi
        self.table.setColumnWidth(4, 75)   # Liman
        self.table.setColumnWidth(5, 90)   # Varış/ETA
        self.table.setColumnWidth(6, 60)   # Geçen Gün
        self.table.setColumnWidth(7, 35)   # Not

        layout.addWidget(self.table, 1)

        # Tablo Altı Sayaç
        self.lbl_table_count = QLabel("0 dosya listeleniyor")
        self.lbl_table_count.setStyleSheet("color: #64748b; font-size: 10.5px;")
        layout.addWidget(self.lbl_table_count)

    # --------------------------------------------------------------------------
    # SAĞ PANEL: KOKPİT & ÇALIŞMA ALANI
    # --------------------------------------------------------------------------

    def _populate_right_panel(self, layout):
        cockpit_box = QFrame()
        cockpit_box.setStyleSheet("""
            QFrame {
                background-color: #0f1523;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        c_lay = QVBoxLayout(cockpit_box)
        c_lay.setContentsMargins(12, 12, 12, 12)
        c_lay.setSpacing(8)

        # 1. Seçili Dosya Künyesi (Top Strip)
        top_strip = QHBoxLayout()
        top_strip.setSpacing(8)

        self.lbl_c_dosya = QLabel("Dosya: —")
        self.lbl_c_dosya.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px;")
        top_strip.addWidget(self.lbl_c_dosya)

        self.lbl_c_po = QLabel("PO: —")
        self.lbl_c_po.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid rgba(56, 189, 248, 0.25);
        """)
        top_strip.addWidget(self.lbl_c_po)

        top_strip.addStretch(1)

        self.lbl_c_status_badge = QLabel("Normal")
        self.lbl_c_status_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            color: #94a3b8;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 4px;
        """)
        top_strip.addWidget(self.lbl_c_status_badge)
        c_lay.addLayout(top_strip)

        # Alt Satır: 4 Detay Çipi
        meta_strip = QHBoxLayout()
        meta_strip.setSpacing(12)

        self.lbl_c_gemi = QLabel("🚢 Gemi: —")
        self.lbl_c_gemi.setStyleSheet("font-size: 11.5px; color: #cbd5e1;")
        self.lbl_c_liman = QLabel("⚓ Liman: —")
        self.lbl_c_liman.setStyleSheet("font-size: 11.5px; color: #cbd5e1;")
        self.lbl_c_varis = QLabel("📅 Varış: —")
        self.lbl_c_varis.setStyleSheet("font-size: 11.5px; color: #cbd5e1;")
        self.lbl_c_eta = QLabel("⏳ ETA: —")
        self.lbl_c_eta.setStyleSheet("font-size: 11.5px; color: #cbd5e1;")

        meta_strip.addWidget(self.lbl_c_gemi)
        meta_strip.addWidget(self.lbl_c_liman)
        meta_strip.addWidget(self.lbl_c_varis)
        meta_strip.addWidget(self.lbl_c_eta)
        meta_strip.addStretch(1)
        c_lay.addLayout(meta_strip)

        # 2. İlerleme Şeridi (Stepper)
        self.stepper_widget = ApexStepperWidget(self)
        c_lay.addWidget(self.stepper_widget)

        # 3. Zengin Fonksiyonel Sekmeler (Sadece Notlar ve Dosya Detayı)
        self.tabs = QTabWidget()

        # Sekme 0: Operasyon Günlüğü & Not Defteri
        self.tab_notes = self._create_notes_tab()
        self.tabs.addTab(self.tab_notes, "📝 Operasyon Notları & Günlük")

        # Sekme 1: Dosya Detay Kaydı (Tüm Alanlar)
        self.tab_details = self._create_details_tab()
        self.tabs.addTab(self.tab_details, "📋 Dosya Detay Kaydı")

        c_lay.addWidget(self.tabs, 1)
        layout.addWidget(cockpit_box, 1)

    def _create_notes_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Hızlı Şablon Butonları (Linear Chips)
        lbl_templates = QLabel("HIZLI OPERASYONEL AKSİYON ŞABLONLARI:")
        lbl_templates.setStyleSheet("font-size: 9.5px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        layout.addWidget(lbl_templates)

        tpl_box = QHBoxLayout()
        tpl_box.setSpacing(6)

        templates = [
            ("🏦 Banka ID İstendi", "Banka ID", "Müşteriden banka referans numarası ve ödeme dekontu talep edildi."),
            ("⚓ Ordino Bekleniyor", "Ordino", "Ordino bedeli acentaya ödendi, konşimento teslimi bekleniyor."),
            ("🔬 TAREKS Randevusu", "TAREKS", "TAREKS fiili denetim heyeti için randevu alındı, numune hazırlandı."),
            ("📄 Beyanname Hazır", "Beyanname", "Beyanname taslağı hazırlandı, tescil onayı bekleniyor.")
        ]

        for label, tag, default_text in templates:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #141c2e;
                    color: #cbd5e1;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 10.5px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #1c273e;
                    border-color: #38bdf8;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, t=tag, txt=default_text: self._add_quick_note(t, txt))
            tpl_box.addWidget(btn)

        tpl_box.addStretch(1)

        btn_clear_all = QPushButton("🗑️ Tümünü Temizle")
        btn_clear_all.setFixedHeight(24)
        btn_clear_all.setToolTip("Bu dosyaya ait tüm notları kalıcı olarak siler")
        btn_clear_all.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #f43f5e;
                border: 1px solid rgba(244, 63, 94, 0.25);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(244, 63, 94, 0.15);
                border-color: #f43f5e;
            }
        """)
        btn_clear_all.clicked.connect(self._clear_all_notes)
        tpl_box.addWidget(btn_clear_all)

        layout.addLayout(tpl_box)

        # Not Giriş Alanı (DENGELİ VE ŞIK BOYUTLAR)
        note_input_box = QHBoxLayout()
        note_input_box.setSpacing(8)

        self.txt_new_note = QTextEdit()
        self.txt_new_note.setPlaceholderText("Seçili dosyaya yeni bir operasyonel not ekleyin...")
        self.txt_new_note.setFixedHeight(42)
        note_input_box.addWidget(self.txt_new_note, 1)

        btn_save_note = QPushButton("➕ Not Ekle")
        btn_save_note.setObjectName("btnPrimary")
        btn_save_note.setFixedHeight(42)
        btn_save_note.setFixedWidth(95)
        btn_save_note.clicked.connect(self._save_custom_note)
        note_input_box.addWidget(btn_save_note)

        layout.addLayout(note_input_box)

        # Not Geçmişi Akışı (Scroll Area)
        self.scroll_notes = QScrollArea()
        self.scroll_notes.setWidgetResizable(True)
        self.scroll_notes.setStyleSheet("background-color: #0b0f19; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")

        self.notes_container = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_container)
        self.notes_layout.setContentsMargins(8, 8, 8, 8)
        self.notes_layout.setSpacing(6)
        self.notes_layout.addStretch(1)
        self.scroll_notes.setWidget(self.notes_container)

        layout.addWidget(self.scroll_notes, 1)
        return w

    def _create_details_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.txt_raw_details = QTextEdit()
        self.txt_raw_details.setReadOnly(True)
        self.txt_raw_details.setStyleSheet("background-color: #0b0f19; color: #cbd5e1; font-family: Consolas, monospace; font-size: 11.5px; border-radius: 6px; padding: 10px; border: 1px solid rgba(255, 255, 255, 0.05);")
        layout.addWidget(self.txt_raw_details)
        return w

    def _create_status_bar(self):
        bar = QFrame()
        bar.setFixedHeight(28)
        bar.setStyleSheet("background-color: #080b11; border-top: 1px solid rgba(255, 255, 255, 0.05); padding: 2px 14px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)

        self.lbl_status = QLabel("✅ SmartClearance Apex hazır.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1e293b; border-radius: 3px; } QProgressBar::chunk { background: #38bdf8; border-radius: 3px; }")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch(1)

        self.lbl_last_update = QLabel("Son Okuma: —")
        self.lbl_last_update.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_last_update)

        return bar

    # --------------------------------------------------------------------------
    # VERİ YÜKLEME VE İZLEME
    # --------------------------------------------------------------------------

    def _attach_file_watcher(self):
        for f in self.watcher.files():
            self.watcher.removePath(f)
        if self.rapor_yolu and os.path.exists(self.rapor_yolu):
            if self.watcher.addPath(self.rapor_yolu):
                self.lbl_watch_status.setText("● Canlı İzleniyor")
                self.lbl_watch_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); color: #34d399; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;")
            else:
                self.lbl_watch_status.setText("● İzlenemiyor")
                self.lbl_watch_status.setStyleSheet("background-color: rgba(250, 204, 21, 0.12); border: 1px solid rgba(250, 204, 21, 0.35); color: #facc15; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;")

    def _on_file_changed(self, path):
        self.lbl_watch_status.setText("● Değişiklik Algılandı...")
        self.lbl_watch_status.setStyleSheet("background-color: rgba(251, 146, 60, 0.12); border: 1px solid rgba(251, 146, 60, 0.35); color: #fb923c; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;")
        self.debounce_timer.start(2000)
        if path not in self.watcher.files():
            self.watcher.addPath(self.rapor_yolu)

    def _browse_report_file(self):
        yol, _ = QFileDialog.getOpenFileName(self, "İş Takip Raporu Seç", os.path.dirname(self.rapor_yolu), "Excel (*.xlsx *.xls)")
        if not yol:
            return
        self.rapor_yolu = yol
        self.config["rapor_yolu"] = yol
        save_config(self.config)
        self.lbl_file_path.setText(f"📄 {os.path.basename(yol)}")
        self.lbl_file_path.setToolTip(yol)
        self._attach_file_watcher()
        self._start_data_load()

    def _start_data_load(self):
        if not self.rapor_yolu or not os.path.exists(self.rapor_yolu):
            self.lbl_status.setText("❌ Rapor dosyası bulunamadı.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText(f"⏳ Rapor okunuyor: {os.path.basename(self.rapor_yolu)}...")

        self.loader_thread = DataLoaderThread(self.rapor_yolu)
        self.loader_thread.finished.connect(self._on_data_loaded)
        self.loader_thread.error.connect(self._on_data_error)
        self.loader_thread.start()

    def _on_data_loaded(self, items, kpi):
        self.progress_bar.setVisible(False)
        self.all_shipments = items
        self.lbl_last_update.setText(f"Son Okuma: {datetime.datetime.now().strftime('%H:%M:%S')}")
        self.lbl_status.setText(f"✅ Rapor yüklendi: {len(items)} aktif sevkiyat.")

        # KPI Güncelle (Header Mini Rozetleri)
        for key, (btn_k, title) in self.kpi_cards.items():
            val = kpi.get(key, 0)
            btn_k.setText(f"{title}: {val}")

        # Sabah Brifingi Güncelle
        if hasattr(self, 'tab_briefing') and self.tab_briefing:
            self.tab_briefing.update_data(items)

        self._apply_filters()

    def _on_data_error(self, err):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("❌ Hata oluştu.")
        QMessageBox.critical(self, "Veri Yükleme Hatası", f"Rapor okunurken hata meydana geldi:\n{err}")

    # --------------------------------------------------------------------------
    # FİLTRE VE TABLO DOLDURMA
    # --------------------------------------------------------------------------

    def _set_filter(self, code):
        self.active_filter = code
        for c, btn in self.pill_buttons.items():
            btn.setProperty("selected", "true" if c == code else "false")
            btn.setStyle(btn.style())  # QSS yenile
        self._apply_filters()

    def _on_search_changed(self, text):
        self.search_query = text.strip().upper()
        self._apply_filters()

    def _apply_filters(self):
        res = []
        for it in self.all_shipments:
            # 1. Kod Filtresi
            if self.active_filter == "SABAH_GOREVLERI":
                is_urgent = (
                    it["durum"] in (Durum.DEMURAJ_RISKI, Durum.BANKA_ID_BEKLER, Durum.TAREKS_DENETIM, Durum.ORDINO_BEKLER) or
                    (it["dosya_no"] == "—" and (it["gemi"] != "—" or (0 <= it.get("gun_kalan", 999) <= 14))) or
                    (0 <= it.get("gun_kalan", 999) <= 3) or
                    (it.get("gun_gecti", 0) > 0) or
                    it.get("hafta_sonu_geldi", False) or
                    it.get("bugun_geldi", False)
                )
                if not is_urgent:
                    continue
            elif self.active_filter == "HAFTA_SONU":
                if not it.get("hafta_sonu_geldi", False) and not it.get("bugun_geldi", False):
                    continue
            elif self.active_filter == "HAFTA_SONU_DOSYASIZ":
                if not it.get("hafta_sonu_dosyasiz", False) and not it.get("bugun_dosyasiz", False):
                    continue
            elif self.active_filter == "ETA_SIRALI":
                if it.get("eta_t", "—") == "—" or it.get("gun_kalan", -1) < 0:
                    continue
            elif self.active_filter != "Tümü" and it["durum"] != self.active_filter:
                continue

            # 2. Metin Arama
            if self.search_query:
                combined = f"{it['dosya_no']} {it['po']} {it['gemi']} {it['liman']} {it['aciklama1']} {it['aciklama2']}".upper()
                if self.search_query not in combined:
                    continue

            res.append(it)

        if self.active_filter == "ETA_SIRALI":
            res.sort(key=lambda x: x.get("gun_kalan", 9999))

        self.filtered_shipments = res
        self._render_table()

    def _render_table(self):
        self.table.setRowCount(0)
        for it in self.filtered_shipments:
            r = self.table.rowCount()
            self.table.insertRow(r)

            # Durum Rozeti (METİNLER KESİNLİKLE KESİLMEYECEK)
            durum_info = it["durum_info"]
            item_durum = QTableWidgetItem(f"{durum_info['icon']} {durum_info['label']}")
            item_durum.setForeground(QColor(durum_info["color"]))
            item_durum.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            # Not İkonu
            has_note = self.notes_mgr.has_notes(it["dosya_no"], it["po"])
            note_str = "📝" if has_note else "—"
            item_note = QTableWidgetItem(note_str)
            item_note.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if has_note:
                item_note.setToolTip(self.notes_mgr.get_last_note_summary(it["dosya_no"], it["po"]))

            # Geçen / Kalan Gün
            if it["gun_gecti"] > 0:
                gun_text = f"+{it['gun_gecti']}g"
            elif it.get("gun_kalan", -1) > 0:
                gun_text = f"-{it['gun_kalan']}g"
            elif it.get("gun_kalan", -1) == 0:
                gun_text = "Bugün"
            else:
                gun_text = "—"
            item_gun = QTableWidgetItem(gun_text)
            item_gun.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if it["gun_gecti"] >= 7:
                item_gun.setForeground(QColor("#f43f5e"))
                item_gun.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            self.table.setItem(r, 0, item_durum)
            self.table.setItem(r, 1, QTableWidgetItem(it["dosya_no"]))
            self.table.setItem(r, 2, QTableWidgetItem(it["po"]))
            self.table.setItem(r, 3, QTableWidgetItem(it["gemi"]))
            self.table.setItem(r, 4, QTableWidgetItem(it["liman"]))
            self.table.setItem(r, 5, QTableWidgetItem(it["varis_t"] if it["varis_t"] != "—" else it["eta_t"]))
            self.table.setItem(r, 6, item_gun)
            self.table.setItem(r, 7, item_note)

        self.lbl_table_count.setText(f"{len(self.filtered_shipments)} dosya listeleniyor (Toplam: {len(self.all_shipments)})")

        if self.filtered_shipments:
            self.table.selectRow(0)

    # --------------------------------------------------------------------------
    # DETAY KOKPİTİ VE NOT SİSTEMİ BAĞLANTILARI
    # --------------------------------------------------------------------------

    def _select_shipment_by_dict(self, it):
        if not it:
            return
        target_po = it.get("po")
        target_dosya = it.get("dosya_no")

        found_idx = -1
        for idx, item in enumerate(self.filtered_shipments):
            if target_po and item.get("po") == target_po:
                found_idx = idx
                break
            elif target_dosya and target_dosya != "—" and item.get("dosya_no") == target_dosya:
                found_idx = idx
                break

        if found_idx == -1:
            # Mevcut filtrede yoksa filtreyi Tümü yap
            self._set_filter("Tümü")
            for idx, item in enumerate(self.filtered_shipments):
                if target_po and item.get("po") == target_po:
                    found_idx = idx
                    break
                elif target_dosya and target_dosya != "—" and item.get("dosya_no") == target_dosya:
                    found_idx = idx
                    break

        if found_idx != -1:
            self.table.selectRow(found_idx)
            item_widget = self.table.item(found_idx, 0)
            if item_widget:
                self.table.scrollToItem(item_widget)
            self._update_cockpit(self.filtered_shipments[found_idx])

    def _on_table_selection_changed(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return
        row = sel[0].row()
        if row < len(self.filtered_shipments):
            self.selected_item = self.filtered_shipments[row]
            self._update_cockpit(self.selected_item)

    def _update_cockpit(self, it):
        # 1. Başlık Künyesi
        self.lbl_c_dosya.setText(f"Dosya: {it['dosya_no']}")
        self.lbl_c_po.setText(f"PO: {it['po']}")
        self.lbl_c_gemi.setText(f"🚢 Gemi: {it['gemi']}")
        self.lbl_c_liman.setText(f"⚓ Liman: {it['liman']}")
        self.lbl_c_varis.setText(f"📅 Varış: {it['varis_t']}")
        self.lbl_c_eta.setText(f"⏳ ETA: {it['eta_t']}")

        # Durum Rozeti
        durum_info = it["durum_info"]
        extra = f" (+{it['gun_gecti']}g)" if it['gun_gecti'] > 0 else ""
        self.lbl_c_status_badge.setText(f"{durum_info['icon']} {durum_info['label']}{extra}")
        self.lbl_c_status_badge.setStyleSheet(f"""
            background-color: {durum_info['bg']};
            color: {durum_info['color']};
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 4px;
            border: 1px solid {durum_info['color']};
        """)

        # 2. Stepper Güncelle
        self.stepper_widget.set_stage(it["stage"], it["next_action"], it["durum"])

        # 3. Notlar Sekmesini Doldur
        self._render_notes_for_selected()

        # 4. Detay Kaydı Sekmesini Doldur
        raw_text = (
            f"=== HANKOOK OPERASYON DOSYA KÜNYESİ ===\n\n"
            f"Dosya No       : {it['dosya_no']}\n"
            f"Referans (PO)  : {it['po']}\n"
            f"Gümrük         : {it['gumruk']}\n"
            f"Bayi           : {it['bayi']}\n"
            f"Gemi & Acenta  : {it['gemi']} ({it['acenta']})\n"
            f"Konşimento (BL): {it['bl_no']}\n"
            f"Konteyner No   : {it['konteyner']}\n"
            f"Liman          : {it['liman']}\n"
            f"Varış Tarihi   : {it['varis_t']}\n"
            f"ETA            : {it['eta_t']}\n"
            f"Ordino Teslim  : {it['ordino_t']}\n"
            f"TAREKS Başvuru : {it['tareks_b']}\n"
            f"TAREKS Sonuç   : {it['tareks_s']}\n"
            f"Fiili Denetim  : {it['fiili_denetim']}\n"
            f"Tescil Tarihi  : {it['tescil_t']}\n"
            f"Kantar Talebi  : {it['kantar']}\n"
            f"\n--- AÇIKLAMALAR ---\n"
            f"Açıklama 1     : {it['aciklama1'] or '—'}\n"
            f"Açıklama 2     : {it['aciklama2'] or '—'}\n"
        )
        self.txt_raw_details.setText(raw_text)

    def _render_notes_for_selected(self):
        while self.notes_layout.count() > 1:
            item = self.notes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.selected_item:
            return

        notes = self.notes_mgr.get_notes(self.selected_item["dosya_no"], self.selected_item["po"])
        if not notes:
            empty_lbl = QLabel("Bu dosyaya ait henüz bir not eklenmemiş. Yukarıdaki şablonlardan veya metin kutusundan ekleyebilirsiniz.")
            empty_lbl.setStyleSheet("color: #64748b; font-size: 11px; padding: 12px;")
            self.notes_layout.insertWidget(0, empty_lbl)
            return

        for n in notes:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #121929;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 6px;
                    padding: 6px 10px;
                }
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(6, 4, 6, 4)
            c_lay.setSpacing(3)

            top_box = QHBoxLayout()
            top_box.setSpacing(6)

            lbl_tag = QLabel(f"[{n.get('tag', 'Not')}]")
            lbl_tag.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700;")

            date_str = n.get("date", "")
            if n.get("updated_at"):
                date_str += f" (Düzenlendi: {n.get('updated_at')})"
            lbl_date = QLabel(date_str)
            lbl_date.setStyleSheet("color: #64748b; font-size: 10px;")

            top_box.addWidget(lbl_tag)
            top_box.addWidget(lbl_date)
            top_box.addStretch(1)

            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(22, 20)
            btn_edit.setToolTip("Notu Düzenle")
            btn_edit.setStyleSheet("background: transparent; color: #38bdf8; font-size: 12px; border: none; padding: 0;")
            btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_edit.clicked.connect(lambda checked, nid=n.get("id"), cur_txt=n.get("text", ""), cur_t=n.get("tag", "Özel Not"): self._edit_note(nid, cur_txt, cur_t))

            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(22, 20)
            btn_del.setToolTip("Kalıcı Olarak Sil")
            btn_del.setStyleSheet("background: transparent; color: #f43f5e; font-size: 12px; border: none; padding: 0;")
            btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_del.clicked.connect(lambda checked, nid=n.get("id"): self._delete_note(nid))

            top_box.addWidget(btn_edit)
            top_box.addWidget(btn_del)
            c_lay.addLayout(top_box)

            lbl_text = QLabel(n.get("text", ""))
            lbl_text.setStyleSheet("color: #f8fafc; font-size: 11.5px;")
            lbl_text.setWordWrap(True)
            c_lay.addWidget(lbl_text)

            self.notes_layout.insertWidget(self.notes_layout.count() - 1, card)

    def _add_quick_note(self, tag, text):
        if not self.selected_item:
            QMessageBox.information(self, "Bilgi", "Lütfen önce tablodan bir dosya seçin.")
            return
        stage_str = f"Aşama {self.selected_item.get('stage', 1)}"
        self.notes_mgr.add_note(self.selected_item["dosya_no"], self.selected_item["po"], text, tag=tag, stage=stage_str)
        self._render_notes_for_selected()
        self._update_table_note_indicator()

    def _save_custom_note(self):
        if not self.selected_item:
            QMessageBox.information(self, "Bilgi", "Lütfen önce tablodan bir dosya seçin.")
            return
        text = self.txt_new_note.toPlainText().strip()
        if not text:
            return
        stage_str = f"Aşama {self.selected_item.get('stage', 1)}"
        self.notes_mgr.add_note(self.selected_item["dosya_no"], self.selected_item["po"], text, tag="Özel Not", stage=stage_str)
        self.txt_new_note.clear()
        self._render_notes_for_selected()
        self._update_table_note_indicator()

    def _edit_note(self, note_id, cur_txt, cur_tag):
        if not self.selected_item:
            return
        dlg = ApexNoteEditDialog(self, cur_txt, cur_tag)
        if dlg.exec():
            new_text, new_tag = dlg.get_data()
            if new_text:
                self.notes_mgr.update_note(self.selected_item["dosya_no"], self.selected_item["po"], note_id, new_text, new_tag)
                self._render_notes_for_selected()
                self._update_table_note_indicator()

    def _delete_note(self, note_id):
        if not self.selected_item:
            return
        reply = QMessageBox.question(
            self, "Notu Kalıcı Olarak Sil",
            "Bu operasyon notunu kalıcı olarak silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.notes_mgr.delete_note(self.selected_item["dosya_no"], self.selected_item["po"], note_id)
            self._render_notes_for_selected()
            self._update_table_note_indicator()

    def _clear_all_notes(self):
        if not self.selected_item:
            QMessageBox.information(self, "Bilgi", "Lütfen önce tablodan bir dosya seçin.")
            return
        has = self.notes_mgr.has_notes(self.selected_item["dosya_no"], self.selected_item["po"])
        if not has:
            QMessageBox.information(self, "Bilgi", "Bu dosyaya ait silinecek not bulunmuyor.")
            return

        reply = QMessageBox.question(
            self, "Tüm Notları Sil",
            f"Seçili dosyaya ({self.selected_item['dosya_no']}) ait TÜM notlar kalıcı olarak silinecektir.\n\nOnaylıyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.notes_mgr.clear_all_notes(self.selected_item["dosya_no"], self.selected_item["po"])
            self._render_notes_for_selected()
            self._update_table_note_indicator()

    def _update_table_note_indicator(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return
        row = sel[0].row()
        has_note = self.notes_mgr.has_notes(self.selected_item["dosya_no"], self.selected_item["po"])
        item = self.table.item(row, 7)
        if item:
            item.setText("📝" if has_note else "—")
            item.setToolTip(self.notes_mgr.get_last_note_summary(self.selected_item["dosya_no"], self.selected_item["po"]))

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        dosya = self.table.item(row, 1).text()
        po = self.table.item(row, 2).text()

        menu = QMenu(self)
        a_copy_dosya = menu.addAction(f"📋 Dosya No Kopyala ({dosya})")
        a_copy_po = menu.addAction(f"📋 PO No Kopyala ({po})")
        menu.addSeparator()
        a_quick_note = menu.addAction("📝 Bu Dosyaya Not Ekle")
        a_open_folder = menu.addAction("📂 Çalışma Klasörünü Aç")

        act = menu.exec(self.table.mapToGlobal(pos))
        if act == a_copy_dosya and dosya != "—":
            QApplication.clipboard().setText(dosya)
        elif act == a_copy_po and po != "—":
            QApplication.clipboard().setText(po)
        elif act == a_quick_note:
            self._switch_view_mode(1)
            self.tabs.setCurrentIndex(0)
            self.txt_new_note.setFocus()
        elif act == a_open_folder:
            try:
                os.startfile(os.path.dirname(self.rapor_yolu))
            except Exception:
                pass

    def _on_screen_changed(self, new_screen=None):
        """Pencere ekran değiştirdiğinde splitter ve arayüz oranlarını orantılı günceller."""
        if hasattr(self, "splitter") and self.splitter:
            tot = self.splitter.width() or self.width()
            if tot > 300:
                left_w = int(tot * 0.52)
                right_w = max(tot - left_w, 320)
                self.splitter.setSizes([left_w, right_w])
        self.updateGeometry()
        self.update()


def main():
    import ctypes
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # Windows Türkçe karakter ve kristal netliğinde Segoe UI font ayarı
    app_font = QFont("Segoe UI", 9)
    app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(app_font)

    window = SmartClearanceApex()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
