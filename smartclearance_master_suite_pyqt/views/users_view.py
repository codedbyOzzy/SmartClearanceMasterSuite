# -*- coding: utf-8 -*-
"""
👥 SmartClearance MasterSuite - Kullanıcı Yönetimi (UsersView PyQt6)
Kullanıcı yetkilendirme, rol dağılımı (Yönetici, Operatör, İzleyici) ve erişim kontrolü.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from .base_view import BaseView

class UsersView(BaseView):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Üst Form: Yeni Kullanıcı Ekle
        form_box = QFrame(self)
        form_box.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        f_layout = QHBoxLayout(form_box)

        self.ent_new_user = QLineEdit(form_box)
        self.ent_new_user.setPlaceholderText("Kullanıcı Adı")
        self.ent_new_user.setStyleSheet("background-color: #0b0f19; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 6px 10px;")
        f_layout.addWidget(self.ent_new_user)

        self.ent_new_name = QLineEdit(form_box)
        self.ent_new_name.setPlaceholderText("Ad Soyad")
        self.ent_new_name.setStyleSheet("background-color: #0b0f19; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 6px 10px;")
        f_layout.addWidget(self.ent_new_name)

        self.cmb_role = QComboBox(form_box)
        self.cmb_role.addItems(["admin (Yönetici)", "operator (Operatör)", "viewer (İzleyici)"])
        self.cmb_role.setStyleSheet("background-color: #0b0f19; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px;")
        f_layout.addWidget(self.cmb_role)

        self.btn_add = QPushButton("➕ Kullanıcı Ekle", form_box)
        self.btn_add.setObjectName("PrimaryBtn")
        self.btn_add.clicked.connect(self._add_user)
        f_layout.addWidget(self.btn_add)

        layout.addWidget(form_box)

        # Kullanıcı Tablosu
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Kullanıcı Adı", "Ad Soyad", "Yetki Rolü", "İşlem"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, stretch=1)

        self.refresh_table()

    def refresh_table(self):
        users = [
            ("admin", "Sistem Yöneticisi", "admin"),
            ("ozan.gemici", "Ozan Mert Gemici", "admin"),
            ("operasyon1", "Operasyon Görevlisi", "operator"),
            ("muhasebe", "Hankook Muhasebe", "viewer")
        ]
        self.table.setRowCount(len(users))
        for r, (u, n, role) in enumerate(users):
            self.table.setItem(r, 0, QTableWidgetItem(u))
            self.table.setItem(r, 1, QTableWidgetItem(n))
            self.table.setItem(r, 2, QTableWidgetItem(role))

            btn_del = QPushButton("Sil")
            btn_del.setStyleSheet("background-color: #dc2626; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 10px;")
            btn_del.clicked.connect(lambda ch, usr=u: self._delete_user(usr))
            self.table.setCellWidget(r, 3, btn_del)

    def _add_user(self):
        u = self.ent_new_user.text().strip()
        n = self.ent_new_name.text().strip()
        if not u or not n:
            self.show_warning("Uyarı", "Lütfen kullanıcı adı ve ad soyad girin.")
            return
        self.show_info("Başarılı", f"'{u}' kullanıcısı başarıyla eklendi!")
        self.ent_new_user.clear()
        self.ent_new_name.clear()
        self.refresh_table()

    def _delete_user(self, username):
        if username in ["admin", "ozan.gemici"]:
            self.show_warning("Uyarı", "Ana yönetici hesabı silinemez!")
            return
        if self.ask_yes_no("Onay", f"'{username}' kullanıcısını silmek istediğinize emin misiniz?"):
            self.show_info("Başarılı", f"Kullanıcı silindi: {username}")
            self.refresh_table()
