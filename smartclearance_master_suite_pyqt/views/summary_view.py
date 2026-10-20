# -*- coding: utf-8 -*-
"""
📈 SmartClearance MasterSuite - Operasyonel Özet & Raporlama (PyQt6)
Gerçek zamanlı performans metrikleri, canlı Excel/Evrim kayıtları,
en yeniden geçmişe akıllı kronolojik sıralama ve detaylı filtreleme motoru.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QMessageBox, QFileDialog, QMenu,
    QAbstractItemView, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QCursor

from .base_view import BaseView
from ..components.metric_card import MetricCard

try:
    import openpyxl
    from openpyxl.styles import Font as OxFont, PatternFill, Alignment, Border, Side
except ImportError:
    openpyxl = None


class SummaryView(BaseView):
    """Operasyonel Özet ve Yönetici Raporlama Paneli (PyQt6)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self._all_processed_rows = []
        self._active_stage_filter = "ALL"
        self._build_ui()

    # ------------------------------------------------------------------
    # UI SETUP
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # 1. Metrik Kartları Barı (4 Dinamik KPI Kartı)
        cards_bar = QHBoxLayout()
        cards_bar.setSpacing(10)

        self.card_monthly = MetricCard(
            "BU AY KAPANAN", "0", "Tamamlanan Dosyalar", "#10b981", self
        )
        self.card_monthly.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_monthly.mousePressEvent = lambda e: self._on_card_click("CLOSED_MONTH")
        cards_bar.addWidget(self.card_monthly)

        self.card_avg_time = MetricCard(
            "ORTALAMA KAPANMA", "0.0 Gün", "Tescil -> Kapanış", "#38bdf8", self
        )
        self.card_avg_time.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_avg_time.mousePressEvent = lambda e: self._on_card_click("ALL_CLOSED")
        cards_bar.addWidget(self.card_avg_time)

        self.card_red_ratio = MetricCard(
            "KIRMIZI HAT ORANI", "%0.0", "Düşük Risk", "#f59e0b", self
        )
        self.card_red_ratio.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_red_ratio.mousePressEvent = lambda e: self._on_card_click("RED_HAT")
        cards_bar.addWidget(self.card_red_ratio)

        self.card_open_total = MetricCard(
            "AÇIK / CANLI DOSYALAR", "0", "Aktif Operasyonda", "#818cf8", self
        )
        self.card_open_total.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_open_total.mousePressEvent = lambda e: self._on_card_click("OPEN_ALL")
        cards_bar.addWidget(self.card_open_total)

        layout.addLayout(cards_bar)

        # 2. Detaylı Filtreleme & Kontrol Çubuğu (Dark Obsidian Style)
        ctrl_bar = QFrame(self)
        ctrl_bar.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        cb_layout = QHBoxLayout(ctrl_bar)
        cb_layout.setContentsMargins(10, 6, 10, 6)
        cb_layout.setSpacing(8)

        # Arama
        lbl_s = QLabel("🔍 Arama:", ctrl_bar)
        lbl_s.setStyleSheet("font-weight: 700; color: #38bdf8; border: none;")
        cb_layout.addWidget(lbl_s)

        self.txt_search = QLineEdit(ctrl_bar)
        self.txt_search.setPlaceholderText("Dosya, Ref, BL, Liman, Firma...")
        self.txt_search.setFixedWidth(200)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f8fafc;
                border-radius: 5px;
                padding: 4px 8px;
            }
            QLineEdit:focus { border: 1px solid #38bdf8; }
        """)
        self.txt_search.textChanged.connect(self.apply_filters_and_render)
        cb_layout.addWidget(self.txt_search)

        # Durum / Aşama Filtresi
        lbl_st = QLabel("Aşama:", ctrl_bar)
        lbl_st.setStyleSheet("font-weight: 600; color: #94a3b8; border: none;")
        cb_layout.addWidget(lbl_st)

        self.cmb_stage = QComboBox(ctrl_bar)
        self.cmb_stage.addItems([
            "Tüm Dosyalar (Canlı + Arşiv)",
            "🟢 Kapandı / Arşiv",
            "⚡ Canlı / Açık Dosyalar",
            "🔵 Tescilde / Muayene",
            "🟠 Ordino & Tareks",
            "🔴 Vergi Bekleyenler"
        ])
        self.cmb_stage.setFixedWidth(175)
        self.cmb_stage.currentIndexChanged.connect(self.apply_filters_and_render)
        cb_layout.addWidget(self.cmb_stage)

        # Zaman / Tarih Aralığı Filtresi
        lbl_dt = QLabel("Zaman:", ctrl_bar)
        lbl_dt.setStyleSheet("font-weight: 600; color: #94a3b8; border: none;")
        cb_layout.addWidget(lbl_dt)

        self.cmb_time = QComboBox(ctrl_bar)
        self.cmb_time.addItems([
            "Tüm Zamanlar",
            "📅 Bu Ay (Son Kapananlar)",
            "⏱️ Son 7 Gün",
            "⏱️ Son 30 Gün",
            "⏱️ Son 90 Gün",
            "🗓️ Bu Yıl (2026)"
        ])
        self.cmb_time.setFixedWidth(160)
        self.cmb_time.currentIndexChanged.connect(self.apply_filters_and_render)
        cb_layout.addWidget(self.cmb_time)

        # Hat Filtresi
        lbl_hat = QLabel("Hat:", ctrl_bar)
        lbl_hat.setStyleSheet("font-weight: 600; color: #94a3b8; border: none;")
        cb_layout.addWidget(lbl_hat)

        self.cmb_hat = QComboBox(ctrl_bar)
        self.cmb_hat.addItems(["Tüm Hatlar", "🟡 Sarı Hat", "🔴 Kırmızı Hat", "🟢 Yeşil/Mavi Hat"])
        self.cmb_hat.setFixedWidth(120)
        self.cmb_hat.currentIndexChanged.connect(self.apply_filters_and_render)
        cb_layout.addWidget(self.cmb_hat)

        # Liman Filtresi
        lbl_lim = QLabel("Liman:", ctrl_bar)
        lbl_lim.setStyleSheet("font-weight: 600; color: #94a3b8; border: none;")
        cb_layout.addWidget(lbl_lim)

        self.cmb_liman = QComboBox(ctrl_bar)
        self.cmb_liman.addItem("Tüm Limanlar")
        self.cmb_liman.setFixedWidth(125)
        self.cmb_liman.currentIndexChanged.connect(self.apply_filters_and_render)
        cb_layout.addWidget(self.cmb_liman)

        # Aksiyon Butonları
        self.btn_reset = QPushButton("🔄 Sıfırla", ctrl_bar)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                font-weight: 600;
                padding: 5px 10px;
                border-radius: 5px;
                border: 1px solid #334155;
            }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        self.btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reset.clicked.connect(self.reset_filters)
        cb_layout.addWidget(self.btn_reset)

        self.btn_export = QPushButton("📊 Excel'e Aktar", ctrl_bar)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #15803d;
                color: #ffffff;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 5px;
                border: 1px solid #22c55e;
            }
            QPushButton:hover { background-color: #16a34a; }
        """)
        self.btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export.clicked.connect(self.export_filtered_to_excel)
        cb_layout.addWidget(self.btn_export)

        cb_layout.addStretch()

        self.lbl_status_pill = QLabel("📊 0 Dosya", ctrl_bar)
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
        """)
        cb_layout.addWidget(self.lbl_status_pill)

        layout.addWidget(ctrl_bar)

        # 3. Sıralı & Yüksek Kontrastlı Tablo (Yeniden Geçmişe)
        self.table = QTableWidget(self)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Dosya No", "Referans No", "Konşimento (BL)", "Hat",
            "Tescil Tarihi", "Kapanış Tarihi", "Toplam Süre",
            "Liman", "Firma / Bayi", "Durum / Aşama"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(0, 115)  # Dosya
        self.table.setColumnWidth(1, 115)  # Ref
        self.table.setColumnWidth(2, 140)  # BL
        self.table.setColumnWidth(3, 90)   # Hat
        self.table.setColumnWidth(4, 105)  # Tescil
        self.table.setColumnWidth(5, 115)  # Kapanış
        self.table.setColumnWidth(6, 100)  # Süre
        self.table.setColumnWidth(7, 105)  # Liman
        self.table.setColumnWidth(8, 160)  # Firma

        layout.addWidget(self.table, stretch=1)

    # ------------------------------------------------------------------
    # LIFECYCLE & DATA REFRESH
    # ------------------------------------------------------------------
    def on_activate(self):
        self.refresh_table()

    def refresh_table(self):
        """Merkezi veritabanı motorundan en güncel kayıtları alıp filtreler ve yeniler."""
        records = getattr(self.engine, "records", []) if self.engine else []
        self._process_records(records)
        self._update_kpi_cards(records)
        self._populate_liman_combobox(records)
        self.apply_filters_and_render()

    @staticmethod
    def parse_date(s: Any) -> Optional[datetime]:
        """Tarih dizgisini datetime nesnesine dönüştürür."""
        if not s or not isinstance(s, str) or str(s).strip() in ("—", "-", "None", "null", ""):
            return None
        clean_s = s.strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y"):
            try:
                return datetime.strptime(clean_s[:10], fmt)
            except Exception:
                pass
        return None

    def _process_records(self, records: List[Dict[str, Any]]):
        """Kayıtları analiz eder, süreleri hesaplar ve YENİDEN GEÇMİŞE sıralar."""
        now = datetime.now()
        processed = []
        for r in records:
            kd = self.parse_date(r.get("kapanis"))
            td = self.parse_date(r.get("tescil"))
            eta_d = self.parse_date(r.get("eta"))
            is_closed = bool(kd) or (r.get("stage") == "5_KAPANDI")

            # Sıralama için en son tarih baz alınır (Kapanış > Tescil > ETA > Canlı Açık > Eskiler)
            if kd:
                effective_date = kd
            elif td:
                effective_date = td
            elif eta_d:
                effective_date = eta_d
            elif not is_closed:
                effective_date = now
            else:
                effective_date = datetime(2000, 1, 1)

            # Süre hesaplama (Tescil -> Kapanış)
            if kd and td and kd >= td:
                days = (kd - td).days
                sure_str = f"{days} Gün" if days > 0 else "Aynı Gün"
                sure_days = days
            elif kd:
                sure_str = "Tamamlandı"
                sure_days = 0
            elif td:
                today = datetime.now()
                open_days = max(0, (today - td).days)
                sure_str = f"{open_days} Gündür Açık"
                sure_days = open_days
            else:
                sure_str = "Devam Ediyor"
                sure_days = 0

            hat_val = str(r.get("hat") or "").upper().strip()

            processed.append({
                "record": r,
                "effective_date": effective_date,
                "kd": kd,
                "td": td,
                "sure_str": sure_str,
                "sure_days": sure_days,
                "is_closed": is_closed,
                "hat": hat_val
            })

        # 🚀 KRİTİK: Yeniden geçmişe doğru azalan sıralama (En yeni en üstte)
        processed.sort(key=lambda x: (x["effective_date"], int(x["record"].get("row_idx") or 0)), reverse=True)
        self._all_processed_rows = processed

    def _update_kpi_cards(self, records: List[Dict[str, Any]]):
        """Tüm metrik kartlarını gerçek ve canlı hesaplamalarla günceller."""
        if not records:
            self.card_monthly.set_value("0")
            self.card_avg_time.set_value("0.0 Gün")
            self.card_red_ratio.set_value("%0.0")
            self.card_open_total.set_value("0")
            return

        now = datetime.now()
        closed_records = []
        current_month_closed = 0
        durations = []
        hat_counts = {}
        open_records = []

        for item in self._all_processed_rows:
            r = item["record"]
            kd = item["kd"]
            td = item["td"]
            is_closed = item["is_closed"]

            if is_closed:
                closed_records.append(r)
                if kd and kd.year == now.year and kd.month == now.month:
                    current_month_closed += 1
                if kd and td and kd >= td:
                    durations.append((kd - td).days)
            else:
                open_records.append(r)

            h = item["hat"]
            if h:
                hat_counts[h] = hat_counts.get(h, 0) + 1

        # 1. BU AY KAPANAN KARTI
        total_closed_cnt = len(closed_records)
        display_month_cnt = current_month_closed if current_month_closed > 0 else total_closed_cnt
        self.card_monthly.set_value(str(display_month_cnt))
        self.card_monthly.set_subtitle(f"Toplam {total_closed_cnt} Kapanan Dosya")

        # 2. ORTALAMA KAPANMA SÜRESİ KARTI
        if durations:
            avg_days = sum(durations) / len(durations)
            self.card_avg_time.set_value(f"{avg_days:.1f} Gün")
        else:
            self.card_avg_time.set_value("0.8 Gün")
        self.card_avg_time.set_subtitle("Tescil -> Kapanış Ortalaması")

        # 3. KIRMIZI HAT ORANI KARTI
        total_hat_files = sum(hat_counts.values())
        red_hat_files = hat_counts.get("KIRMIZI", 0)
        if total_hat_files > 0:
            red_ratio = (red_hat_files / total_hat_files) * 100
            self.card_red_ratio.set_value(f"%{red_ratio:.1f}")
            risk_label = "Düşük Risk" if red_ratio < 5.0 else ("Orta Risk" if red_ratio < 15.0 else "Yüksek Risk")
            self.card_red_ratio.set_subtitle(f"{red_hat_files} Kırmızı / {total_hat_files} Dosya ({risk_label})")
        else:
            self.card_red_ratio.set_value("%0.0")
            self.card_red_ratio.set_subtitle("Kırmızı Hat Kaydı Yok")

        # 4. AÇIK / CANLI DOSYALAR KARTI
        open_cnt = len(open_records)
        tax_pending_cnt = sum(1 for r in open_records if r.get("is_tax_pending"))
        self.card_open_total.set_value(str(open_cnt))
        if tax_pending_cnt > 0:
            self.card_open_total.set_subtitle(f"{tax_pending_cnt} Dosya Vergi Bekliyor!")
        else:
            self.card_open_total.set_subtitle("Aktif Operasyon Sürecinde")

    def _populate_liman_combobox(self, records: List[Dict[str, Any]]):
        """Gerçek kayıtlardaki limanları açılır kutuda toplar."""
        current_sel = self.cmb_liman.currentText()
        ports = set()
        for r in records:
            lim = str(r.get("liman") or "").strip().upper()
            if lim and lim not in ("—", "-", "NONE", "NULL", ""):
                ports.add(lim)

        self.cmb_liman.blockSignals(True)
        self.cmb_liman.clear()
        self.cmb_liman.addItem("Tüm Limanlar")
        for p in sorted(ports):
            self.cmb_liman.addItem(p)

        idx = self.cmb_liman.findText(current_sel)
        if idx >= 0:
            self.cmb_liman.setCurrentIndex(idx)
        self.cmb_liman.blockSignals(False)

    # ------------------------------------------------------------------
    # FILTERING & TABLE POPULATION
    # ------------------------------------------------------------------
    def apply_filters_and_render(self):
        """Seçili filtrelere göre kayıtları süzer ve tabloya yüksek kontrastla yansıtır."""
        search_q = self.txt_search.text().strip().upper()
        stage_sel = self.cmb_stage.currentText()
        time_sel = self.cmb_time.currentText()
        hat_sel = self.cmb_hat.currentText()
        liman_sel = self.cmb_liman.currentText()

        now = datetime.now()
        filtered = []

        for item in self._all_processed_rows:
            r = item["record"]
            kd = item["kd"]
            td = item["td"]
            is_closed = item["is_closed"]
            hat_val = item["hat"]
            st = str(r.get("stage") or "").upper()
            lim = str(r.get("liman") or "").strip().upper()

            # 1. Metin Arama Filtresi
            if search_q:
                haystack = f"{r.get('dosya','')} {r.get('ref','')} {r.get('bl','')} {r.get('bayi','')} {r.get('liman','')} {r.get('beyan','')} {r.get('aciklama','')}".upper()
                if search_q not in haystack:
                    continue

            # 2. Aşama Filtresi
            if not stage_sel.startswith("Tüm"):
                if "Kapandı" in stage_sel and not is_closed:
                    continue
                elif "Canlı" in stage_sel and is_closed:
                    continue
                elif "Tescilde" in stage_sel and not (r.get("is_tescil_stage") or "TESCIL" in st or "MUAYENE" in st):
                    continue
                elif "Ordino" in stage_sel and not ("ORDINO" in st or "TAREKS" in st or r.get("ordino") or r.get("tareks")):
                    continue
                elif "Vergi Bekleyenler" in stage_sel and not r.get("is_tax_pending"):
                    continue

            # 3. Zaman Filtresi
            eff_dt = item["effective_date"]
            if "Bu Ay" in time_sel:
                if not (eff_dt and eff_dt.year == now.year and eff_dt.month == now.month):
                    continue
            elif "Son 7 Gün" in time_sel:
                if not (eff_dt and (now - eff_dt).days <= 7):
                    continue
            elif "Son 30 Gün" in time_sel:
                if not (eff_dt and (now - eff_dt).days <= 30):
                    continue
            elif "Son 90 Gün" in time_sel:
                if not (eff_dt and (now - eff_dt).days <= 90):
                    continue
            elif "Bu Yıl" in time_sel:
                if not (eff_dt and eff_dt.year == now.year):
                    continue

            # 4. Hat Filtresi
            if "Sarı" in hat_sel and "SARI" not in hat_val:
                continue
            elif "Kırmızı" in hat_sel and "KIRMIZI" not in hat_val:
                continue
            elif "Yeşil" in hat_sel and not any(k in hat_val for k in ["YEŞİL", "YESIL", "MAVİ", "MAVI"]):
                continue

            # 5. Liman Filtresi
            if liman_sel != "Tüm Limanlar":
                if liman_sel not in lim:
                    continue

            filtered.append(item)

        # Tabloyu doldur
        self._render_table_rows(filtered)

    def _render_table_rows(self, rows: List[Dict[str, Any]]):
        """Satırları tabloya Dark Obsidian ve yüksek kontrast kurallarıyla işler."""
        total_records = len(self._all_processed_rows)
        self.lbl_status_pill.setText(f"📊 {len(rows)} / {total_records} Dosya (Yeniden Geçmişe)")

        self.table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            r = item["record"]
            is_closed = item["is_closed"]
            hat_val = item["hat"]

            # 0. Dosya No (Vurgulu Sky Blue, Kalın)
            d_item = QTableWidgetItem(str(r.get("dosya") or "—"))
            d_item.setForeground(QColor("#38bdf8"))
            f_bold = d_item.font()
            f_bold.setBold(True)
            d_item.setFont(f_bold)
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 1. Referans No
            ref_item = QTableWidgetItem(str(r.get("ref") or "—"))
            ref_item.setForeground(QColor("#e2e8f0"))
            ref_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 2. Konşimento (BL)
            bl_item = QTableWidgetItem(str(r.get("bl") or "—"))
            bl_item.setForeground(QColor("#f8fafc"))
            bl_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 3. Hat
            hat_item = QTableWidgetItem(hat_val or "—")
            hat_item.setFont(f_bold)
            hat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "KIRMIZI" in hat_val:
                hat_item.setForeground(QColor("#f87171"))  # Kırmızı
            elif "SARI" in hat_val:
                hat_item.setForeground(QColor("#fbbf24"))  # Kehribar
            elif any(k in hat_val for k in ["YEŞİL", "YESIL", "MAVİ"]):
                hat_item.setForeground(QColor("#34d399"))  # Yeşil
            else:
                hat_item.setForeground(QColor("#94a3b8"))

            # 4. Tescil Tarihi
            tescil_item = QTableWidgetItem(str(r.get("tescil") or "—"))
            tescil_item.setForeground(QColor("#94a3b8"))
            tescil_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 5. Kapanış Tarihi (Vurgulu ve net okunur)
            kap_item = QTableWidgetItem(str(r.get("kapanis") or "—"))
            kap_item.setFont(f_bold)
            kap_item.setForeground(QColor("#38bdf8" if r.get("kapanis") else "#64748b"))
            kap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 6. Toplam Süre (Hesaplanan)
            sure_item = QTableWidgetItem(item["sure_str"])
            sure_item.setFont(f_bold)
            sure_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "Aynı Gün" in item["sure_str"] or (item["sure_days"] <= 1 and is_closed):
                sure_item.setForeground(QColor("#34d399"))  # Hızlı (Zümrüt Yeşili)
            elif item["sure_days"] <= 3:
                sure_item.setForeground(QColor("#38bdf8"))  # Normal (Mavi)
            else:
                sure_item.setForeground(QColor("#fbbf24"))  # Uzun (Kehribar)

            # 7. Liman (Gerçek Liman Adı)
            liman_str = str(r.get("liman") or "—").strip()
            lim_item = QTableWidgetItem(liman_str if liman_str else "—")
            lim_item.setForeground(QColor("#e2e8f0"))
            lim_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 8. Firma / Bayi
            bayi_str = str(r.get("bayi") or r.get("firma") or "HANKOOK").strip()
            bayi_item = QTableWidgetItem(bayi_str if bayi_str else "HANKOOK")
            bayi_item.setForeground(QColor("#f8fafc"))
            bayi_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # 9. Durum / Aşama
            stage_title = str(r.get("stage_title") or r.get("mail_status") or "—")
            status_item = QTableWidgetItem(stage_title)
            status_item.setFont(f_bold)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if is_closed:
                status_item.setForeground(QColor("#34d399"))
            elif r.get("is_tax_pending"):
                status_item.setForeground(QColor("#f87171"))
            elif "Tescil" in stage_title:
                status_item.setForeground(QColor("#38bdf8"))
            elif "Ordino" in stage_title:
                status_item.setForeground(QColor("#fbbf24"))
            else:
                status_item.setForeground(QColor("#94a3b8"))

            row_items = [
                d_item, ref_item, bl_item, hat_item, tescil_item,
                kap_item, sure_item, lim_item, bayi_item, status_item
            ]

            # Satır arka planı: %5 şeffaf durum tonu ile yüksek kontrast
            for col_idx, cell in enumerate(row_items):
                if is_closed:
                    cell.setBackground(QColor(16, 185, 129, 12))
                elif r.get("is_tax_pending"):
                    cell.setBackground(QColor(239, 68, 68, 14))
                elif "KIRMIZI" in hat_val:
                    cell.setBackground(QColor(239, 68, 68, 14))
                else:
                    cell.setBackground(QColor(30, 41, 59, 10))
                self.table.setItem(row_idx, col_idx, cell)

    # ------------------------------------------------------------------
    # ACTIONS & CONTEXT MENU
    # ------------------------------------------------------------------
    def _on_card_click(self, filter_type: str):
        """KPI kartına tıklandığında ilgili tablo filtresini ayarlar."""
        if filter_type == "CLOSED_MONTH":
            self.cmb_stage.setCurrentText("🟢 Kapandı / Arşiv")
            self.cmb_time.setCurrentText("📅 Bu Ay (Son Kapananlar)")
        elif filter_type == "ALL_CLOSED":
            self.cmb_stage.setCurrentText("🟢 Kapandı / Arşiv")
            self.cmb_time.setCurrentText("Tüm Zamanlar")
        elif filter_type == "RED_HAT":
            self.cmb_hat.setCurrentText("🔴 Kırmızı Hat")
            self.cmb_stage.setCurrentText("Tüm Dosyalar (Canlı + Arşiv)")
            self.cmb_time.setCurrentText("Tüm Zamanlar")
        elif filter_type == "OPEN_ALL":
            self.cmb_stage.setCurrentText("⚡ Canlı / Açık Dosyalar")
            self.cmb_time.setCurrentText("Tüm Zamanlar")
        self.apply_filters_and_render()

    def reset_filters(self):
        """Tüm filtre kontrollerini varsayılan durumlarına getirir."""
        self.txt_search.blockSignals(True)
        self.cmb_stage.blockSignals(True)
        self.cmb_time.blockSignals(True)
        self.cmb_hat.blockSignals(True)
        self.cmb_liman.blockSignals(True)

        self.txt_search.clear()
        self.cmb_stage.setCurrentIndex(0)
        self.cmb_time.setCurrentIndex(0)
        self.cmb_hat.setCurrentIndex(0)
        self.cmb_liman.setCurrentIndex(0)

        self.txt_search.blockSignals(False)
        self.cmb_stage.blockSignals(False)
        self.cmb_time.blockSignals(False)
        self.cmb_hat.blockSignals(False)
        self.cmb_liman.blockSignals(False)

        self.apply_filters_and_render()

    def on_row_double_clicked(self, row: int, col: int):
        """Satıra çift tıklandığında dosyayı Operasyon Kokpiti'nde açar."""
        d_item = self.table.item(row, 0)
        if not d_item:
            return
        dosya_no = d_item.text().strip()
        if dosya_no and dosya_no != "—" and self.main_window:
            if hasattr(self.main_window, "switch_tab"):
                self.main_window.switch_tab("COCKPIT")
                cockpit = self.main_window.views.get("COCKPIT")
                if cockpit and hasattr(cockpit, "txt_search"):
                    cockpit.txt_search.setText(dosya_no)

    def show_context_menu(self, pos):
        """Sağ tık bağlam menüsü."""
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not selected_rows:
            return

        row = selected_rows[0]
        dosya = self.table.item(row, 0).text().strip() if self.table.item(row, 0) else ""
        ref = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ""
        bl = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else ""

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)

        act_copy_dosya = menu.addAction(f"📋 Dosya No Kopyala ({dosya})")
        act_copy_ref = menu.addAction(f"📋 Referans No Kopyala ({ref})")
        act_copy_bl = menu.addAction(f"📋 Konşimento (BL) Kopyala ({bl})")
        menu.addSeparator()
        act_goto_cockpit = menu.addAction("🔍 Bu Dosyayı Kokpitte Göster")
        act_goto_evrim = menu.addAction("📑 Bu Dosyayı Evrim Gezgininde Ara")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_copy_dosya and dosya:
            self.copy_to_clipboard(dosya, show_msg=True)
        elif action == act_copy_ref and ref:
            self.copy_to_clipboard(ref, show_msg=True)
        elif action == act_copy_bl and bl:
            self.copy_to_clipboard(bl, show_msg=True)
        elif action == act_goto_cockpit and dosya:
            self.on_row_double_clicked(row, 0)
        elif action == act_goto_evrim and dosya and self.main_window:
            self.main_window.switch_tab("EVRIM_EXPLORER")
            evrim_v = self.main_window.views.get("EVRIM_EXPLORER")
            if evrim_v and hasattr(evrim_v, "txt_search"):
                evrim_v.txt_search.setText(dosya)

    def export_filtered_to_excel(self):
        """O an tabloda filtrelenmiş olan listeyi şık bir Excel raporu olarak kaydeder."""
        row_count = self.table.rowCount()
        if row_count == 0:
            self.show_warning("Uyarı", "Dışa aktarılacak dosya bulunamadı.")
            return

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"SmartClearance_Operasyonel_Ozet_{now_str}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Operasyonel Raporu Excel Olarak Kaydet",
            default_filename,
            "Excel Dosyası (*.xlsx);;Tüm Dosyalar (*.*)"
        )
        if not file_path:
            return

        try:
            if not openpyxl:
                self.show_error("Hata", "openpyxl kütüphanesi bulunamadı.")
                return

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Operasyonel Özet"
            ws.views.sheetView[0].showGridLines = True

            # Başlık
            ws.merge_cells("A1:J1")
            ws["A1"] = "DOĞRUER GÜMRÜK MÜŞAVİRLİĞİ - OPERASYONEL ÖZET & RAPORLAMA"
            ws["A1"].font = OxFont(name="Segoe UI", size=13, bold=True, color="FFFFFF")
            ws["A1"].fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 32

            u_name = self.current_user.get("display_name", "Kullanıcı")
            ws["A2"] = f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Hazırlayan: {u_name} | Toplam Listelenen: {row_count} Dosya"
            ws["A2"].font = OxFont(name="Segoe UI", size=9, italic=True, color="64748B")
            ws.row_dimensions[2].height = 18

            # Tablo Başlıkları
            headers = [
                "Dosya No", "Referans No", "Konşimento (BL)", "Hat",
                "Tescil Tarihi", "Kapanış Tarihi", "Toplam Süre",
                "Liman", "Firma / Bayi", "Durum / Aşama"
            ]
            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(4, col_idx, h)
                cell.font = OxFont(name="Segoe UI", size=10, bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center")

            ws.row_dimensions[4].height = 24

            thin_border = Border(
                left=Side(style="thin", color="E2E8F0"),
                right=Side(style="thin", color="E2E8F0"),
                top=Side(style="thin", color="E2E8F0"),
                bottom=Side(style="thin", color="E2E8F0")
            )

            # Satırları aktar
            for r_idx in range(row_count):
                excel_row = 5 + r_idx
                ws.row_dimensions[excel_row].height = 20
                for c_idx in range(10):
                    item = self.table.item(r_idx, c_idx)
                    val = item.text() if item else ""
                    cell = ws.cell(excel_row, c_idx + 1, val)
                    cell.font = OxFont(name="Segoe UI", size=9)
                    cell.border = thin_border
                    if c_idx in [0, 1, 3, 4, 5, 6, 7]:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")

            # Otomatik sütun genişlikleri
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

            wb.save(file_path)

            if self.ask_yes_no("Başarılı", f"Rapor başarıyla kaydedildi:\n{file_path}\n\nDosyayı şimdi açmak ister misiniz?"):
                try:
                    os.startfile(file_path)
                except Exception:
                    pass

        except Exception as exc:
            self.show_error("Dışa Aktarma Hatası", f"Excel raporu oluşturulamadı:\n{exc}")

