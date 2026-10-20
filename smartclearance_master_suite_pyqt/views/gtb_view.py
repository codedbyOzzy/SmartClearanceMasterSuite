# -*- coding: utf-8 -*-
"""
gtb_view.py — GTB Otonom Beyanname Takip Görünümü (PyQt6)
MasterSuite için GTB canlı takip tablosu, manuel sorgu diyaloğu, akıllı içe aktarma, filtreler, vergi maili ve otonom takip motoru bağlantısı.
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
    QTextEdit, QRadioButton, QButtonGroup, QComboBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QCursor, QKeySequence, QShortcut

from .base_view import BaseView
from ..components.metric_card import MetricCard


# ----------------------------------------------------------------------
# Background Worker for Querying Single or Multiple GTB Declarations
# ----------------------------------------------------------------------
class GTBQueryWorker(QThread):
    progress = pyqtSignal(int, int, str, str)  # current, total, beyan_no, status
    finished_batch = pyqtSignal(int, float)    # count, elapsed
    error = pyqtSignal(str)

    def __init__(self, gtb_tracker, beyan_list: List[str]):
        super().__init__()
        self.gtb_tracker = gtb_tracker
        self.beyan_list = beyan_list

    def run(self):
        if not self.gtb_tracker or not self.beyan_list:
            return
        t_start = time.time()
        total = len(self.beyan_list)
        for i, b in enumerate(self.beyan_list, 1):
            try:
                res = self.gtb_tracker.query_single_now(b)
                st = res.get("durum", "") if res.get("success") else res.get("error", "Hata")
            except Exception as exc:
                st = str(exc)
            self.progress.emit(i, total, b, st)
            time.sleep(0.3)
        elapsed = time.time() - t_start
        self.finished_batch.emit(total, elapsed)


class GTBView(BaseView):
    """GTB Otonom Beyanname Takip Sekmesi (PyQt6)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.current_gtb_filter = "ALL"  # 'ALL', 'CLOSED', 'IN_PROC'
        self._active_worker: Optional[GTBQueryWorker] = None
        self._build_ui()

    @property
    def gtb_tracker(self):
        if self.main_window and hasattr(self.main_window, "gtb_tracker"):
            return self.main_window.gtb_tracker
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

        self.card_gtb_total = MetricCard(
            "İZLENEN BEYANNAMELER", "0", "Otonom Havuzda", "#38bdf8", self
        )
        self.card_gtb_total.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_gtb_total.mousePressEvent = lambda e: self.filter_gtb_table("ALL")
        metric_bar.addWidget(self.card_gtb_total)

        self.card_gtb_closed = MetricCard(
            "KAPANAN / TAMAMLANAN", "0", "Gümrük Bitti", "#10b981", self
        )
        self.card_gtb_closed.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_gtb_closed.mousePressEvent = lambda e: self.filter_gtb_table("CLOSED")
        metric_bar.addWidget(self.card_gtb_closed)

        self.card_gtb_in_proc = MetricCard(
            "İŞLEMDE OLANLAR", "0", "Tescil / Muayene", "#f59e0b", self
        )
        self.card_gtb_in_proc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_gtb_in_proc.mousePressEvent = lambda e: self.filter_gtb_table("IN_PROC")
        metric_bar.addWidget(self.card_gtb_in_proc)

        self.card_gtb_last_scan = MetricCard(
            "SON OTONOM TARAMA", "—", "10 Dk Döngü", "#38bdf8", self
        )
        metric_bar.addWidget(self.card_gtb_last_scan)

        layout.addLayout(metric_bar)

        # 2. Kontrol Çubuğu & Aksiyon Butonları (Modern Dark Obsidian Ahengi)
        ctrl_bar = QFrame(self)
        ctrl_bar.setStyleSheet("""
            QFrame {
                background-color: #0e131d;
                border: 1px solid #1c2433;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        cb_layout = QHBoxLayout(ctrl_bar)
        cb_layout.setContentsMargins(10, 6, 10, 6)
        cb_layout.setSpacing(8)

        lbl_s = QLabel("🔍 Ara / Filtrele:", ctrl_bar)
        lbl_s.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 11px; border: none; background: transparent;")
        cb_layout.addWidget(lbl_s)

        self.txt_gtb_search = QLineEdit(ctrl_bar)
        self.txt_gtb_search.setPlaceholderText("Beyan No, Dosya, Ref veya Firma...")
        self.txt_gtb_search.setFixedWidth(230)
        self.txt_gtb_search.setStyleSheet("background-color: #080c14; color: #f8fafc; border: 1px solid #232c3d; border-radius: 6px; padding: 6px 10px; font-size: 11px;")
        self.txt_gtb_search.textChanged.connect(self.refresh_gtb_takip_table)
        cb_layout.addWidget(self.txt_gtb_search)

        self.btn_gtb_add = QPushButton("➕ Manuel Beyanname Ekle", ctrl_bar)
        self.btn_gtb_add.setStyleSheet("background-color: #1e293b; color: #f8fafc; border: 1px solid rgba(56, 189, 248, 0.4); font-weight: 600; padding: 6px 12px; border-radius: 6px;")
        self.btn_gtb_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_gtb_add.clicked.connect(self.show_gtb_add_dialog)
        cb_layout.addWidget(self.btn_gtb_add)

        self.btn_gtb_auto_sync = QPushButton("⚡ Otomatik İçe Aktar (Evrim & Excel)", ctrl_bar)
        self.btn_gtb_auto_sync.setStyleSheet("background-color: #065f46; color: #34d399; border: 1px solid #10b981; font-weight: 700; padding: 6px 12px; border-radius: 6px;")
        self.btn_gtb_auto_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_gtb_auto_sync.clicked.connect(self.auto_sync_gtb_from_evrim_and_excel)
        cb_layout.addWidget(self.btn_gtb_auto_sync)

        self.btn_gtb_sync = QPushButton("📅 Tescil Tarihine Göre Aktar...", ctrl_bar)
        self.btn_gtb_sync.setStyleSheet("background-color: #151d2a; color: #e2e8f0; border: 1px solid #2a374f; font-weight: 600; padding: 6px 12px; border-radius: 6px;")
        self.btn_gtb_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_gtb_sync.clicked.connect(self.show_gtb_smart_import_dialog)
        cb_layout.addWidget(self.btn_gtb_sync)

        self.btn_gtb_scan_now = QPushButton("🔄 Şimdi Tümünü Tara", ctrl_bar)
        self.btn_gtb_scan_now.setStyleSheet("background-color: #0284c7; color: #ffffff; border: 1px solid #38bdf8; font-weight: 700; padding: 6px 14px; border-radius: 6px;")
        self.btn_gtb_scan_now.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_gtb_scan_now.clicked.connect(self.run_gtb_scan_now)
        cb_layout.addWidget(self.btn_gtb_scan_now)

        self.btn_gtb_mail = QPushButton("📧 Vergi Talebi Maili Oluştur", ctrl_bar)
        self.btn_gtb_mail.setStyleSheet("background-color: #1e293b; color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.4); font-weight: 600; padding: 6px 12px; border-radius: 6px;")
        self.btn_gtb_mail.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_gtb_mail.clicked.connect(self.create_tax_mail_from_gtb)
        cb_layout.addWidget(self.btn_gtb_mail)

        self.btn_gtb_clear_all = QPushButton("🗑️ Havuzu Temizle", ctrl_bar)
        self.btn_gtb_clear_all.setStyleSheet("background-color: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 600; padding: 6px 10px; border-radius: 6px;")
        self.btn_gtb_clear_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_gtb_clear_all.clicked.connect(self.clear_all_gtb_pool)
        cb_layout.addWidget(self.btn_gtb_clear_all)

        cb_layout.addStretch()

        self.lbl_gtb_status = QLabel("🤖 10 Dk Otonom İzleme Aktif", ctrl_bar)
        self.lbl_gtb_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")
        cb_layout.addWidget(self.lbl_gtb_status)

        layout.addWidget(ctrl_bar)

        # 3. Tablo
        self.tree_gtb = QTableWidget(self)
        self.tree_gtb.setColumnCount(7)
        self.tree_gtb.setHorizontalHeaderLabels([
            "16 Haneli Beyanname No", "Dosya No", "Referans No",
            "Firma / Bayi", "GTB Bakanlık Canlı Durumu", "Son Kontrol", "Değişim Zamanı"
        ])
        self.tree_gtb.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_gtb.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_gtb.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_gtb.setAlternatingRowColors(True)
        self.tree_gtb.verticalHeader().setVisible(False)
        self.tree_gtb.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_gtb.customContextMenuRequested.connect(self.show_gtb_context_menu)
        self.tree_gtb.cellDoubleClicked.connect(lambda r, c: self.on_gtb_row_double_click(r))

        # Header sütun genişlikleri
        header = self.tree_gtb.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)

        self.tree_gtb.setColumnWidth(0, 180)
        self.tree_gtb.setColumnWidth(1, 100)
        self.tree_gtb.setColumnWidth(2, 130)
        self.tree_gtb.setColumnWidth(3, 140)
        self.tree_gtb.setColumnWidth(5, 120)
        self.tree_gtb.setColumnWidth(6, 120)

        # Kısayollar: Delete
        shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.tree_gtb)
        shortcut_del.activated.connect(self.remove_gtb_selected_rows)

        layout.addWidget(self.tree_gtb, stretch=1)

    # ------------------------------------------------------------------
    # LIFECYCLE & REFRESH
    # ------------------------------------------------------------------
    def on_activate(self):
        self.refresh_gtb_takip_table()

    def refresh_table(self):
        self.refresh_gtb_takip_table()

    def on_gtb_status_changed(self):
        """Called by background tracker when statuses update."""
        QTimer.singleShot(0, self.refresh_gtb_takip_table)

    def filter_gtb_table(self, filter_type: str):
        self.current_gtb_filter = filter_type
        self.refresh_gtb_takip_table()

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

    def refresh_gtb_takip_table(self):
        if not self.gtb_tracker:
            self.tree_gtb.setRowCount(0)
            return

        raw_tracked = self.gtb_tracker.list_tracked(only_active=True)
        tracked = [
            item for item in raw_tracked
            if item.get("beyanname_no") and not str(item.get("beyanname_no")).startswith("BEYAN")
        ]
        search_q = self.txt_gtb_search.text().strip().upper()

        kapanan_cnt = 0
        islemde_cnt = 0
        displayed_rows = []

        for item in tracked:
            b_no = str(item.get("beyanname_no", ""))
            d_no = str(item.get("dosya_no", "—") or "—")
            ref_no = str(item.get("ref", "—") or "—")
            firma = str(item.get("firma", "—") or "—")
            statu = str(item.get("durum", "—") or "—")
            is_kapandi = bool(item.get("kapandi")) or "kapan" in statu.lower() or "tamamlan" in statu.lower()
            son_chk = self.format_check_time(item.get("son_kontrol") or item.get("son_sorgu_zamani") or "—")
            deg_dt = self.format_check_time(item.get("degisim_tarihi") or "—")

            if is_kapandi:
                kapanan_cnt += 1
            else:
                islemde_cnt += 1

            if self.current_gtb_filter == "CLOSED" and not is_kapandi:
                continue
            elif self.current_gtb_filter == "IN_PROC" and is_kapandi:
                continue

            if search_q:
                haystack = f"{b_no} {d_no} {ref_no} {firma} {statu}".upper()
                if search_q not in haystack:
                    continue

            displayed_rows.append({
                "beyan_no": b_no,
                "dosya_no": d_no,
                "ref": ref_no,
                "firma": firma,
                "statu": statu,
                "son_chk": son_chk,
                "deg_dt": deg_dt,
                "is_kapandi": is_kapandi
            })

        # Update metrics
        self.card_gtb_total.set_value(len(tracked))
        self.card_gtb_closed.set_value(kapanan_cnt)
        self.card_gtb_in_proc.set_value(islemde_cnt)

        last_scan = getattr(self.gtb_tracker, "last_scan_time", "—")
        scan_t = last_scan.split(" ")[-1] if " " in str(last_scan) else str(last_scan)
        self.card_gtb_last_scan.set_value(scan_t or "—")

        # Status label (Modern Pill)
        if self.current_gtb_filter == "CLOSED":
            self.lbl_gtb_status.setText(f"🟢 Filtre: Kapananlar ({len(displayed_rows)}/{len(tracked)})")
            self.lbl_gtb_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")
        elif self.current_gtb_filter == "IN_PROC":
            self.lbl_gtb_status.setText(f"🟡 Filtre: İşlemde Olanlar ({len(displayed_rows)}/{len(tracked)})")
            self.lbl_gtb_status.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")
        else:
            self.lbl_gtb_status.setText(f"🤖 10 Dk Otonom İzleme Aktif ({len(displayed_rows)} Beyanname)")
            self.lbl_gtb_status.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 6px;")

        # Populate Table (Yüksek Kontrast & Kolay Okunur Dark Obsidian Renkleri)
        self.tree_gtb.setRowCount(len(displayed_rows))
        for row_idx, r in enumerate(displayed_rows):
            is_closed = r["is_kapandi"]
            statu_lower = r["statu"].lower()
            is_proc = "işlemde" in statu_lower or "süresi" in statu_lower or "tescil" in statu_lower or "muayene" in statu_lower
            is_red = any(k in statu_lower for k in ["kırmızı", "bloke", "red", "iptal", "hata"])

            # 1. Beyanname No (Vurgulu Sky Blue)
            b_item = QTableWidgetItem(r["beyan_no"])
            b_item.setForeground(QColor("#38bdf8"))
            f_bold = b_item.font()
            f_bold.setBold(True)
            b_item.setFont(f_bold)
            b_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 2. Dosya No
            d_item = QTableWidgetItem(r["dosya_no"])
            d_item.setForeground(QColor("#e2e8f0"))
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 3. Referans No
            ref_item = QTableWidgetItem(r["ref"])
            ref_item.setForeground(QColor("#e2e8f0"))
            ref_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 4. Firma / Bayi
            firma_item = QTableWidgetItem(r["firma"])
            firma_item.setForeground(QColor("#f8fafc"))
            firma_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 5. GTB Canlı Durumu
            statu_item = QTableWidgetItem(r["statu"])
            statu_item.setFont(f_bold)
            statu_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            if is_closed:
                statu_item.setForeground(QColor("#34d399"))  # Zümrüt Yeşili
            elif is_red:
                statu_item.setForeground(QColor("#f87171"))  # Canlı Kırmızı
            elif is_proc or "sarı" in statu_lower:
                statu_item.setForeground(QColor("#fbbf24"))  # Canlı Kehribar Sarısı
            else:
                statu_item.setForeground(QColor("#f8fafc"))  # Temiz Beyaz

            # 6. Son Kontrol (Saat Bazlı)
            son_chk_item = QTableWidgetItem(r["son_chk"])
            son_chk_item.setForeground(QColor("#38bdf8" if r["son_chk"] != "—" else "#64748b"))
            son_chk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 7. Değişim Zamanı (Saat Bazlı)
            deg_dt_item = QTableWidgetItem(r["deg_dt"])
            deg_dt_item.setForeground(QColor("#94a3b8" if r["deg_dt"] != "—" else "#64748b"))
            deg_dt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            row_items = [b_item, d_item, ref_item, firma_item, statu_item, son_chk_item, deg_dt_item]
            for col_idx, item in enumerate(row_items):
                if is_closed:
                    item.setBackground(QColor(16, 185, 129, 14))
                elif is_proc:
                    item.setBackground(QColor(245, 158, 11, 14))
                elif is_red:
                    item.setBackground(QColor(239, 68, 68, 16))
                self.tree_gtb.setItem(row_idx, col_idx, item)

    # ------------------------------------------------------------------
    # ACTIONS & WORKERS
    # ------------------------------------------------------------------
    def on_gtb_row_double_click(self, row: int):
        item = self.tree_gtb.item(row, 0)
        if item:
            b_no = item.text().strip()
            if b_no:
                self.query_selected_gtb_row(b_no)

    def query_selected_gtb_row(self, beyanname_no: str):
        if not self.gtb_tracker:
            self.show_warning("GTB Servisi", "GTB takip servisi aktif değil.")
            return

        self.lbl_gtb_status.setText(f"⏳ {beyanname_no} sorgulanıyor...")
        self.lbl_gtb_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #1e40af; background-color: #dbeafe; padding: 5px 10px; border-radius: 6px;")

        self._active_worker = GTBQueryWorker(self.gtb_tracker, [beyanname_no])
        self._active_worker.progress.connect(self._on_single_query_progress)
        self._active_worker.finished_batch.connect(self._on_single_query_finished)
        self._active_worker.start()

    def _on_single_query_progress(self, cur, tot, b_no, status):
        self.refresh_gtb_takip_table()
        self.show_info("GTB Canlı Sonuç", f"📑 Beyanname: {b_no}\n\n🏛️ Bakanlık Durumu:\n{status}")

    def _on_single_query_finished(self, count, elapsed):
        self.refresh_gtb_takip_table()

    def run_gtb_scan_now(self):
        if not self.gtb_tracker:
            self.show_warning("GTB Servisi", "GTB takip servisi aktif değil.")
            return

        raw_tracked = self.gtb_tracker.list_tracked(only_active=True)
        beyan_list = [r["beyanname_no"] for r in raw_tracked if r.get("beyanname_no") and not str(r.get("beyanname_no")).startswith("BEYAN")]
        if not beyan_list:
            self.show_info("Bilgi", "GTB Takip havuzunda taranacak beyanname bulunamadı.")
            return

        self.btn_gtb_scan_now.setEnabled(False)
        self.btn_gtb_scan_now.setText(f"⏳ {len(beyan_list)} Taranıyor...")

        self._active_worker = GTBQueryWorker(self.gtb_tracker, beyan_list)
        self._active_worker.progress.connect(self._on_scan_progress)
        self._active_worker.finished_batch.connect(self._on_scan_finished)
        self._active_worker.start()

    def _on_scan_progress(self, cur, tot, b_no, status):
        self.lbl_gtb_status.setText(f"🔄 Taranıyor [{cur}/{tot}]: {b_no}")
        self.lbl_gtb_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #92400e; background-color: #fef3c7; padding: 5px 10px; border-radius: 6px;")
        self.refresh_gtb_takip_table()

    def _on_scan_finished(self, count, elapsed):
        self.btn_gtb_scan_now.setEnabled(True)
        self.btn_gtb_scan_now.setText("🔄 Şimdi Tümünü Tara")
        self.refresh_gtb_takip_table()
        self.show_info("Tamamlandı", f"⚡ {count} adet beyanname {elapsed:.1f} saniyede GTB üzerinden sorgulandı ve güncellendi!")

    def remove_gtb_selected_rows(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_gtb.selectedIndexes()))
        if not selected_rows or not self.gtb_tracker:
            return

        beyan_list = [self.tree_gtb.item(r, 0).text().strip() for r in selected_rows if self.tree_gtb.item(r, 0)]
        if not beyan_list:
            return

        msg = f"Seçili {len(beyan_list)} adet beyannameyi takip havuzundan çıkarmak istediğinize emin misiniz?" if len(beyan_list) > 1 else f"'{beyan_list[0]}' takip havuzundan çıkarılsın mı?"
        reply = QMessageBox.question(self, "Takipten Çıkar", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.gtb_tracker, "remove_multiple_from_tracking"):
                self.gtb_tracker.remove_multiple_from_tracking(beyan_list)
            else:
                for b in beyan_list:
                    self.gtb_tracker.remove_from_tracking(b)
            self.refresh_gtb_takip_table()

    def clear_all_gtb_pool(self):
        tracked = self.gtb_tracker.list_tracked() if self.gtb_tracker else []
        if not tracked:
            self.show_info("Bilgi", "Takip havuzu zaten boş.")
            return

        reply = QMessageBox.question(
            self, "Tüm Havuzu Temizle",
            f"Takip havuzundaki TÜM {len(tracked)} beyannameyi silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.gtb_tracker, "clear_all_tracking"):
                self.gtb_tracker.clear_all_tracking()
            else:
                for r in tracked:
                    self.gtb_tracker.remove_from_tracking(r.get("beyanname_no"))
            self.refresh_gtb_takip_table()
            self.show_info("Temizlendi", "GTB takip havuzu tamamen temizlendi.")

    # ------------------------------------------------------------------
    # TAX MAIL DRAFT (OUTLOOK)
    # ------------------------------------------------------------------
    def create_tax_mail_from_gtb(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_gtb.selectedIndexes()))
        use_all = not selected_rows

        if use_all:
            if self.tree_gtb.rowCount() == 0:
                self.show_warning("Uyarı", "GTB Takip havuzunda beyanname bulunamadı.\nÖnce beyanname ekleyin.")
                return
            target_rows = list(range(self.tree_gtb.rowCount()))
        else:
            target_rows = selected_rows

        gtb_rows = []
        for r in target_rows:
            b_item = self.tree_gtb.item(r, 0)
            d_item = self.tree_gtb.item(r, 1)
            ref_item = self.tree_gtb.item(r, 2)
            f_item = self.tree_gtb.item(r, 3)
            s_item = self.tree_gtb.item(r, 4)
            if b_item:
                gtb_rows.append({
                    "beyan_no": b_item.text().strip(),
                    "dosya_no": d_item.text().strip() if d_item else "",
                    "ref": ref_item.text().strip() if ref_item else "",
                    "firma": f_item.text().strip() if f_item else "",
                    "statu": s_item.text().strip() if s_item else ""
                })

        if not gtb_rows:
            self.show_warning("Uyarı", "Seçili satırlardan veri alınamadı.")
            return

        # Evrim lookup
        evrim_lookup = {}
        for er in self.evrim_records:
            ref_k = (er.get("hankook_ref") or "").strip().upper()
            dosya_k = (er.get("dosya_no") or "").strip().upper()
            if ref_k: evrim_lookup[ref_k] = er
            if dosya_k: evrim_lookup[dosya_k] = er

        formatted_records = []
        for row in gtb_rows:
            ref = row["ref"]
            dosya = row["dosya_no"]
            beyan = row["beyan_no"]
            clean_b = re.sub(r"[^A-Z0-9]", "", beyan.upper())

            ev = evrim_lookup.get(ref.upper()) or evrim_lookup.get(dosya.upper()) or evrim_lookup.get(clean_b) or {}
            if ev:
                ref = (ev.get("hankook_ref") or ref).strip() or ref
                dosya = (ev.get("dosya_no") or dosya).strip() or dosya
                beyan = (ev.get("beyanname_no") or beyan).strip() or beyan

            formatted_records.append({
                "ref": ref or beyan,
                "dosya": dosya or "—",
                "beyan_no": beyan,
                "beyanname": beyan
            })

        if not self.engine or not hasattr(self.engine, "create_tax_mail_draft"):
            self.show_error("Hata", "Motor veya vergi maili oluşturucu bulunamadı.")
            return

        ok, msg = self.engine.create_tax_mail_draft(formatted_records)
        if ok:
            self.show_info("Başarılı", f"✅ {len(formatted_records)} adet beyanname için Vergi Talebi taslağı Outlook'ta açıldı!")
        else:
            self.show_error("Outlook Hatası", msg)

    # ------------------------------------------------------------------
    # CLIPBOARD ACTIONS
    # ------------------------------------------------------------------
    def copy_gtb_column(self, col_idx: int, col_title: str, only_selected=True):
        if only_selected:
            rows = sorted(set(idx.row() for idx in self.tree_gtb.selectedIndexes()))
            scope_name = f"Seçili {len(rows)} adet"
        else:
            rows = list(range(self.tree_gtb.rowCount()))
            scope_name = f"Havuzdaki tüm ({len(rows)})"

        if not rows:
            self.show_warning("Uyarı", "Kopyalanacak satır bulunamadı.")
            return

        vals = []
        for r in rows:
            it = self.tree_gtb.item(r, col_idx)
            if it:
                v = it.text().strip()
                if v and v != "—":
                    vals.append(v)

        if not vals:
            self.show_warning("Uyarı", f"Bu sütunda geçerli {col_title} bulunamadı.")
            return

        self.copy_to_clipboard("\n".join(vals))
        self.show_info("Kopyalandı", f"📋 {scope_name} {col_title} alt alta panoya kopyalandı!")

    def copy_selected_gtb_rows_as_table(self):
        rows = sorted(set(idx.row() for idx in self.tree_gtb.selectedIndexes()))
        if not rows:
            self.show_warning("Uyarı", "Lütfen önce tablodan satır seçin.")
            return

        lines = ["Beyanname No\tDosya No\tReferans No\tFirma / Bayi\tGTB Bakanlık Canlı Durumu\tSon Kontrol\tDeğişim Zamanı"]
        for r in rows:
            row_vals = [self.tree_gtb.item(r, c).text() if self.tree_gtb.item(r, c) else "" for c in range(7)]
            lines.append("\t".join(row_vals))

        self.copy_to_clipboard("\n".join(lines))
        self.show_info("Kopyalandı", f"📋 Seçili {len(rows)} satır Excel formatında panoya kopyalandı!")

    # ------------------------------------------------------------------
    # CONTEXT MENU
    # ------------------------------------------------------------------
    def show_gtb_context_menu(self, pos):
        selected_rows = sorted(set(idx.row() for idx in self.tree_gtb.selectedIndexes()))
        sel_count = len(selected_rows)
        if sel_count == 0:
            return

        menu = QMenu(self)
        if sel_count == 1:
            r = selected_rows[0]
            b_no = self.tree_gtb.item(r, 0).text() if self.tree_gtb.item(r, 0) else ""
            menu.addAction(f"🔍 Şimdi Canlı Sorgula (GTB): {b_no}", lambda: self.query_selected_gtb_row(b_no))
            menu.addAction("📧 Vergi Talebi Maili Oluştur", self.create_tax_mail_from_gtb)
            menu.addSeparator()
            menu.addAction("📋 Beyanname No Kopyala", lambda: self.copy_gtb_column(0, "Beyanname No", True))
            menu.addAction("📋 Dosya No Kopyala", lambda: self.copy_gtb_column(1, "Dosya No", True))
            menu.addAction("📋 Referans No Kopyala", lambda: self.copy_gtb_column(2, "Referans No", True))
            menu.addSeparator()
            menu.addAction("❌ Takipten Çıkar", self.remove_gtb_selected_rows)
        else:
            menu.addAction(f"🔍 Seçili ({sel_count}) Beyannameyi Canlı Sorgula (GTB)", self._query_multiple_selected)
            menu.addAction(f"📧 Seçili ({sel_count}) Beyanname İçin Vergi Talebi Maili Oluştur", self.create_tax_mail_from_gtb)
            menu.addSeparator()
            menu.addAction(f"📋 Seçili ({sel_count}) Beyanname No'ları Kopyala (Alt Alta)", lambda: self.copy_gtb_column(0, "Beyanname No", True))
            menu.addAction(f"📋 Seçili ({sel_count}) Dosya No'ları Kopyala (Alt Alta)", lambda: self.copy_gtb_column(1, "Dosya No", True))
            menu.addAction(f"📋 Seçili ({sel_count}) Referans No'ları Kopyala (Alt Alta)", lambda: self.copy_gtb_column(2, "Referans No", True))
            menu.addAction(f"📋 Seçili ({sel_count}) Satırı Excel Tablosu Olarak Kopyala", self.copy_selected_gtb_rows_as_table)
            menu.addSeparator()
            menu.addAction(f"❌ Seçili ({sel_count}) Beyannameyi Takipten Çıkar", self.remove_gtb_selected_rows)

        # Tablodaki Tüm Sütunu Kopyala Alt Menüsü
        all_count = self.tree_gtb.rowCount()
        sub_all = menu.addMenu(f"📑 Tablodaki TÜM Sütunu Kopyala ({all_count} Satır)...")
        sub_all.addAction(f"📑 TÜM Beyanname No'ları Kopyala", lambda: self.copy_gtb_column(0, "Beyanname No", False))
        sub_all.addAction(f"📑 TÜM Dosya No'ları Kopyala", lambda: self.copy_gtb_column(1, "Dosya No", False))
        sub_all.addAction(f"📑 TÜM Referans No'ları Kopyala", lambda: self.copy_gtb_column(2, "Referans No", False))

        menu.addSeparator()
        menu.addAction("🗑️ Havuzdaki TÜMÜNÜ Takipten Çıkar (Temizle)", self.clear_all_gtb_pool)
        menu.exec(self.tree_gtb.viewport().mapToGlobal(pos))

    def _query_multiple_selected(self):
        selected_rows = sorted(set(idx.row() for idx in self.tree_gtb.selectedIndexes()))
        beyan_list = [self.tree_gtb.item(r, 0).text().strip() for r in selected_rows if self.tree_gtb.item(r, 0)]
        if not beyan_list or not self.gtb_tracker:
            return

        self.btn_gtb_scan_now.setEnabled(False)
        self.btn_gtb_scan_now.setText(f"⏳ {len(beyan_list)} Taranıyor...")

        self._active_worker = GTBQueryWorker(self.gtb_tracker, beyan_list)
        self._active_worker.progress.connect(self._on_scan_progress)
        self._active_worker.finished_batch.connect(self._on_scan_finished)
        self._active_worker.start()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # MODAL: MANUEL BEYANNAME EKLE
    # ------------------------------------------------------------------
    def show_gtb_add_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("➕ GTB Takip Havuzuna Beyanname Ekle")
        dlg.resize(520, 420)
        dlg.setStyleSheet("background-color: #0b0f19; color: #f8fafc;")

        d_layout = QVBoxLayout(dlg)
        d_layout.setContentsMargins(18, 18, 18, 18)
        d_layout.setSpacing(12)

        lbl = QLabel("İzlemek istediğiniz 16 haneli Beyanname numaralarını veya\nreferansları alt alta yapıştırın:", dlg)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")
        d_layout.addWidget(lbl)

        txt_input = QTextEdit(dlg)
        txt_input.setFont(QFont("Consolas", 10))
        txt_input.setPlaceholderText("Örnek:\n24340000EX012345\n24340000IM098765")
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

        # Evrim lookup
        lookup_map = {}
        pool = list(self.evrim_records)
        engine_recs = getattr(self.engine, "records", []) if self.engine else []
        for r in engine_recs:
            if not any(e.get("dosya_no") == r.get("dosya") for e in pool):
                pool.append(r)
        for rec in pool:
            b_raw = rec.get("beyanname_no") or rec.get("gumruk_beyanname_no") or rec.get("beyan")
            clean_b = re.sub(r"[^A-Z0-9]", "", str(b_raw or "").upper())
            if clean_b:
                lookup_map[clean_b] = rec

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
            if not self.gtb_tracker:
                self.show_error("Hata", "GTB takip servisi devrede değil.")
                return
            raw = txt_input.toPlainText().strip()
            if not raw:
                self.show_warning("Uyarı", "Lütfen en az bir beyanname numarası girin.")
                return

            lines = [l.strip() for l in re.split(r"[\n,;]+", raw) if l.strip()]
            added = 0
            updated = 0
            for line in lines:
                clean_no = re.sub(r"[^A-Z0-9]", "", line.upper())
                if len(clean_no) >= 10:
                    rec_match = lookup_map.get(clean_no, {})
                    dosya_no = rec_match.get("dosya_no") or rec_match.get("dosya") or "—"
                    ref_no = rec_match.get("hankook_ref") or rec_match.get("musteri_referans") or rec_match.get("ref") or "—"
                    firma = rec_match.get("yurt_disi_firma") or rec_match.get("bayi") or rec_match.get("firma") or "WH-HANKOOK"

                    res = self.gtb_tracker.add_to_tracking(clean_no, dosya_no=dosya_no, firma=firma, ref=ref_no)
                    if res.get("success"):
                        if res.get("created"):
                            added += 1
                        else:
                            updated += 1

            self.refresh_gtb_takip_table()
            dlg.accept()
            if added > 0 or updated > 0:
                self.show_info("Başarılı", f"{added} yeni beyanname eklendi, {updated} mevcut kayıt güncellendi!")
            else:
                self.show_warning("Uyarı", "Geçerli formatta (en az 10 haneli) beyanname numarası bulunamadı.")

        btn_save.clicked.connect(_do_add)
        btn_box.addWidget(btn_save)
        d_layout.addLayout(btn_box)

        dlg.exec()

    def auto_sync_gtb_from_evrim_and_excel(self):
        """Evrim ve Excel'deki 16 haneli tescil almış beyannameleri tek tıkla GTB takip havuzuna aktarır."""
        if not self.gtb_tracker:
            self.show_warning("GTB Servisi", "GTB takip servisi aktif değil.")
            return

        evrim_recs = list(self.evrim_records)
        engine_recs = getattr(self.engine, "records", []) if self.engine else []
        for r in engine_recs:
            d_no = r.get("dosya") or r.get("dosya_no")
            if not any(e.get("dosya_no") == d_no for e in evrim_recs):
                evrim_recs.append({
                    "beyanname_no": r.get("beyanname_no") or r.get("gumruk_beyanname_no") or r.get("beyan"),
                    "dosya_no": d_no,
                    "hankook_ref": r.get("hankook_ref") or r.get("musteri_referans") or r.get("ref"),
                    "yurt_disi_firma": r.get("bayi") or r.get("firma") or "WH-HANKOOK",
                    "statu": r.get("stage_title") or r.get("statu") or "",
                })

        cnt = self.gtb_tracker.auto_sync_from_evrim_and_excel(evrim_recs)
        self.refresh_gtb_takip_table()
        self.show_info(
            "GTB Senkronizasyonu",
            f"✅ Evrim ve Excel kayıtları taranarak toplam {cnt} adet tescilli beyanname GTB takip havuzuna başarıyla aktarıldı!"
        )

    # ------------------------------------------------------------------
    # MODAL: AKILLI İÇE AKTARMA (TESCİL TARİHİNE GÖRE)
    # ------------------------------------------------------------------
    def show_gtb_smart_import_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("⚡ GTB Takip İçin Dosyaları İçe Aktar (Tescil Tarihine Göre)")
        dlg.resize(760, 600)
        dlg.setStyleSheet("background-color: #0b0f19; color: #f8fafc;")

        d_layout = QVBoxLayout(dlg)
        d_layout.setContentsMargins(16, 16, 16, 16)
        d_layout.setSpacing(12)

        # 1. Havuz Toplama
        date_counts: Dict[str, int] = {}
        all_candidates = []
        seen_beyan = set()

        pool_records = list(self.evrim_records)
        engine_recs = getattr(self.engine, "records", []) if self.engine else []
        for r in engine_recs:
            if not any(e.get("dosya_no") == r.get("dosya") for e in pool_records):
                pool_records.append(r)

        for rec in pool_records:
            b_no = rec.get("beyanname_no") or rec.get("gumruk_beyanname_no") or rec.get("beyan")
            clean_b = re.sub(r"[^A-Z0-9]", "", str(b_no or "").upper())
            if clean_b and len(clean_b) >= 10:
                if clean_b in seen_beyan:
                    continue
                seen_beyan.add(clean_b)

                t_dt = (rec.get("beyanname_tarihi") or rec.get("tescil") or rec.get("tescil_tarihi") or "").strip()
                d_no = rec.get("dosya_no") or rec.get("dosya") or "—"
                ref_no = rec.get("hankook_ref") or rec.get("musteri_referans") or rec.get("ref") or "—"
                firma = rec.get("yurt_disi_firma") or rec.get("bayi") or rec.get("firma") or "WH-HANKOOK"
                statu = rec.get("statu") or rec.get("stage_title") or rec.get("stage") or ""
                is_closed = "kapan" in str(statu).lower() or "teslim" in str(statu).lower() or bool(rec.get("kapanis"))

                cand = {
                    "beyanname_no": clean_b,
                    "dosya_no": d_no,
                    "ref": ref_no,
                    "firma": firma,
                    "tescil": t_dt or "Tarih Yok",
                    "is_closed": is_closed
                }
                all_candidates.append(cand)
                k_date = t_dt or "Tarih Yok"
                date_counts[k_date] = date_counts.get(k_date, 0) + 1

        def _parse_date_sort_key(d_str: str):
            s = str(d_str or "").strip()
            if not s or s == "Tarih Yok":
                return (0, 0, 0)
            # GG.AA.YYYY veya GG/AA/YYYY
            m_dmy = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", s)
            if m_dmy:
                return (int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))
            # YYYY-AA-GG
            m_ymd = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", s)
            if m_ymd:
                return (int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3)))
            return (0, 0, 0)

        sorted_dates = sorted(date_counts.keys(), key=_parse_date_sort_key, reverse=True)
        all_candidates.sort(key=lambda c: _parse_date_sort_key(c.get("tescil", "")), reverse=True)

        # Başlık Paneli
        header_f = QFrame(dlg)
        header_f.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        hf_layout = QVBoxLayout(header_f)
        lbl_h = QLabel("⚡ Tescil Tarihine Göre Toplu İçe Aktarma", header_f)
        lbl_h.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 800; border: none;")
        hf_layout.addWidget(lbl_h)
        lbl_sub = QLabel("Evrim veya Excel'deki tescil almış beyannameleri filtreleyerek GTB Takip havuzuna aktarın.", header_f)
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 10px; border: none;")
        hf_layout.addWidget(lbl_sub)
        d_layout.addWidget(header_f)

        # Filtre Seçenekleri Barı
        opt_frame = QFrame(dlg)
        opt_frame.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        of_layout = QVBoxLayout(opt_frame)

        btn_group = QButtonGroup(dlg)
        rb1 = QRadioButton("📅 Belirli Bir Tescil Tarihindekiler:", opt_frame)
        rb2 = QRadioButton("🟡 Sadece Açık / Kapanmamış Olan Tüm Dosyalar", opt_frame)
        rb3 = QRadioButton("🌐 Sistemdeki Tüm Tescilli Beyannameler", opt_frame)
        for rb in (rb1, rb2, rb3):
            rb.setStyleSheet("color: #e2e8f0; font-weight: 600; font-size: 12px;")
        btn_group.addButton(rb1, 1)
        btn_group.addButton(rb2, 2)
        btn_group.addButton(rb3, 3)

        r1_box = QHBoxLayout()
        r1_box.addWidget(rb1)
        cb_dates = QComboBox(opt_frame)
        cb_dates.setStyleSheet("""
            QComboBox {
                background-color: #0b0f19;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        for d in sorted_dates:
            cb_dates.addItem(f"{d} ({date_counts[d]} Dosya)", d)
        cb_dates.setFixedWidth(220)
        r1_box.addWidget(cb_dates)
        r1_box.addStretch()
        of_layout.addLayout(r1_box)
        of_layout.addWidget(rb2)
        of_layout.addWidget(rb3)

        if sorted_dates:
            rb1.setChecked(True)
        else:
            rb2.setChecked(True)

        d_layout.addWidget(opt_frame)

        # Önizleme Tablosu
        table_prev = QTableWidget(dlg)
        table_prev.setColumnCount(5)
        table_prev.setHorizontalHeaderLabels(["Beyanname No", "Dosya No", "Referans No", "Firma", "Tescil Tarihi"])
        table_prev.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_prev.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table_prev.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table_prev.horizontalHeader().setStretchLastSection(True)
        table_prev.verticalHeader().setVisible(False)
        table_prev.setStyleSheet("""
            QTableWidget {
                background-color: #111827;
                color: #f8fafc;
                border: 1px solid #1e293b;
                gridline-color: #1e293b;
                selection-background-color: #0284c7;
            }
            QHeaderView::section {
                background-color: #0b0f19;
                color: #38bdf8;
                border: 1px solid #1e293b;
                padding: 4px;
                font-weight: bold;
            }
        """)
        d_layout.addWidget(table_prev, stretch=1)

        lbl_info_count = QLabel("Toplam 0 Beyanname Listelendi", dlg)
        lbl_info_count.setStyleSheet("font-weight: 700; color: #38bdf8;")

        def _update_preview():
            mode = btn_group.checkedId()
            sel_date = cb_dates.currentData() if cb_dates.count() > 0 else ""
            filtered = []
            for c in all_candidates:
                if mode == 1:
                    if c["tescil"] == sel_date:
                        filtered.append(c)
                elif mode == 2:
                    if not c["is_closed"]:
                        filtered.append(c)
                else:
                    filtered.append(c)

            table_prev.setRowCount(len(filtered))
            for i, c in enumerate(filtered):
                table_prev.setItem(i, 0, QTableWidgetItem(c["beyanname_no"]))
                table_prev.setItem(i, 1, QTableWidgetItem(c["dosya_no"]))
                table_prev.setItem(i, 2, QTableWidgetItem(c["ref"]))
                table_prev.setItem(i, 3, QTableWidgetItem(c["firma"]))
                table_prev.setItem(i, 4, QTableWidgetItem(c["tescil"]))
            table_prev.selectAll()
            lbl_info_count.setText(f"Toplam {len(filtered)} Beyanname Listelendi")

        rb1.toggled.connect(_update_preview)
        rb2.toggled.connect(_update_preview)
        rb3.toggled.connect(_update_preview)
        cb_dates.currentIndexChanged.connect(_update_preview)
        _update_preview()

        # Alt Butonlar
        bot_box = QHBoxLayout()
        bot_box.addWidget(lbl_info_count)
        bot_box.addStretch()

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
        bot_box.addWidget(btn_cancel)

        btn_import_do = QPushButton("⚡ Seçilenleri GTB Havuzuna Aktar", dlg)
        btn_import_do.setStyleSheet("""
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

        def _do_import():
            selected_rows = sorted(set(idx.row() for idx in table_prev.selectedIndexes()))
            if not selected_rows:
                selected_rows = list(range(table_prev.rowCount()))

            if not selected_rows:
                self.show_warning("Uyarı", "İçe aktarılacak beyanname bulunamadı.")
                return

            added = 0
            updated = 0
            for r in selected_rows:
                b_no = table_prev.item(r, 0).text().strip()
                d_no = table_prev.item(r, 1).text().strip()
                ref = table_prev.item(r, 2).text().strip()
                firma = table_prev.item(r, 3).text().strip()
                res = self.gtb_tracker.add_to_tracking(b_no, dosya_no=d_no, firma=firma, ref=ref)
                if res.get("success"):
                    if res.get("created"):
                        added += 1
                    else:
                        updated += 1

            self.refresh_gtb_takip_table()
            dlg.accept()
            self.show_info("İçe Aktarma Tamamlandı", f"✅ {added} yeni beyanname eklendi, {updated} mevcut kayıt güncellendi!")

        btn_import_do.clicked.connect(_do_import)
        bot_box.addWidget(btn_import_do)
        d_layout.addLayout(bot_box)

        dlg.exec()
