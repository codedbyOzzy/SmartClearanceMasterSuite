# -*- coding: utf-8 -*-
"""
📑 SmartClearance MasterSuite - Sağ Seçili Dosya Detay Çekmecesi (PyQt6)
Dosya Özeti, Canlı GTB Bakanlık Durumu, Outlook Vergi Maili Durumu ve Asenkron Mail Zaman Tüneli.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont


class TimelineWorker(QThread):
    """Outlook mail akışını arayüzü dondurmadan arka planda tarayan iş parçacığı."""
    finished = pyqtSignal(list, object)

    def __init__(self, engine, record):
        super().__init__()
        self.engine = engine
        self.record = record

    def run(self):
        try:
            if self.engine and hasattr(self.engine, "fetch_file_mail_timeline") and self.record:
                timeline = self.engine.fetch_file_mail_timeline(self.record)
                self.finished.emit(timeline or [], self.record.get("row_idx"))
            else:
                self.finished.emit([], getattr(self.record, "row_idx", None))
        except Exception as e:
            print(f"Timeline fetch error: {e}")
            self.finished.emit([], getattr(self.record, "row_idx", None))


class CockpitDetailDrawer(QWidget):
    gtb_query_requested = pyqtSignal(dict)
    open_draft_requested = pyqtSignal(dict)
    open_horizon_requested = pyqtSignal(dict)

    def __init__(self, parent=None, engine=None):
        super().__init__(parent)
        self.engine = engine
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        self.setStyleSheet("background-color: #0b0f19; border-left: 1px solid #1e293b;")
        self.current_rec = None
        self.current_timeline_items = []
        self.timeline_worker = None

        self._build_ui()

    def set_engine(self, engine):
        self.engine = engine

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Başlık Barı
        header = QWidget(self)
        header.setStyleSheet("background-color: #0d1322; border-bottom: 1px solid #1e293b;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 10, 12, 10)

        lbl_h = QLabel("📋 SEÇİLİ DOSYA DETAYI", header)
        lbl_h.setStyleSheet("font-size: 12px; font-weight: 800; color: #38bdf8; background: transparent; border: none;")
        h_layout.addWidget(lbl_h)
        h_layout.addStretch()

        self.lbl_dosya_badge = QLabel("—", header)
        self.lbl_dosya_badge.setStyleSheet("""
            background-color: #1e293b; color: #38bdf8;
            font-size: 11px; font-weight: 800;
            padding: 3px 8px; border-radius: 4px; border: 1px solid #334155;
        """)
        h_layout.addWidget(self.lbl_dosya_badge)

        main_layout.addWidget(header)

        # 2. Sekmeli Alan
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background-color: #0b0f19; }
            QTabBar::tab { font-size: 11px; font-weight: 700; padding: 7px 12px; background-color: #111827; color: #94a3b8; }
            QTabBar::tab:selected { color: #ffffff; background-color: #1d4ed8; border-bottom: 2px solid #38bdf8; }
        """)

        # Sekme 1: Dosya Özeti
        self.tab_summary = QWidget()
        self.tab_summary.setStyleSheet("background-color: #0b0f19;")
        self._build_summary_tab(self.tab_summary)
        self.tabs.addTab(self.tab_summary, "📋 Dosya Özeti")

        # Sekme 2: Mail Zaman Tüneli
        self.tab_timeline = QWidget()
        self.tab_timeline.setStyleSheet("background-color: #0b0f19;")
        self._build_timeline_tab(self.tab_timeline)
        self.tabs.addTab(self.tab_timeline, "📜 Mail Zaman Tüneli")

        main_layout.addWidget(self.tabs)

    def _build_summary_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        scroll.viewport().setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(10, 10, 10, 10)
        c_layout.setSpacing(8)

        # Temel Bilgiler Kartı
        card_info = QFrame(content)
        card_info.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 10px;")
        card_layout = QVBoxLayout(card_info)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(5)

        self.info_labels = {}
        fields = [
            ("ref", "🔖 Referans No:"),
            ("bl", "🚢 Konşimento (B/L):"),
            ("bayi", "🏢 Bayi / Alıcı:"),
            ("liman", "📍 Gümrük & Liman:"),
            ("stage", "⚡ Operasyonel Aşama:"),
            ("hat", "🚦 Hat Durumu:"),
            ("tescil_tarihi", "📅 Tescil Tarihi:"),
            ("ordino", "📦 Ordino Teslim:"),
            ("tareks", "📋 Tareks Başvuru:"),
            ("aciklama", "📝 Açıklama:"),
        ]

        for code, label in fields:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl_key = QLabel(label, card_info)
            lbl_key.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; background: transparent; border: none;")
            lbl_val = QLabel("—", card_info)
            lbl_val.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; background: transparent; border: none;")
            lbl_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl_val.setWordWrap(True)
            row.addWidget(lbl_key)
            row.addStretch()
            row.addWidget(lbl_val)
            card_layout.addLayout(row)
            self.info_labels[code] = lbl_val

        c_layout.addWidget(card_info)

        # Outlook Vergi Maili Kutusu
        mail_box = QFrame(content)
        mail_box.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 8px 10px;")
        mb_layout = QVBoxLayout(mail_box)
        mb_layout.setSpacing(3)

        mb_title = QLabel("📬 OUTLOOK VERGİ MAİL DURUMU", mail_box)
        mb_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #38bdf8; background: transparent; border: none;")
        mb_layout.addWidget(mb_title)

        self.lbl_mail_durum = QLabel("• Durum: —", mail_box)
        self.lbl_mail_durum.setStyleSheet("font-size: 11px; color: #f1f5f9; font-weight: 600; background: transparent; border: none;")
        mb_layout.addWidget(self.lbl_mail_durum)

        self.lbl_mail_saat = QLabel("• Gönderim Saati: —", mail_box)
        self.lbl_mail_saat.setStyleSheet("font-size: 10px; color: #94a3b8; background: transparent; border: none;")
        mb_layout.addWidget(self.lbl_mail_saat)

        self.lbl_mail_alici = QLabel("• Alıcı: —", mail_box)
        self.lbl_mail_alici.setStyleSheet("font-size: 10px; color: #94a3b8; background: transparent; border: none;")
        mb_layout.addWidget(self.lbl_mail_alici)

        self.lbl_mail_atts = QLabel("• Ekler: —", mail_box)
        self.lbl_mail_atts.setStyleSheet("font-size: 10px; color: #94a3b8; background: transparent; border: none;")
        mb_layout.addWidget(self.lbl_mail_atts)

        c_layout.addWidget(mail_box)

        # GTB Bakanlık Canlı Durum Kutusu
        gtb_box = QFrame(content)
        gtb_box.setStyleSheet("background-color: #064e3b; border: 1px solid #059669; border-radius: 8px; padding: 8px 10px;")
        gb_layout = QVBoxLayout(gtb_box)
        gb_layout.setSpacing(3)

        gb_title = QLabel("🏛️ GTB BAKANLIK CANLI DURUM", gtb_box)
        gb_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #34d399; background: transparent; border: none;")
        gb_layout.addWidget(gb_title)

        self.lbl_gtb_status = QLabel("Takip Havuzunda Bulunamadı", gtb_box)
        self.lbl_gtb_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #ecfdf5; background: transparent; border: none;")
        self.lbl_gtb_status.setWordWrap(True)
        gb_layout.addWidget(self.lbl_gtb_status)

        c_layout.addWidget(gtb_box)

        # Aksiyon Butonları
        c_layout.addSpacing(4)
        self.btn_open_draft = QPushButton("✉️ Vergi Maili Taslağı Aç (Seçilen Dosyalar)", content)
        self.btn_open_draft.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_draft.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #f8fafc;
                font-size: 11px; font-weight: 700; padding: 8px 12px;
                border-radius: 6px; border: 1px solid #334155;
            }
            QPushButton:hover { background-color: #334155; border-color: #38bdf8; color: #ffffff; }
            QPushButton:pressed { background-color: #0f172a; }
        """)
        self.btn_open_draft.clicked.connect(lambda: self.open_draft_requested.emit(self.current_rec or {}))
        c_layout.addWidget(self.btn_open_draft)

        self.btn_gtb_query = QPushButton("🏛️ GTB Bakanlık'tan Canlı Sorgula", content)
        self.btn_gtb_query.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gtb_query.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; color: #ffffff;
                font-size: 11px; font-weight: 700; padding: 8px 12px;
                border-radius: 6px; border: 1px solid #38bdf8;
            }
            QPushButton:hover { background-color: #0369a1; border-color: #7dd3fc; }
            QPushButton:pressed { background-color: #075985; }
        """)
        self.btn_gtb_query.clicked.connect(lambda: self.gtb_query_requested.emit(self.current_rec or {}))
        c_layout.addWidget(self.btn_gtb_query)

        self.btn_horizon = QPushButton("🌐 Haritada Canlı Gör (Horizon)", content)
        self.btn_horizon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_horizon.setStyleSheet("""
            QPushButton {
                background-color: #0f172a; color: #38bdf8;
                font-size: 11px; font-weight: 700; padding: 8px 12px;
                border-radius: 6px; border: 1px solid #0284c7;
            }
            QPushButton:hover { background-color: #0369a1; color: #ffffff; border-color: #38bdf8; }
            QPushButton:pressed { background-color: #0c4a6e; }
        """)
        self.btn_horizon.clicked.connect(lambda: self.open_horizon_requested.emit(self.current_rec or {}))
        c_layout.addWidget(self.btn_horizon)

        c_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_timeline_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.lbl_tl_status = QLabel("Dosya seçildiğinde mail akışı taranır.", tab)
        self.lbl_tl_status.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
        layout.addWidget(self.lbl_tl_status)

        # Zaman Tüneli Tablosu
        self.tbl_timeline = QTableWidget(tab)
        self.tbl_timeline.setColumnCount(5)
        self.tbl_timeline.setHorizontalHeaderLabels(["Yön", "Tarih/Saat", "Muhatap", "Konu", "Ek"])
        self.tbl_timeline.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_timeline.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_timeline.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_timeline.verticalHeader().setVisible(False)
        self.tbl_timeline.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tbl_timeline.horizontalHeader().setStretchLastSection(False)
        self.tbl_timeline.setColumnWidth(0, 50)   # Yön
        self.tbl_timeline.setColumnWidth(1, 95)   # Tarih
        self.tbl_timeline.setColumnWidth(2, 90)   # Muhatap
        self.tbl_timeline.setColumnWidth(3, 100)  # Konu
        self.tbl_timeline.setColumnWidth(4, 45)   # Ekler
        self.tbl_timeline.cellDoubleClicked.connect(self._on_timeline_double_click)
        layout.addWidget(self.tbl_timeline, stretch=1)

        btn_open_mail = QPushButton("📬 Seçili Maili Outlook'ta Aç", tab)
        btn_open_mail.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_mail.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #38bdf8;
                font-size: 11px; font-weight: 700; padding: 7px 12px;
                border: 1px solid #334155; border-radius: 6px;
            }
            QPushButton:hover { background-color: #2563eb; color: #ffffff; border-color: #38bdf8; }
            QPushButton:pressed { background-color: #1d4ed8; }
        """)
        btn_open_mail.clicked.connect(self._open_selected_mail)
        layout.addWidget(btn_open_mail)

    def set_record(self, rec):
        self.current_rec = rec
        if not rec:
            self.lbl_dosya_badge.setText("Dosya Seçilmedi")
            for k, lbl in self.info_labels.items():
                lbl.setText("—")
                lbl.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; background: transparent; border: none;")
            self.lbl_mail_durum.setText("• Durum: —")
            self.lbl_mail_saat.setText("• Gönderim Saati: —")
            self.lbl_mail_alici.setText("• Alıcı: —")
            self.lbl_mail_atts.setText("• Ekler: —")
            self.lbl_gtb_status.setText("Seçim Bekleniyor...")
            self.lbl_tl_status.setText("Dosya seçilmedi.")
            self.tbl_timeline.setRowCount(0)
            self.tabs.setTabText(1, "📜 Mail Zaman Tüneli")
            return

        self.lbl_dosya_badge.setText(rec.get("dosya") or "Dosya No Yok")
        self.info_labels["ref"].setText(rec.get("ref") or "—")
        self.info_labels["bl"].setText(rec.get("bl") or "—")
        self.info_labels["bayi"].setText(rec.get("bayi") or "—")
        self.info_labels["liman"].setText(f"{rec.get('gumruk') or '—'} / {rec.get('liman') or '—'}")

        # Aşama ve Hat için canlı renk vurgusu
        stage_str = rec.get("stage_title") or "—"
        self.info_labels["stage"].setText(stage_str)
        if "Tescil" in stage_str:
            self.info_labels["stage"].setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700; background: transparent;")
        elif "Ordino" in stage_str or "Tareks" in stage_str:
            self.info_labels["stage"].setStyleSheet("color: #fb923c; font-size: 11px; font-weight: 700; background: transparent;")
        elif "Yeni" in stage_str or "Hazırlık" in stage_str:
            self.info_labels["stage"].setStyleSheet("color: #facc15; font-size: 11px; font-weight: 700; background: transparent;")
        elif "Kapan" in stage_str or "Arşiv" in stage_str:
            self.info_labels["stage"].setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 700; background: transparent;")
        else:
            self.info_labels["stage"].setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; background: transparent;")

        hat_str = str(rec.get("hat") or "—").strip()
        self.info_labels["hat"].setText(hat_str)
        if "SARI" in hat_str.upper():
            self.info_labels["hat"].setStyleSheet("color: #facc15; font-size: 11px; font-weight: 800; background: transparent;")
        elif "KIRMIZI" in hat_str.upper():
            self.info_labels["hat"].setStyleSheet("color: #f87171; font-size: 11px; font-weight: 800; background: transparent;")
        elif "YEŞİL" in hat_str.upper():
            self.info_labels["hat"].setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 800; background: transparent;")
        elif "MAVİ" in hat_str.upper():
            self.info_labels["hat"].setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; background: transparent;")
        else:
            self.info_labels["hat"].setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; background: transparent;")

        self.info_labels["tescil_tarihi"].setText(rec.get("tescil") or rec.get("tescil_tarihi") or "—")
        self.info_labels["ordino"].setText(rec.get("ordino") or rec.get("ordino_tarihi") or "—")
        self.info_labels["tareks"].setText(rec.get("tareks") or rec.get("tareks_tarihi") or "—")
        self.info_labels["aciklama"].setText(rec.get("aciklama") or "Yok")

        # Mail durumu
        m_stat = rec.get("mail_status") or "Mail Gönderilmedi"
        self.lbl_mail_durum.setText(f"• Durum: {m_stat}")
        self.lbl_mail_saat.setText(f"• Gönderim Saati: {rec.get('mail_date') or rec.get('mail_time') or '—'}")
        self.lbl_mail_alici.setText(f"• Alıcı: {rec.get('mail_to') or '—'}")
        atts = rec.get("mail_attachments", [])
        self.lbl_mail_atts.setText(f"• Ekler: {', '.join(atts) if atts else '—'}")

        # GTB Durumu
        gtb_durum = rec.get("gtb_status") or rec.get("gtb_durum") or "Takip Havuzunda Bulunamadı"
        self.lbl_gtb_status.setText(gtb_durum)

        # Zaman Tüneli Yükleme (Asenkron Worker)
        self._fetch_timeline(rec)

    def _fetch_timeline(self, rec):
        self.lbl_tl_status.setText("⏳ Mail akışı Outlook'tan taranıyor...")
        self.tbl_timeline.setRowCount(0)
        self.current_timeline_items = []

        if not self.engine:
            self.lbl_tl_status.setText("ℹ️ Veri motoru bağlı değil.")
            return

        self.timeline_worker = TimelineWorker(self.engine, rec)
        self.timeline_worker.finished.connect(self._on_timeline_fetched)
        self.timeline_worker.start()

    def _on_timeline_fetched(self, timeline, target_row_idx):
        if not self.current_rec or self.current_rec.get("row_idx") != target_row_idx:
            return

        self.current_timeline_items = timeline
        count = len(timeline)
        self.tabs.setTabText(1, f"📜 Mail Zaman Tüneli ({count})")

        if count == 0:
            self.lbl_tl_status.setText("ℹ️ Bu dosyaya ait Outlook mail akışı bulunamadı.")
            self.tbl_timeline.setRowCount(0)
            return

        self.lbl_tl_status.setText(f"✅ {count} adet ilgili mail bulundu (Çift tıkla aç).")
        self.tbl_timeline.setRowCount(count)

        for idx, m in enumerate(timeline):
            is_out = (m.get("direction") == "OUT")
            yon_text = "Giden 📤" if is_out else "Gelen 📥"
            atts = m.get("attachments", [])
            att_icon = f"📎 ({len(atts)})" if atts else "—"

            item_yon = QTableWidgetItem(yon_text)
            item_time = QTableWidgetItem(m.get("time_str") or "—")
            item_party = QTableWidgetItem(m.get("party") or "—")
            item_subj = QTableWidgetItem(m.get("subject") or "—")
            item_att = QTableWidgetItem(att_icon)

            color = QColor("#4ade80") if is_out else QColor("#60a5fa")
            for item in [item_yon, item_time, item_party, item_subj, item_att]:
                item.setForeground(color)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

            self.tbl_timeline.setItem(idx, 0, item_yon)
            self.tbl_timeline.setItem(idx, 1, item_time)
            self.tbl_timeline.setItem(idx, 2, item_party)
            self.tbl_timeline.setItem(idx, 3, item_subj)
            self.tbl_timeline.setItem(idx, 4, item_att)

    def _on_timeline_double_click(self, row, col):
        self._open_selected_mail()

    def _open_selected_mail(self):
        selected_rows = self.tbl_timeline.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.current_timeline_items):
            item = self.current_timeline_items[row]
            entry_id = item.get("entry_id")
            if entry_id and self.engine and hasattr(self.engine, "open_outlook_mail_by_id"):
                ok = self.engine.open_outlook_mail_by_id(entry_id)
                if not ok:
                    QMessageBox.warning(self, "Uyarı", "Mail Outlook'ta açılamadı.")
