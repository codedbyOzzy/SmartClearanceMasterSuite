# -*- coding: utf-8 -*-
"""
⚙️ SmartClearance MasterSuite - Sistem Ayarları (SettingsView PyQt6)
Koyu (Dark Obsidian) Temalı, Tam Fonksiyonel Sistem ve Entegrasyon Yapılandırması:
1. Excel ve PDF Dizinleri (Gözat ve Klasörü Aç)
2. E-Posta Alıcı ve Bilgi (CC) Listeleri
3. 3 Portal Kimlik ve Otomatik Doldurma Bilgileri (QNB, GLP, Doğruer Online)
4. 2FA Mail OTP (Aktivasyon Kodu Okuyucu) ve IMAP Test Motoru
5. Telegram Mobil Asistanı (@scMASTERSUITbot) Açma ve Test Bildirimi
6. Windows Masaüstü Balon / Toast Bildirimleri ve Test Gönderimi
7. Tüm Ayarları Kaydet ve Varsayılana Dön Butonları
"""

import os
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFileDialog, QScrollArea,
    QFrame, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .base_view import BaseView
from tools.dogruer_master_suite.engine import (
    DEFAULT_CONFIG, load_app_config, save_app_config
)


class ImapTestWorker(QThread):
    """IMAP / Outlook 2FA bağlantısını arka planda test eden iş parçacığı."""
    test_finished = pyqtSignal(bool, str)

    def run(self):
        try:
            from tools.dogruer_online_bridge.evrim_imap_reader import EvrimImapReader
            reader = EvrimImapReader()
            ok, msg = reader.test_connection()
            self.test_finished.emit(ok, msg)
        except Exception as e:
            self.test_finished.emit(False, f"Bağlantı hatası: {e}")


