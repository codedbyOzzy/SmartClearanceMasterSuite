# -*- coding: utf-8 -*-
"""
kantar_view.py — DP World & Körfez Kantar / DBA Takip Görünümü (PyQt6)
MasterSuite için DP World & Körfez Kantar/DBA tablosu, tike PDF indirme ve birleştirme motoru, filtreler, otonom takip.
"""

import os
import sys
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QFileDialog, QMenu, QDialog,
    QTextEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from PyQt6.QtGui import QColor, QFont, QCursor, QKeySequence, QShortcut

from .base_view import BaseView
from ..components.metric_card import MetricCard


# ----------------------------------------------------------------------
# Background Worker for Live Kantar Queries
# ----------------------------------------------------------------------
class KantarQueryWorker(QThread):
    progress = pyqtSignal(int, int, str, dict)  # current, total, cntr_no, res
    finished_batch = pyqtSignal(int, float)     # count, elapsed
    error = pyqtSignal(str)

    def __init__(self, kantar_tracker, cntr_list: List[str]):
        super().__init__()
        self.kantar_tracker = kantar_tracker
        self.cntr_list = cntr_list

    def run(self):
        if not self.kantar_tracker or not self.cntr_list:
            return
        t_start = time.time()
        total = len(self.cntr_list)
        for i, c in enumerate(self.cntr_list, 1):
            try:
                res = self.kantar_tracker.query_single_now(c)
            except Exception as exc:
                res = {"success": False, "error": str(exc)}
            self.progress.emit(i, total, c, res)
            time.sleep(0.3)
        elapsed = time.time() - t_start
        self.finished_batch.emit(total, elapsed)


# ----------------------------------------------------------------------
# Background Worker for Full Cycle Scan
# ----------------------------------------------------------------------
class KantarScanCycleWorker(QThread):
    finished_scan = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, kantar_tracker):
        super().__init__()
        self.kantar_tracker = kantar_tracker

    def run(self):
        try:
            res = self.kantar_tracker.run_full_cycle()
            self.finished_scan.emit(res if isinstance(res, dict) else {})
        except Exception as exc:
            self.error.emit(str(exc))


# ----------------------------------------------------------------------
# Background Worker for PDF Merge
# ----------------------------------------------------------------------
class KantarMergeWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_merge = pyqtSignal(dict)

    def __init__(self, kantar_tracker, output_path: str, cntr_list: Optional[List[str]] = None):
        super().__init__()
        self.kantar_tracker = kantar_tracker
        self.output_path = output_path
        self.cntr_list = cntr_list

    def run(self):
        def _cb(done: int, total: int, cntr: str):
            self.progress.emit(done, total, cntr)

        try:
            res = self.kantar_tracker.merge_all_pdfs(
                output_path=self.output_path,
                konteyner_list=self.cntr_list,
                on_progress=_cb
            )
        except Exception as exc:
            res = {"success": False, "error": str(exc), "total": 0, "skipped": 0, "merged_path": None}
        self.finished_merge.emit(res)



