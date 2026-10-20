# -*- coding: utf-8 -*-
"""
📊 SmartClearance MasterSuite - Modern KPI Metrik Kartı (PyQt6)
Tıklanabilir, renkli üst şeritli, canlı sayaçlı kart bileşeni.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

class MetricCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title, val, subtitle, accent_color="#1e3a8a", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.accent_color = accent_color
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 10)
        layout.setSpacing(4)

        # Üst renkli şerit
        self.top_strip = QWidget(self)
        self.top_strip.setFixedHeight(4)
        self.top_strip.setStyleSheet(f"background-color: {accent_color}; border-top-left-radius: 4px; border-top-right-radius: 4px;")
        layout.addWidget(self.top_strip)

        # Başlık
        self.lbl_title = QLabel(title, self)
        self.lbl_title.setObjectName("MetricCardTitle")
        layout.addWidget(self.lbl_title)

        # Büyük Sayı Değeri
        self.lbl_val = QLabel(str(val), self)
        self.lbl_val.setObjectName("MetricCardValue")
        self.lbl_val.setStyleSheet(f"color: {accent_color};")
        layout.addWidget(self.lbl_val)

        # Alt Başlık
        self.lbl_subtitle = QLabel(subtitle, self)
        self.lbl_subtitle.setObjectName("MetricCardSubtitle")
        layout.addWidget(self.lbl_subtitle)

    def set_value(self, val):
        self.lbl_val.setText(str(val))

    def set_subtitle(self, text):
        self.lbl_subtitle.setText(str(text))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
