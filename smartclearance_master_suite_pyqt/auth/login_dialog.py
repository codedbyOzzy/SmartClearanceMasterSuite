# -*- coding: utf-8 -*-
"""
🛡️ SmartClearance MasterSuite - Modern Kullanıcı Giriş & Şifre Değiştirme (PyQt6)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
"""

import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor

# Root directory import guard
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

try:
    from tools.auth_manager import get_auth_manager
except Exception:
    get_auth_manager = None


class PyQtLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth = get_auth_manager() if get_auth_manager else None
        self.authenticated_user = None

        self.setWindowTitle("Giriş Yap — Doğruer MasterSuite")
        self.setFixedSize(420, 530)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #090d16;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 0px 14px;
                min-height: 42px;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit:focus {
                border: 1.5px solid #38bdf8;
                background-color: #0d1527;
            }
            QPushButton#LoginBtn {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                min-height: 44px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#LoginBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#LoginBtn:pressed {
                background-color: #1e40af;
            }
            QPushButton#EyeBtn {
                background-color: #090d16;
                color: #94a3b8;
                border: 1px solid #334155;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                min-height: 42px;
                min-width: 42px;
                font-size: 16px;
            }
            QPushButton#EyeBtn:hover {
                color: #ffffff;
                background-color: #1e293b;
            }
            QCheckBox {
                color: #94a3b8;
                font-size: 12px;
                min-height: 26px;
                spacing: 8px;
            }
            QCheckBox:hover {
                color: #cbd5e1;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #090d16;
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #2563eb;
            }
        """)

        self._build_ui()
        self._check_remembered()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        # Başlık ve Logo
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel("⚡", self)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 38px; color: #38bdf8;")
        title_box.addWidget(lbl_icon)

        lbl_title = QLabel("SmartClearance MasterSuite", self)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        title_box.addWidget(lbl_title)

        lbl_sub = QLabel("Doğruer Gümrük Müşavirliği A.Ş. — Kullanıcı Girişi", self)
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("font-size: 10px; color: #94a3b8;")
        title_box.addWidget(lbl_sub)

        layout.addLayout(title_box)
        layout.addSpacing(10)

        # Kart konteyneri
        card = QFrame(self)
        card.setStyleSheet("background-color: #1e293b; border-radius: 12px;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 20, 18, 20)
        card_layout.setSpacing(12)

        # Kullanıcı Adı
        lbl_u = QLabel("Kullanıcı Adı", card)
        lbl_u.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 700;")
        card_layout.addWidget(lbl_u)

        self.ent_user = QLineEdit(card)
        self.ent_user.setPlaceholderText("Kullanıcı adınızı girin...")
        card_layout.addWidget(self.ent_user)

        # Şifre
        lbl_p = QLabel("Şifre", card)
        lbl_p.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 700;")
        card_layout.addWidget(lbl_p)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)
        self.ent_pass = QLineEdit(card)
        self.ent_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ent_pass.setPlaceholderText("Şifrenizi girin...")
        self.ent_pass.setStyleSheet("border-top-right-radius: 0px; border-bottom-right-radius: 0px; border-right: none;")
        pass_row.addWidget(self.ent_pass)

        self.btn_eye = QPushButton("👁️", card)
        self.btn_eye.setObjectName("EyeBtn")
        self.btn_eye.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_eye.clicked.connect(self._toggle_password)
        pass_row.addWidget(self.btn_eye)
        card_layout.addLayout(pass_row)

        # Beni Hatırla
        self.chk_remember = QCheckBox("Beni Hatırla (Oturumu Açık Tut)", card)
        self.chk_remember.setChecked(True)
        card_layout.addWidget(self.chk_remember)

        layout.addWidget(card)

        # Durum / Hata etiketi
        self.lbl_status = QLabel("", self)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.lbl_status)

        # Giriş Butonu
        self.btn_login = QPushButton("Giriş Yap", self)
        self.btn_login.setObjectName("LoginBtn")
        self.btn_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_login.clicked.connect(self._on_login)
        layout.addWidget(self.btn_login)

        self.ent_pass.returnPressed.connect(self._on_login)
        self.ent_user.returnPressed.connect(lambda: self.ent_pass.setFocus())

    def _toggle_password(self):
        if self.ent_pass.echoMode() == QLineEdit.EchoMode.Password:
            self.ent_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_eye.setText("🔒")
        else:
            self.ent_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_eye.setText("👁️")

    def _check_remembered(self):
        if not self.auth:
            return
        session = getattr(self.auth, "get_saved_session", lambda: None)()
        if session and session.get("username"):
            self.ent_user.setText(session["username"])
            self.ent_pass.setFocus()
        elif hasattr(self.auth, "users") and len(self.auth.users) == 1 and self.auth.users[0].get("username") == "admin":
            self.ent_user.setText("admin")
            self.ent_pass.setFocus()
        else:
            self.ent_user.setFocus()

    def _on_login(self):
        u = self.ent_user.text().strip()
        p = self.ent_pass.text()

        if not u or not p:
            self.lbl_status.setText("Lütfen kullanıcı adı ve şifrenizi girin.")
            return

        self.btn_login.setEnabled(False)
        self.lbl_status.setText("Doğrulanıyor...")

        if not self.auth:
            # Fallback admin hesabı
            if u.lower() == "admin" and p == "123456":
                self.authenticated_user = {"username": "admin", "display_name": "Sistem Yöneticisi", "role": "admin"}
                self.accept()
                return
            else:
                self.lbl_status.setText("Hatalı kullanıcı adı veya şifre!")
                self.btn_login.setEnabled(True)
                return

        ok, msg, user = self.auth.login(u, p, remember_me=self.chk_remember.isChecked())
        if ok and user:
            # Eğer varsayılan şifre ("123456") ise veya must_change_password bayrağı varsa şifre değiştirme zorunlu
            if p == "123456" or user.get("must_change_password"):
                pwd_dlg = PyQtChangePasswordDialog(user.get("username", u), parent=self)
                if pwd_dlg.exec() != QDialog.DialogCode.Accepted:
                    self.lbl_status.setText("İlk girişte varsayılan şifreyi değiştirmeniz zorunludur.")
                    self.btn_login.setEnabled(True)
                    return
                user = getattr(self.auth, "current_user", user) or user

            self.authenticated_user = user
            self.accept()
        else:
            self.lbl_status.setText(msg or "Hatalı kullanıcı adı veya şifre!")
            self.btn_login.setEnabled(True)
            self.ent_pass.clear()
            self.ent_pass.setFocus()


class PyQtChangePasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.auth = get_auth_manager() if get_auth_manager else None

        self.setWindowTitle("Şifre Değiştir — Doğruer MasterSuite")
        self.setFixedSize(380, 360)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #ffffff; }
            QLineEdit {
                background-color: #090d16; color: #ffffff;
                border: 1px solid #334155; border-radius: 6px;
                padding: 8px 12px; font-size: 12px;
            }
            QPushButton#ActionBtn {
                background-color: #2563eb; color: #ffffff;
                font-weight: 700; border-radius: 6px; padding: 10px; border: none;
            }
            QPushButton#ActionBtn:hover { background-color: #1d4ed8; }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        lbl_t = QLabel(f"🔑 Şifre Değiştir ({self.username})", self)
        lbl_t.setStyleSheet("font-size: 15px; font-weight: 800; color: #38bdf8;")
        layout.addWidget(lbl_t)

        layout.addWidget(QLabel("Mevcut Şifre:", self))
        self.ent_old = QLineEdit(self)
        self.ent_old.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.ent_old)

        layout.addWidget(QLabel("Yeni Şifre (En az 8 karakter):", self))
        self.ent_new1 = QLineEdit(self)
        self.ent_new1.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.ent_new1)

        layout.addWidget(QLabel("Yeni Şifre Tekrar:", self))
        self.ent_new2 = QLineEdit(self)
        self.ent_new2.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.ent_new2)

        layout.addSpacing(8)
        self.btn_save = QPushButton("Şifreyi Güncelle", self)
        self.btn_save.setObjectName("ActionBtn")
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_save)

    def _on_save(self):
        old_p = self.ent_old.text()
        n1 = self.ent_new1.text()
        n2 = self.ent_new2.text()

        if not old_p or not n1 or not n2:
            QMessageBox.warning(self, "Uyarı", "Lütfen tüm alanları doldurun.")
            return
        if n1 != n2:
            QMessageBox.warning(self, "Hata", "Yeni şifreler birbiriyle uyuşmuyor!")
            return
        if len(n1) < 8:
            QMessageBox.warning(self, "Hata", "Yeni şifre en az 8 karakter olmalıdır!")
            return

        if self.auth:
            ok, msg = self.auth.change_own_password(self.username, old_p, n1)
            if ok:
                QMessageBox.information(self, "Başarılı", "Şifreniz başarıyla güncellendi!")
                self.accept()
            else:
                QMessageBox.critical(self, "Hata", msg or "Şifre güncellenemedi.")
        else:
            QMessageBox.information(self, "Bilgi", "Şifre güncellendi (Demo mod).")
            self.accept()


def prompt_login_dialog(force_prompt: bool = False):
    """Beni Hatırla oturumunu kontrol eder veya giriş penceresini açar."""
    auth = get_auth_manager() if get_auth_manager else None
    if auth and not force_prompt:
        saved_user = auth.get_saved_session()
        if saved_user:
            return saved_user
    dlg = PyQtLoginDialog()
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.authenticated_user
    return None
