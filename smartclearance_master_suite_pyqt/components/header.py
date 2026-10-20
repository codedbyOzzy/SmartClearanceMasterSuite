# -*- coding: utf-8 -*-
"""
🏛️ SmartClearance MasterSuite - Modern Üst Başlık Barı (PyQt6)
Dinamik sayfa başlığı, alt başlık ve hızlı aksiyon butonları (Excel Aç, Şimdi Yenile).
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt

class MasterSuiteHeader(QWidget):
    refresh_requested = pyqtSignal()
    open_excel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(58)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(12)

        # Sol taraf: Başlık & Alt Başlık
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.lbl_title = QLabel("📊 MERKEZİ OPERASYON KONTROL PANELİ", self)
        self.lbl_title.setObjectName("HeaderTitle")
        title_box.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel("Tüm aktif dosyaların gümrük tescil ve Outlook vergi mail durumları", self)
        self.lbl_subtitle.setObjectName("HeaderSubtitle")
        title_box.addWidget(self.lbl_subtitle)

        layout.addLayout(title_box)
        layout.addStretch()

        # Sağ taraf: Aksiyon Butonları
        self.btn_open_excel = QPushButton("Excel Dosyasını Aç", self)
        self.btn_open_excel.setObjectName("ExcelBtn")
        self.btn_open_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_excel.clicked.connect(self.open_excel_requested.emit)
        layout.addWidget(self.btn_open_excel)

        self.btn_refresh = QPushButton("Şimdi Senkronize Et", self)
        self.btn_refresh.setObjectName("PrimaryBtn")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.btn_refresh)

    def set_titles(self, title, subtitle):
        self.lbl_title.setText(title)
        self.lbl_subtitle.setText(subtitle)
