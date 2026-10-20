# -*- coding: utf-8 -*-
"""
tools/dogruer_online_bridge/evrim_auto_auth.py
===============================================
Doğruer Online 2FA Otomatik Giriş Koordinatörü.

Durum makinesi (State Machine):
  IDLE → LOGIN_PAGE → WAITING_MAIL_OTP → WAITING_SMS_OTP → REDIRECTING → LOGGED_IN

Kullanım:
  auth = EvrimAutoAuth(browser_page, on_status_cb)
  auth.start_auto_login()
"""

import os
import re
import threading
import json
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIntValidator

CONFIG_DIR   = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
CONFIG_PATH  = os.path.join(CONFIG_DIR, "config.json")
PORTAL_URL   = "https://dogruer.online/REPORT/AccountReport/WorkFollowUp"
LOGIN_URL    = "https://dogruer.online/Account/Login"

# Durum tanımları
STATE_IDLE            = "IDLE"
STATE_LOGIN_PAGE      = "LOGIN_PAGE"
STATE_WAITING_MAIL    = "WAITING_MAIL_OTP"
STATE_WAITING_SMS     = "WAITING_SMS_OTP"
STATE_REDIRECTING     = "REDIRECTING"
STATE_LOGGED_IN       = "LOGGED_IN"


# ---------------------------------------------------------------------------
# SMS OTP Popup Penceresi
# ---------------------------------------------------------------------------
class SmsOtpDialog(QDialog):
    """
    SMS OTP girişi için minimal, odaklanmış popup.
    6 haneli kod girilip Enter'a basılınca veya "Gir" butonuna tıklanınca kapanır.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.FramelessWindowHint)
        self.otp_code: Optional[str] = None
        self._build_ui()
        self.setFixedWidth(340)
        self.setModal(True)

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0f172a;
                border: 2px solid #3b82f6;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Başlık
        title = QLabel("📱 SMS Doğrulama Kodu")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #f8fafc; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Bilgi metni
        info = QLabel("Telefonunuza gelen 6 haneli\nkodu aşağıya girin:")
        info.setFont(QFont("Segoe UI", 9))
        info.setStyleSheet("color: #94a3b8; background: transparent;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Ayraç
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #1e293b; max-height: 1px;")
        layout.addWidget(sep)

        # Kod giriş alanı
        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("• • • • • •")
        self.txt_code.setMaxLength(6)
        self.txt_code.setValidator(QIntValidator(0, 999999))
        self.txt_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_code.setFont(QFont("Courier New", 22, QFont.Weight.Bold))
        self.txt_code.setStyleSheet("""
            QLineEdit {
                background: #1e293b;
                color: #38bdf8;
                border: 2px solid #334155;
                border-radius: 8px;
                padding: 10px;
                letter-spacing: 8px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.txt_code.textChanged.connect(self._on_text_changed)
        self.txt_code.returnPressed.connect(self._submit)
        layout.addWidget(self.txt_code)

        # Buton satırı
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("İptal")
        btn_cancel.setFont(QFont("Segoe UI", 9))
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background: #334155; color: #94a3b8; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_ok = QPushButton("✅ Gir")
        self.btn_ok.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_ok.setEnabled(False)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #1e293b; color: #334155; }
        """)
        self.btn_ok.clicked.connect(self._submit)
        btn_row.addWidget(self.btn_ok)

        layout.addLayout(btn_row)

        # Countdown label
        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setFont(QFont("Segoe UI", 8))
        self.lbl_countdown.setStyleSheet("color: #475569; background: transparent;")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_countdown)

        # 120 saniyelik geri sayım (portal timeout'u genellikle 3-5 dk)
        self._remaining = 120
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _on_text_changed(self, text: str):
        self.btn_ok.setEnabled(len(text) == 6)
        # 6 hane dolunca otomatik gönder
        if len(text) == 6:
            QTimer.singleShot(300, self._submit)

    def _submit(self):
        code = self.txt_code.text().strip()
        if len(code) == 6:
            self.otp_code = code
            self._timer.stop()
            self.accept()

    def _tick(self):
        self._remaining -= 1
        self.lbl_countdown.setText(f"Kodun geçerlilik süresi: {self._remaining}s")
        if self._remaining <= 0:
            self._timer.stop()
            self.reject()


# ---------------------------------------------------------------------------
# Sinyal Köprüsü (thread-safe UI güncellemeleri için)
# ---------------------------------------------------------------------------
class AuthSignalBridge(QObject):
    status_changed     = pyqtSignal(str)          # Durum mesajı (UI gösterimi için)
    fill_code_signal   = pyqtSignal(str, str)     # (selector, code) — JS ile doldur
    click_button_signal = pyqtSignal(str)         # (selector) — JS ile tıkla
    navigate_signal    = pyqtSignal(str)          # URL — navigate et
    show_sms_popup     = pyqtSignal()             # SMS popup'ını göster
    sync_trigger       = pyqtSignal()             # Veri çekmeyi başlat


# ---------------------------------------------------------------------------
# Ana Koordinatör
# ---------------------------------------------------------------------------
class EvrimAutoAuth:
    """
    Doğruer Online 2FA otomatik giriş koordinatörü.
    `page` : QWebEnginePage referansı
    `on_status` : str → None  (UI durum güncellemesi callback'i)
    """

    # Olası 2FA input seçicileri (portal güncellenirse buradan genişletilir)
    MAIL_OTP_SELECTORS = [
        "input[name='EmailCode']",
        "input[id*='email'][type='text']",
        "input[id*='Email'][type='text']",
        "input[placeholder*='mail']",
        "input[placeholder*='Mail']",
        "input[placeholder*='e-posta']",
        "input[autocomplete*='one-time']",
    ]
    SMS_OTP_SELECTORS = [
        "input[name='SmsCode']",
        "input[name='PhoneCode']",
        "input[id*='sms']",
        "input[id*='Sms']",
        "input[id*='phone']",
        "input[id*='Phone']",
        "input[placeholder*='sms']",
        "input[placeholder*='SMS']",
        "input[placeholder*='telefon']",
        "input[placeholder*='cep']",
    ]
    SUBMIT_SELECTORS = [
        "button[type='submit']",
        "input[type='submit']",
        "button:contains('Devam')",
        "button:contains('İleri')",
        "button:contains('Doğrula')",
        "button:contains('Onayla')",
        ".btn-primary",
    ]

    def __init__(self, page, on_status: Callable[[str], None] = None):
        self.page      = page           # QWebEnginePage
        self.on_status = on_status or (lambda msg: print(f"[AUTO-AUTH] {msg}"))
        self.state     = STATE_IDLE
        self.bridge    = AuthSignalBridge()
        self._imap_thread: Optional[threading.Thread] = None
        self._sms_code: Optional[str] = None
        self._cancelled = False

    def start_auto_login(self):
        """Ana giriş akışını başlatır (non-blocking)."""
        self._cancelled = False
        self.state = STATE_LOGIN_PAGE
        self._status("🔐 Otomatik giriş başlatılıyor...")
        self._run_in_thread(self._login_flow)

    def cancel(self):
        self._cancelled = True
        self.state = STATE_IDLE
        self._status("⛔ Otomatik giriş iptal edildi.")

    # ------------------------------------------------------------------
    # Ana Akış (arka plan thread'i)
    # ------------------------------------------------------------------
    def _login_flow(self):
        import time

        # 1. Kullanıcı adı / şifre otofill'i tetikle (zaten var ama garantiye alalım)
        self._status("✍️ Kullanıcı adı ve şifre dolduruluyor...")
        self._inject_autofill()
        time.sleep(1.5)

        # 2. Login butonuna tıkla
        self._status("🖱️ Giriş butonuna tıklanıyor...")
        self._click_login_button()
        time.sleep(3)   # Sayfa yüklensin

        # 3. 2FA durumunu tespit et
        self._detect_and_handle_2fa()

    def _detect_and_handle_2fa(self):
        import time

        for attempt in range(1, 4):
            if self._cancelled:
                return

            state = self._get_auth_state_sync()
            self._status(f"🔍 Sayfa durumu: {state} (deneme {attempt})")

            if state == "WAITING_MAIL_OTP":
                self.state = STATE_WAITING_MAIL
                self._handle_mail_otp()
                return
            elif state == "WAITING_SMS_OTP":
                self.state = STATE_WAITING_SMS
                self._handle_sms_otp()
                return
            elif state == "LOGGED_IN":
                self.state = STATE_LOGGED_IN
                self._post_login()
                return
            else:
                time.sleep(2)

        self._status("⚠️ Durum tespit edilemedi. Lütfen portal penceresini kontrol edin.")

    # ------------------------------------------------------------------
    # Mail OTP Akışı
    # ------------------------------------------------------------------
    def _handle_mail_otp(self):
        import time
        self._status("📬 Mail doğrulama kodu bekleniyor — kutu otomatik kontrol ediliyor...")

        try:
            from tools.dogruer_online_bridge.evrim_imap_reader import EvrimImapReader
            reader = EvrimImapReader()
            code = reader.fetch_latest_otp(timeout_seconds=90, on_progress=self._status)
        except Exception as e:
            self._status(f"⚠️ IMAP hatası: {e}")
            code = None

        if self._cancelled:
            return

        if code:
            self._status(f"✅ Mail kodu alındı: {code[:2]}****")
            self._fill_otp_and_submit(code, self.MAIL_OTP_SELECTORS)
            time.sleep(3)
            # Sonraki aşama: SMS mı, yoksa giriş mi?
            self._detect_and_handle_2fa()
        else:
            self._status("⚠️ Mail kodu otomatik okunamadı. SMS adımına geçiliyor...")
            # Yine de sonraki adımı dene
            self._detect_and_handle_2fa()

    # ------------------------------------------------------------------
    # SMS OTP Akışı
    # ------------------------------------------------------------------
    def _handle_sms_otp(self):
        import time
        self._status("📱 SMS doğrulama kodu bekleniyor — popup açılıyor...")
        # SMS popup'ı ana thread'de açmak için sinyal gönder
        self.bridge.show_sms_popup.emit()
        # Popup'tan kod gelene kadar bekle (dialog.exec() thread-safe değil,
        # bu yüzden sinyalle koordine ediyoruz)
        for _ in range(60):  # 60 × 2 sn = 2 dakika bekle
            if self._cancelled:
                return
            if self._sms_code:
                break
            time.sleep(2)

        if self._sms_code:
            self._status(f"✅ SMS kodu girildi.")
            self._fill_otp_and_submit(self._sms_code, self.SMS_OTP_SELECTORS)
            self._sms_code = None
            time.sleep(3)
            self._detect_and_handle_2fa()
        else:
            self._status("⚠️ SMS kodu girilmedi veya zaman aşımı. Lütfen manuel giriş yapın.")

    def set_sms_code(self, code: str):
        """SMS popup'tan kod geldiğinde dışarıdan bu metot çağrılır."""
        self._sms_code = code

    # ------------------------------------------------------------------
    # Giriş Sonrası
    # ------------------------------------------------------------------
    def _post_login(self):
        import time
        self.state = STATE_REDIRECTING
        self._status("🔀 Giriş başarılı! İş Takip sayfasına yönlendiriliyor...")
        time.sleep(1)
        self.bridge.navigate_signal.emit(PORTAL_URL)
        time.sleep(3)
        self.state = STATE_LOGGED_IN
        self._status("✅ Giriş tamamlandı! Evrim verileri çekiliyor...")
        self.bridge.sync_trigger.emit()

    # ------------------------------------------------------------------
    # JS Yardımcıları
    # ------------------------------------------------------------------
    def _inject_autofill(self):
        """Mevcut config.json'daki kullanıcı adı/şifreyi doldurur."""
        cfg = self._load_config()
        u = cfg.get("dogruer_user", "").replace('"', '\\"')
        p = cfg.get("dogruer_pass", "").replace('"', '\\"')
        if not u or not p:
            return

        js = f"""
        (function() {{
            function tryFill() {{
                let uF = document.getElementById('UserName') ||
                         document.querySelector("input[name='UserName']") ||
                         document.querySelector("input[type='email']");
                let pF = document.getElementById('Password') ||
                         document.querySelector("input[name='Password']") ||
                         document.querySelector("input[type='password']");
                let rF = document.getElementById('RememberMe') ||
                         document.querySelector("input[name*='Remember']");
                if (rF && !rF.checked) {{
                    rF.checked = true;
                    rF.dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
                if (uF) {{
                    uF.value = "{u}";
                    uF.dispatchEvent(new Event('input', {{bubbles:true}}));
                    uF.dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
                if (pF) {{
                    pF.value = "{p}";
                    pF.dispatchEvent(new Event('input', {{bubbles:true}}));
                    pF.dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
            }}
            tryFill();
            setTimeout(tryFill, 600);
            setTimeout(tryFill, 1500);
        }})();
        """
        self.page.runJavaScript(js)

    def _click_login_button(self):
        js = """
        (function() {
            let btn = document.querySelector("button[type='submit']") ||
                      document.querySelector("input[type='submit']") ||
                      document.querySelector(".btn-login") ||
                      document.querySelector("form button");
            if (btn) { btn.click(); return "clicked"; }
            return "not_found";
        })();
        """
        self.page.runJavaScript(js)

    def _get_auth_state_sync(self) -> str:
        """
        Mevcut sayfa URL'sini ve DOM'unu analiz ederek durumu döner.
        QWebEnginePage.runJavaScript async çalıştığından URL'yi direkt alırız.
        """
        # URL tabanlı tespit (hızlı yol)
        current_url = self.page.url().toString().lower()

        if "workreport" in current_url or "workfollowup" in current_url:
            return "LOGGED_IN"
        if any(k in current_url for k in ["emailverif", "emailcode", "mailcode", "mailverif"]):
            return "WAITING_MAIL_OTP"
        if any(k in current_url for k in ["smscode", "phonecode", "smsverif", "phoneверif"]):
            return "WAITING_SMS_OTP"

        # DOM tabanlı tespit (JS ile)
        result_holder = [None]
        event = threading.Event()

        mail_sel  = ", ".join(self.MAIL_OTP_SELECTORS[:4])
        sms_sel   = ", ".join(self.SMS_OTP_SELECTORS[:4])

        js = f"""
        (function() {{
            if (document.querySelector('{mail_sel}')) return 'WAITING_MAIL_OTP';
            if (document.querySelector('{sms_sel}'))  return 'WAITING_SMS_OTP';
            let url = window.location.href.toLowerCase();
            if (url.includes('workfollowup') || url.includes('workreport')) return 'LOGGED_IN';
            if (url.includes('account/login') || url.includes('/login')) return 'LOGIN_PAGE';
            return 'UNKNOWN';
        }})();
        """

        def _cb(val):
            result_holder[0] = val
            event.set()

        self.page.runJavaScript(js, _cb)
        event.wait(timeout=4)
        return result_holder[0] or "UNKNOWN"

    def _fill_otp_and_submit(self, code: str, selectors: list):
        """OTP kodunu ilgili input'a yazar ve submit butonuna tıklar."""
        sel_css = ", ".join(selectors[:5])
        submit_sel = ", ".join(self.SUBMIT_SELECTORS[:4])
        js = f"""
        (function() {{
            let inp = document.querySelector('{sel_css}');
            if (inp) {{
                inp.value = '{code}';
                inp.dispatchEvent(new Event('input',  {{bubbles:true}}));
                inp.dispatchEvent(new Event('change', {{bubbles:true}}));
                inp.dispatchEvent(new KeyboardEvent('keyup', {{bubbles:true}}));
            }}
            // Kısa bekleme sonrası submit
            setTimeout(function() {{
                let btn = document.querySelector('{submit_sel}');
                if (btn) btn.click();
            }}, 600);
            return inp ? 'filled' : 'input_not_found';
        }})();
        """
        self.page.runJavaScript(js)

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------
    def _status(self, msg: str):
        try:
            self.on_status(msg)
            self.bridge.status_changed.emit(msg)
        except Exception:
            pass

    def _run_in_thread(self, fn):
        t = threading.Thread(target=fn, daemon=True)
        t.start()

    @staticmethod
    def _load_config() -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
