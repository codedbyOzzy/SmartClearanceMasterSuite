# -*- coding: utf-8 -*-
"""
📊 SmartClearance MasterSuite - Modern Operasyon Kokpiti (PyQt6)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Excel Canlı Senkronizasyon, 5 Aşamalı Operasyonel Süreç Takibi, Outlook Vergi Maili
Entegrasyonu, Canlı Mail Zaman Tüneli (Timeline) ve GTB Bakanlık Durum Paneli.
"""

import os
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFileDialog, QMessageBox, QFrame, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QAction, QCursor

from .base_view import BaseView
from .detail_drawer import CockpitDetailDrawer
from ..components.metric_card import MetricCard

try:
    from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
except Exception:
    send_desktop_notification = lambda t, m, f=False: None


class TaxMailWorker(QThread):
    """Outlook vergi talebi taslağını UI'yi dondurmadan oluşturan iş parçacığı."""
    finished = pyqtSignal(bool, str, int)

    def __init__(self, engine, records):
        super().__init__()
        self.engine = engine
        self.records = records

    def run(self):
        try:
            if not self.engine or not hasattr(self.engine, "create_tax_mail_draft"):
                self.finished.emit(False, "Veri motorunda vergi maili oluşturucu bulunamadı.", len(self.records))
                return

            ok, msg = self.engine.create_tax_mail_draft(self.records)
            self.finished.emit(ok, msg, len(self.records))
        except Exception as e:
            self.finished.emit(False, str(e), len(self.records))


class GTBSingleQueryWorker(QThread):
    """Bakanlık canlı sorgusunu asenkron yürüten iş parçacığı."""
    finished = pyqtSignal(dict)

    def __init__(self, tracker, beyanname_no):
        super().__init__()
        self.tracker = tracker
        self.beyanname_no = beyanname_no

    def run(self):
        try:
            if self.tracker and hasattr(self.tracker, "query_single_now"):
                res = self.tracker.query_single_now(self.beyanname_no)
                self.finished.emit(res or {})
            else:
                self.finished.emit({"success": False, "error": "GTB izleyici servisi aktif değil."})
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})


