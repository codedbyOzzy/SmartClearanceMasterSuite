# -*- coding: utf-8 -*-
"""
📶 SmartClearance MasterSuite - Modern Durum Çubuğu (PyQt6)
Canlı servis nabızları (GTB, Kantar, Telegram) ve sistem sağlık durumu göstergesi.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal

class MasterSuiteStatusBar(QWidget):
    health_report_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBarWidget")
        self.setFixedHeight(30)
        self.setStyleSheet("background-color: #090d16; border-top: 1px solid #1e293b;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 2, 14, 2)
        layout.setSpacing(16)

        self.lbl_title = QLabel("CANLILIK:", self)
        self.lbl_title.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 10px;")
        layout.addWidget(self.lbl_title)

        self.lbl_gtb = QLabel("🟢 GTB Takip: Aktif", self)
        self.lbl_gtb.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        layout.addWidget(self.lbl_gtb)

        self.lbl_kantar = QLabel("🟢 Kantar & DBA: Aktif", self)
        self.lbl_kantar.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        layout.addWidget(self.lbl_kantar)

        self.lbl_telegram = QLabel("🟢 Telegram Bot: Aktif", self)
        self.lbl_telegram.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        layout.addWidget(self.lbl_telegram)

        layout.addStretch()

        self.btn_health = QPushButton("🩺 Servis Sağlık Raporu", self)
        self.btn_health.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #38bdf8;
                border: none;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: #7dd3fc;
                text-decoration: underline;
            }
        """)
        self.btn_health.clicked.connect(self.health_report_requested.emit)
        layout.addWidget(self.btn_health)

    def set_service_status(self, service, is_ok, text):
        lbl = None
        if service == "gtb": lbl = self.lbl_gtb
        elif service == "kantar": lbl = self.lbl_kantar
        elif service == "telegram": lbl = self.lbl_telegram

        if lbl:
            icon = "🟢" if is_ok else "🔴"
            lbl.setText(f"{icon} {text}")
            lbl.setStyleSheet(f"color: {'#cbd5e1' if is_ok else '#f87171'}; font-size: 10px;")