class SettingsView(BaseView):
    """Sistem Ayarları ve Entegrasyon Yapılandırma Görünümü (PyQt6 - Dark Obsidian)"""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self._imap_worker = None
        self._build_ui()

    def on_activate(self):
        """Sekmeye geçildiğinde güncel ayarları yükle."""
        self.load_settings_into_ui()

    def on_deactivate(self):
        """Sekmeden çıkılırken ayarları sessizce kaydet."""
        self._silent_save_settings_from_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Üst Başlık ve Açıklama Bandı
        header_widget = QWidget(self)
        h_layout = QVBoxLayout(header_widget)
        h_layout.setContentsMargins(4, 0, 4, 6)
        h_layout.setSpacing(2)

        lbl_title = QLabel("⚙️ SİSTEM VE ENTEGRASYON AYARLARI", header_widget)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        h_layout.addWidget(lbl_title)

        lbl_sub = QLabel(
            "Excel yolları, PDF arşiv dizinleri, portal kimlikleri, 2FA e-posta okuyucu ve mobil bildirim tercihleri.",
            header_widget
        )
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        h_layout.addWidget(lbl_sub)

        layout.addWidget(header_widget)

        # Kaydırılabilir Alan
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(4, 4, 12, 16)
        c_layout.setSpacing(14)

        # ── 1. KART: EXCEL DOSYA YOLU & PDF KLASÖRÜ ─────────────────────────────
        card_dirs = QFrame(content)
        card_dirs.setStyleSheet(self._card_qss())
        cd_layout = QVBoxLayout(card_dirs)
        cd_layout.setSpacing(10)

        lbl_cd_title = QLabel("📁 EXCEL VE PDF DOSYA DİZİNLERİ", card_dirs)
        lbl_cd_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8;")
        cd_layout.addWidget(lbl_cd_title)

        # Excel Yolu
        cd_layout.addWidget(self._make_label("📊 İş Takip Raporu (Excel Dosyası):", bold=True))
        cd_layout.addWidget(self._make_sub_label("Sistemin gümrük tescil, ordino, tareks ve beyanname aşamalarını anlık okuduğu ana Excel dosyası."))
        row_e = QHBoxLayout()
        self.txt_set_excel = self._make_line_edit("Excel dosya yolu...")
        row_e.addWidget(self.txt_set_excel, stretch=1)

        btn_browse_excel = self._make_btn("📁 Dosya Seç...", self.browse_excel_path)
        row_e.addWidget(btn_browse_excel)

        btn_open_excel_dir = self._make_btn("📂 Klasörü Aç", lambda: self.open_folder_of_file(self.txt_set_excel.text()))
        row_e.addWidget(btn_open_excel_dir)
        cd_layout.addLayout(row_e)

        # Ayırıcı Çizgi
        cd_layout.addWidget(self._make_separator())

        # PDF Klasörü
        cd_layout.addWidget(self._make_label("📁 Otomatik Vergi Maili PDF Klasörü (Kapanan / Hazır PDF'ler):", bold=True))
        cd_layout.addWidget(self._make_sub_label("Tek tıkla veya toplu vergi maili oluşturulurken beyanname ve vergi PDF'lerinin taranıp ekleneceği klasör."))
        row_p = QHBoxLayout()
        self.txt_set_pdf = self._make_line_edit("PDF arşiv klasörü...")
        row_p.addWidget(self.txt_set_pdf, stretch=1)

        btn_browse_pdf = self._make_btn("📁 Klasör Seç...", self.browse_pdf_folder)
        row_p.addWidget(btn_browse_pdf)

        btn_open_pdf_dir = self._make_btn("📂 Klasörü Aç", lambda: self.open_folder_of_file(self.txt_set_pdf.text()))
        row_p.addWidget(btn_open_pdf_dir)
        cd_layout.addLayout(row_p)

        c_layout.addWidget(card_dirs)

        # ── 2. KART: E-POSTA ALICI VE BİLGİ LİSTESİ ─────────────────────────────
        card_mail = QFrame(content)
        card_mail.setStyleSheet(self._card_qss())
        cm_layout = QVBoxLayout(card_mail)
        cm_layout.setSpacing(8)

        lbl_cm_title = QLabel("📧 OTOMATİK VERGİ MAİLİ ALICI & BİLGİ (CC) AYARLARI", card_mail)
        lbl_cm_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8;")
        cm_layout.addWidget(lbl_cm_title)
        cm_layout.addWidget(self._make_sub_label("Taslak vergi maili oluşturulduğunda otomatik eklenecek adresler (noktalı virgül ';' ile ayırın)."))

        cm_layout.addWidget(self._make_label("Kime (TO):"))
        self.txt_set_to = self._make_line_edit("muhasebe@hankookn.com")
        cm_layout.addWidget(self.txt_set_to)

        cm_layout.addWidget(self._make_label("Bilgi (CC):"))
        self.txt_set_cc = self._make_line_edit("ornek1@dogruer.com; ornek2@hankookn.com")
        cm_layout.addWidget(self.txt_set_cc)

        c_layout.addWidget(card_mail)

        # ── 3. KART: PORTAL KİMLİK BİLGİLERİ (3 PORTAL) ──────────────────────────
        card_portals = QFrame(content)
        card_portals.setStyleSheet(self._card_qss())
        cp_layout = QVBoxLayout(card_portals)
        cp_layout.setSpacing(12)

        lbl_cp_title = QLabel("🔑 PORTAL KİMLİK BİLGİLERİ VE OTOMATİK DOLDURMA", card_portals)
        lbl_cp_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8;")
        cp_layout.addWidget(lbl_cp_title)
        cp_layout.addWidget(self._make_sub_label(
            "Girdiğiniz kullanıcı kodları ve şifreler bilgisayarınızda güvenle saklanır; ilgili portal açıldığında otomatik doldurulur."
        ))

        # A) QNB eSolutions Portalı
        cp_layout.addWidget(self._make_label("💳 QNB eSolutions Portalı", bold=True))
        row_qnb = QHBoxLayout()
        self.txt_qnb_user = self._make_line_edit("Kullanıcı Kodu / T.C. / Kullanıcı Adı")
        row_qnb.addWidget(self.txt_qnb_user, stretch=1)
        self.txt_qnb_pass = self._make_line_edit("Portal Şifresi", is_password=True)
        row_qnb.addWidget(self.txt_qnb_pass, stretch=1)
        cp_layout.addLayout(row_qnb)

        self.chk_qnb_autofill = QCheckBox("⚡ QNB Portalı açıldığında kullanıcı adı ve şifremi otomatik doldur", card_portals)
        self.chk_qnb_autofill.setStyleSheet(self._checkbox_qss())
        cp_layout.addWidget(self.chk_qnb_autofill)

        cp_layout.addWidget(self._make_separator())

        # B) Hankook GLP Lojistik Portalı
        cp_layout.addWidget(self._make_label("🚛 Hankook GLP Lojistik Portalı", bold=True))
        row_glp = QHBoxLayout()
        self.txt_glp_user = self._make_line_edit("GLP User ID / Kullanıcı Adı")
        row_glp.addWidget(self.txt_glp_user, stretch=1)
        self.txt_glp_pass = self._make_line_edit("GLP Şifresi", is_password=True)
        row_glp.addWidget(self.txt_glp_pass, stretch=1)
        cp_layout.addLayout(row_glp)

        self.chk_glp_autofill = QCheckBox("⚡ GLP Portalı açıldığında kullanıcı adı ve şifremi otomatik doldur", card_portals)
        self.chk_glp_autofill.setStyleSheet(self._checkbox_qss())
        cp_layout.addWidget(self.chk_glp_autofill)

        cp_layout.addWidget(self._make_separator())

        # C) Doğruer Online (dogruer.online)
        cp_layout.addWidget(self._make_label("🌐 Doğruer Online Portalı (dogruer.online)", bold=True))
        row_dogruer = QHBoxLayout()
        self.txt_dogruer_user = self._make_line_edit("Doğruer Kullanıcı Kodu / E-Posta")
        row_dogruer.addWidget(self.txt_dogruer_user, stretch=1)
        self.txt_dogruer_pass = self._make_line_edit("Doğruer Şifresi", is_password=True)
        row_dogruer.addWidget(self.txt_dogruer_pass, stretch=1)
        cp_layout.addLayout(row_dogruer)

        self.chk_dogruer_autofill = QCheckBox("⚡ Doğruer Portalı açıldığında kullanıcı adı ve şifremi otomatik doldur", card_portals)
        self.chk_dogruer_autofill.setStyleSheet(self._checkbox_qss())
        cp_layout.addWidget(self.chk_dogruer_autofill)

        c_layout.addWidget(card_portals)

        # ── 4. KART: 2FA MAIL OTP (AKTİVASYON KODU OKUYUCU) ──────────────────────
        card_imap = QFrame(content)
        card_imap.setStyleSheet(self._card_qss())
        ci_layout = QVBoxLayout(card_imap)
        ci_layout.setSpacing(10)

        lbl_ci_title = QLabel("📬 2FA MAIL OTP (AKTİVASYON KODU OKUYUCU) AYARLARI", card_imap)
        lbl_ci_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8;")
        ci_layout.addWidget(lbl_ci_title)
        ci_layout.addWidget(self._make_sub_label(
            "Sistem önce bilgisayarınızdaki Outlook uygulamasından (COM API) kodu okur — IMAP şifresi gerekmez!\n"
            "Outlook açık değilse yedek olarak IMAP dener. Microsoft 365'te Basic Auth kapalıysa yalnızca Outlook yöntemi çalışır."
        ))

        # IMAP Alanları (Grid)
        grid_imap = QGridLayout()
        grid_imap.setSpacing(8)

        grid_imap.addWidget(self._make_label("IMAP Sunucusu (Host):"), 0, 0)
        self.txt_imap_host = self._make_line_edit("outlook.office365.com")
        grid_imap.addWidget(self.txt_imap_host, 0, 1)

        grid_imap.addWidget(self._make_label("IMAP Port:"), 0, 2)
        self.txt_imap_port = self._make_line_edit("993")
        self.txt_imap_port.setMaximumWidth(90)
        grid_imap.addWidget(self.txt_imap_port, 0, 3)

        grid_imap.addWidget(self._make_label("Mail Kullanıcı Adı (e-posta):"), 1, 0)
        self.txt_imap_user = self._make_line_edit("ornek@dogruer.com")
        grid_imap.addWidget(self.txt_imap_user, 1, 1)

        grid_imap.addWidget(self._make_label("Mail Şifresi / App Password:"), 1, 2)
        self.txt_imap_pass = self._make_line_edit("Şifre veya Uygulama Şifresi", is_password=True)
        grid_imap.addWidget(self.txt_imap_pass, 1, 3)

        ci_layout.addLayout(grid_imap)

        # Test Butonu ve Durum Göstergesi
        row_imap_test = QHBoxLayout()
        self.lbl_imap_test_result = QLabel("", card_imap)
        self.lbl_imap_test_result.setStyleSheet("font-size: 12px; font-weight: 600; color: #34d399;")
        row_imap_test.addWidget(self.lbl_imap_test_result, stretch=1)

        self.btn_imap_test = QPushButton("🔌 Bağlantıyı Test Et", card_imap)
        self.btn_imap_test.setStyleSheet(self._btn_primary_qss())
        self.btn_imap_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_imap_test.clicked.connect(self.test_imap_connection)
        row_imap_test.addWidget(self.btn_imap_test)
        ci_layout.addLayout(row_imap_test)

        c_layout.addWidget(card_imap)

        # ── 5. KART: TELEGRAM MOBİL OPERASYON ASİSTANI ─────────────────────────
        card_tg = QFrame(content)
        card_tg.setStyleSheet(self._card_qss())
        ctg_layout = QVBoxLayout(card_tg)
        ctg_layout.setSpacing(10)

        lbl_tg_title = QLabel("📱 TELEGRAM MOBİL OPERASYON ASİSTANI (@scMASTERSUITbot)", card_tg)
        lbl_tg_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8;")
        ctg_layout.addWidget(lbl_tg_title)
        ctg_layout.addWidget(self._make_sub_label(
            "Telefonunuzdan @scMASTERSUITbot botuna herhangi bir Dosya No (örn: 26-085915), Referans veya /durum, /kirmizi komutlarını göndererek 7/24 bilgi alabilirsiniz."
        ))

        # Bot Token Giriş Alanı
        lbl_token = QLabel("Telegram Bot API Token (BotFather):", card_tg)
        lbl_token.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8;")
        ctg_layout.addWidget(lbl_token)

        row_token = QHBoxLayout()
        self.txt_tg_token = self._make_line_edit("Örn: 7891234567:AAHxyz...", is_password=False)
        row_token.addWidget(self.txt_tg_token, stretch=1)

        btn_save_token = QPushButton("💾 Tokeni Doğrula & Başlat", card_tg)
        btn_save_token.setStyleSheet(self._btn_primary_qss())
        btn_save_token.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_token.clicked.connect(self.save_telegram_token)
        row_token.addWidget(btn_save_token)

        ctg_layout.addLayout(row_token)

        self.lbl_tg_status = QLabel(card_tg)
        self.lbl_tg_status.setStyleSheet("font-size: 11px; font-weight: 600;")
        ctg_layout.addWidget(self.lbl_tg_status)

        row_tg_btn = QHBoxLayout()
        btn_open_tg = QPushButton("📱 Telegram'da Botu Aç (@scMASTERSUITbot)", card_tg)
        btn_open_tg.setStyleSheet(self._btn_telegram_qss())
        btn_open_tg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_tg.clicked.connect(lambda: webbrowser.open("https://t.me/scMASTERSUITbot"))
        row_tg_btn.addWidget(btn_open_tg)

        btn_test_tg = QPushButton("🤖 Telegram Test Mesajı Gönder", card_tg)
        btn_test_tg.setStyleSheet(self._btn_secondary_qss())
        btn_test_tg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_tg.clicked.connect(self.send_telegram_test_notification)
        row_tg_btn.addWidget(btn_test_tg)

        row_tg_btn.addStretch()
        ctg_layout.addLayout(row_tg_btn)

        c_layout.addWidget(card_tg)

        # ── 6. KART: WINDOWS MASAÜSTÜ BİLDİRİMLERİ (TOAST) ──────────────────────
        card_notify = QFrame(content)
        card_notify.setStyleSheet(self._card_qss())
        cnot_layout = QVBoxLayout(card_notify)
        cnot_layout.setSpacing(10)

        lbl_not_title = QLabel("🔔 WINDOWS MASAÜSTÜ BALON / TOAST BİLDİRİMLERİ", card_notify)
        lbl_not_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8;")
        cnot_layout.addWidget(lbl_not_title)
        cnot_layout.addWidget(self._make_sub_label(
            "GTB beyanname tescil/statü değişimlerinde ve DP World kantar sonuçları çıktığında ekranınızın sağ alt köşesinde Windows bildirimi gösterir."
        ))

        row_notify = QHBoxLayout()
        self.chk_desktop_notify = QCheckBox("🔔 Masaüstü bildirimlerini etkinleştir (GTB Tescil & Kantar Sonuçları)", card_notify)
        self.chk_desktop_notify.setStyleSheet(self._checkbox_qss())
        row_notify.addWidget(self.chk_desktop_notify)

        btn_test_toast = QPushButton("🔔 Test Bildirimi Gönder", card_notify)
        btn_test_toast.setStyleSheet(self._btn_secondary_qss())
        btn_test_toast.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_toast.clicked.connect(self.send_desktop_test_notification)
        row_notify.addWidget(btn_test_toast)

        row_notify.addStretch()
        cnot_layout.addLayout(row_notify)

        c_layout.addWidget(card_notify)

        # ── 7. AKSİYON ÇUBUĞU (KAYDET & SIFIRLA) ────────────────────────────────
        card_actions = QFrame(content)
        card_actions.setStyleSheet(self._card_qss())
        ca_layout = QHBoxLayout(card_actions)
        ca_layout.setContentsMargins(14, 12, 14, 12)
        ca_layout.setSpacing(12)

        self.btn_save = QPushButton("💾 Tüm Ayarları Kaydet", card_actions)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                color: #ffffff;
                padding: 10px 24px;
                font-weight: 800;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_settings_from_ui)
        ca_layout.addWidget(self.btn_save)

        self.btn_reset = QPushButton("↩️ Varsayılana Dön", card_actions)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94a3b8;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self.reset_settings_to_default)
        ca_layout.addWidget(self.btn_reset)

        ca_layout.addStretch()
        c_layout.addWidget(card_actions)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # İlk yükleme
        self.load_settings_into_ui()

    # ── YARDIMCI BİLEŞEN FABRİKALARI & STİLLER ──────────────────────────────

    def _card_qss(self) -> str:
        return """
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 14px;
            }
        """

    def _checkbox_qss(self) -> str:
        return """
            QCheckBox {
                color: #e2e8f0;
                font-size: 12px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #475569;
                border-radius: 4px;
                background-color: #0b0f19;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """

    def _btn_primary_qss(self) -> str:
        return """
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                color: #ffffff;
                padding: 7px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """

    def _btn_telegram_qss(self) -> str:
        return """
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #0369a1;
                border-radius: 6px;
                color: #ffffff;
                padding: 7px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """

    def _btn_secondary_qss(self) -> str:
        return """
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f1f5f9;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
        """

    def _make_label(self, text: str, bold: bool = False) -> QLabel:
        lbl = QLabel(text, self)
        weight = "700" if bold else "600"
        lbl.setStyleSheet(f"font-size: 12px; font-weight: {weight}; color: #cbd5e1;")
        return lbl

    def _make_sub_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.3;")
        return lbl

    def _make_line_edit(self, placeholder: str = "", is_password: bool = False) -> QLineEdit:
        le = QLineEdit(self)
        le.setPlaceholderText(placeholder)
        if is_password:
            le.setEchoMode(QLineEdit.EchoMode.Password)
        le.setStyleSheet("""
            QLineEdit {
                background-color: #0b0f19;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 7px 10px;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #0f172a;
            }
        """)
        return le

    def _input_qss(self) -> str:
        return """
            QLineEdit {
                background-color: #0b0f19;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 7px 10px;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #0f172a;
            }
        """

    def _make_btn(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setStyleSheet(self._btn_secondary_qss())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def _make_separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("border: none; background-color: #1e293b; height: 1px; margin: 4px 0px;")
        return line

    # ── VERİ VE İŞ MANTIĞI YÖNETİMİ ──────────────────────────────────────────

    def load_settings_into_ui(self):
        """Ayarları diskten/bellekten okuyup arayüze aktarır."""
        cfg = load_app_config()
        if self.main_window and hasattr(self.main_window, "config"):
            self.main_window.config = cfg

        self.txt_set_excel.setText(cfg.get("excel_path", ""))
        self.txt_set_pdf.setText(cfg.get("pdf_folder", ""))
        self.txt_set_to.setText(cfg.get("mail_to", ""))
        self.txt_set_cc.setText(cfg.get("mail_cc", ""))

        # Portallar
        self.txt_qnb_user.setText(cfg.get("qnb_user", ""))
        self.txt_qnb_pass.setText(cfg.get("qnb_pass", ""))
        self.chk_qnb_autofill.setChecked(cfg.get("qnb_autofill", True))

        self.txt_glp_user.setText(cfg.get("glp_user", ""))
        self.txt_glp_pass.setText(cfg.get("glp_pass", ""))
        self.chk_glp_autofill.setChecked(cfg.get("glp_autofill", True))

        self.txt_dogruer_user.setText(cfg.get("dogruer_user", ""))
        self.txt_dogruer_pass.setText(cfg.get("dogruer_pass", ""))
        self.chk_dogruer_autofill.setChecked(cfg.get("dogruer_autofill", True))

        # IMAP
        self.txt_imap_host.setText(cfg.get("imap_host", "outlook.office365.com"))
        self.txt_imap_port.setText(str(cfg.get("imap_port", 993)))
        self.txt_imap_user.setText(cfg.get("imap_user", cfg.get("dogruer_user", "")))
        self.txt_imap_pass.setText(cfg.get("imap_pass", ""))

        # Bildirimler
        self.chk_desktop_notify.setChecked(cfg.get("enable_desktop_notifications", True))

        # Telegram Bot Token & Durumu
        try:
            from tools.telegram_bridge.telegram_bot_service import load_telegram_config
            tg_cfg = load_telegram_config()
            tok = tg_cfg.get("bot_token", "")
            if hasattr(self, "txt_tg_token"):
                self.txt_tg_token.setText(tok)
            self._update_tg_status_label(tok)
        except Exception:
            pass

    def browse_excel_path(self):
        """İş takip raporu Excel dosyasını seçtirir."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "İş Takip Raporu Excel Dosyasını Seçin",
            "",
            "Excel Dosyaları (*.xlsx *.xls);;Tüm Dosyalar (*.*)"
        )
        if filename:
            self.txt_set_excel.setText(filename)
            self._silent_save_settings_from_ui()
            self.apply_live_config()

    def browse_pdf_folder(self):
        """Vergi maili PDF arşiv klasörünü seçtirir."""
        folder = QFileDialog.getExistingDirectory(self, "Vergi Maili PDF Klasörünü Seçin")
        if folder:
            self.txt_set_pdf.setText(folder)
            self._silent_save_settings_from_ui()
            self.apply_live_config()

    def open_folder_of_file(self, path: str):
        """Verilen dosya veya klasörün konumunu Windows Gezgini'nde açar."""
        p = path.strip()
        if not p:
            self.show_warning("Yol Belirtilmedi", "Lütfen önce bir dosya veya klasör yolu girin.")
            return
        target = p if os.path.isdir(p) else os.path.dirname(p)
        if os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                self.show_error("Hata", f"Klasör açılamadı:\n{e}")
        else:
            self.show_warning("Klasör Bulunamadı", f"Belirtilen klasör mevcut değil:\n{target}")

    def reset_settings_to_default(self):
        """Tüm ayarları varsayılan değerlere döndürür."""
        reply = QMessageBox.question(
            self,
            "Varsayılana Sıfırla",
            "Tüm ayarları sistem varsayılan değerlerine sıfırlamak istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            cfg = DEFAULT_CONFIG.copy()
            save_app_config(cfg)
            if self.main_window and hasattr(self.main_window, "config"):
                self.main_window.config = cfg
            self.load_settings_into_ui()
            self.apply_live_config()
            self.show_info("Sıfırlandı", "✅ Tüm sistem ayarları varsayılan fabrika değerlerine sıfırlandı!")

    def _silent_save_settings_from_ui(self):
        """Sekme geçişlerinde arayüzdeki verileri sessizce kaydeder."""
        self._apply_settings_from_ui(preserve_empty_passwords=True)

    def _apply_settings_from_ui(self, preserve_empty_passwords: bool = True):
        cfg = getattr(self.main_window, "config", load_app_config()) if self.main_window else load_app_config()
        if not isinstance(cfg, dict):
            cfg = {}

        excel_p = self.txt_set_excel.text().strip()
        pdf_p = self.txt_set_pdf.text().strip()
        mail_to = self.txt_set_to.text().strip()
        mail_cc = self.txt_set_cc.text().strip()

        if excel_p: cfg["excel_path"] = excel_p
        if pdf_p: cfg["pdf_folder"] = pdf_p
        if mail_to: cfg["mail_to"] = mail_to
        if mail_cc: cfg["mail_cc"] = mail_cc

        # QNB
        cfg["qnb_user"] = self.txt_qnb_user.text().strip()
        qnb_pass = self.txt_qnb_pass.text().strip()
        if qnb_pass or not preserve_empty_passwords:
            cfg["qnb_pass"] = qnb_pass
        cfg["qnb_autofill"] = self.chk_qnb_autofill.isChecked()

        # GLP
        cfg["glp_user"] = self.txt_glp_user.text().strip()
        glp_pass = self.txt_glp_pass.text().strip()
        if glp_pass or not preserve_empty_passwords:
            cfg["glp_pass"] = glp_pass
        cfg["glp_autofill"] = self.chk_glp_autofill.isChecked()

        # Doğruer
        cfg["dogruer_user"] = self.txt_dogruer_user.text().strip()
        dogruer_pass = self.txt_dogruer_pass.text().strip()
        if dogruer_pass or not preserve_empty_passwords:
            cfg["dogruer_pass"] = dogruer_pass
        cfg["dogruer_autofill"] = self.chk_dogruer_autofill.isChecked()

        # IMAP
        cfg["imap_host"] = self.txt_imap_host.text().strip() or "outlook.office365.com"
        try:
            cfg["imap_port"] = int(self.txt_imap_port.text().strip())
        except ValueError:
            cfg["imap_port"] = 993
        cfg["imap_user"] = self.txt_imap_user.text().strip()
        imap_pass = self.txt_imap_pass.text().strip()
        if imap_pass or not preserve_empty_passwords:
            cfg["imap_pass"] = imap_pass

        # Bildirimler
        cfg["enable_desktop_notifications"] = self.chk_desktop_notify.isChecked()

        # Kaydet
        save_app_config(cfg)
        if self.main_window:
            self.main_window.config = cfg
            if hasattr(self.main_window, "engine") and self.main_window.engine:
                self.main_window.engine.config = cfg
                self.main_window.engine.excel_path = cfg.get("excel_path", "")

    def save_settings_from_ui(self):
        """'Tüm Ayarları Kaydet' butonuna basıldığında çağrılır."""
        excel_p = self.txt_set_excel.text().strip()
        if excel_p and not os.path.exists(excel_p):
            reply = QMessageBox.question(
                self,
                "Dosya Bulunamadı",
                f"Seçilen Excel dosyası bulunamadı:\n{excel_p}\n\nYine de kaydetmek istiyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._apply_settings_from_ui(preserve_empty_passwords=False)
        self.apply_live_config()
        self.show_info(
            "Başarılı",
            "✅ Tüm sistem ayarları başarıyla kaydedildi ve arka plan motorlarına anlık olarak yansıtıldı!"
        )

    def apply_live_config(self):
        """Değişen ayarları çalışan ana pencereye ve canlı motorlara uygular."""
        cfg = getattr(self.main_window, "config", load_app_config()) if self.main_window else load_app_config()
        if self.main_window and hasattr(self.main_window, "engine") and self.main_window.engine:
            self.main_window.engine.config = cfg
            self.main_window.engine.excel_path = cfg.get("excel_path", "")
        if self.main_window and hasattr(self.main_window, "trigger_sync_async"):
            self.main_window.trigger_sync_async()

    def test_imap_connection(self):
        """'🔌 Bağlantıyı Test Et' butonuna basıldığında asenkron IMAP ve Outlook testi başlatır."""
        self._apply_settings_from_ui(preserve_empty_passwords=True)
        self.lbl_imap_test_result.setText("⏳ Bağlantı test ediliyor (Outlook COM & IMAP)...")
        self.lbl_imap_test_result.setStyleSheet("font-size: 12px; font-weight: 600; color: #f59e0b;")
        self.btn_imap_test.setEnabled(False)

        self._imap_worker = ImapTestWorker()
        self._imap_worker.test_finished.connect(self._on_imap_test_finished)
        self._imap_worker.start()

    def _on_imap_test_finished(self, ok: bool, msg: str):
        self.btn_imap_test.setEnabled(True)
        if ok:
            self.lbl_imap_test_result.setText(f"✅ {msg}")
            self.lbl_imap_test_result.setStyleSheet("font-size: 12px; font-weight: 600; color: #34d399;")
            self.show_info("Bağlantı Başarılı", f"E-Posta OTP Bağlantısı Başarılı:\n{msg}")
        else:
            self.lbl_imap_test_result.setText("❌ Bağlantı Başarısız")
            self.lbl_imap_test_result.setStyleSheet("font-size: 12px; font-weight: 600; color: #f87171;")
            self.show_warning("Bağlantı Hatası", f"2FA Mail OTP Bağlantı Testi Başarısız Oldu:\n\n{msg}")

    def _update_tg_status_label(self, token=""):
        if not hasattr(self, "lbl_tg_status"):
            return
        tok = token or (self.txt_tg_token.text().strip() if hasattr(self, "txt_tg_token") else "")
        if tok:
            self.lbl_tg_status.setText("🟢 Bot Token Tanımlı & Servis Aktif (@scMASTERSUITbot)")
            self.lbl_tg_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #34d399;")
        else:
            self.lbl_tg_status.setText("🔴 Bot Token Henüz Girilmemiş — Lütfen @BotFather'dan aldığınız API Tokenini yukarıya yapıştırıp kaydedin.")
            self.lbl_tg_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #f87171;")

    def save_telegram_token(self):
        """Kullanıcının girdiği Telegram API tokenini doğrular ve kaydeder."""
        token = self.txt_tg_token.text().strip() if hasattr(self, "txt_tg_token") else ""
        if not token:
            self.show_warning("Token Gerekli", "Lütfen @BotFather'dan aldığınız Telegram Bot Tokenini giriniz.")
            return

        tg_svc = getattr(self.main_window, "telegram_service", None) if self.main_window else None
        if not tg_svc and self.main_window and hasattr(self.main_window, "service_supervisor") and self.main_window.service_supervisor:
            tg_svc = self.main_window.service_supervisor.get_service("telegram")

        if tg_svc and hasattr(tg_svc, "update_token"):
            res = tg_svc.update_token(token)
            if res.get("ok"):
                bot_info = res.get("bot", {})
                bot_username = bot_info.get("username", "scMASTERSUITbot")
                self._update_tg_status_label(token)
                self.show_info(
                    "Bot Başarıyla Bağlandı",
                    f"✅ Telegram Botu Doğrulandı ve Bağlandı!\n\n"
                    f"Bot Adı: @{bot_username}\n\n"
                    f"Şimdi telefonunuzdan botu açıp /start yazarak anında kullanmaya başlayabilirsiniz."
                )
            else:
                self.show_warning("Doğrulama Başarısız", f"Telegram API tokeni doğrulayamadı:\n\n{res.get('error')}")
        else:
            # Doğrudan confige yaz
            try:
                from tools.telegram_bridge.telegram_bot_service import load_telegram_config, save_telegram_config
                cfg = load_telegram_config()
                cfg["bot_token"] = token
                save_telegram_config(cfg)
                self._update_tg_status_label(token)
                self.show_info("Kaydedildi", "Token kaydedildi. Lütfen uygulamayı yeniden başlatın.")
            except Exception as ex:
                self.show_warning("Hata", f"Token kaydedilemedi: {ex}")

    def send_telegram_test_notification(self):
        """Telegram botu üzerinden test mesajı gönderir."""
        tg_svc = getattr(self.main_window, "telegram_service", None) if self.main_window else None
        if not tg_svc and self.main_window and hasattr(self.main_window, "service_supervisor") and self.main_window.service_supervisor:
            tg_svc = self.main_window.service_supervisor.get_service("telegram")

        if not tg_svc or not getattr(tg_svc, "token", ""):
            self.show_warning(
                "Bot Token Girilmemiş",
                "Telegram botu çalıştırılamıyor çünkü Bot API Tokeni henüz tanımlanmamış.\n\n"
                "Lütfen yukarıdaki 'Telegram Bot API Token' alanına @BotFather'dan aldığınız tokeni yapıştırıp 'Tokeni Doğrula & Başlat' butonuna basınız."
            )
            return

        chat_ids = getattr(tg_svc, "config", {}).get("authorized_chat_ids", [])
        if not chat_ids:
            reply = QMessageBox.question(
                self,
                "Telegram Yetkilendirme Gerekli",
                "Telefonunuz henüz bot ile eşleştirilmemiş.\n\n"
                "Lütfen telefonunuzdan Telegram uygulamasında @scMASTERSUITbot botuna girip /start mesajı atınız. Bot sizi otomatik olarak yetkilendirecektir.\n\nBot sayfası açılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open("https://t.me/scMASTERSUITbot")
            return

        if hasattr(tg_svc, "notify_critical_event"):
            tg_svc.notify_critical_event(
                "TEST BİLDİRİMİ",
                "✅ SmartClearance MasterSuite Telegram Mobil Asistanınız başarıyla bağlandı ve canlı çalışıyor!"
            )
        self.show_info("Başarılı", "✅ Test bildirimi telefonunuza gönderildi!")

    def send_desktop_test_notification(self):
        """Windows 10/11 masaüstü toast bildirim testini çalıştırır."""
        try:
            from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
            send_desktop_notification(
                title="🏛️ Doğruer MasterSuite Test Bildirimi",
                message="✅ Windows masaüstü bildirim sistemi aktif ve başarıyla çalışıyor!",
                force=True
            )
            self.show_info("Bildirim Gönderildi", "Ekranınızın sağ alt köşesine test bildirimi gönderildi!")
        except Exception as e:
            self.show_error("Hata", f"Masaüstü bildirimi gönderilemedi:\n{e}")