class CockpitView(BaseView):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.current_stage_filter = "ALL_ACTIVE"
        self.filtered_records = []
        self.selected_record = None
        self.mail_worker = None
        self.gtb_worker = None

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. ÜST METRİK KARTLARI (5 Adet)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_active = MetricCard("AÇIK DOSYALAR", "0", "Toplam Aktif", "#1e3a8a", self)
        self.card_active.clicked.connect(lambda: self.set_stage_filter("ALL_ACTIVE"))
        cards_layout.addWidget(self.card_active)

        self.card_mail_wait = MetricCard("VERGİ MAİLİ BEKLEYEN", "0", "Acil Gönderim", "#dc2626", self)
        self.card_mail_wait.clicked.connect(lambda: self.set_stage_filter("MAIL_WAITING"))
        cards_layout.addWidget(self.card_mail_wait)

        self.card_tescil = MetricCard("TESCİL / MUAYENE", "0", "Sarı / Kırmızı Hat", "#2563eb", self)
        self.card_tescil.clicked.connect(lambda: self.set_stage_filter("3_TESCILDE"))
        cards_layout.addWidget(self.card_tescil)

        self.card_ordino = MetricCard("ORDİNO / TAREKS", "0", "İşlem Aşamasında", "#7c3aed", self)
        self.card_ordino.clicked.connect(lambda: self.set_stage_filter("2_ORDINO_TAREKS"))
        cards_layout.addWidget(self.card_ordino)

        self.card_closed = MetricCard("KAPANDI / ARŞİV", "0", "Tamamlananlar", "#16a34a", self)
        self.card_closed.clicked.connect(lambda: self.set_stage_filter("5_KAPANDI"))
        cards_layout.addWidget(self.card_closed)

        main_layout.addLayout(cards_layout)

        # 2. ARAMA VE HIZLI FİLTRELEME BARI
        filter_box = QFrame(self)
        filter_box.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 4px;")
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setContentsMargins(10, 4, 10, 4)
        filter_layout.setSpacing(10)

        lbl_s = QLabel("🔍 Hızlı Filtrele / Ara:", filter_box)
        lbl_s.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")
        filter_layout.addWidget(lbl_s)

        self.txt_search = QLineEdit(filter_box)
        self.txt_search.setPlaceholderText("Dosya No, Ref, BL, Liman, Bayi veya Gemi ara...")
        self.txt_search.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.txt_search, stretch=1)

        # Hızlı Aşama Sekme Butonları
        self.stage_buttons = {}
        stage_defs = [
            ("ALL_ACTIVE", "⚡ Aktif", "#1e3a8a"),
            ("MAIL_WAITING", "✉️ Vergi Bekleyen", "#dc2626"),
            ("3_TESCILDE", "🟢 Tescilde", "#2563eb"),
            ("2_ORDINO_TAREKS", "📦 Ordino/Tareks", "#7c3aed"),
            ("5_KAPANDI", "📁 Kapandı", "#64748b"),
            ("ALL", "Tümü", "#0f172a"),
        ]

        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(4)
        for code, label, color in stage_defs:
            btn = QPushButton(label, filter_box)
            btn.setObjectName("StageTabBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=code: self.set_stage_filter(c))
            tabs_layout.addWidget(btn)
            self.stage_buttons[code] = btn

        filter_layout.addLayout(tabs_layout)

        # Excel Aktarım Butonu & Sayaç
        self.lbl_count = QLabel("0 Kayıt Listeleniyor", filter_box)
        self.lbl_count.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        filter_layout.addWidget(self.lbl_count)

        self.btn_export = QPushButton("📥 Excel'e Aktar", filter_box)
        self.btn_export.setObjectName("ExcelBtn")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_to_excel)
        filter_layout.addWidget(self.btn_export)

        main_layout.addWidget(filter_box)

        # 3. MERKEZİ ALAN: TABLO VE SAĞ ÇEKMECE (SPLITTER)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(4)

        # Tablo
        self.table = QTableWidget(splitter)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Dosya No", "Referans No", "Konşimento (B/L)",
            "Operasyonel Aşama", "Hat", "Vergi Maili Durumu",
            "Bayi / Alıcı", "Liman"
        ])
        # Çoklu seçim desteği (Ctrl veya Shift ile satır seçimi)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 110)  # Dosya No
        self.table.setColumnWidth(1, 120)  # Referans No
        self.table.setColumnWidth(2, 140)  # Konşimento
        self.table.setColumnWidth(3, 160)  # Aşama
        self.table.setColumnWidth(4, 80)   # Hat
        self.table.setColumnWidth(5, 170)  # Mail Durumu
        self.table.setColumnWidth(6, 130)  # Bayi
        self.table.itemSelectionChanged.connect(self._on_table_select)

        # Sağ Tık Bağlam Menüsü (Custom Context Menu)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        splitter.addWidget(self.table)

        # Sağ Detay Çekmecesi
        self.detail_drawer = CockpitDetailDrawer(splitter, engine=self.engine)
        self.detail_drawer.open_draft_requested.connect(self.open_mail_draft_action)
        self.detail_drawer.gtb_query_requested.connect(self.query_selected_gtb_action)
        self.detail_drawer.open_horizon_requested.connect(self.open_in_horizon_action)
        splitter.addWidget(self.detail_drawer)

        # Splitter dinamik oranları (%72 Tablo / %28 Detay Çekmecesi)
        self.splitter = splitter
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([850, 320])
        main_layout.addWidget(splitter, stretch=1)

        self._update_stage_button_styles()

    def _on_screen_changed(self, new_screen=None):
        """Laptop ve büyük ekran geçişinde tablo ve detay çekmecesi genişliklerini orantılar."""
        if hasattr(self, "splitter") and self.splitter:
            tot = self.splitter.width() or self.width()
            if tot > 300:
                drawer_w = max(260, min(360, int(tot * 0.28)))
                table_w = tot - drawer_w
                self.splitter.setSizes([table_w, drawer_w])
        self.updateGeometry()
        self.update()

    def on_activate(self):
        if hasattr(self.detail_drawer, "set_engine"):
            self.detail_drawer.set_engine(self.engine)
        self.refresh_table()

    def refresh_table(self):
        self.update_metrics()
        self.apply_filter()

    def update_metrics(self):
        records = getattr(self.engine, "records", []) if self.engine else []
        total_open = sum(1 for r in records if not r.get("kapanis"))
        mail_waiting = sum(1 for r in records if not r.get("kapanis") and r.get("is_tax_pending") and r.get("mail_badge") == "red")
        tescil_count = sum(1 for r in records if not r.get("kapanis") and (r.get("stage") in ["3_TESCILDE", "3_MUAYENE"]))
        ordino_count = sum(1 for r in records if not r.get("kapanis") and r.get("stage") == "2_ORDINO_TAREKS")
        closed_count = sum(1 for r in records if r.get("kapanis"))

        self.card_active.set_value(total_open)
        self.card_mail_wait.set_value(mail_waiting)
        self.card_tescil.set_value(tescil_count)
        self.card_ordino.set_value(ordino_count)
        self.card_closed.set_value(closed_count)

    def set_stage_filter(self, stage_code):
        self.current_stage_filter = stage_code
        self._update_stage_button_styles()
        self.apply_filter()

    def _update_stage_button_styles(self):
        for code, btn in self.stage_buttons.items():
            is_active = (code == self.current_stage_filter)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def apply_filter(self):
        st = self.current_stage_filter
        records = getattr(self.engine, "records", []) if self.engine else []

        if st == "ALL_ACTIVE":
            subset = [r for r in records if not r.get("kapanis")]
        elif st == "MAIL_WAITING":
            subset = [r for r in records if not r.get("kapanis") and r.get("is_tax_pending") and r.get("mail_badge") == "red"]
        elif st == "3_TESCILDE":
            subset = [r for r in records if not r.get("kapanis") and r.get("stage") in ["3_TESCILDE", "3_MUAYENE"]]
        elif st == "2_ORDINO_TAREKS":
            subset = [r for r in records if not r.get("kapanis") and r.get("stage") == "2_ORDINO_TAREKS"]
        elif st == "5_KAPANDI":
            subset = [r for r in records if r.get("kapanis")]
        else:
            subset = records[:]

        query = self.txt_search.text().strip().upper()
        final_list = []
        for r in subset:
            full_str = f"{r.get('dosya', '')} {r.get('ref', '')} {r.get('bl', '')} {r.get('bayi', '')} {r.get('acenta', '')} {r.get('liman', '')} {r.get('gumruk', '')} {r.get('hat', '')} {r.get('stage_title', '')} {r.get('aciklama', '')} {r.get('konteyner', '')} {r.get('gemi', '')} {r.get('beyanname_no', '')} {r.get('beyan_no', '')}".upper()
            if not query or query in full_str:
                final_list.append(r)

        self.filtered_records = final_list
        self._render_table(final_list)
        self.lbl_count.setText(f"{len(final_list)} Kayıt Listeleniyor")

    def _render_table(self, records):
        self.table.setRowCount(len(records))
        for row_idx, r in enumerate(records):
            dosya_item = QTableWidgetItem(r.get("dosya") or "—")
            ref_item = QTableWidgetItem(r.get("ref") or "—")
            bl_item = QTableWidgetItem(r.get("bl") or "—")
            stage_item = QTableWidgetItem(r.get("stage_title") or "—")
            hat_item = QTableWidgetItem(r.get("hat") or "—")
            mail_item = QTableWidgetItem(r.get("mail_status") or "—")
            bayi_item = QTableWidgetItem(r.get("bayi") or "—")
            liman_item = QTableWidgetItem(r.get("liman") or "—")

            if r.get("kapanis"):
                for it in [dosya_item, ref_item, bl_item, stage_item, hat_item, mail_item, bayi_item, liman_item]:
                    it.setForeground(QColor("#94a3b8"))
            elif r.get("hat") == "KIRMIZI":
                hat_item.setForeground(QColor("#dc2626"))
                hat_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            elif r.get("hat") == "SARI":
                hat_item.setForeground(QColor("#d97706"))
                hat_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            if r.get("mail_badge") == "red":
                mail_item.setForeground(QColor("#dc2626"))
            elif r.get("mail_badge") == "green":
                mail_item.setForeground(QColor("#16a34a"))

            if r.get("stage") in ["3_TESCILDE", "3_MUAYENE"]:
                stage_item.setForeground(QColor("#16a34a"))
                stage_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            items = [dosya_item, ref_item, bl_item, stage_item, hat_item, mail_item, bayi_item, liman_item]
            for col_idx, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row_idx, col_idx, item)

    def _on_table_select(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row_idx = selected_rows[0].row()
        if 0 <= row_idx < len(self.filtered_records):
            rec = self.filtered_records[row_idx]
            self.selected_record = rec
            self.detail_drawer.set_record(rec)

    def _get_selected_records(self):
        """Tabloda seçili olan tüm kayıtları döner."""
        selected_rows = self.table.selectionModel().selectedRows()
        records = []
        for index in selected_rows:
            r_idx = index.row()
            if 0 <= r_idx < len(self.filtered_records):
                records.append(self.filtered_records[r_idx])
        return records

    # -------------------------------------------------------------------------
    # Sağ Tık Bağlam Menüsü (Context Menu)
    # -------------------------------------------------------------------------
    def _show_context_menu(self, pos):
        selected_records = self._get_selected_records()
        if not selected_records:
            return

        menu = QMenu(self)
        sel_count = len(selected_records)

        # 1. Operasyonel Aksiyonlar
        if sel_count == 1:
            rec = selected_records[0]
            act_mail = menu.addAction("📧 Vergi Talebi Maili Oluştur")
            act_gtb = menu.addAction("🔍 GTB Canlı Sorgula")
            act_rpa = menu.addAction("🤖 Otonom RPA İstasyonuna Gönder")
            act_evrim = menu.addAction("📑 Evrim Detayına Git")
            act_timeline = menu.addAction("📜 Mail Zaman Tüneline Git")
            act_shield = menu.addAction("🛡️ Mail Güvenlik Kalkanında Sorgula")
            act_talep = menu.addAction("💸 Bu Dosya İçin Para Talebi Aç")
            act_horizon = menu.addAction("🌐 Horizon Radarda Canlı Haritada Gör (AIS)")
            act_apex = menu.addAction("🚀 Apex Hankook Masasında Aç (Evrak & Stepper)")

            act_mail.triggered.connect(lambda: self.open_mail_draft_action(rec))
            act_gtb.triggered.connect(lambda: self.query_selected_gtb_action(rec))
            act_rpa.triggered.connect(lambda: self.send_to_rpa_action(rec))
            act_evrim.triggered.connect(lambda: self.navigate_to_evrim_action(rec))
            act_timeline.triggered.connect(lambda: self.detail_drawer.tabs.setCurrentIndex(1))
            act_shield.triggered.connect(lambda: self.cross_inspect_shield_action(rec))
            act_talep.triggered.connect(lambda: self.send_to_talep_action(rec))
            act_horizon.triggered.connect(lambda: self.open_in_horizon_action(rec))
            act_apex.triggered.connect(lambda: self.open_in_apex_action(rec))
        else:
            act_mail = menu.addAction(f"📧 Seçili ({sel_count}) Dosya İçin Vergi Talebi Maili Oluştur")
            act_rpa = menu.addAction(f"🤖 Seçili ({sel_count}) Dosyayı Otonom RPA İstasyonuna Gönder")
            act_gtb = menu.addAction(f"🔍 Seçili ({sel_count}) Dosyayı GTB'de Canlı Sorgula")
            act_horizon = menu.addAction(f"🌐 İlk Dosyayı Horizon Radarda Canlı Gör (AIS)")

            act_mail.triggered.connect(lambda: self.open_mail_draft_action())
            act_rpa.triggered.connect(lambda: self.send_to_rpa_action())
            act_gtb.triggered.connect(lambda: self.query_selected_gtb_action())
            act_horizon.triggered.connect(lambda: self.open_in_horizon_action())

        menu.addSeparator()

        # 2. Seçili Sütun Kopyalama
        lbl_dosya = f"📋 Seçili ({sel_count}) Dosya No'ları Kopyala" if sel_count > 1 else "📋 Dosya Numarasını Kopyala"
        lbl_ref = f"📋 Seçili ({sel_count}) Referans No'ları Kopyala" if sel_count > 1 else "📋 Referans Numarasını Kopyala"
        lbl_bl = f"📋 Seçili ({sel_count}) Konşimento (B/L) Kopyala" if sel_count > 1 else "📋 Konşimento (B/L) Kopyala"

        act_cp_dosya = menu.addAction(lbl_dosya)
        act_cp_ref = menu.addAction(lbl_ref)
        act_cp_bl = menu.addAction(lbl_bl)

        act_cp_dosya.triggered.connect(lambda: self.copy_column_values("dosya", only_selected=True))
        act_cp_ref.triggered.connect(lambda: self.copy_column_values("ref", only_selected=True))
        act_cp_bl.triggered.connect(lambda: self.copy_column_values("bl", only_selected=True))

        if sel_count > 1:
            act_cp_table = menu.addAction(f"📋 Seçili ({sel_count}) Satırı Tablo Olarak Kopyala")
            act_cp_table.triggered.connect(self.copy_selected_rows_as_table)

        menu.addSeparator()

        # 3. Tablodaki TÜM Sütunları Kopyalama Alt Menüsü
        all_count = len(self.filtered_records)
        all_menu = menu.addMenu(f"📑 Tablodaki TÜM Kayıtları Kopyala ({all_count} Satır)...")
        act_all_dosya = all_menu.addAction(f"Dosya No ({all_count} Satır)")
        act_all_ref = all_menu.addAction(f"Referans No ({all_count} Satır)")
        act_all_bl = all_menu.addAction(f"Konşimento (B/L) ({all_count} Satır)")

        act_all_dosya.triggered.connect(lambda: self.copy_column_values("dosya", only_selected=False))
        act_all_ref.triggered.connect(lambda: self.copy_column_values("ref", only_selected=False))
        act_all_bl.triggered.connect(lambda: self.copy_column_values("bl", only_selected=False))

        menu.addSeparator()
        act_export = menu.addAction("📊 Excel'e Aktar (.csv)")
        act_export.triggered.connect(self.export_to_excel)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    # -------------------------------------------------------------------------
    # Aksiyon Metodları: Vergi Maili, GTB, RPA, Evrim, Shield, Talep
    # -------------------------------------------------------------------------
    def open_mail_draft_action(self, rec=None):
        """Seçili dosyalar için Outlook'ta Vergi Talebi taslağını asenkron oluşturur."""
        records = [rec] if rec else self._get_selected_records()
        if not records:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce tablodan en az bir dosya seçin.")
            return

        count = len(records)
        self.set_header_subtitle(f"⏳ {count} dosya için vergi maili taslağı Outlook'ta hazırlanıyor, lütfen bekleyin...")

        self.mail_worker = TaxMailWorker(self.engine, records)
        self.mail_worker.finished.connect(self._on_mail_draft_finished)
        self.mail_worker.start()

    def _on_mail_draft_finished(self, success, msg, count):
        if success:
            self.set_header_subtitle(f"✅ {count} dosya için Vergi Talebi taslağı Outlook'ta açıldı!")
            send_desktop_notification("📧 Outlook Vergi Maili", f"{count} adet dosya için vergi taslağı hazırlandı.")
        else:
            self.set_header_subtitle("⚠️ Vergi maili taslağı oluşturulamadı.")
            QMessageBox.critical(self, "Hata", f"Outlook vergi maili hatası:\n{msg}")

    def query_selected_gtb_action(self, rec=None):
        """Seçili dosya için Ticaret Bakanlığı canlı sorgusu yapar."""
        records = [rec] if rec else self._get_selected_records()
        if not records:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce tablodan bir dosya seçin.")
            return

        rec_target = records[0]
        b_no = (rec_target.get("beyanname_no") or rec_target.get("beyan_no") or "").strip()
        if not b_no:
            QMessageBox.warning(self, "Uyarı", "Bu dosyaya ait tescilli beyanname numarası bulunamadı.")
            return

        tracker = getattr(self.main_window, "gtb_tracker", None)
        self.set_header_subtitle(f"🏛️ Beyanname ({b_no}) GTB Bakanlık'tan sorgulanıyor...")

        self.gtb_worker = GTBSingleQueryWorker(tracker, b_no)
        self.gtb_worker.finished.connect(lambda res: self._on_gtb_query_finished(res, b_no))
        self.gtb_worker.start()

    def _on_gtb_query_finished(self, res, b_no):
        if res.get("success"):
            durum = res.get("durum") or res.get("hat") or "Tamamlandı"
            self.set_header_subtitle(f"✅ GTB Sonucu ({b_no}): {durum}")
            QMessageBox.information(
                self, "GTB Canlı Sonuç",
                f"📑 Beyanname: {b_no}\n\n🏛️ Bakanlık Durumu:\n{durum}"
            )
            # Tablo ve çekmeceyi güncelle
            self.refresh_table()
        else:
            err = res.get("error") or "Bilinmeyen hata"
            self.set_header_subtitle(f"⚠️ GTB Sorgu Hatası ({b_no})")
            QMessageBox.critical(self, "GTB Hatası", f"Sorgulama başarısız:\n{err}")

    def send_to_rpa_action(self, rec=None):
        self.switch_tab("RPA_STATION")

    def navigate_to_evrim_action(self, rec=None):
        rec = rec or (self._get_selected_records()[0] if self._get_selected_records() else None)
        if not rec:
            return
        query = (rec.get("ref") or rec.get("dosya") or rec.get("bl") or "").strip()
        if hasattr(self.main_window, "navigate_to_evrim_detail"):
            self.main_window.navigate_to_evrim_detail(query)

    def cross_inspect_shield_action(self, rec=None):
        rec = rec or (self._get_selected_records()[0] if self._get_selected_records() else None)
        if not rec:
            return
        query = (rec.get("ref") or rec.get("dosya") or rec.get("bl") or "").strip()
        if hasattr(self.main_window, "do_shield_quick_search"):
            self.main_window.do_shield_quick_search(query)

    def send_to_talep_action(self, rec=None):
        rec = rec or (self._get_selected_records()[0] if self._get_selected_records() else None)
        if not rec:
            return
        payload = {
            "dosyaNo": rec.get("dosya", ""),
            "ref": rec.get("ref", ""),
            "liman": rec.get("liman", ""),
            "aciklama": "ARDİYE FATURASI"
        }
        if hasattr(self.main_window, "send_to_talep_form"):
            self.main_window.send_to_talep_form(payload)

    def open_in_horizon_action(self, rec=None):
        rec = rec or (self._get_selected_records()[0] if self._get_selected_records() else None)
        if not rec:
            return
        # Arama önceliği: Gemi Adı -> Konşimento (BL) -> Dosya No
        query = (rec.get("gemi") or rec.get("bl") or rec.get("dosya") or "").strip()
        if hasattr(self.main_window, "open_in_horizon"):
            self.main_window.open_in_horizon(query)
        elif self.main_window:
            self.main_window.switch_tab("HORIZON")

    def open_in_apex_action(self, rec=None):
        rec = rec or (self._get_selected_records()[0] if self._get_selected_records() else None)
        if self.main_window:
            self.main_window.switch_tab("APEX")
            apex_v = self.main_window.views.get("APEX")
            if apex_v and hasattr(apex_v, "apex_widget") and apex_v.apex_widget:
                query = (rec.get("dosya") or rec.get("ref") or "").strip() if rec else ""
                if query and hasattr(apex_v.apex_widget, "txt_search"):
                    apex_v.apex_widget.txt_search.setText(query)

    # -------------------------------------------------------------------------
    # Kopyalama Yardımcıları
    # -------------------------------------------------------------------------
    def copy_column_values(self, col_key, only_selected=True):
        records = self._get_selected_records() if only_selected else self.filtered_records
        if not records:
            return
        vals = [str(r.get(col_key) or "").strip() for r in records if (r.get(col_key) or "").strip()]
        text = "\n".join(vals)
        self.copy_to_clipboard(text)
        self.set_header_subtitle(f"📋 {len(vals)} adet kayıt panoya kopyalandı.")

    def copy_selected_rows_as_table(self):
        records = self._get_selected_records()
        if not records:
            return
        lines = ["Dosya No\tReferans No\tKonşimento\tAşama\tHat\tVergi Maili\tBayi\tLiman"]
        for r in records:
            lines.append(f"{r.get('dosya','')}\t{r.get('ref','')}\t{r.get('bl','')}\t{r.get('stage_title','')}\t{r.get('hat','')}\t{r.get('mail_status','')}\t{r.get('bayi','')}\t{r.get('liman','')}")
        self.copy_to_clipboard("\n".join(lines))
        self.set_header_subtitle(f"📋 {len(records)} satır Excel formatında panoya kopyalandı.")

    def export_to_excel(self):
        if not self.filtered_records:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak kayıt bulunamadı.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Excel Olarak Kaydet", "Operasyon_Kokpiti.csv", "CSV Dosyası (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Dosya No", "Referans No", "Konşimento", "Aşama", "Hat", "Vergi Maili", "Bayi / Alıcı", "Liman"])
                for r in self.filtered_records:
                    writer.writerow([
                        r.get("dosya", ""), r.get("ref", ""), r.get("bl", ""),
                        r.get("stage_title", ""), r.get("hat", ""), r.get("mail_status", ""),
                        r.get("bayi", ""), r.get("liman", "")
                    ])
            QMessageBox.information(self, "Başarılı", f"Kayıtlar başarıyla aktarıldı:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")
