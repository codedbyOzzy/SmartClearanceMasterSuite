# -*- coding: utf-8 -*-
"""
📌 SmartClearance MasterSuite - Modern Sol Navigasyon Menüsü (PyQt6)
Daraltılabilir, kategorili, ikonlu ve kullanıcı profilli modern kenar çubuğu.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt

class MasterSuiteSidebar(QWidget):
    tab_changed = pyqtSignal(str)
    change_password_requested = pyqtSignal()
    logout_requested = pyqtSignal()

    MENU_ITEMS = [
        # (Category, [ (code, title, icon) ])
        ("GÜMRÜK OPERASYONLARI", [
            ("COCKPIT", "Operasyon Kokpiti", "📊"),
            ("AI_ASSISTANT", "Gemini AI Danışmanı", "🧠"),
            ("APEX", "Hankook Apex Masası", "🚀"),
            ("HORIZON", "Horizon Konteyner Radarı", "🌐"),
            ("ACTIVITY_HUB", "İşlem & Not Günlüğü", "📋"),
            ("EXCEL_AKTARIM", "Excel Aktarım", "📑"),
            ("RPA_STATION", "Otonom RPA İstasyonu", "🤖"),
            ("MASTER_KONTROL", "Master Data Kontrol", "🔍"),
            ("GTB_TAKIP", "GTB Beyanname Takip", "🏛️"),
            ("KANTAR_TAKIP", "Kantar & DBA Takip", "⚖️"),
            ("ETA_YAKLASANLAR", "ETA Yaklaşanlar", "⏳"),
            ("EVRIM_EXPLORER", "Evrim Veri Merkezi", "💾"),
            ("SHIELD", "Akıllı Konuşma Gezgini", "💬"),
        ]),
        ("ENTEGRE PORTALLAR", [
            ("QNB_PORTAL", "QNB eSolutions", "📦"),
            ("GLP_PORTAL", "Hankook GLP Portalı", "🚢"),
            ("DOGRUER_PORTAL", "Doğruer Online", "🏢"),
            ("TALEP", "Finansal Talepler", "💰"),
        ]),
        ("YÖNETİM & AYARLAR", [
            ("SUMMARY", "Operasyonel Özet", "📈"),
            ("SETTINGS", "Sistem Ayarları", "⚙️"),
            ("USERS", "Kullanıcı Yönetimi", "👥"),
        ])
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(225)
        self.is_collapsed = False
        self.current_tab = "COCKPIT"
        self.nav_buttons = {}

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Logo ve Marka Başlığı
        brand_box = QWidget(self)
        brand_box.setFixedHeight(60)
        brand_layout = QHBoxLayout(brand_box)
        brand_layout.setContentsMargins(16, 12, 16, 12)
        brand_layout.setSpacing(8)

        self.lbl_brand = QLabel("SmartClearance", brand_box)
        self.lbl_brand.setObjectName("SidebarBrand")
        brand_layout.addWidget(self.lbl_brand)

        self.lbl_ver = QLabel("v5.5 PRO", brand_box)
        self.lbl_ver.setObjectName("SidebarVersion")
        brand_layout.addWidget(self.lbl_ver)
        brand_layout.addStretch()

        main_layout.addWidget(brand_box)

        # 2. Menüyü Daralt Butonu
        toggle_box = QWidget(self)
        toggle_layout = QHBoxLayout(toggle_box)
        toggle_layout.setContentsMargins(12, 0, 12, 6)
        self.btn_toggle = QPushButton("◀ Menüyü Daralt", toggle_box)
        self.btn_toggle.setObjectName("SidebarToggleBtn")
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        toggle_layout.addWidget(self.btn_toggle)
        main_layout.addWidget(toggle_box)

        # 3. Kaydırılabilir Menü Alanı
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent;")

        menu_container = QWidget()
        menu_container.setStyleSheet("background-color: transparent;")
        self.menu_layout = QVBoxLayout(menu_container)
        self.menu_layout.setContentsMargins(0, 6, 0, 6)
        self.menu_layout.setSpacing(2)

        self.category_labels = []

        for cat_title, items in self.MENU_ITEMS:
            cat_lbl = QLabel(cat_title, menu_container)
            cat_lbl.setObjectName("SidebarCategory")
            self.menu_layout.addWidget(cat_lbl)
            self.category_labels.append(cat_lbl)

            for code, title, icon in items:
                btn = QPushButton(f"{icon}  {title}", menu_container)
                btn.setObjectName("SidebarNavBtn")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, c=code: self._on_btn_clicked(c))
                self.menu_layout.addWidget(btn)
                self.nav_buttons[code] = (btn, title, icon)

        self.menu_layout.addStretch()
        scroll.setWidget(menu_container)
        main_layout.addWidget(scroll)

        # 4. Alt Kullanıcı Profili ve Çıkış Kutusu
        self.user_box = QWidget(self)
        self.user_box.setObjectName("SidebarUserBox")
        user_layout = QVBoxLayout(self.user_box)
        user_layout.setContentsMargins(8, 8, 8, 8)
        user_layout.setSpacing(6)

        self.lbl_user_name = QLabel("Ozan Mert Gemici", self.user_box)
        self.lbl_user_name.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 11px;")
        user_layout.addWidget(self.lbl_user_name)

        self.lbl_user_role = QLabel("🛡️ Yönetici", self.user_box)
        self.lbl_user_role.setStyleSheet("color: #94a3b8; font-size: 9px;")
        user_layout.addWidget(self.lbl_user_role)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_change_pass = QPushButton("Şifre", self.user_box)
        self.btn_change_pass.setStyleSheet("background-color: #161d2a; color: #cbd5e1; border: 1px solid #283449; border-radius: 4px; font-size: 10px; font-weight: 600; padding: 4px 8px;")
        self.btn_change_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_change_pass.clicked.connect(self.change_password_requested.emit)
        btn_row.addWidget(self.btn_change_pass)

        self.btn_logout = QPushButton("Çıkış", self.user_box)
        self.btn_logout.setStyleSheet("background-color: #241419; color: #f87171; border: 1px solid #421822; border-radius: 4px; font-size: 10px; font-weight: 600; padding: 4px 8px;")
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        btn_row.addWidget(self.btn_logout)
        user_layout.addLayout(btn_row)

        self.lbl_live_status = QLabel("● Canlı İzleme (Excel & Outlook)", self.user_box)
        self.lbl_live_status.setStyleSheet("color: #10b981; font-size: 9px; font-weight: 600; margin-top: 4px;")
        user_layout.addWidget(self.lbl_live_status)

        main_layout.addWidget(self.user_box)

        # Varsayılan sekme seç
        self.update_active_tab("COCKPIT")

    def _on_btn_clicked(self, code):
        self.update_active_tab(code)
        self.tab_changed.emit(code)

    def update_active_tab(self, code):
        self.current_tab = code
        for c, (btn, title, icon) in self.nav_buttons.items():
            is_active = (c == code)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def toggle_collapse(self, manual=True):
        if manual:
            self._manually_expanded = self.is_collapsed
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(64)
            self.btn_toggle.setText("▶")
            self.lbl_brand.setVisible(False)
            self.lbl_ver.setVisible(False)
            for lbl in self.category_labels:
                lbl.setVisible(False)
            for c, (btn, title, icon) in self.nav_buttons.items():
                btn.setText(icon)
                btn.setToolTip(title)
            self.user_box.setVisible(False)
        else:
            self.setFixedWidth(225)
            self.btn_toggle.setText("◀ Menüyü Daralt")
            self.lbl_brand.setVisible(True)
            self.lbl_ver.setVisible(True)
            for lbl in self.category_labels:
                lbl.setVisible(True)
            for c, (btn, title, icon) in self.nav_buttons.items():
                btn.setText(f"{icon}  {title}")
                btn.setToolTip("")
            self.user_box.setVisible(True)

    def adapt_to_screen(self, screen=None):
        """Laptop ekranında dar alanda yer açmak için akıllı sidebar adaptasyonu."""
        if not screen:
            screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        if avail.width() < 1350 and not self.is_collapsed and not getattr(self, "_manually_expanded", False):
            self.toggle_collapse(manual=False)

    def set_user_info(self, name, role):
        self.lbl_user_name.setText(name or "Kullanıcı")
        self.lbl_user_role.setText(f"🛡️ {role or 'Personel'}")
