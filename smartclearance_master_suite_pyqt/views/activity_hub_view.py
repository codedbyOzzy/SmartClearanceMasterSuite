# -*- coding: utf-8 -*-
"""
📋 SmartClearance MasterSuite - Dosya Notları & Operasyonel İşlem Günlüğü (ActivityHubView PyQt6)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Dosyalara ait operasyonel notlar, GTB tescil hareketleri, vergi mail kayıtları,
zaman tüneli, Supabase bulut senkronizasyonu ve çöp kutusu/geri alma mekanizması.
"""

import os
import csv
import json
import threading
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QHeaderView, QFrame, QMessageBox, QFileDialog, QComboBox,
    QDialog, QMenu, QApplication, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QCursor

from .base_view import BaseView
from ..components.metric_card import MetricCard

try:
    from tools.supabase_sync_manager import get_supabase_manager
except Exception:
    get_supabase_manager = None


class PyQtAddNoteDialog(QDialog):
    """Modern Not Ekleme & Düzenleme Modalı."""
    def __init__(self, parent=None, current_user=None, default_dosya="", default_ref="", default_beyan="", existing_log=None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self.existing_log = existing_log
        self.is_edit = existing_log is not None

        title = "✏️ Operasyon Notunu Düzenle" if self.is_edit else "➕ Yeni Operasyon Notu Ekle"
        self.setWindowTitle(title)
        self.setFixedSize(540, 560)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #ffffff; font-size: 11px; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #1e293b; color: #ffffff;
                border: 1px solid #334155; border-radius: 6px;
                padding: 6px 10px; font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1.5px solid #38bdf8;
            }
            QPushButton#SaveBtn {
                background-color: #16a34a; color: #ffffff;
                font-weight: 700; border-radius: 6px; padding: 9px 18px; border: none; font-size: 12px;
            }
            QPushButton#SaveBtn:hover { background-color: #15803d; }
            QPushButton#CancelBtn {
                background-color: #334155; color: #e2e8f0;
                font-weight: 600; border-radius: 6px; padding: 9px 16px; border: none; font-size: 12px;
            }
            QPushButton#CancelBtn:hover { background-color: #475569; }
            QPushButton#TmplBtn {
                background-color: #1e293b; color: #94a3b8;
                border: 1px solid #334155; border-radius: 4px; padding: 4px 8px; font-size: 10px;
            }
            QPushButton#TmplBtn:hover { background-color: #334155; color: #ffffff; }
        """)

        self._build_ui(default_dosya, default_ref, default_beyan)

    def _build_ui(self, default_dosya, default_ref, default_beyan):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        t_lbl = QLabel(f"📝 {'Not Düzenleme' if self.is_edit else 'Operasyon Notu Girişi'}", self)
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #38bdf8;")
        layout.addWidget(t_lbl)

        # 1. Satır: Dosya No & Ref No
        row1 = QHBoxLayout()
        r1_left = QVBoxLayout()
        r1_left.addWidget(QLabel("Dosya No:", self))
        self.ent_dosya = QLineEdit(self)
        self.ent_dosya.setText(self.existing_log.get("dosya_no", "") if self.is_edit else default_dosya)
        r1_left.addWidget(self.ent_dosya)
        row1.addLayout(r1_left)

        r1_right = QVBoxLayout()
        r1_right.addWidget(QLabel("Ref / BL No:", self))
        self.ent_ref = QLineEdit(self)
        self.ent_ref.setText(self.existing_log.get("ref_no", "") if self.is_edit else default_ref)
        r1_right.addWidget(self.ent_ref)
        row1.addLayout(r1_right)
        layout.addLayout(row1)

        # 2. Satır: Beyanname No & Etiket
        row2 = QHBoxLayout()
        r2_left = QVBoxLayout()
        r2_left.addWidget(QLabel("Beyanname No:", self))
        self.ent_beyan = QLineEdit(self)
        self.ent_beyan.setText(self.existing_log.get("beyanname_no", "") if self.is_edit else default_beyan)
        r2_left.addWidget(self.ent_beyan)
        row2.addLayout(r2_left)

        r2_right = QVBoxLayout()
        r2_right.addWidget(QLabel("Etiket / Durum:", self))
        self.cmb_tag = QComboBox(self)
        self.cmb_tag.addItems(["Normal", "Acil", "Beklemede", "Tamamlandı", "Bilgi"])
        if self.is_edit and self.existing_log.get("etiket"):
            idx = self.cmb_tag.findText(self.existing_log.get("etiket"))
            if idx >= 0: self.cmb_tag.setCurrentIndex(idx)
        r2_right.addWidget(self.cmb_tag)
        row2.addLayout(r2_right)
        layout.addLayout(row2)

        # Başlık
        layout.addWidget(QLabel("Not Başlığı (Kısa Konu):", self))
        self.ent_baslik = QLineEdit(self)
        if self.is_edit: self.ent_baslik.setText(self.existing_log.get("baslik", ""))
        layout.addWidget(self.ent_baslik)

        # Hızlı Şablon Butonları
        layout.addWidget(QLabel("Hızlı Şablon Ekle:", self))
        tmpl_layout = QHBoxLayout()
        tmpl_layout.setSpacing(6)
        templates = ["Ordino Alındı", "Evrak Bekleniyor", "Müşteriye Bilgi Verildi", "Muayenede", "Kantar Yapıldı", "Vergi Ödendi"]
        for tmpl in templates:
            b = QPushButton(tmpl, self)
            b.setObjectName("TmplBtn")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda ch, t=tmpl: self._append_template(t))
            tmpl_layout.addWidget(b)
        layout.addLayout(tmpl_layout)

        # Not İçeriği
        layout.addWidget(QLabel("Not Açıklaması / Detay:", self))
        self.txt_icerik = QTextEdit(self)
        if self.is_edit: self.txt_icerik.setPlainText(self.existing_log.get("icerik", ""))
        layout.addWidget(self.txt_icerik, stretch=1)

        # Alt Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("İptal", self)
        btn_cancel.setObjectName("CancelBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Notu Kaydet & Eşitle", self)
        btn_save.setObjectName("SaveBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _append_template(self, txt):
        cur = self.txt_icerik.toPlainText().strip()
        if cur:
            self.txt_icerik.setPlainText(cur + " | " + txt)
        else:
            self.txt_icerik.setPlainText(txt)
        if not self.ent_baslik.text():
            self.ent_baslik.setText(txt)

    def _on_save(self):
        head = self.ent_baslik.text().strip()
        body = self.txt_icerik.toPlainText().strip()

        if not head and not body:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen en azından bir başlık veya not metni girin.")
            return

        if not head:
            head = body[:40]

        d_val = self.ent_dosya.text().strip()
        r_val = self.ent_ref.text().strip()
        b_val = self.ent_beyan.text().strip()
        t_val = self.cmb_tag.currentText()
        u_name = self.current_user.get("full_name") or self.current_user.get("username") or os.environ.get("USERNAME", "Operatör")

        sm = get_supabase_manager() if get_supabase_manager else None
        if not sm:
            QMessageBox.warning(self, "Uyarı", "Supabase yöneticisi bulunamadı.")
            self.reject()
            return

        try:
            if self.is_edit:
                sm.update_activity_note(
                    log_id=self.existing_log["id"],
                    baslik=head,
                    icerik=body,
                    etiket=t_val,
                    dosya_no=d_val,
                    ref_no=r_val,
                    beyanname_no=b_val
                )
            else:
                sm.add_activity_log(
                    dosya_no=d_val,
                    ref_no=r_val,
                    beyanname_no=b_val,
                    islem_tipi="NOT",
                    baslik=head,
                    icerik=body,
                    etiket=t_val,
                    kullanici=u_name
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Not kaydedilemedi: {e}")


class ActivityHubView(BaseView):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.current_activity_logs = []
        self.act_show_trash = False
        self.last_deleted_ids = []

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. Üst Metrik Kartları
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_notes = MetricCard("AKTİVİTE NOTLARI", "0", "Kullanıcı Notları", "#7c3aed", self)
        self.card_notes.clicked.connect(lambda: self._filter_type_action("NOT"))
        cards_layout.addWidget(self.card_notes)

        self.card_mail = MetricCard("VERGİ MAİLLERİ", "0", "Vergi & Bilgilendirme", "#2563eb", self)
        self.card_mail.clicked.connect(lambda: self._filter_type_action("MAIL"))
        cards_layout.addWidget(self.card_mail)

        self.card_tescil = MetricCard("GTB & GÜMRÜK", "0", "Bakanlık Hareketleri", "#16a34a", self)
        self.card_tescil.clicked.connect(lambda: self._filter_type_action("TESCIL"))
        cards_layout.addWidget(self.card_tescil)

        self.card_fatura = MetricCard("FATURA & EŞLEME", "0", "Fatura & Eşleme", "#d97706", self)
        self.card_fatura.clicked.connect(lambda: self._filter_type_action("FATURA"))
        cards_layout.addWidget(self.card_fatura)

        main_layout.addLayout(cards_layout)

        # 2. Kontrol & Filtre Çubuğu
        ctrl_bar = QFrame(self)
        ctrl_bar.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        cb_layout = QHBoxLayout(ctrl_bar)
        cb_layout.setContentsMargins(10, 6, 10, 6)
        cb_layout.setSpacing(10)

        lbl_s = QLabel("🔍 Ara:", ctrl_bar)
        lbl_s.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")
        cb_layout.addWidget(lbl_s)

        self.txt_search = QLineEdit(ctrl_bar)
        self.txt_search.setPlaceholderText("Dosya No, Ref, Başlık veya Not ara...")
        self.txt_search.textChanged.connect(self.refresh_activity_hub)
        cb_layout.addWidget(self.txt_search, stretch=1)

        lbl_d = QLabel("📅 Tarih:", ctrl_bar)
        lbl_d.setStyleSheet("font-size: 10px; font-weight: 700; color: #475569;")
        cb_layout.addWidget(lbl_d)

        self.cmb_date = QComboBox(ctrl_bar)
        self.cmb_date.addItems(["Tümü", "Bugün", "Dün", "Son 3 Gün", "Bu Hafta", "Bu Ay"])
        self.cmb_date.currentTextChanged.connect(self.refresh_activity_hub)
        cb_layout.addWidget(self.cmb_date)

        lbl_t = QLabel("🏷️ Tip:", ctrl_bar)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: 700; color: #475569;")
        cb_layout.addWidget(lbl_t)

        self.cmb_type = QComboBox(ctrl_bar)
        self.cmb_type.addItems(["TÜMÜ", "NOT", "TESCIL", "MAIL", "FATURA", "ETA", "KANTAR"])
        self.cmb_type.currentTextChanged.connect(self.refresh_activity_hub)
        cb_layout.addWidget(self.cmb_type)

        lbl_tag = QLabel("Etiket:", ctrl_bar)
        lbl_tag.setStyleSheet("font-size: 10px; font-weight: 700; color: #475569;")
        cb_layout.addWidget(lbl_tag)

        self.cmb_tag = QComboBox(ctrl_bar)
        self.cmb_tag.addItems(["TÜMÜ", "Normal", "Acil", "Beklemede", "Tamamlandı", "Bilgi"])
        self.cmb_tag.currentTextChanged.connect(self.refresh_activity_hub)
        cb_layout.addWidget(self.cmb_tag)

        # Aksiyon Butonları
        self.btn_add_note = QPushButton("➕ Yeni Not Ekle", ctrl_bar)
        self.btn_add_note.setObjectName("PrimaryBtn")
        self.btn_add_note.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_note.clicked.connect(self.show_add_note_dialog)
        cb_layout.addWidget(self.btn_add_note)

        self.btn_sync = QPushButton("🔄 Bulut Senkronize Et", ctrl_bar)
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.clicked.connect(self.sync_activity_with_supabase)
        cb_layout.addWidget(self.btn_sync)

        self.btn_export = QPushButton("📊 Excel İndir", ctrl_bar)
        self.btn_export.setObjectName("ExcelBtn")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_activity_to_excel)
        cb_layout.addWidget(self.btn_export)

        self.btn_trash = QPushButton("🗑️ Çöp Kutusu", ctrl_bar)
        self.btn_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trash.clicked.connect(self.toggle_activity_trash)
        cb_layout.addWidget(self.btn_trash)

        self.btn_empty_trash = QPushButton("🔥 Çöpü Boşalt", ctrl_bar)
        self.btn_empty_trash.setStyleSheet("background-color: #b91c1c; color: #ffffff; font-weight: 700; border-radius: 6px; padding: 6px 10px;")
        self.btn_empty_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_trash.clicked.connect(self.empty_activity_trash)
        self.btn_empty_trash.setVisible(False)
        cb_layout.addWidget(self.btn_empty_trash)

        main_layout.addWidget(ctrl_bar)

        # Geri Al (Undo) Bilgi Çubuğu
        self.undo_banner = QFrame(self)
        self.undo_banner.setStyleSheet("background-color: #1e293b; border: 1px solid #38bdf8; border-radius: 8px; padding: 6px 12px;")
        ub_layout = QHBoxLayout(self.undo_banner)
        ub_layout.setContentsMargins(10, 4, 10, 4)
        self.lbl_undo_text = QLabel("Silinen not çöp kutusuna taşındı.", self.undo_banner)
        self.lbl_undo_text.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 11px;")
        ub_layout.addWidget(self.lbl_undo_text)
        ub_layout.addStretch()

        self.btn_undo = QPushButton("↩️ Geri Al (Undo)", self.undo_banner)
        self.btn_undo.setStyleSheet("background-color: #38bdf8; color: #0f172a; font-weight: 800; border-radius: 4px; padding: 4px 10px;")
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.clicked.connect(self._undo_delete_action)
        ub_layout.addWidget(self.btn_undo)

        btn_close_undo = QPushButton("✕", self.undo_banner)
        btn_close_undo.setStyleSheet("background-color: transparent; color: #94a3b8; font-size: 13px; font-weight: 700; border: none;")
        btn_close_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_undo.clicked.connect(lambda: self.undo_banner.setVisible(False))
        ub_layout.addWidget(btn_close_undo)

        self.undo_banner.setVisible(False)
        main_layout.addWidget(self.undo_banner)

        # 3. Ana Tablo (Treeview karşılığı QTableWidget)
        self.table = QTableWidget(self)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Tarih & Saat", "Dosya No", "Ref / Konşimento", "İşlem Tipi",
            "Etiket", "Başlık", "İçerik & Not Detayı", "Kullanıcı", "Bulut"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(0, 130)  # Tarih
        self.table.setColumnWidth(1, 110)  # Dosya No
        self.table.setColumnWidth(2, 130)  # Ref / BL
        self.table.setColumnWidth(3, 100)  # Tip
        self.table.setColumnWidth(4, 90)   # Etiket
        self.table.setColumnWidth(5, 200)  # Başlık
        self.table.setColumnWidth(6, 320)  # İçerik
        self.table.setColumnWidth(7, 100)  # Kullanıcı
        self.table.setColumnWidth(8, 70)   # Bulut

        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        main_layout.addWidget(self.table, stretch=1)

    def on_activate(self):
        self.refresh_activity_hub()

    def _filter_type_action(self, t_code):
        cur = self.cmb_type.currentText()
        if cur == t_code:
            self.cmb_type.setCurrentText("TÜMÜ")
        else:
            self.cmb_type.setCurrentText(t_code)
        self.refresh_activity_hub()

    def refresh_activity_hub(self):
        search_txt = self.txt_search.text().strip()
        date_sel = self.cmb_date.currentText()
        type_sel = self.cmb_type.currentText()
        tag_sel = self.cmb_tag.currentText()

        # Tarih filtre hesaplama
        now = datetime.now()
        date_from = None
        date_to = None

        if date_sel == "Bugün":
            date_from = now.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
        elif date_sel == "Dün":
            yst = now - timedelta(days=1)
            date_from = yst.strftime("%Y-%m-%d")
            date_to = yst.strftime("%Y-%m-%d")
        elif date_sel == "Son 3 Gün":
            d3 = now - timedelta(days=2)
            date_from = d3.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
        elif date_sel == "Bu Hafta":
            start_week = now - timedelta(days=now.weekday())
            date_from = start_week.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
        elif date_sel == "Bu Ay":
            date_from = now.strftime("%Y-%m-01")
            date_to = now.strftime("%Y-%m-%d")

        logs = []
        sm = get_supabase_manager() if get_supabase_manager else None
        if sm:
            try:
                logs = sm.fetch_activity_logs(
                    search_term=search_txt if search_txt else None,
                    islem_tipi=None,
                    date_from=date_from,
                    date_to=date_to,
                    limit=500,
                    only_deleted=self.act_show_trash
                ) or []
            except Exception as e:
                print(f"[ACT-FETCH-ERROR]: {e}")
                logs = []

        # Metrik Sayaçları
        cnt_notes = sum(1 for l in logs if (l.get("islem_tipi") or "NOT").upper() == "NOT")
        cnt_mail = sum(1 for l in logs if (l.get("islem_tipi") or "").upper() == "MAIL")
        cnt_tescil = sum(1 for l in logs if (l.get("islem_tipi") or "").upper() in ("TESCIL", "GTB", "GÜMRÜK"))
        cnt_fatura = sum(1 for l in logs if (l.get("islem_tipi") or "").upper() in ("FATURA", "ESLEME", "EŞLEME"))

        self.card_notes.set_value(cnt_notes)
        self.card_mail.set_value(cnt_mail)
        self.card_tescil.set_value(cnt_tescil)
        self.card_fatura.set_value(cnt_fatura)

        # Tip ve Etiket Filtreleme
        display_logs = logs
        if type_sel != "TÜMÜ":
            if type_sel == "NOT":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "NOT").upper() == "NOT"]
            elif type_sel == "TESCIL":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() in ("TESCIL", "GTB", "GÜMRÜK")]
            elif type_sel == "MAIL":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() == "MAIL"]
            elif type_sel == "FATURA":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() in ("FATURA", "ESLEME", "EŞLEME")]
            else:
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() == type_sel.upper()]

        if tag_sel != "TÜMÜ":
            display_logs = [l for l in display_logs if str(l.get("etiket", "")).lower() == tag_sel.lower()]

        self.current_activity_logs = display_logs
        self._render_table(display_logs)

    def _render_table(self, logs):
        self.table.setRowCount(len(logs))
        for row_idx, l in enumerate(logs):
            c_time = self.format_check_time(l.get("created_at"))
            d_no = l.get("dosya_no") or "—"
            r_no = l.get("ref_no") or l.get("beyanname_no") or "—"
            tip = (l.get("islem_tipi") or "NOT").upper()
            tag = l.get("etiket") or "Normal"
            head = l.get("baslik") or "—"
            body = (l.get("icerik") or "").replace("\n", " ")
            user = l.get("kullanici") or "—"
            synced = "☁️ Evet" if l.get("is_synced") else "💾 Yerel"

            items = [
                QTableWidgetItem(c_time),
                QTableWidgetItem(d_no),
                QTableWidgetItem(r_no),
                QTableWidgetItem(tip),
                QTableWidgetItem(tag),
                QTableWidgetItem(head),
                QTableWidgetItem(body),
                QTableWidgetItem(user),
                QTableWidgetItem(synced)
            ]

            # Renk Rozetleri
            type_colors = {
                "NOT": QColor("#7c3aed"),
                "TESCIL": QColor("#16a34a"),
                "GTB": QColor("#16a34a"),
                "MAIL": QColor("#2563eb"),
                "FATURA": QColor("#d97706"),
                "ESLEME": QColor("#d97706"),
                "ETA": QColor("#0d9488"),
                "KANTAR": QColor("#db2777")
            }
            tip_color = type_colors.get(tip, QColor("#475569"))
            items[3].setForeground(tip_color)
            items[3].setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            if tag == "Acil":
                items[4].setForeground(QColor("#dc2626"))
                items[4].setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            for col_idx, it in enumerate(items):
                it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if col_idx in (0, 3, 4, 7, 8) else Qt.AlignmentFlag.AlignLeft))
                self.table.setItem(row_idx, col_idx, it)

    def _get_selected_logs(self):
        selected_rows = self.table.selectionModel().selectedRows()
        logs = []
        for index in selected_rows:
            r = index.row()
            if 0 <= r < len(self.current_activity_logs):
                logs.append(self.current_activity_logs[r])
        return logs

    def _on_table_double_click(self, row, col):
        if 0 <= row < len(self.current_activity_logs):
            log = self.current_activity_logs[row]
            # Düzenleme veya görüntüleme modalı aç
            if log.get("islem_tipi") == "NOT" and not log.get("is_deleted"):
                dlg = PyQtAddNoteDialog(self, current_user=self.current_user, existing_log=log)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.refresh_activity_hub()
            else:
                QMessageBox.information(
                    self, f"Aktivite Detayı: {log.get('baslik', '')}",
                    f"📅 Tarih: {self.format_check_time(log.get('created_at'))}\n"
                    f"📁 Dosya No: {log.get('dosya_no', '—')}\n"
                    f"🔖 Ref No: {log.get('ref_no', '—')}\n"
                    f"👤 Ekleyen: {log.get('kullanici', '—')}\n"
                    f"🏷️ İşlem Tipi: {log.get('islem_tipi', '—')} ({log.get('etiket', '—')})\n\n"
                    f"📝 İçerik:\n{log.get('icerik', '—')}"
                )

    def _show_context_menu(self, pos):
        sel_logs = self._get_selected_logs()
        if not sel_logs:
            return

        menu = QMenu(self)
        sel_count = len(sel_logs)

        if sel_count == 1:
            log = sel_logs[0]
            d_no = log.get("dosya_no") or ""
            r_no = log.get("ref_no") or ""

            act_add = menu.addAction(f"📝 Bu Dosyaya Yeni Not Ekle ({d_no})")
            act_add.triggered.connect(lambda: self.show_add_note_dialog(default_dosya=d_no, default_ref=r_no))

            if log.get("islem_tipi") == "NOT" and not log.get("is_deleted"):
                act_edit = menu.addAction("✏️ Notu Düzenle")
                act_edit.triggered.connect(lambda: self._edit_note(log))

            menu.addSeparator()
            if d_no:
                act_cp_dosya = menu.addAction(f"📋 Dosya Numarasını Kopyala ({d_no})")
                act_cp_dosya.triggered.connect(lambda: self.copy_to_clipboard(d_no, show_msg=True))

            if r_no:
                act_cp_ref = menu.addAction(f"📋 Referans Numarasını Kopyala ({r_no})")
                act_cp_ref.triggered.connect(lambda: self.copy_to_clipboard(r_no, show_msg=True))

            menu.addSeparator()
            if log.get("is_deleted") == 1:
                act_restore = menu.addAction("♻️ Bu Notu Geri Yükle")
                act_restore.triggered.connect(lambda: self.undo_delete_activity_notes([log["id"]]))
            elif log.get("islem_tipi") == "NOT":
                act_del = menu.addAction("🗑️ Bu Notu Sil (Çöpe Taşı)")
                act_del.triggered.connect(lambda: self.delete_activity_notes([log["id"]]))
        else:
            dosyalar = list(dict.fromkeys(l.get("dosya_no") for l in sel_logs if l.get("dosya_no")))
            if dosyalar:
                act_cp_all_dosya = menu.addAction(f"📋 Seçili {len(dosyalar)} Dosya Numarasını Kopyala")
                act_cp_all_dosya.triggered.connect(lambda: self.copy_to_clipboard("\n".join(dosyalar), show_msg=True))

            menu.addSeparator()
            if self.act_show_trash:
                trash_ids = [l["id"] for l in sel_logs if l.get("is_deleted") == 1]
                if trash_ids:
                    act_restore_all = menu.addAction(f"♻️ Seçilenleri Geri Yükle ({len(trash_ids)} Not)")
                    act_restore_all.triggered.connect(lambda: self.undo_delete_activity_notes(trash_ids))
            else:
                deletable_ids = [l["id"] for l in sel_logs if l.get("islem_tipi") == "NOT" and not l.get("is_deleted")]
                if deletable_ids:
                    act_del_all = menu.addAction(f"🗑️ Seçilenleri Sil ({len(deletable_ids)} Not)")
                    act_del_all.triggered.connect(lambda: self.delete_activity_notes(deletable_ids))

        menu.addSeparator()
        act_excel = menu.addAction("📊 Excel'e Aktar (.csv)")
        act_excel.triggered.connect(self.export_activity_to_excel)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def show_add_note_dialog(self, default_dosya="", default_ref="", default_beyan=""):
        dlg = PyQtAddNoteDialog(
            self, current_user=self.current_user,
            default_dosya=default_dosya, default_ref=default_ref, default_beyan=default_beyan
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_activity_hub()

    def _edit_note(self, log):
        dlg = PyQtAddNoteDialog(self, current_user=self.current_user, existing_log=log)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_activity_hub()

    def delete_activity_notes(self, log_ids):
        if not log_ids:
            return
        if not self.ask_yes_no("Notu Sil", f"Seçili {len(log_ids)} adet not çöp kutusuna taşınacak. Onaylıyor musunuz?"):
            return

        sm = get_supabase_manager() if get_supabase_manager else None
        if not sm:
            QMessageBox.critical(self, "Hata", "Supabase yöneticisi bulunamadı.")
            return

        count = 0
        for lid in log_ids:
            if sm.soft_delete_activity_log(lid):
                count += 1

        if count > 0:
            self.last_deleted_ids = log_ids
            self.refresh_activity_hub()
            self.lbl_undo_text.setText(f"🗑️ {count} not çöp kutusuna taşındı.")
            self.undo_banner.setVisible(True)
            QTimer.singleShot(10000, lambda: self.undo_banner.setVisible(False))
        else:
            QMessageBox.warning(self, "Uyarı", "Notlar silinemedi.")

    def _undo_delete_action(self):
        if self.last_deleted_ids:
            self.undo_delete_activity_notes(self.last_deleted_ids)
            self.undo_banner.setVisible(False)

    def undo_delete_activity_notes(self, log_ids):
        sm = get_supabase_manager() if get_supabase_manager else None
        if not sm:
            return
        count = 0
        for lid in log_ids:
            if sm.restore_activity_log(lid):
                count += 1
        if count > 0:
            self.refresh_activity_hub()
            QMessageBox.information(self, "Geri Alındı", f"✅ {count} adet not başarıyla geri yüklendi!")

    def toggle_activity_trash(self):
        self.act_show_trash = not self.act_show_trash
        if self.act_show_trash:
            self.btn_trash.setText("📂 Aktif Notlara Dön")
            self.btn_trash.setStyleSheet("background-color: #dc2626; color: #ffffff; font-weight: 700;")
            self.btn_empty_trash.setVisible(True)
            self.set_header_subtitle("🗑️ Çöp Kutusu: Silinen notlar listeleniyor.")
        else:
            self.btn_trash.setText("🗑️ Çöp Kutusu")
            self.btn_trash.setStyleSheet("")
            self.btn_empty_trash.setVisible(False)
            self.set_header_subtitle("Özel dosya notları ve gümrük hareketlerinin canlı tarihçesi")
        self.refresh_activity_hub()

    def empty_activity_trash(self):
        if not self.ask_yes_no(
            "Çöp Kutusunu Boşalt",
            "⚠️ DİKKAT: Çöp kutusundaki tüm notlar hem yerelden hem buluttan kalıcı olarak temizlenecektir.\n\nDevam etmek istiyor musunuz?"
        ):
            return
        sm = get_supabase_manager() if get_supabase_manager else None
        if sm:
            count = sm.empty_trash()
            self.refresh_activity_hub()
            QMessageBox.information(self, "Temizlendi", f"🗑️ {count} adet silinmiş kayıt kalıcı olarak temizlendi.")

    def sync_activity_with_supabase(self):
        sm = get_supabase_manager() if get_supabase_manager else None
        if sm:
            sm.sync_activity_logs()
            QTimer.singleShot(1200, self.refresh_activity_hub)
            QMessageBox.information(self, "Senkronizasyon", "Aktivite notları Supabase bulutu ile senkronize edildi!")
        else:
            QMessageBox.warning(self, "Uyarı", "Supabase senkronizasyon yöneticisi bulunamadı.")

    def export_activity_to_excel(self):
        if not self.current_activity_logs:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak kayıt bulunamadı.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Aktivite Notlarını Kaydet", "Aktivite_Notlari.csv", "CSV Dosyası (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Tarih", "Dosya No", "Ref No", "İşlem Tipi", "Etiket", "Başlık", "İçerik", "Kullanıcı", "Bulut Durumu"])
                for l in self.current_activity_logs:
                    writer.writerow([
                        l.get("created_at", ""), l.get("dosya_no", ""), l.get("ref_no", ""),
                        l.get("islem_tipi", ""), l.get("etiket", ""), l.get("baslik", ""),
                        (l.get("icerik", "")).replace("\n", " "), l.get("kullanici", ""),
                        "Evet" if l.get("is_synced") else "Hayır"
                    ])
            QMessageBox.information(self, "Başarılı", f"Kayıtlar başarıyla aktarıldı:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")
