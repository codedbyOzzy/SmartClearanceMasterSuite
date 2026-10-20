# -*- coding: utf-8 -*-
"""
ai_assistant_view.py — SmartClearance MasterSuite (PyQt6) Gemini AI Danışmanı
Gümrük Mevzuatı, GTİP Tespiti ve Dış Ticaret Operasyon Asistanı
"""

import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextBrowser, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from .base_view import BaseView
from tools.secrets_store import get_secret, set_secret
from tools.dogruer_master_suite.gemini_assistant_service import get_assistant_service


class GeminiQueryWorker(QThread):
    """Gemini API çağrısını arka planda yapan ve arayüzü kilitlemeyen iş parçacığı."""
    result_ready = pyqtSignal(bool, str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        svc = get_assistant_service()
        ok, reply = svc.ask(self.query)
        self.result_ready.emit(ok, reply)


class AIAssistantView(BaseView):
    """PyQt6 SmartClearance Gemini Yapay Zeka Operasyon & Mevzuat Danışmanı."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.assistant_service = get_assistant_service()
        self.current_worker = None
        self._build_ui()

    def on_activate(self):
        """Sekmeye geçildiğinde başlığı ve API durumunu tazele."""
        self.set_header_subtitle("🧠 Doğruer Akıllı Gümrük & Mevzuat Danışmanı (Google Gemini AI)")
        self._refresh_api_status()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        # 1. ÜST BİLGİ KARTI & API KEY BARI
        card_top = QFrame(self)
        card_top.setStyleSheet("""
            QFrame {
                background-color: #111622;
                border: 1px solid #1c2433;
                border-radius: 8px;
            }
        """)
        top_layout = QVBoxLayout(card_top)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(8)

        # Başlık ve Rozet Satırı
        row_title = QHBoxLayout()
        row_title.setSpacing(10)

        lbl_icon = QLabel("🧠", card_top)
        lbl_icon.setStyleSheet("font-size: 20px; border: none;")
        row_title.addWidget(lbl_icon)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        lbl_head = QLabel("SmartClearance AI Danışmanı (Google Gemini)", card_top)
        lbl_head.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold; border: none;")
        v_head.addWidget(lbl_head)

        lbl_sub = QLabel(
            "Gümrük Kanunu, 12 haneli GTİP tespiti, ithalat/ihracat kuralları ve Hankook operasyonel danışmanı.",
            card_top
        )
        lbl_sub.setStyleSheet("color: #8b9bb4; font-size: 10px; border: none;")
        v_head.addWidget(lbl_sub)
        row_title.addLayout(v_head)
        row_title.addStretch()

        self.lbl_status = QLabel("● Kontrol Ediliyor...", card_top)
        self.lbl_status.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 12px;
                background-color: #1c2433;
                color: #f59e0b;
                border: none;
            }
        """)
        row_title.addWidget(self.lbl_status)
        top_layout.addLayout(row_title)

        # API Key Giriş Satırı
        row_key = QHBoxLayout()
        row_key.setSpacing(8)

        lbl_k = QLabel("Gemini API Key:", card_top)
        lbl_k.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: bold; border: none;")
        row_key.addWidget(lbl_k)

        self.txt_key = QLineEdit(card_top)
        self.txt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_key.setPlaceholderText("Google Gemini API anahtarınızı giriniz...")
        self.txt_key.setStyleSheet("""
            QLineEdit {
                background-color: #0c1017;
                color: #f1f5f9;
                border: 1px solid #2d3748;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        cur_key = self.assistant_service.get_api_key()
        if cur_key:
            self.txt_key.setText(cur_key)
        row_key.addWidget(self.txt_key)

        btn_save_key = QPushButton("💾 Key Kaydet", card_top)
        btn_save_key.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_key.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 5px 12px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        btn_save_key.clicked.connect(self._save_key)
        row_key.addWidget(btn_save_key)

        btn_get_key = QPushButton("🔑 Ücretsiz Key Al", card_top)
        btn_get_key.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_get_key.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                font-size: 11px;
                padding: 5px 10px;
                border-radius: 5px;
                border: 1px solid #334155;
            }
            QPushButton:hover { color: #f8fafc; border-color: #475569; }
        """)
        btn_get_key.clicked.connect(lambda: webbrowser.open("https://aistudio.google.com/app/apikey"))
        row_key.addWidget(btn_get_key)

        top_layout.addLayout(row_key)
        layout.addWidget(card_top)

        # 2. HIZLI ŞABLON BUTONLARI
        row_chips = QHBoxLayout()
        row_chips.setSpacing(6)

        lbl_c = QLabel("Hızlı Şablonlar:", self)
        lbl_c.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        row_chips.addWidget(lbl_c)

        quick_prompts = [
            ("🔍 Lastik GTİP ve Vergi", "Otomobil dış lastikleri için olası 12 haneli GTİP kodları, gümrük vergisi ve TAREKS denetim şartları nelerdir?"),
            ("📋 Ordino vs Konşimento", "Dış ticarette konşimento ile ordino arasındaki hukuki ve operasyonel fark nedir?"),
            ("🏛️ Antrepo Süresi & Teminat", "Gümrük Kanununa göre antrepo rejiminde bekleme süresi sınırı var mıdır, teminat oranları nedir?"),
            ("⚠️ Damping Vergisi", "İthalatta dampinge karşı kesin önlem (vergi) nedir ve nasıl hesaplanır?")
        ]

        for title, p_text in quick_prompts:
            btn = QPushButton(title, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #162032;
                    color: #38bdf8;
                    border: 1px solid #1c2e4a;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #1e3a5f;
                    border-color: #38bdf8;
                }
            """)
            btn.clicked.connect(lambda _, pt=p_text: self._send_quick_prompt(pt))
            row_chips.addWidget(btn)

        row_chips.addStretch()

        btn_clear = QPushButton("🧹 Temizle", self)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #1f1d24;
                color: #f87171;
                border: 1px solid #37282b;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #2b1f24; border-color: #ef4444; }
        """)
        btn_clear.clicked.connect(self._clear_chat)
        row_chips.addWidget(btn_clear)

        layout.addLayout(row_chips)

        # 3. SOHBET GEÇMİŞİ (QTextBrowser)
        self.chat_view = QTextBrowser(self)
        self.chat_view.setOpenExternalLinks(True)
        self.chat_view.setStyleSheet("""
            QTextBrowser {
                background-color: #0c1017;
                color: #e2e8f0;
                border: 1px solid #1c2433;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.chat_view, stretch=1)

        # 4. GİRİŞ ÇUBUĞU
        f_input = QFrame(self)
        f_input.setStyleSheet("""
            QFrame {
                background-color: #111622;
                border: 1px solid #1c2433;
                border-radius: 8px;
            }
        """)
        inp_layout = QHBoxLayout(f_input)
        inp_layout.setContentsMargins(10, 8, 10, 8)
        inp_layout.setSpacing(8)

        self.txt_input = QLineEdit(f_input)
        self.txt_input.setPlaceholderText("Gümrük mevzuatı, GTİP veya operasyonel bir soru sorun... (Göndermek için Enter)")
        self.txt_input.setStyleSheet("""
            QLineEdit {
                background-color: #0c1017;
                color: #f8fafc;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #38bdf8; }
        """)
        self.txt_input.returnPressed.connect(self._send_message)
        inp_layout.addWidget(self.txt_input, stretch=1)

        self.btn_send = QPushButton("🚀 Gönder", f_input)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369a1; }
            QPushButton:disabled { background-color: #334155; color: #94a3b8; }
        """)
        self.btn_send.clicked.connect(self._send_message)
        inp_layout.addWidget(self.btn_send)

        layout.addWidget(f_input)

        # Karşılama mesajı
        self._append_ai_bubble(
            "Merhaba! Ben SmartClearance MasterSuite Gümrük ve Dış Ticaret Yapay Zeka Danışmanınızım. 🤖<br><br>"
            "Bana 12 haneli GTİP tespiti, gümrük rejimleri, vergi oranları, TAREKS/TSE mevzuatı veya "
            "Hankook operasyon süreçleriyle ilgili aklınıza gelen her şeyi sorabilirsiniz."
        )

        self._refresh_api_status()

    def _refresh_api_status(self):
        key = self.assistant_service.get_api_key()
        if key:
            self.lbl_status.setText("🟢 Canlı Gemini API Aktif")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    padding: 4px 10px;
                    border-radius: 12px;
                    background-color: #064e3b;
                    color: #34d399;
                    border: none;
                }
            """)
        else:
            self.lbl_status.setText("🟠 Test Modu (Key Girilmedi)")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    padding: 4px 10px;
                    border-radius: 12px;
                    background-color: #451a03;
                    color: #fb923c;
                    border: none;
                }
            """)

    def _save_key(self):
        new_key = self.txt_key.text().strip()
        if not new_key:
            QMessageBox.warning(self, "Eksik Anahtar", "Lütfen geçerli bir Gemini API anahtarı giriniz.")
            return
        if self.assistant_service.set_api_key(new_key):
            QMessageBox.information(self, "Başarılı", "Gemini API anahtarı güvenli şekilde kaydedildi!")
            self._refresh_api_status()
        else:
            QMessageBox.critical(self, "Hata", "API anahtarı kaydedilemedi.")

    def _send_quick_prompt(self, text: str):
        if self.current_worker and self.current_worker.isRunning():
            return
        self.txt_input.setText(text)
        self._send_message()

    def _send_message(self):
        if self.current_worker and self.current_worker.isRunning():
            return
        query = self.txt_input.text().strip()
        if not query:
            return

        self.txt_input.clear()
        self._append_user_bubble(query)

        self.btn_send.setEnabled(False)
        self.btn_send.setText("⏳ Yanıt Aranıyor...")
        self.txt_input.setEnabled(False)

        self.current_worker = GeminiQueryWorker(query)
        self.current_worker.result_ready.connect(self._on_response_ready)
        self.current_worker.start()

    def _on_response_ready(self, success: bool, reply: str):
        self.btn_send.setEnabled(True)
        self.btn_send.setText("🚀 Gönder")
        self.txt_input.setEnabled(True)
        self.txt_input.setFocus()

        if success:
            formatted_html = reply.replace("\n", "<br>")
            self._append_ai_bubble(formatted_html)
        else:
            self._append_ai_bubble(f"⚠️ <b>Hata:</b> {reply}")

    def _append_user_bubble(self, text: str):
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        html = f"""
        <div style="margin-bottom: 12px; margin-left: 60px; text-align: right;">
            <div style="font-size: 10px; color: #38bdf8; font-weight: bold; margin-bottom: 3px;">👤 SİZ:</div>
            <div style="background-color: #162032; border: 1px solid #1c3558; border-radius: 8px; padding: 10px 14px; color: #f8fafc; display: inline-block; text-align: left;">
                {escaped}
            </div>
        </div>
        """
        self.chat_view.append(html)

    def _append_ai_bubble(self, text_or_html: str):
        html = f"""
        <div style="margin-bottom: 14px; margin-right: 40px; text-align: left;">
            <div style="font-size: 10px; color: #34d399; font-weight: bold; margin-bottom: 3px;">🤖 SMARTCLEARANCE AI:</div>
            <div style="background-color: #111622; border: 1px solid #1c2433; border-radius: 8px; padding: 12px 16px; color: #e2e8f0; line-height: 1.5;">
                {text_or_html}
            </div>
        </div>
        """
        self.chat_view.append(html)

    def _clear_chat(self):
        self.assistant_service.clear_history()
        self.chat_view.clear()
        self._append_ai_bubble("Sohbet geçmişi temizlendi. Size nasıl yardımcı olabilirim?")
