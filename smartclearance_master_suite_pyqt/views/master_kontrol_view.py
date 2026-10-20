# -*- coding: utf-8 -*-
"""
🔍 SmartClearance MasterSuite - Master Data Kontrol & GTİP Denetimi (PyQt6)
Ürün kataloğu karşılaştırması, GTİP ve Türkçe tanım çapraz denetim merkezi.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from .base_view import BaseView
from ..components.metric_card import MetricCard

class MasterKontrolView(BaseView):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Kartlar
        cards = QHBoxLayout()
        self.card_total = MetricCard("DENETLENEN ÜRÜN", "1,240", "Master Katalog", "#1e3a8a", self)
        cards.addWidget(self.card_total)
        self.card_ok = MetricCard("UYUMLU GTİP", "1,228", "%99 Doğruluk", "#16a34a", self)
        cards.addWidget(self.card_ok)
        self.card_mismatch = MetricCard("UYUMSUZ / EKSİK", "12", "İnceleme Gereken", "#dc2626", self)
        cards.addWidget(self.card_mismatch)
        layout.addLayout(cards)

        # Arama
        bar = QFrame(self)
        bar.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        b_layout = QHBoxLayout(bar)
        lbl_s = QLabel("🔍 Ürün Kodu / GTİP Ara:", bar)
        lbl_s.setStyleSheet("color: #38bdf8; font-weight: 700;")
        b_layout.addWidget(lbl_s)
        self.txt_search = QLineEdit(bar)
        self.txt_search.setPlaceholderText("Ürün kodu veya parça adı...")
        self.txt_search.setStyleSheet("background-color: #0b0f19; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 6px 10px;")
        self.txt_search.textChanged.connect(self.refresh_table)
        b_layout.addWidget(self.txt_search, stretch=1)

        btn_check = QPushButton("⚡ Çapraz Denetimi Çalıştır", bar)
        btn_check.setObjectName("PrimaryBtn")
        btn_check.clicked.connect(self.refresh_table)
        b_layout.addWidget(btn_check)
        layout.addWidget(bar)

        # Tablo
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Ürün Kodu", "Orijinal Tanım", "Master GTİP", "Evrak GTİP", "Durum", "Denetim Sonucu"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, stretch=1)

        self.refresh_table()

    def refresh_table(self):
        sample = [
            ("HK-2055516-V", "VENTUS PRIME 4 205/55R16", "4011.10.00.00.00", "4011.10.00.00.00", "UYUMLU", "Birebir Eşleşti"),
            ("HK-2254517-K", "Kinergy Eco 2 225/45R17", "4011.10.00.00.00", "4011.10.00.00.00", "UYUMLU", "Birebir Eşleşti"),
            ("HK-3158022-A", "SmartFlex AH31 315/80R22.5", "4011.20.90.00.00", "4011.20.10.00.00", "FARKLI", "Alt Tarife Uyuşmazlığı"),
            ("HK-1956515-W", "Winter i*cept RS3 195/65R15", "4011.10.00.00.00", "4011.10.00.00.00", "UYUMLU", "Birebir Eşleşti"),
        ]
        q = self.txt_search.text().strip().upper()
        filtered = [x for x in sample if not q or q in f"{x[0]} {x[1]} {x[2]}".upper()]

        self.table.setRowCount(len(filtered))
        for r, row in enumerate(filtered):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                if val == "FARKLI":
                    item.setForeground(QColor("#dc2626"))
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                elif val == "UYUMLU":
                    item.setForeground(QColor("#16a34a"))
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table.setItem(r, c, item)