# ----------------------------------------------------------------------
# YILPORT Oturum & Çerez Bağlantı Penceresi (Hızlı & Güvenli)
# ----------------------------------------------------------------------
class YilportAuthDialog(QDialog):
    def __init__(self, parent=None, on_success=None):
        super().__init__(parent)
        self.on_success = on_success
        self.setWindowTitle("🌐 YILPORT Online Service Oturum & Çerez Tanımlama")
        self.resize(620, 360)
        self.setStyleSheet("background-color: #0b0f19; color: #f8fafc;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        lbl_header = QLabel("🌐 <b>Yılport Online Service Oturum Bağlantısı</b>")
        lbl_header.setStyleSheet("font-size: 14px; color: #38bdf8; font-weight: bold;")
        layout.addWidget(lbl_header)

        desc_text = (
            "Yılport sistemi robot koruması kullandığı için tarayıcınızdaki aktif oturum çerezini sisteme bağlamanız gerekir.<br><br>"
            "<b>Nasıl Yapılır? (5 Saniyede):</b><br>"
            "1. Yılport'un açık olduğu Edge tarayıcınızda <b>F12</b> tuşuna basıp <b>Konsol (Console)</b> sekmesine gelin.<br>"
            "2. <code>document.cookie</code> yazıp Enter'a basın ve çıkan metni kopyalayın.<br>"
            "3. Kopyaladığınız metni aşağıdaki alana yapıştırıp 'Kaydet' butonuna basın."
        )
        lbl_desc = QLabel(desc_text)
        lbl_desc.setStyleSheet("background-color: #111827; color: #cbd5e1; border: 1px solid #1e293b; padding: 12px 14px; border-radius: 6px; font-size: 11px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Input box
        lbl_input = QLabel("📋 <b>Yılport Çerezini (document.cookie) Yapıştırın:</b>")
        lbl_input.setStyleSheet("font-size: 11px; color: #c084fc; font-weight: bold;")
        layout.addWidget(lbl_input)

        self.txt_cookie = QLineEdit(self)
        self.txt_cookie.setPlaceholderText("Örnek: Location=TR; Port=201; ASP.NET_SessionId=...")
        self.txt_cookie.setStyleSheet("background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 8px 10px; border-radius: 6px; font-size: 12px;")
        layout.addWidget(self.txt_cookie)

        # Buttons
        btn_box = QHBoxLayout()

        btn_open_browser = QPushButton("🌐 Yılport Sayfasını Aç", self)
        btn_open_browser.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 8px 14px; border-radius: 6px; font-weight: bold;")
        btn_open_browser.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open_browser.clicked.connect(self._open_in_browser)
        btn_box.addWidget(btn_open_browser)

        btn_box.addStretch()

        btn_cancel = QPushButton("İptal", self)
        btn_cancel.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 8px 14px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("✅ Oturumu Kaydet ve Taramayı Başlat", self)
        btn_save.setStyleSheet("background-color: #0284c7; color: #ffffff; border: 1px solid #38bdf8; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save.clicked.connect(self._save_cookie_and_run)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

        self.session_file = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "yilport_session.json")

    def _open_in_browser(self):
        import webbrowser
        webbrowser.open("https://online.yilport.com/TRGEB/Unit")

    def _save_cookie_and_run(self):
        raw = self.txt_cookie.text().strip().strip('"').strip("'")
        if not raw:
            QMessageBox.warning(self, "Uyarı", "Lütfen kopyaladığınız çerez metnini yapıştırın.")
            return

        cookies_dict = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cookies_dict[k.strip()] = v.strip().strip('"')

        if not cookies_dict:
            QMessageBox.warning(self, "Uyarı", "Geçerli bir çerez formatı tespit edilemedi.")
            return

        os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(cookies_dict, f, indent=2)

        QMessageBox.information(self, "Başarılı", "✅ Yılport oturumu kaydedildi! Şimdi otomatik tarama yapılıyor...")
        if self.on_success:
            self.on_success()
        self.accept()



class KantarView(BaseView):
    """DP World & Körfez Kantar / DBA Takip Sekmesi (PyQt6)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.current_kantar_filter = "ALL"  # 'ALL', 'READY', 'PENDING'
        self._active_worker = None
        self._build_ui()

    @property
    def kantar_tracker(self):
        if self.main_window and hasattr(self.main_window, "kantar_tracker"):
            return self.main_window.kantar_tracker
        return None

    @property
    def engine(self):
        if self.main_window and hasattr(self.main_window, "engine"):
            return self.main_window.engine
        return None

    @property
    def evrim_records(self):
        if self.main_window and hasattr(self.main_window, "evrim_records"):
            return self.main_window.evrim_records
        return []

    # ------------------------------------------------------------------
    # UI SETUP
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # 1. Metrik Kartları Barı
        metric_bar = QHBoxLayout()
        metric_bar.setSpacing(10)

        self.card_k_total = MetricCard(
            "İZLENEN KONTEYNERLER", "0", "Otonom Havuzda", "#38bdf8", self
        )
        self.card_k_total.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_k_total.mousePressEvent = lambda e: self.filter_kantar_table("ALL")
        metric_bar.addWidget(self.card_k_total)

        self.card_k_ready = MetricCard(
            "TARTIM HAZIR (TİKE VAR)", "0", "PDF İndirilebilir", "#10b981", self
        )
        self.card_k_ready.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_k_ready.mousePressEvent = lambda e: self.filter_kantar_table("READY")
        metric_bar.addWidget(self.card_k_ready)

        self.card_k_pending = MetricCard(
            "TARTIM BEKLİYOR", "0", "Liman / Sahada", "#f59e0b", self
        )
        self.card_k_pending.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_k_pending.mousePressEvent = lambda e: self.filter_kantar_table("PENDING")
        metric_bar.addWidget(self.card_k_pending)

        self.card_k_last_scan = MetricCard(
            "SON OTONOM TARAMA", "—", "10 Dk Döngü", "#38bdf8", self
        )
        metric_bar.addWidget(self.card_k_last_scan)

        layout.addLayout(metric_bar)

        # 2. Kontrol Çubuğu & Butonlar
        ctrl_bar = QFrame(self)
        ctrl_bar.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 4px;")
        cb_layout = QHBoxLayout(ctrl_bar)
        cb_layout.setContentsMargins(10, 6, 10, 6)
        cb_layout.setSpacing(8)

        lbl_s = QLabel("🔍 Ara / Filtrele:", ctrl_bar)
        lbl_s.setStyleSheet("font-weight: 700; color: #38bdf8; border: none;")
        cb_layout.addWidget(lbl_s)

        self.txt_kantar_search = QLineEdit(ctrl_bar)
        self.txt_kantar_search.setPlaceholderText("Konteyner, Dosya, Plaka, Firma...")
        self.txt_kantar_search.setFixedWidth(200)
        self.txt_kantar_search.textChanged.connect(self.refresh_kantar_takip_table)
        cb_layout.addWidget(self.txt_kantar_search)

        self.btn_kantar_add = QPushButton("➕ Konteyner Ekle", ctrl_bar)
        self.btn_kantar_add.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 700; padding: 6px 14px; border-radius: 6px; border: 1px solid #3b82f6;")
        self.btn_kantar_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kantar_add.clicked.connect(self.show_kantar_add_dialog)
        cb_layout.addWidget(self.btn_kantar_add)

        self.btn_kantar_sync = QPushButton("⚡ Evrim/Excel'den Aktar", ctrl_bar)
        self.btn_kantar_sync.setStyleSheet("background-color: #0284c7; color: #ffffff; font-weight: 700; padding: 6px 14px; border-radius: 6px; border: 1px solid #38bdf8;")
        self.btn_kantar_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kantar_sync.clicked.connect(self.auto_sync_kantar_from_evrim)
        cb_layout.addWidget(self.btn_kantar_sync)

        self.btn_kantar_scan_now = QPushButton("🔄 Şimdi Tümünü Tara", ctrl_bar)
        self.btn_kantar_scan_now.setStyleSheet("background-color: #1e293b; color: #f8fafc; font-weight: 700; padding: 6px 14px; border-radius: 6px; border: 1px solid #334155;")
        self.btn_kantar_scan_now.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kantar_scan_now.clicked.connect(self.run_kantar_scan_now)
        cb_layout.addWidget(self.btn_kantar_scan_now)

        self.btn_yilport_login = QPushButton("🌐 Yılport Oturumu Aç / Doğrula", ctrl_bar)
        self.btn_yilport_login.setStyleSheet("background-color: #1e1b4b; color: #c084fc; font-weight: 700; padding: 6px 14px; border-radius: 6px; border: 1px solid #7c3aed;")
        self.btn_yilport_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yilport_login.clicked.connect(self.launch_yilport_auth_helper)
        cb_layout.addWidget(self.btn_yilport_login)

        self.btn_open_pdf = QPushButton("📥 Seçili Kantar PDF'ini Aç", ctrl_bar)
        self.btn_open_pdf.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-weight: 700; padding: 6px 14px; border-radius: 6px; border: 1px solid #6366f1;")
        self.btn_open_pdf.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_pdf.clicked.connect(self.download_and_open_selected_kantar_pdf)
        cb_layout.addWidget(self.btn_open_pdf)

        self.btn_kantar_merge_pdf = QPushButton("📦 Tike PDF'lerini Birleştir", ctrl_bar)
        self.btn_kantar_merge_pdf.setStyleSheet("background-color: #0d9488; color: #ffffff; font-weight: 700; padding: 6px 14px; border-radius: 6px; border: 1px solid #14b8a6;")
        self.btn_kantar_merge_pdf.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kantar_merge_pdf.clicked.connect(self.merge_and_download_kantar_pdfs)
        cb_layout.addWidget(self.btn_kantar_merge_pdf)

        self.btn_kantar_clear = QPushButton("🗑️ Temizle", ctrl_bar)
        self.btn_kantar_clear.setStyleSheet("background-color: rgba(239, 68, 68, 0.12); color: #f87171; font-weight: 700; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(239, 68, 68, 0.35);")
        self.btn_kantar_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kantar_clear.clicked.connect(self.clear_all_kantar_pool)
        cb_layout.addWidget(self.btn_kantar_clear)

        cb_layout.addStretch()

        self.lbl_kantar_status = QLabel("🤖 10 Dk Otonom İzleme Aktif", ctrl_bar)
        self.lbl_kantar_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #16a34a; background-color: #dcfce7; padding: 5px 10px; border-radius: 6px;")
        cb_layout.addWidget(self.lbl_kantar_status)

        layout.addWidget(ctrl_bar)

        # 3. Tablo
        self.tree_kantar = QTableWidget(self)
        self.tree_kantar.setColumnCount(10)
        self.tree_kantar.setHorizontalHeaderLabels([
            "Konteyner No", "Dosya No", "Liman / Kaynak",
            "Tartım No", "Tartım Tarihi", "Çekici Plaka",
            "Firma / Bayi", "DBA (VGM) / Dara", "Kantar Tikesi Durumu", "Son Kontrol"
        ])
        self.tree_kantar.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_kantar.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_kantar.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_kantar.setAlternatingRowColors(True)
        self.tree_kantar.verticalHeader().setVisible(False)
        self.tree_kantar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_kantar.customContextMenuRequested.connect(self.show_kantar_context_menu)
        self.tree_kantar.cellDoubleClicked.connect(lambda r, c: self.download_and_open_selected_kantar_pdf())

        header = self.tree_kantar.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Interactive)

        self.tree_kantar.setColumnWidth(0, 130)
        self.tree_kantar.setColumnWidth(1, 100)
        self.tree_kantar.setColumnWidth(2, 100)
        self.tree_kantar.setColumnWidth(3, 100)
        self.tree_kantar.setColumnWidth(4, 110)
        self.tree_kantar.setColumnWidth(5, 100)
        self.tree_kantar.setColumnWidth(6, 130)
        self.tree_kantar.setColumnWidth(7, 100)
        self.tree_kantar.setColumnWidth(9, 110)

        shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.tree_kantar)
        shortcut_del.activated.connect(self.remove_kantar_selected_rows)

        layout.addWidget(self.tree_kantar, stretch=1)

    # ------------------------------------------------------------------
    # LIFECYCLE & REFRESH
    # ------------------------------------------------------------------
    def on_activate(self):
        self.refresh_kantar_takip_table()

    def refresh_table(self):
        self.refresh_kantar_takip_table()

    def on_kantar_status_changed(self):
        QTimer.singleShot(0, self.refresh_kantar_takip_table)

    def filter_kantar_table(self, filter_type: str):
        self.current_kantar_filter = filter_type
        self.refresh_kantar_takip_table()

    @staticmethod
    def format_check_time(val) -> str:
        """Tarih ve zaman bilgisini saat bazlı ve yüksek okunurluklu formata dönüştürür."""
        if not val or str(val).strip() in ("—", "-", "None", "null", ""):
            return "—"
        s = str(val).strip()

        # 1. DD.MM.YYYY HH:MM or DD.MM.YYYY HH:MM:SS
        m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}:\d{2}(?::\d{2})?)', s)
        if m:
            day, month, year, time_part = m.groups()
            today = datetime.now()
            if int(day) == today.day and int(month) == today.month and int(year) == today.year:
                return time_part
            return f"{day.zfill(2)}.{month.zfill(2)} {time_part}"

        # 2. ISO timestamp: 2026-09-17T11:09:30 or 2026-09-17 11:09:30
        if "T" in s or (len(s) >= 19 and s[4] == "-" and s[7] == "-"):
            try:
                clean_iso = s.replace("Z", "").split("+")[0]
                if "." in clean_iso:
                    clean_iso = clean_iso.split(".")[0]
                clean_iso = clean_iso.replace("T", " ")
                dt = datetime.strptime(clean_iso[:19], "%Y-%m-%d %H:%M:%S")
                today = datetime.now().date()
                if dt.date() == today:
                    return dt.strftime("%H:%M:%S")
                return dt.strftime("%d.%m %H:%M")
            except Exception:
                pass

        # 3. Sadece saat: HH:MM veya HH:MM:SS
        if re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', s):
            return s

        return s

    def refresh_kantar_takip_table(self):
        if not self.kantar_tracker:
            self.tree_kantar.setRowCount(0)
            return

        tracked = self.kantar_tracker.list_tracked(only_active=True)
        search_q = self.txt_kantar_search.text().strip().upper()

        ready_cnt = 0
        pending_cnt = 0
        displayed_rows = []

        for item in tracked:
            c_no = str(item.get("konteyner_no", "")).strip()
            dosya_no = item.get("dosya_no")
            if not dosya_no or str(dosya_no).strip() in ("—", "-", "None", ""):
                if hasattr(self.kantar_tracker, "_find_dosya_no_from_excel"):
                    found = self.kantar_tracker._find_dosya_no_from_excel(c_no)
                    if found:
                        dosya_no = found
                        item["dosya_no"] = found
                if (not dosya_no or str(dosya_no).strip() in ("—", "-", "None", "")) and self.engine and hasattr(self.engine, "records"):
                    c_clean = c_no.strip().upper()
                    for rec in (self.engine.records or []):
                        raw = str(rec.get("konteyner") or "").upper()
                        parts = [p.strip() for p in raw.replace(",", " ").split()]
                        if c_clean in parts:
                            dosya_no = str(rec.get("dosya") or "").strip()
                            item["dosya_no"] = dosya_no
                            break
            if not dosya_no:
                dosya_no = "—"

            kaynak = str(item.get("kaynak", "Liman")).capitalize()
            t_no = str(item.get("tartim_no", "—") or "—")
            t_dt = str(item.get("tarih", "—") or "—")
            plaka = str(item.get("plaka", "—") or "—")
            firma = str(item.get("firma", "—") or "—")
            dba = str(item.get("dba", "—") or "—")
            durum = str(item.get("durum", "⏳ Tartım Bekliyor") or "⏳ Tartım Bekliyor")

            t_val = str(item.get("tartim_no") or "").strip()
            dba_val = str(item.get("dba") or "").strip()
            has_t = bool(t_val) and t_val not in ("—", "-", "None", "")
            has_dba = bool(dba_val) and dba_val not in ("—", "-", "None", "")
            hazir = bool(item.get("hazir")) or "hazır" in durum.lower() or has_t or has_dba
            son_chk = self.format_check_time(item.get("son_kontrol") or item.get("updated_at") or "—")

            if hazir:
                ready_cnt += 1
            else:
                pending_cnt += 1

            if self.current_kantar_filter == "READY" and not hazir:
                continue
            elif self.current_kantar_filter == "PENDING" and hazir:
                continue

            if search_q:
                haystack = f"{c_no} {dosya_no} {t_no} {plaka} {firma} {dba} {kaynak}".upper()
                if search_q not in haystack:
                    continue

            displayed_rows.append({
                "c_no": c_no,
                "dosya_no": dosya_no,
                "kaynak": kaynak,
                "t_no": t_no,
                "t_dt": t_dt,
                "plaka": plaka,
                "firma": firma,
                "dba": dba,
                "durum": durum,
                "son_chk": son_chk,
                "hazir": hazir
            })

        # Update KPI Cards
        self.card_k_total.set_value(len(tracked))
        self.card_k_ready.set_value(ready_cnt)
        self.card_k_pending.set_value(pending_cnt)

        last_scan = getattr(self.kantar_tracker, "last_scan_time", "—")
        scan_t = last_scan.split(" ")[-1] if " " in str(last_scan) else str(last_scan)
        self.card_k_last_scan.set_value(scan_t or "—")

        # Status badge (Modern Pill)
        if self.current_kantar_filter == "READY":
            self.lbl_kantar_status.setText(f"🟢 Filtre: Tartımı Hazır ({len(displayed_rows)}/{len(tracked)})")
            self.lbl_kantar_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")
        elif self.current_kantar_filter == "PENDING":
            self.lbl_kantar_status.setText(f"🟡 Filtre: Tartım Bekleyen ({len(displayed_rows)}/{len(tracked)})")
            self.lbl_kantar_status.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")
        else:
            self.lbl_kantar_status.setText(f"🤖 10 Dk Otonom İzleme Aktif ({len(displayed_rows)} Konteyner)")
            self.lbl_kantar_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")

        # Populate Table (Yüksek Kontrast & Kolay Okunur Dark Obsidian Renkleri)
        self.tree_kantar.setRowCount(len(displayed_rows))
        for row_idx, r in enumerate(displayed_rows):
            is_ready = r["hazir"]

            # 0. Konteyner No (Vurgulu Sky Blue, Bold)
            c_item = QTableWidgetItem(r["c_no"])
            c_item.setForeground(QColor("#38bdf8"))
            f_bold = c_item.font()
            f_bold.setBold(True)
            c_item.setFont(f_bold)
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 1. Dosya No
            d_item = QTableWidgetItem(r["dosya_no"])
            d_item.setForeground(QColor("#e2e8f0"))
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 2. Kaynak
            src_item = QTableWidgetItem(r["kaynak"])
            src_lower = r["kaynak"].lower()
            if "yılport" in src_lower or "yilport" in src_lower:
                src_item.setForeground(QColor("#c084fc"))
            elif "körfez" in src_lower or "korfez" in src_lower or "evyap" in src_lower:
                src_item.setForeground(QColor("#34d399"))
            elif "yarımca" in src_lower or "yarimca" in src_lower:
                src_item.setForeground(QColor("#38bdf8"))
            else:
                src_item.setForeground(QColor("#94a3b8"))
            src_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 3. Tartım No
            t_item = QTableWidgetItem(r["t_no"])
            t_item.setForeground(QColor("#f8fafc"))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 4. Tartım Tarihi
            t_dt_item = QTableWidgetItem(r["t_dt"])
            t_dt_item.setForeground(QColor("#e2e8f0"))
            t_dt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 5. Çekici Plaka
            p_item = QTableWidgetItem(r["plaka"])
            p_item.setForeground(QColor("#f8fafc"))
            p_item.setFont(f_bold)
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 6. Firma / Bayi
            f_item = QTableWidgetItem(r["firma"])
            f_item.setForeground(QColor("#f8fafc"))
            f_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 7. DBA / VGM (Kg)
            dba_item = QTableWidgetItem(r["dba"])
            dba_item.setForeground(QColor("#38bdf8" if r["dba"] not in ("—", "-", "") else "#94a3b8"))
            dba_item.setFont(f_bold)
            dba_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 8. Kantar Durumu
            durum_item = QTableWidgetItem(r["durum"])
            durum_item.setFont(f_bold)
            durum_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if is_ready:
                durum_item.setForeground(QColor("#34d399"))  # Zümrüt Yeşili
            else:
                durum_item.setForeground(QColor("#fbbf24"))  # Kehribar Sarısı

            # 9. Son Kontrol (Saat Bazlı)
            son_chk_item = QTableWidgetItem(r["son_chk"])
            son_chk_item.setForeground(QColor("#38bdf8" if r["son_chk"] != "—" else "#64748b"))
            son_chk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            row_items = [c_item, d_item, src_item, t_item, t_dt_item, p_item, f_item, dba_item, durum_item, son_chk_item]
            for col_idx, item in enumerate(row_items):
                if is_ready:
                    item.setBackground(QColor(16, 185, 129, 14))
                else:
                    item.setBackground(QColor(245, 158, 11, 12))
                self.tree_kantar.setItem(row_idx, col_idx, item)

    # ------------------------------------------------------------------
    # ACTIONS & WORKERS
    # ------------------------------------------------------------------
    def download_and_open_selected_kantar_pdf(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_kantar.selectedIndexes()))
        if not selected_rows:
            self.show_info("Bilgi", "Lütfen PDF tikesini açmak istediğiniz bir konteyner seçin.")
            return

        c_item = self.tree_kantar.item(selected_rows[0], 0)
        c_no = c_item.text().strip() if c_item else ""
        if not c_no or not self.kantar_tracker:
            return

        self.lbl_kantar_status.setText(f"⏳ {c_no} tikesi indiriliyor...")
        fn = getattr(self.kantar_tracker, "download_and_get_pdf", None) or getattr(self.kantar_tracker, "download_pdf_tike", None)
        if not fn:
            self.show_warning("Uyarı", "PDF indirme fonksiyonu bulunamadı.")
            return

        def _worker():
            pdf_path = fn(c_no)
            def _done():
                self.refresh_kantar_takip_table()
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.startfile(pdf_path)
                    except Exception:
                        self.show_info("PDF İndirildi", f"Kantar tikesi başarıyla indirildi:\n{pdf_path}")
                else:
                    self.show_warning("Tike Bulunamadı", f"'{c_no}' konteyneri için henüz bir kantar tikesi veya PDF oluşturulmamış.\nLiman tartımının tamamlanması bekleniyor.")
            QTimer.singleShot(0, _done)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def query_selected_kantar_row(self, cntr_no: str):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return

        self.lbl_kantar_status.setText(f"⏳ {cntr_no} sorgulanıyor...")
        self._active_worker = KantarQueryWorker(self.kantar_tracker, [cntr_no])
        self._active_worker.progress.connect(self._on_single_kantar_query_done)
        self._active_worker.start()

    def _on_single_kantar_query_done(self, cur, tot, c_no, res):
        self.refresh_kantar_takip_table()
        if res.get("success"):
            hazir = res.get("hazir")
            msg = f"📦 Konteyner: {c_no}\n"
            msg += f"📊 Durum: {'🟢 Tartım Hazır' if hazir else '⏳ Tartım Bekliyor'}\n"
            msg += f"🧾 Tartım No: {res.get('tartim_no') or '—'}\n"
            msg += f"📅 Tarih: {res.get('tarih') or '—'}\n"
            msg += f"🚛 Plaka: {res.get('plaka') or '—'}\n"
            msg += f"⚖️ DBA (VGM): {res.get('dba') or '—'}\n"
            self.show_info("DP World & Körfez Kantar Sonucu", msg)
        else:
            self.show_error("Hata", f"Kantar sorgulanamadı:\n{res.get('error')}")

    def launch_yilport_auth_helper(self):
        """Yılport oturum ve doğrulama penceresini doğrudan PyQt6 içinde açar."""
        dlg = YilportAuthDialog(self, on_success=self.run_kantar_scan_now)
        dlg.exec()

    def run_kantar_scan_now(self):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return
        if getattr(self.kantar_tracker, "is_scanning", False):
            self.show_warning("Tarama Sürüyor", "Kantar taraması şu anda devam ediyor, lütfen bekleyin.")
            return

        active_list = self.kantar_tracker.list_tracked(only_active=True)
        if not active_list:
            self.show_info("Bilgi", "Kantar takip havuzunda taranacak aktif konteyner bulunamadı.\nÖnce konteyner ekleyin veya Evrim'den aktarın.")
            return

        self.btn_kantar_scan_now.setEnabled(False)
        self.btn_kantar_scan_now.setText("⏳ Taranıyor...")
        self.lbl_kantar_status.setText(f"🔄 Canlı Kantar Taraması Yapılıyor ({len(active_list)} Konteyner)...")

        self._active_worker = KantarScanCycleWorker(self.kantar_tracker)
        self._active_worker.finished_scan.connect(self._on_kantar_scan_cycle_done)
        self._active_worker.error.connect(lambda err: self.show_error("Tarama Hatası", err))
        self._active_worker.start()

    def _on_kantar_scan_cycle_done(self, res: dict):
        self.btn_kantar_scan_now.setEnabled(True)
        self.btn_kantar_scan_now.setText("🔄 Şimdi Tümünü Tara")
        self.refresh_kantar_takip_table()
        tot = res.get("total_checked", 0)
        chg = res.get("changed_count", 0)
        self.show_info("Tarama Tamamlandı", f"{tot} konteyner kantar portallarında sorgulandı.\nHazır olan yeni tike: {chg} adet.")

    def auto_sync_kantar_from_evrim(self):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return
        if self.engine and not getattr(self.engine, "records", None):
            if hasattr(self.engine, "fetch_excel_records"):
                self.engine.fetch_excel_records()

        evrim_recs = self.evrim_records
        engine_recs = getattr(self.engine, "records", []) if self.engine else []
        cnt = self.kantar_tracker.auto_sync_from_evrim_and_excel(evrim_recs, engine_recs)
        self.refresh_kantar_takip_table()
        self.show_info("Kantar Senkronizasyonu", f"Excel U Sütunu ve Evrim'den {cnt} yeni konteyner Kantar takip havuzuna aktarıldı!")

    def merge_and_download_kantar_pdfs(self):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return

        selected_rows = sorted(set(idx.row() for idx in self.tree_kantar.selectedIndexes()))
        if selected_rows:
            cntr_list = [self.tree_kantar.item(r, 0).text().strip() for r in selected_rows if self.tree_kantar.item(r, 0)]
        else:
            cntr_list = None

        tracked = self.kantar_tracker.list_tracked(only_active=True)
        if cntr_list is not None:
            c_set = set(cntr_list)
            ready_recs = [r for r in tracked if r.get("konteyner_no") in c_set and (r.get("hazir") or r.get("pdf_url"))]
        else:
            ready_recs = [r for r in tracked if r.get("hazir") or r.get("pdf_url")]

        if not ready_recs:
            self.show_warning("Hazır Tike Yok", "Birleştirilecek hazır kantar tikesi (PDF) bulunamadı.\nLütfen önce tarama yapın veya hazır konteynerleri seçin.")
            return

        tarih_str = datetime.now().strftime("%Y%m%d_%H%M")
        oneri_ad = f"Kantar_Tikeler_{tarih_str}.pdf"
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Birleşik Kantar Tike PDF'ini Kaydet", oneri_ad, "PDF Dosyası (*.pdf)"
        )
        if not output_path:
            return

        self.btn_kantar_merge_pdf.setEnabled(False)
        self.btn_kantar_merge_pdf.setText("⏳ Birleştiriliyor...")

        self._active_worker = KantarMergeWorker(self.kantar_tracker, output_path, cntr_list)
        self._active_worker.progress.connect(lambda done, tot, cntr: self.lbl_kantar_status.setText(f"📦 Birleştiriliyor: {cntr} ({done}/{tot})"))
        self._active_worker.finished_merge.connect(self._on_merge_done)
        self._active_worker.start()

    def _on_merge_done(self, res: dict):
        self.btn_kantar_merge_pdf.setEnabled(True)
        self.btn_kantar_merge_pdf.setText("📦 Tike PDF'lerini Birleştir")
        self.refresh_kantar_takip_table()

        if res.get("success"):
            merged = res.get("total", 0)
            skipped = res.get("skipped", 0)
            merged_path = res.get("merged_path", "")
            atla_satiri = f"\n⚠️ PDF'i henüz hazır olmayan: {skipped} adet (atlandı)" if skipped else ""
            msg = f"✅ {merged} adet kantar tikesi başarıyla birleştirildi!{atla_satiri}\n\n📁 Kaydedilen dosya:\n{merged_path}\n\nPDF şimdi açılsın mı?"
            reply = QMessageBox.question(self, "Birleştirme Tamamlandı", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.startfile(merged_path)
                except Exception:
                    pass
        else:
            self.show_error("Birleştirme Başarısız", f"PDF birleştirme işlemi tamamlanamadı:\n{res.get('error', 'Bilinmeyen hata')}")

    def remove_kantar_selected_rows(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_kantar.selectedIndexes()))
        if not selected_rows or not self.kantar_tracker:
            return
        cntrs = [self.tree_kantar.item(r, 0).text().strip() for r in selected_rows if self.tree_kantar.item(r, 0)]
        if not cntrs:
            return

        msg = f"Seçili {len(cntrs)} adet konteyner takipten çıkarılsın mı?" if len(cntrs) > 1 else f"'{cntrs[0]}' takipten çıkarılsın mı?"
        reply = QMessageBox.question(self, "Takipten Çıkar", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.kantar_tracker.remove_multiple_from_tracking(cntrs)
            self.refresh_kantar_takip_table()

    def clear_all_kantar_pool(self):
        if not self.kantar_tracker:
            return
        tracked = self.kantar_tracker.list_tracked()
        if not tracked:
            self.show_info("Bilgi", "Kantar takip havuzu zaten boş.")
            return

        reply = QMessageBox.question(self, "Havuzu Temizle", f"Tüm kantar takip havuzundaki ({len(tracked)} konteyner) sıfırlamak istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.kantar_tracker.clear_all_tracking()
            self.refresh_kantar_takip_table()
            self.show_info("Temizlendi", "Kantar takip havuzu tamamen temizlendi.")

    # ------------------------------------------------------------------
    # CONTEXT MENU
    # ------------------------------------------------------------------
    def show_kantar_context_menu(self, pos):
        selected_rows = sorted(set(idx.row() for idx in self.tree_kantar.selectedIndexes()))
        sel_count = len(selected_rows)
        if sel_count == 0:
            return

        menu = QMenu(self)
        if sel_count == 1:
            r = selected_rows[0]
            c_no = self.tree_kantar.item(r, 0).text() if self.tree_kantar.item(r, 0) else ""
            d_no = self.tree_kantar.item(r, 1).text() if self.tree_kantar.item(r, 1) else ""
            menu.addAction(f"📄 Kantar Tikesi PDF'ini Aç / İndir: {c_no}", self.download_and_open_selected_kantar_pdf)
            menu.addAction(f"🔍 Şimdi Canlı Tartım Sorgula: {c_no}", lambda: self.query_selected_kantar_row(c_no))
            menu.addAction("📋 Konteyner No Kopyala", lambda: self.copy_to_clipboard(c_no))
            if d_no and d_no not in ("—", "-", "None", ""):
                menu.addAction(f"📋 Dosya No Kopyala ({d_no})", lambda: self.copy_to_clipboard(d_no))
            menu.addSeparator()
            menu.addAction("❌ Takipten Çıkar", self.remove_kantar_selected_rows)
        else:
            menu.addAction(f"🔍 Seçili ({sel_count}) Konteyneri Canlı Sorgula", self._query_multiple_kantar)
            menu.addAction(f"📦 Seçili ({sel_count}) Tike PDF'ini Birleştir & İndir", self.merge_and_download_kantar_pdfs)
            menu.addAction(f"📋 Seçili ({sel_count}) Konteyner Numaralarını Kopyala", self._copy_selected_cntrs)
            menu.addSeparator()
            menu.addAction(f"❌ Seçili ({sel_count}) Konteyneri Takipten Çıkar", self.remove_kantar_selected_rows)

        menu.addSeparator()
        menu.addAction("🗑️ Tüm Kantar Havuzunu Temizle", self.clear_all_kantar_pool)
        menu.exec(self.tree_kantar.viewport().mapToGlobal(pos))

    def _query_multiple_kantar(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_kantar.selectedIndexes()))
        cntrs = [self.tree_kantar.item(r, 0).text().strip() for r in selected_rows if self.tree_kantar.item(r, 0)]
        if not cntrs or not self.kantar_tracker:
            return

        self.btn_kantar_scan_now.setEnabled(False)
        self.btn_kantar_scan_now.setText(f"⏳ {len(cntrs)} Taranıyor...")

        self._active_worker = KantarQueryWorker(self.kantar_tracker, cntrs)
        self._active_worker.progress.connect(lambda cur, tot, c, res: self.refresh_kantar_takip_table())
        self._active_worker.finished_batch.connect(lambda c, el: self.refresh_kantar_takip_table())
        self._active_worker.start()

    def _copy_selected_cntrs(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_kantar.selectedIndexes()))
        cntrs = [self.tree_kantar.item(r, 0).text().strip() for r in selected_rows if self.tree_kantar.item(r, 0)]
        if cntrs:
            self.copy_to_clipboard("\n".join(cntrs))
            self.show_info("Kopyalandı", f"{len(cntrs)} adet konteyner numarası panoya kopyalandı!")

    # ------------------------------------------------------------------
    # MODAL: KONTEYNER EKLE
    # ------------------------------------------------------------------
    def show_kantar_add_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("➕ Kantar Takip Havuzuna Konteyner Ekle")
        dlg.resize(520, 420)
        dlg.setStyleSheet("background-color: #0b0f19; color: #f8fafc;")

        d_layout = QVBoxLayout(dlg)
        d_layout.setContentsMargins(18, 18, 18, 18)
        d_layout.setSpacing(12)

        lbl = QLabel("İzlemek istediğiniz Konteyner numaralarını alt alta yapıştırın:", dlg)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")
        d_layout.addWidget(lbl)

        txt_input = QTextEdit(dlg)
        txt_input.setFont(QFont("Consolas", 10))
        txt_input.setPlaceholderText("Örnek:\nMSKU1234567\nTGHU9876543")
        txt_input.setStyleSheet("""
            QTextEdit {
                background-color: #111827;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', monospace;
            }
            QTextEdit:focus {
                border-color: #38bdf8;
            }
        """)
        d_layout.addWidget(txt_input, stretch=1)

        # Lookup
        cntr_lookup = {}
        pool = list(self.evrim_records)
        engine_recs = getattr(self.engine, "records", []) if self.engine else []
        for r in engine_recs:
            if not any(e.get("dosya_no") == r.get("dosya") for e in pool):
                pool.append(r)
        for rec in pool:
            c_raw = rec.get("konteyner") or rec.get("konteyner_no") or rec.get("cntr") or ""
            if isinstance(c_raw, str):
                for part in re.split(r"[\s,;+/]+", c_raw):
                    c_clean = re.sub(r"[^A-Z0-9]", "", part.upper())
                    if len(c_clean) >= 4:
                        cntr_lookup[c_clean] = rec

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("İptal", dlg)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #94a3b8;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #334155; color: #f8fafc; }
        """)
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("✅ Havuza Ekle ve Başlat", dlg)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                color: #ffffff;
                padding: 6px 16px;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)

        def _do_add():
            if not self.kantar_tracker:
                self.show_error("Hata", "Kantar takip servisi devrede değil.")
                return
            raw = txt_input.toPlainText().strip()
            if not raw:
                self.show_warning("Uyarı", "Lütfen en az bir konteyner numarası girin.")
                return

            lines = [l.strip() for l in re.split(r"[\n,;]+", raw) if l.strip()]
            added = 0
            updated = 0
            for line in lines:
                clean_no = re.sub(r"[^A-Z0-9]", "", line.upper())
                if len(clean_no) >= 4:
                    rec_match = cntr_lookup.get(clean_no, {})
                    dosya = rec_match.get("dosya_no") or rec_match.get("dosya") or "—"
                    ref = rec_match.get("hankook_ref") or rec_match.get("musteri_referans") or rec_match.get("ref") or "—"
                    firma = rec_match.get("yurt_disi_firma") or rec_match.get("bayi") or rec_match.get("firma") or "WH-HANKOOK"

                    res = self.kantar_tracker.add_to_tracking(clean_no, dosya_no=dosya, ref=ref, firma=firma, kaynak="otomatik")
                    if res.get("success"):
                        if res.get("created"):
                            added += 1
                        else:
                            updated += 1

            self.refresh_kantar_takip_table()
            dlg.accept()
            if added > 0 or updated > 0:
                self.show_info("Başarılı", f"{added} yeni konteyner eklendi, {updated} mevcut kayıt güncellendi!")
            else:
                self.show_warning("Uyarı", "Geçerli formatta (en az 4 haneli) konteyner numarası bulunamadı.")

        btn_save.clicked.connect(_do_add)
        btn_box.addWidget(btn_save)
        d_layout.addLayout(btn_box)

        dlg.exec()
