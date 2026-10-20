# -*- coding: utf-8 -*-
"""
💾 SmartClearance MasterSuite - Evrim Canlı Veri Gezgini ve Detaylı Dosya Sorgulama (PyQt6)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Evrim gümrük kayıtları tablosu, filtreleme, detay künyesi, vergi maili, QNB/GLP/Talep/GTB entegrasyonları.
"""

import os
import csv
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QMessageBox, QFileDialog, QComboBox,
    QMenu, QApplication, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QCursor

from .base_view import BaseView
from ..components.metric_card import MetricCard

try:
    from tools.dogruer_master_suite.engine import (
        load_evrim_cached_data, save_evrim_cached_data
    )
except Exception:
    load_evrim_cached_data = lambda: []
    save_evrim_cached_data = lambda d: None


class EvrimTaxMailWorker(QThread):
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


class EvrimView(BaseView):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.current_filter = "ALL"
        self.filtered_records = []
        self.selected_record = None
        self.sort_column = -1
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.mail_worker = None

        self._build_ui()

    @property
    def evrim_records(self):
        records = getattr(self.main_window, "evrim_records", []) if self.main_window else []
        if not records and self.engine:
            records = getattr(self.engine, "evrim_records", []) or getattr(self.engine, "records", [])
        return records

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. Üst Metrik Kartları (5 Adet)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_total = MetricCard("TOPLAM EVRİM KAYDI", "0", "Hafızadaki Dosyalar", "#0f172a", self)
        self.card_total.clicked.connect(lambda: self.set_evrim_filter("ALL"))
        cards_layout.addWidget(self.card_total)

        self.card_beyan = MetricCard("BEYANNAMELİ / TESCİLLİ", "0", "Tescil No Alınmış", "#16a34a", self)
        self.card_beyan.clicked.connect(lambda: self.set_evrim_filter("TESCILLI"))
        cards_layout.addWidget(self.card_beyan)

        self.card_pending = MetricCard("İŞLEMDE / BEKLEYEN", "0", "Tescil Bekleyen", "#f59e0b", self)
        self.card_pending.clicked.connect(lambda: self.set_evrim_filter("PENDING"))
        cards_layout.addWidget(self.card_pending)

        self.card_closed = MetricCard("TESLİM EDİLENLER", "0", "Teslimatı Yapılan", "#2563eb", self)
        self.card_closed.clicked.connect(lambda: self.set_evrim_filter("CLOSED"))
        cards_layout.addWidget(self.card_closed)

        self.card_ports = MetricCard("LİMAN / ANTREPOLAR", "0", "Farklı Konum", "#7c3aed", self)
        self.card_ports.clicked.connect(lambda: self.cmb_port.setFocus())
        cards_layout.addWidget(self.card_ports)

        main_layout.addLayout(cards_layout)

        # 2. Arama ve Filtreleme Barı (2 Satırlı Modern Tasarım)
        filter_container = QFrame(self)
        filter_container.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        fc_layout = QVBoxLayout(filter_container)
        fc_layout.setContentsMargins(10, 6, 10, 6)
        fc_layout.setSpacing(6)

        # Satır 1: Arama, Hızlı Butonlar, Aksiyonlar
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_s = QLabel("Anlık Arama:", filter_container)
        lbl_s.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4af37;")
        row1.addWidget(lbl_s)

        self.txt_search = QLineEdit(filter_container)
        self.txt_search.setPlaceholderText("Dosya No (örn. 26-088175), Ref, Beyanname No, Liman veya Firma ara...")
        self.txt_search.textChanged.connect(self.apply_filters)
        row1.addWidget(self.txt_search, stretch=1)

        # Hızlı Aşama Butonları
        self.btn_f_all = QPushButton("Tümü", filter_container)
        self.btn_f_beyan = QPushButton("Tescilliler", filter_container)
        self.btn_f_pending = QPushButton("İşlemde", filter_container)
        self.btn_f_closed = QPushButton("Teslim Edilen", filter_container)

        self.filter_buttons = {
            "ALL": self.btn_f_all,
            "TESCILLI": self.btn_f_beyan,
            "PENDING": self.btn_f_pending,
            "CLOSED": self.btn_f_closed
        }

        for code, btn in self.filter_buttons.items():
            btn.setObjectName("StageTabBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=code: self.set_evrim_filter(c))
            row1.addWidget(btn)

        self.btn_sync_evrim = QPushButton("Doğruer'den Canlı Çek", filter_container)
        self.btn_sync_evrim.setObjectName("PrimaryBtn")
        self.btn_sync_evrim.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_evrim.clicked.connect(self.trigger_dogruer_sync)
        row1.addWidget(self.btn_sync_evrim)

        self.btn_export = QPushButton("Excel'e Aktar", filter_container)
        self.btn_export.setObjectName("ExcelBtn")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_to_excel)
        row1.addWidget(self.btn_export)

        fc_layout.addLayout(row1)

        # Satır 2: Detaylı Combobox Filtreleri (Liman, Antrepo, Statü)
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        lbl_port = QLabel("Liman / Konum:", filter_container)
        lbl_port.setStyleSheet("font-size: 10px; font-weight: 700; color: #8b9bb4;")
        row2.addWidget(lbl_port)

        self.cmb_port = QComboBox(filter_container)
        self.cmb_port.addItem("TÜMÜ")
        self.cmb_port.currentTextChanged.connect(self.apply_filters)
        row2.addWidget(self.cmb_port)

        lbl_antrepo = QLabel("Antrepo / Depo:", filter_container)
        lbl_antrepo.setStyleSheet("font-size: 10px; font-weight: 700; color: #8b9bb4;")
        row2.addWidget(lbl_antrepo)

        self.cmb_antrepo = QComboBox(filter_container)
        self.cmb_antrepo.addItem("TÜMÜ")
        self.cmb_antrepo.currentTextChanged.connect(self.apply_filters)
        row2.addWidget(self.cmb_antrepo)

        lbl_statu = QLabel("Statü:", filter_container)
        lbl_statu.setStyleSheet("font-size: 10px; font-weight: 700; color: #8b9bb4;")
        row2.addWidget(lbl_statu)

        self.cmb_statu = QComboBox(filter_container)
        self.cmb_statu.addItem("TÜMÜ")
        self.cmb_statu.currentTextChanged.connect(self.apply_filters)
        row2.addWidget(self.cmb_statu)

        btn_reset = QPushButton("🧹 Filtreleri Temizle", filter_container)
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_filters)
        row2.addWidget(btn_reset)

        row2.addStretch()

        self.lbl_count = QLabel("0 Kayıt Listeleniyor", filter_container)
        self.lbl_count.setStyleSheet("color: #1e40af; font-size: 11px; font-weight: 700;")
        row2.addWidget(self.lbl_count)

        fc_layout.addLayout(row2)
        main_layout.addWidget(filter_container)

        # 3. İki Bölümlü Ana Alan (Sol: Tablo, Sağ: Detay Künyesi Paneli)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(4)

        # Tablo
        self.table = QTableWidget(splitter)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Evrim Dosya No", "Hankook Ref (F.Ref)", "Beyanname No", "Tescil Tarihi",
            "Statü Açıklama", "Aşama / %", "Bulunduğu Yer / Liman", "Gümrük Müdürlüğü",
            "Teslim Tarihi", "Yurt Dışı Firma"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 145)
        self.table.setColumnWidth(3, 95)
        self.table.setColumnWidth(4, 200)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 140)
        self.table.setColumnWidth(7, 145)
        self.table.setColumnWidth(8, 95)
        self.table.setColumnWidth(9, 180)

        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.itemSelectionChanged.connect(self._on_table_select)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        splitter.addWidget(self.table)

        # Sağ Detay Künyesi
        self.detail_panel = self._build_detail_panel(splitter)
        splitter.addWidget(self.detail_panel)

        splitter.setSizes([880, 360])
        main_layout.addWidget(splitter, stretch=1)

        self._update_filter_button_styles()

    def _build_detail_panel(self, parent):
        container = QFrame(parent)
        container.setFixedWidth(360)
        container.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        lbl_t = QLabel("SEÇİLEN DOSYA KÜNYESİ", container)
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #d4af37; letter-spacing: 0.5px;")
        layout.addWidget(lbl_t)

        self.lbl_status_badge = QLabel("Lütfen tablodan bir dosya seçin", container)
        self.lbl_status_badge.setStyleSheet("""
            background-color: #111622; color: #8b9bb4;
            font-size: 11px; font-weight: 600;
            padding: 6px 10px; border-radius: 6px; border: 1px solid #1c2433;
        """)
        self.lbl_status_badge.setWordWrap(True)
        layout.addWidget(self.lbl_status_badge)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        scroll.viewport().setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0, 4, 0, 4)
        c_layout.setSpacing(4)

        self.detail_labels = {}
        fields = [
            ("ref", "Hankook Referansı:"),
            ("dosya", "Evrim Dosya No:"),
            ("beyan_no", "Beyanname No:"),
            ("beyan_tarih", "Tescil Tarihi:"),
            ("gumruk", "Gümrük Müdürlüğü:"),
            ("liman", "Bulunduğu Yer / Liman:"),
            ("rejim", "Rejim / Tip:"),
            ("statu", "Statü Durumu:"),
            ("asama", "Aşama & İlerleme:"),
            ("teslim", "Teslimat Tarihi:"),
            ("yurt_disi", "Yurt Dışı Firma:")
        ]

        for code, label in fields:
            row = QHBoxLayout()
            lbl_k = QLabel(label, content)
            lbl_k.setStyleSheet("color: #8b9bb4; font-size: 11px; font-weight: 600;")
            lbl_v = QLabel("—", content)
            lbl_v.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: 700;")
            lbl_v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl_v.setWordWrap(True)
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            c_layout.addLayout(row)
            self.detail_labels[code] = lbl_v

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # Hızlı Aksiyon Butonları (Swiss Executive Standartları)
        lbl_act = QLabel("HIZLI İŞLEM MENÜSÜ", container)
        lbl_act.setStyleSheet("font-size: 10px; font-weight: 800; color: #8b9bb4; letter-spacing: 0.8px; margin-top: 6px;")
        layout.addWidget(lbl_act)

        # 1. Ana Aksiyon (Hero Buton)
        self.btn_act_mail = QPushButton("Tek Tıkla Vergi Maili Hazırla", container)
        self.btn_act_mail.setStyleSheet("""
            QPushButton { 
                background-color: #d4af37; 
                color: #0a0e16; 
                font-weight: 700; 
                font-size: 11px; 
                padding: 8px 12px; 
                border-radius: 6px; 
                border: 1px solid #c29e2f; 
            }
            QPushButton:hover { 
                background-color: #e5c158; 
                color: #000000; 
                border-color: #d4af37; 
            }
            QPushButton:pressed { 
                background-color: #b89528; 
            }
        """)
        self.btn_act_mail.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_act_mail.clicked.connect(self._create_tax_mail_action)
        layout.addWidget(self.btn_act_mail)

        # İkincil Aksiyonlar İçin Ortak Kurumsal Stil
        sec_style = """
            QPushButton { 
                background-color: #141926; 
                color: #cbd5e1; 
                font-weight: 600; 
                font-size: 11px; 
                padding: 6px 10px; 
                border-radius: 6px; 
                border: 1px solid #232c3d; 
            }
            QPushButton:hover { 
                background-color: #1c2436; 
                border-color: #d4af37; 
                color: #ffffff; 
            }
            QPushButton:pressed { 
                background-color: #0e131d; 
            }
        """

        self.btn_act_copy = QPushButton("Dosya & Beyanname No Kopyala", container)
        self.btn_act_copy.setStyleSheet(sec_style)
        self.btn_act_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_act_copy.clicked.connect(self._copy_details_action)
        layout.addWidget(self.btn_act_copy)

        self.btn_act_gtb = QPushButton("GTB Takip Havuzuna Ekle", container)
        self.btn_act_gtb.setStyleSheet(sec_style)
        self.btn_act_gtb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_act_gtb.clicked.connect(self._send_to_gtb_action)
        layout.addWidget(self.btn_act_gtb)

        self.btn_act_qnb = QPushButton("QNB Fatura Eşleştirici'ye Aktar", container)
        self.btn_act_qnb.setStyleSheet(sec_style)
        self.btn_act_qnb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_act_qnb.clicked.connect(self._send_to_qnb_action)
        layout.addWidget(self.btn_act_qnb)

        self.btn_act_talep = QPushButton("Bu Dosya İçin Para Talebi Aç", container)
        self.btn_act_talep.setStyleSheet(sec_style)
        self.btn_act_talep.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_act_talep.clicked.connect(self._send_to_talep_action)
        layout.addWidget(self.btn_act_talep)

        return container

    def on_activate(self):
        self._populate_comboboxes()
        self.refresh_table()

    def refresh_table(self):
        self.update_metrics()
        self.apply_filters()

    def _populate_comboboxes(self):
        records = self.evrim_records
        ports = set()
        antrepos = set()
        status_set = set()

        for r in records:
            p = (r.get("liman") or r.get("yer") or "").strip()
            if p: ports.add(p)
            a = (r.get("antrepo") or "").strip()
            if a: antrepos.add(a)
            s = (r.get("statu") or r.get("statu_aciklama") or "").strip()
            if s: status_set.add(s)

        current_port = self.cmb_port.currentText()
        self.cmb_port.blockSignals(True)
        self.cmb_port.clear()
        self.cmb_port.addItem("TÜMÜ")
        for p in sorted(ports): self.cmb_port.addItem(p)
        idx = self.cmb_port.findText(current_port)
        self.cmb_port.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_port.blockSignals(False)

        current_ant = self.cmb_antrepo.currentText()
        self.cmb_antrepo.blockSignals(True)
        self.cmb_antrepo.clear()
        self.cmb_antrepo.addItem("TÜMÜ")
        for a in sorted(antrepos): self.cmb_antrepo.addItem(a)
        idx = self.cmb_antrepo.findText(current_ant)
        self.cmb_antrepo.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_antrepo.blockSignals(False)

        current_st = self.cmb_statu.currentText()
        self.cmb_statu.blockSignals(True)
        self.cmb_statu.clear()
        self.cmb_statu.addItem("TÜMÜ")
        for s in sorted(status_set): self.cmb_statu.addItem(s)
        idx = self.cmb_statu.findText(current_st)
        self.cmb_statu.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_statu.blockSignals(False)

    def update_metrics(self):
        records = self.evrim_records
        total = len(records)
        beyan_cnt = sum(1 for r in records if (r.get("beyanname_no") or r.get("beyan_no") or "").strip())
        closed_cnt = sum(1 for r in records if r.get("teslim_tarihi") or r.get("kapanis"))
        pending_cnt = sum(1 for r in records if not (r.get("beyanname_no") or r.get("beyan_no")) and not (r.get("teslim_tarihi") or r.get("kapanis")))
        ports_cnt = len(set((r.get("liman") or r.get("yer") or "").strip() for r in records if (r.get("liman") or r.get("yer"))))

        self.card_total.set_value(total)
        self.card_beyan.set_value(beyan_cnt)
        self.card_pending.set_value(pending_cnt)
        self.card_closed.set_value(closed_cnt)
        self.card_ports.set_value(ports_cnt)

    def set_evrim_filter(self, code):
        self.current_filter = code
        self._update_filter_button_styles()
        self.apply_filters()

    def _update_filter_button_styles(self):
        for code, btn in self.filter_buttons.items():
            is_active = (code == self.current_filter)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def reset_filters(self):
        self.txt_search.clear()
        self.cmb_port.setCurrentIndex(0)
        self.cmb_antrepo.setCurrentIndex(0)
        self.cmb_statu.setCurrentIndex(0)
        self.set_evrim_filter("ALL")

    def apply_filters(self):
        records = self.evrim_records
        f_code = self.current_filter

        if f_code == "TESCILLI":
            subset = [r for r in records if (r.get("beyanname_no") or r.get("beyan_no") or "").strip()]
        elif f_code == "PENDING":
            subset = [r for r in records if not (r.get("beyanname_no") or r.get("beyan_no")) and not (r.get("teslim_tarihi") or r.get("kapanis"))]
        elif f_code == "CLOSED":
            subset = [r for r in records if r.get("teslim_tarihi") or r.get("kapanis")]
        else:
            subset = records[:]

        q = self.txt_search.text().strip().upper()
        p_filter = self.cmb_port.currentText()
        a_filter = self.cmb_antrepo.currentText()
        s_filter = self.cmb_statu.currentText()

        final_list = []
        for r in subset:
            if p_filter != "TÜMÜ" and (r.get("liman") or r.get("yer") or "") != p_filter:
                continue
            if a_filter != "TÜMÜ" and (r.get("antrepo") or "") != a_filter:
                continue
            if s_filter != "TÜMÜ" and (r.get("statu") or r.get("statu_aciklama") or "") != s_filter:
                continue

            full_str = f"{r.get('dosya', '')} {r.get('dosya_no', '')} {r.get('ref', '')} {r.get('hankook_ref', '')} {r.get('beyanname_no', '')} {r.get('beyan_no', '')} {r.get('bl', '')} {r.get('liman', '')} {r.get('gumruk', '')} {r.get('yurt_disi_firma', '')}".upper()
            if not q or q in full_str:
                final_list.append(r)

        self.filtered_records = final_list
        self._render_table(final_list)
        self.lbl_count.setText(f"{len(final_list)} Kayıt Listeleniyor")

    def _render_table(self, records):
        self.table.setRowCount(len(records))
        for row_idx, r in enumerate(records):
            dosya = r.get("dosya_no") or r.get("dosya") or "—"
            ref = r.get("hankook_ref") or r.get("ref") or "—"
            beyan = r.get("beyanname_no") or r.get("beyan_no") or "—"
            b_tarih = r.get("beyanname_tarihi") or r.get("tescil") or "—"
            statu = r.get("statu") or r.get("statu_aciklama") or "—"
            asama = r.get("asama") or r.get("stage_title") or "—"
            liman = r.get("liman") or r.get("yer") or "—"
            gumruk = r.get("gumruk") or "—"
            teslim = r.get("teslim_tarihi") or r.get("kapanis") or "—"
            firma = r.get("yurt_disi_firma") or r.get("firma") or "—"

            vals = [dosya, ref, beyan, b_tarih, statu, asama, liman, gumruk, teslim, firma]
            items = [QTableWidgetItem(str(v)) for v in vals]

            is_closed = bool(r.get("teslim_tarihi") or r.get("kapanis"))
            is_tescilli = bool((r.get("beyanname_no") or r.get("beyan_no") or "").strip())

            for item in items:
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                if is_closed:
                    item.setForeground(QColor("#60a5fa"))
                elif is_tescilli:
                    item.setForeground(QColor("#34d399"))
                else:
                    item.setForeground(QColor("#d4af37"))

            for col_idx, item in enumerate(items):
                self.table.setItem(row_idx, col_idx, item)

    def _on_table_select(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row_idx = selected_rows[0].row()
        if 0 <= row_idx < len(self.filtered_records):
            rec = self.filtered_records[row_idx]
            self.selected_record = rec
            self._update_detail_panel(rec)

    def _update_detail_panel(self, rec):
        if not rec:
            self.lbl_status_badge.setText("Lütfen tablodan bir dosya seçin")
            self.lbl_status_badge.setStyleSheet("background-color: #111622; color: #8b9bb4; font-size: 11px; font-weight: 600; padding: 6px 10px; border-radius: 6px; border: 1px solid #1c2433;")
            for k, lbl in self.detail_labels.items():
                lbl.setText("—")
            return

        dosya = rec.get("dosya_no") or rec.get("dosya") or "—"
        ref = rec.get("hankook_ref") or rec.get("ref") or "—"
        beyan = rec.get("beyanname_no") or rec.get("beyan_no") or "—"
        statu = rec.get("statu") or rec.get("statu_aciklama") or "—"

        if rec.get("teslim_tarihi") or rec.get("kapanis"):
            self.lbl_status_badge.setText(f"● Teslim Edildi: {dosya}")
            self.lbl_status_badge.setStyleSheet("background-color: #121d2d; color: #60a5fa; font-weight: 700; padding: 6px 10px; border-radius: 6px; border: 1px solid #1e3a8a;")
        elif beyan != "—":
            self.lbl_status_badge.setText(f"● Beyanname Tescilli: {beyan}")
            self.lbl_status_badge.setStyleSheet("background-color: #0e241d; color: #34d399; font-weight: 700; padding: 6px 10px; border-radius: 6px; border: 1px solid #10b981;")
        else:
            self.lbl_status_badge.setText(f"● Tescil Bekliyor: {dosya}")
            self.lbl_status_badge.setStyleSheet("background-color: #241d10; color: #d4af37; font-weight: 700; padding: 6px 10px; border-radius: 6px; border: 1px solid #947622;")

        self.detail_labels["ref"].setText(ref)
        self.detail_labels["dosya"].setText(dosya)
        self.detail_labels["beyan_no"].setText(beyan)
        self.detail_labels["beyan_tarih"].setText(rec.get("beyanname_tarihi") or rec.get("tescil") or "—")
        self.detail_labels["gumruk"].setText(rec.get("gumruk") or "—")
        self.detail_labels["liman"].setText(rec.get("liman") or rec.get("yer") or "—")
        self.detail_labels["rejim"].setText(rec.get("rejim") or rec.get("tip") or "—")
        self.detail_labels["statu"].setText(statu)
        self.detail_labels["asama"].setText(rec.get("asama") or rec.get("stage_title") or "—")
        self.detail_labels["teslim"].setText(rec.get("teslim_tarihi") or rec.get("kapanis") or "—")
        self.detail_labels["yurt_disi"].setText(rec.get("yurt_disi_firma") or rec.get("firma") or "—")

    def _get_selected_records(self):
        selected_rows = self.table.selectionModel().selectedRows()
        records = []
        for index in selected_rows:
            r_idx = index.row()
            if 0 <= r_idx < len(self.filtered_records):
                records.append(self.filtered_records[r_idx])
        return records

    def _on_header_clicked(self, logical_index):
        if self.sort_column == logical_index:
            self.sort_order = (
                Qt.SortOrder.DescendingOrder
                if self.sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self.sort_column = logical_index
            self.sort_order = Qt.SortOrder.AscendingOrder

        self.table.sortItems(logical_index, self.sort_order)

    def _show_context_menu(self, pos):
        selected_records = self._get_selected_records()
        if not selected_records:
            return

        menu = QMenu(self)
        sel_count = len(selected_records)

        act_mail = menu.addAction(f"📧 Vergi Talebi Maili Aç ({sel_count} Dosya)" if sel_count > 1 else "📧 Vergi Talebi Maili Aç")
        act_rpa = menu.addAction("🤖 Otonom RPA İstasyonuna Gönder")
        act_qnb = menu.addAction("📦 QNB Fatura Eşleştiriciye Gönder")
        act_glp = menu.addAction("🚛 GLP Referans Sorgusuna Gönder")
        act_talep = menu.addAction("💸 Para Talebine Gönder")
        act_gtb = menu.addAction("🏛️ GTB Takip Havuzuna Ekle")

        act_mail.triggered.connect(self._create_tax_mail_action)
        act_rpa.triggered.connect(lambda: self.switch_tab("RPA_STATION"))
        act_qnb.triggered.connect(self._send_to_qnb_action)
        act_glp.triggered.connect(self._send_to_glp_action)
        act_talep.triggered.connect(self._send_to_talep_action)
        act_gtb.triggered.connect(self._send_to_gtb_action)

        menu.addSeparator()

        act_cp_dosya = menu.addAction(f"📋 Seçili ({sel_count}) Dosya No'ları Kopyala" if sel_count > 1 else "📋 Dosya Numarasını Kopyala")
        act_cp_ref = menu.addAction(f"📋 Seçili ({sel_count}) Referans No'ları Kopyala" if sel_count > 1 else "📋 Referans Numarasını Kopyala")
        act_cp_beyan = menu.addAction(f"📋 Seçili ({sel_count}) Beyanname No'ları Kopyala" if sel_count > 1 else "📋 Beyanname Numarasını Kopyala")

        act_cp_dosya.triggered.connect(lambda: self._copy_column("dosya_no"))
        act_cp_ref.triggered.connect(lambda: self._copy_column("hankook_ref"))
        act_cp_beyan.triggered.connect(lambda: self._copy_column("beyanname_no"))

        if sel_count > 1:
            act_cp_table = menu.addAction(f"📋 Seçili ({sel_count}) Satırı Tablo Olarak Kopyala")
            act_cp_table.triggered.connect(self._copy_selected_as_table)

        menu.addSeparator()
        act_excel = menu.addAction("📊 Excel'e Aktar (.csv)")
        act_excel.triggered.connect(self.export_to_excel)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    # -------------------------------------------------------------------------
    # Aksiyonlar: Vergi Maili, QNB, GLP, Talep, GTB, Senkronizasyon
    # -------------------------------------------------------------------------
    def _create_tax_mail_action(self):
        records = self._get_selected_records()
        if not records:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce tablodan en az bir dosya seçin.")
            return

        formatted_records = []
        for r in records:
            formatted_records.append({
                "dosya": r.get("dosya_no") or r.get("dosya") or "",
                "ref": r.get("hankook_ref") or r.get("ref") or "",
                "beyanname_no": r.get("beyanname_no") or r.get("beyan_no") or "",
                "bl": r.get("bl") or ""
            })

        count = len(formatted_records)
        self.set_header_subtitle(f"⏳ {count} Evrim kaydı için vergi maili taslağı hazırlanıyor...")

        self.mail_worker = EvrimTaxMailWorker(self.engine, formatted_records)
        self.mail_worker.finished.connect(self._on_mail_worker_done)
        self.mail_worker.start()

    def _on_mail_worker_done(self, success, msg, count):
        if success:
            self.set_header_subtitle(f"✅ {count} Evrim kaydı için Vergi Talebi taslağı Outlook'ta açıldı!")
            QMessageBox.information(self, "Başarılı", f"{count} dosya için Vergi Talebi taslağı açıldı.")
        else:
            self.set_header_subtitle("⚠️ Vergi mail taslağı oluşturulamadı.")
            QMessageBox.critical(self, "Hata", f"Vergi maili hatası: {msg}")

    def _copy_details_action(self):
        if not self.selected_record:
            return
        d = self.selected_record.get("dosya_no") or self.selected_record.get("dosya") or ""
        b = self.selected_record.get("beyanname_no") or self.selected_record.get("beyan_no") or ""
        text = f"{d} - {b}" if b else d
        self.copy_to_clipboard(text, show_msg=True)

    def _copy_column(self, col_key):
        records = self._get_selected_records()
        vals = [str(r.get(col_key) or r.get(col_key.replace('_no','')) or "").strip() for r in records if str(r.get(col_key) or "").strip()]
        if vals:
            self.copy_to_clipboard("\n".join(vals))
            self.set_header_subtitle(f"📋 {len(vals)} adet kayıt kopyalandı.")

    def _copy_selected_as_table(self):
        records = self._get_selected_records()
        lines = ["Dosya No\tRef\tBeyanname No\tTarih\tStatü\tAşama\tLiman\tGümrük\tTeslim\tFirma"]
        for r in records:
            lines.append(f"{r.get('dosya_no','')}\t{r.get('hankook_ref','')}\t{r.get('beyanname_no','')}\t{r.get('beyanname_tarihi','')}\t{r.get('statu','')}\t{r.get('asama','')}\t{r.get('liman','')}\t{r.get('gumruk','')}\t{r.get('teslim_tarihi','')}\t{r.get('yurt_disi_firma','')}")
        self.copy_to_clipboard("\n".join(lines))
        self.set_header_subtitle(f"📋 {len(records)} kayıt tablo formatında kopyalandı.")

    def _send_to_gtb_action(self):
        records = self._get_selected_records()
        if not records:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kayıt seçin.")
            return
        b_no = (records[0].get("beyanname_no") or records[0].get("beyan_no") or "").strip()
        if not b_no:
            QMessageBox.warning(self, "Uyarı", "Bu kayıtta tescilli beyanname numarası bulunmuyor.")
            return
        if hasattr(self.main_window, "query_selected_gtb_row"):
            self.main_window.query_selected_gtb_row(b_no)

    def _send_to_qnb_action(self):
        records = self._get_selected_records()
        if not records:
            return
        dosya = records[0].get("dosya_no") or records[0].get("dosya") or ""
        self.copy_to_clipboard(dosya)
        self.switch_tab("QNB_PORTAL")

    def _send_to_glp_action(self):
        records = self._get_selected_records()
        if not records:
            return
        ref = records[0].get("hankook_ref") or records[0].get("ref") or ""
        self.copy_to_clipboard(ref)
        self.switch_tab("GLP_PORTAL")

    def _send_to_talep_action(self):
        records = self._get_selected_records()
        if not records:
            return
        r = records[0]
        payload = {
            "dosyaNo": r.get("dosya_no") or r.get("dosya") or "",
            "ref": r.get("hankook_ref") or r.get("ref") or "",
            "liman": r.get("liman") or r.get("yer") or "",
            "aciklama": "ARDİYE / LİMAN MASRAFI"
        }
        if hasattr(self.main_window, "send_to_talep_form"):
            self.main_window.send_to_talep_form(payload)

    def trigger_dogruer_sync(self):
        self.set_header_subtitle("🔄 Doğruer Online & Evrim veritabanı taranıyor...")
        self.btn_sync_evrim.setEnabled(False)

        def _work():
            try:
                if self.engine and hasattr(self.engine, "sync_evrim_data"):
                    self.engine.sync_evrim_data()
                success = True
                msg = "Evrim verileri güncellendi."
            except Exception as e:
                success = False
                msg = str(e)

            def _done():
                self.btn_sync_evrim.setEnabled(True)
                self.refresh_table()
                if success:
                    self.set_header_subtitle("✅ Evrim verileri başarıyla çekildi.")
                    QMessageBox.information(self, "Başarılı", "Evrim verileri güncellendi.")
                else:
                    self.set_header_subtitle("⚠️ Evrim çekme hatası.")
                    QMessageBox.critical(self, "Hata", msg)

            QTimer.singleShot(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def search_with_query(self, query):
        self.txt_search.setText(query)

    def export_to_excel(self):
        if not self.filtered_records:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak kayıt bulunamadı.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Evrim Kayıtlarını Kaydet", "Evrim_Raporu.csv", "CSV Dosyası (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "Evrim Dosya No", "Hankook Ref", "Beyanname No", "Tescil Tarihi",
                    "Statü", "Aşama", "Liman", "Gümrük", "Teslim Tarihi", "Yurt Dışı Firma"
                ])
                for r in self.filtered_records:
                    writer.writerow([
                        r.get("dosya_no") or r.get("dosya", ""),
                        r.get("hankook_ref") or r.get("ref", ""),
                        r.get("beyanname_no") or r.get("beyan_no", ""),
                        r.get("beyanname_tarihi") or r.get("tescil", ""),
                        r.get("statu") or r.get("statu_aciklama", ""),
                        r.get("asama") or r.get("stage_title", ""),
                        r.get("liman") or r.get("yer", ""),
                        r.get("gumruk", ""),
                        r.get("teslim_tarihi") or r.get("kapanis", ""),
                        r.get("yurt_disi_firma", "")
                    ])
            QMessageBox.information(self, "Başarılı", f"Kayıtlar başarıyla aktarıldı:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")
