"""
main_window.py — QFileSystemWatcher + dosya seçici (config ile kalıcı)
"""

import datetime, os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QStatusBar, QPushButton, QLabel, QHBoxLayout,
    QProgressBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher

from .dashboard_tab import DashboardTab
from .shipments_tab  import ShipmentsTab
from .actions_tab    import ActionsTab
from .data_loader    import DataLoaderThread, get_rapor_yolu
from .config         import rapor_yolu_kaydet
from .theme import (
    BG_BASE, BG_HEADER, BORDER,
    TEXT_PRIMARY, TEXT_DIM, TEXT_WHITE, ACCENT, TAB_STYLE,
)


class MainWindow(QMainWindow):
    DEBOUNCE_MS  = 2000
    FALLBACK_MS  = 5 * 60 * 1000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hankook Gümrük Operasyon Masası")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 880)
        self.setStyleSheet(TAB_STYLE)

        self._loader       = None
        self._rapor_yolu   = get_rapor_yolu()

        # Debounce: dosya değişince 2sn bekle
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._start_load)

        self._build_ui()
        self._setup_watcher()
        self._start_load()

        # Yedek yenileme (5dk)
        self._fallback = QTimer(self)
        self._fallback.timeout.connect(self._start_load)
        self._fallback.start(self.FALLBACK_MS)

    # ── Dosya izleyici ────────────────────────────────────────────────────────
    def _setup_watcher(self):
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._attach_watcher(self._rapor_yolu)

    def _attach_watcher(self, yol: str):
        """Watcher'ı yeni dosyaya bağla, eskisini çıkar."""
        for f in self._watcher.files():
            self._watcher.removePath(f)
        if self._watcher.addPath(yol):
            self.lbl_watch.setText("● İzleniyor")
            self.lbl_watch.setStyleSheet("color: #22C55E; font-size: 10px;")
        else:
            self.lbl_watch.setText("● İzlenemiyor")
            self.lbl_watch.setStyleSheet(f"color: #F59E0B; font-size: 10px;")

    def _on_file_changed(self, path: str):
        self.lbl_watch.setText("● Değişiklik — yükleniyor...")
        self.lbl_watch.setStyleSheet("color: #F59E0B; font-size: 10px;")
        self._debounce.start(self.DEBOUNCE_MS)
        # Watcher bazı uygulamalarda dosyayı listeden çıkarır — tekrar ekle
        if path not in self._watcher.files():
            self._watcher.addPath(self._rapor_yolu)

    # ── Dosya değiştir ────────────────────────────────────────────────────────
    def _dosya_sec(self):
        """Kullanıcıdan rapor dosyasını seçmesini ister."""
        mevcut_klasor = os.path.dirname(self._rapor_yolu) if self._rapor_yolu else ""
        yeni_yol, _ = QFileDialog.getOpenFileName(
            self,
            "İş Takip Raporunu Seç",
            mevcut_klasor,
            "Excel Dosyaları (*.xlsx *.xls);;Tüm Dosyalar (*.*)"
        )
        if not yeni_yol:
            return  # İptal edildi

        # Config'e kaydet
        rapor_yolu_kaydet(yeni_yol)
        self._rapor_yolu = yeni_yol

        # UI güncelle
        self._update_dosya_label()
        self._attach_watcher(yeni_yol)

        # Hemen yenile
        self._start_load()

    def _update_dosya_label(self):
        dosya_adi = os.path.basename(self._rapor_yolu)
        klasor    = os.path.dirname(self._rapor_yolu)
        # Klasörü kısa tut: son 2 parça
        parts = klasor.replace("\\", "/").rstrip("/").split("/")
        kisa_klasor = "/".join(parts[-2:]) if len(parts) >= 2 else klasor
        self.lbl_dosya.setText(f"{kisa_klasor}  /  {dosya_adi}")
        self.lbl_dosya.setToolTip(self._rapor_yolu)

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background-color: {BG_BASE};")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(46)
        header.setStyleSheet(f"background-color: {BG_HEADER}; border-bottom: 1px solid {BORDER};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 16, 0)
        h_lay.setSpacing(12)

        lbl_title = QLabel("HANKOOK GÜMRÜK OPERASYON MASASI")
        lbl_title.setStyleSheet(
            f"color: {TEXT_WHITE}; font-size: 12px; font-weight: 700; letter-spacing: 2px;"
        )
        h_lay.addWidget(lbl_title)

        # Dikey ayırıcı
        h_lay.addWidget(self._vsep())

        # Dosya yolu göstergesi
        self.lbl_dosya = QLabel("")
        self.lbl_dosya.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; font-family: Consolas;"
        )
        self.lbl_dosya.setMaximumWidth(400)
        h_lay.addWidget(self.lbl_dosya)

        # Dosya değiştir butonu
        btn_dosya = QPushButton("Dosya Değiştir")
        btn_dosya.setFixedHeight(24)
        btn_dosya.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 0 10px;
                font-size: 10px;
            }}
            QPushButton:hover {{ color: {TEXT_WHITE}; border-color: {ACCENT}; }}
        """)
        btn_dosya.clicked.connect(self._dosya_sec)
        h_lay.addWidget(btn_dosya)

        h_lay.addStretch()

        # İzleme göstergesi
        self.lbl_watch = QLabel("● Bağlanıyor...")
        self.lbl_watch.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        h_lay.addWidget(self.lbl_watch)

        h_lay.addWidget(self._vsep())

        self.lbl_ts = QLabel("")
        self.lbl_ts.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        h_lay.addWidget(self.lbl_ts)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedSize(50, 2)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background: {BORDER}; border-radius: 1px; }}
            QProgressBar::chunk {{ background: {ACCENT}; border-radius: 1px; }}
        """)
        self.progress.setVisible(False)
        h_lay.addWidget(self.progress)

        btn_refresh = QPushButton("Yenile")
        btn_refresh.setFixedHeight(24)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 0 12px;
                font-size: 10px;
            }}
            QPushButton:hover {{ color: {TEXT_WHITE}; border-color: {ACCENT}; }}
        """)
        btn_refresh.clicked.connect(self._start_load)
        h_lay.addWidget(btn_refresh)

        root.addWidget(header)

        # ── Sekmeler ─────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.dashboard_tab = DashboardTab()
        self.shipments_tab = ShipmentsTab()
        self.actions_tab   = ActionsTab()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.shipments_tab, "Sevkiyat Takibi")
        self.tabs.addTab(self.actions_tab,   "Aksiyonlar")

        root.addWidget(self.tabs)

        # ── Status bar ───────────────────────────────────────────────────────
        sb = QStatusBar()
        sb.setFixedHeight(24)
        self.setStatusBar(sb)
        self.lbl_status = QLabel("Hazır")
        self.lbl_status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        sb.addWidget(self.lbl_status)

        # Dosya label'ını doldur
        self._update_dosya_label()

    @staticmethod
    def _vsep():
        sep = QLabel("|")
        sep.setFixedWidth(12)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setStyleSheet(f"color: {BORDER}; font-size: 14px;")
        return sep

    # ── Veri yükleme ──────────────────────────────────────────────────────────
    def _start_load(self):
        if self._loader and self._loader.isRunning():
            return
        self.progress.setVisible(True)
        self.lbl_status.setText("Rapor okunuyor...")
        self._loader = DataLoaderThread(rapor_yolu=self._rapor_yolu)
        self._loader.finished.connect(self._on_loaded)
        self._loader.error.connect(self._on_error)
        self._loader.start()

    def _on_loaded(self, rows: list, kpis: dict):
        self.progress.setVisible(False)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.lbl_ts.setText(f"Son: {ts}")
        self.lbl_watch.setText("● İzleniyor")
        self.lbl_watch.setStyleSheet("color: #22C55E; font-size: 10px;")
        self.lbl_status.setText(
            f"{kpis['toplam']} kayıt   |   "
            f"Demuraj: {kpis['demuraj']}   "
            f"Banka ID: {kpis['banka_id']}   "
            f"TAREKS: {kpis['tareks']}   "
            f"Ordino: {kpis['ordino']}   "
            f"ETA<7g: {kpis['eta_7']}"
        )
        self.dashboard_tab.update_data(rows, kpis)
        self.shipments_tab.update_data(rows, kpis)
        self.actions_tab.update_data(rows, kpis)

    def _on_error(self, err: str):
        self.progress.setVisible(False)
        self.lbl_watch.setText("● Hata")
        self.lbl_watch.setStyleSheet("color: #EF4444; font-size: 10px;")
        self.lbl_status.setText(f"Hata: {err}")
