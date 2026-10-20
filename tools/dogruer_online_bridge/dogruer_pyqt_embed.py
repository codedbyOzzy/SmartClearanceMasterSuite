import sys
import os
import json
import threading

# YENİ: Emoji ve Türkçe karakterlerin stdout üzerinden hatasız yazdırılması için
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript, QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, QTimer
from PyQt6 import QtCore

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
PORTAL_WORK_URL = "https://dogruer.online/REPORT/AccountReport/WorkFollowUp"

# 2FA sayfa tespiti için URL anahtar kelimeleri
MAIL_OTP_URL_KEYS = ["emailverif", "emailcode", "mailcode", "mailverif", "emailotp", "email-otp"]
SMS_OTP_URL_KEYS  = ["smscode", "phonecode", "smsverif", "phoneverif", "smsotp", "sms-otp"]

# 2FA input seçicileri (DOM tabanlı tespit)
MAIL_OTP_SELECTORS = "input[name='EmailCode'], input[id*='EmailCode'], input[placeholder*='mail'], input[placeholder*='Mail'], input[autocomplete='one-time-code']"
SMS_OTP_SELECTORS  = "input[name='SmsCode'], input[name='PhoneCode'], input[id*='Sms'], input[id*='sms'], input[placeholder*='SMS'], input[placeholder*='sms'], input[placeholder*='telefon']"
SUBMIT_SELECTORS   = "button[type='submit'], input[type='submit'], .btn-primary, form button"


def get_dogruer_autofill_js():
    config_path = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("dogruer_autofill", True):
                    u = cfg.get("dogruer_user", "").replace('\\', '\\\\').replace('"', '\\"')
                    p = cfg.get("dogruer_pass", "").replace('\\', '\\\\').replace('"', '\\"')
                    if u and p:
                        return f"""
                        (function() {{
                            function tryFill() {{
                                let uField = document.getElementById('UserName') || document.getElementById('Email') || document.querySelector("input[name='UserName']") || document.querySelector("input[type='email']") || document.querySelector("input[name*='User']");
                                let pField = document.getElementById('Password') || document.querySelector("input[name='Password']") || document.querySelector("input[type='password']");
                                let rField = document.getElementById('RememberMe') || document.querySelector("input[name*='Remember']");
                                if (rField && !rField.checked) {{
                                    rField.checked = true;
                                    rField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                }}
                                if (uField && pField) {{
                                    if (!uField.value) {{
                                        uField.value = "{u}";
                                        uField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        uField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    if (!pField.value) {{
                                        pField.value = "{p}";
                                        pField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        pField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}
                            }}
                            tryFill();
                            setTimeout(tryFill, 800);
                            setTimeout(tryFill, 1800);
                        }})();
                        """
        except Exception:
            pass
    return ""


class PopupWebEngineView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.popups = []

    def createWindow(self, type):
        popup = QWebEngineView()
        if self.page() and self.page().profile():
            popup_page = SilentWebEnginePage(self.page().profile(), popup)
            popup.setPage(popup_page)
        popup.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.resize(1050, 850)

        def handle_print():
            file_path, _ = QFileDialog.getSaveFileName(popup, "PDF Kaydet", "Evrak.pdf", "PDF Dosyaları (*.pdf)")
            if file_path:
                def on_pdf_done(file_path_res, success):
                    if success:
                        QMessageBox.information(popup, "Başarılı", "PDF başarıyla kaydedildi!")
                        popup.close()
                popup.page().printToPdf(file_path)
                popup.page().pdfPrintingFinished.connect(on_pdf_done)

        popup.page().printRequested.connect(handle_print)
        popup.show()
        self.popups.append(popup)
        return popup


class SilentWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        pass


class StdinListener(QObject):
    sync_signal       = pyqtSignal()
    quit_signal       = pyqtSignal()
    auto_login_signal = pyqtSignal()

    def listen(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line or "QUIT" in line:
                    self.quit_signal.emit()
                    break
                if "SYNC" in line:
                    self.sync_signal.emit()
                if "AUTO_LOGIN" in line:
                    self.auto_login_signal.emit()
            except Exception:
                self.quit_signal.emit()
                break


class DogruerPortalEmbed(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DOGRUER_PYQT_EMBED_WINDOW")

        # ── Otomatik giriş durumu ──────────────────────────────────────────
        self._auto_login_active  = False   # AUTO_LOGIN komutu alındı mı?
        self._click_login_pending = False   # Login sayfasında butona tıklanacak mı?
        self._auto_sync_pending  = False   # WorkFollowUp yüklenince sync başlat mı?
        self._2fa_handled        = False   # Bu oturumda 2FA işlendi mi?
        # ─────────────────────────────────────────────────────────────────

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Kalıcı Profil & Çerez Depolama
        base_dir    = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "Dogruer_Profile")
        storage_dir = os.path.join(base_dir, "Storage")
        cache_dir   = os.path.join(base_dir, "Cache")
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)

        self.browser = PopupWebEngineView()
        self.profile = QWebEngineProfile("SmartClearance_Dogruer_Storage", self.browser)
        self.profile.setPersistentStoragePath(storage_dir)
        self.profile.setCachePath(cache_dir)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.page = SilentWebEnginePage(self.profile, self.browser)
        self.browser.setPage(self.page)

        self.browser.page().profile().downloadRequested.connect(self.on_download_requested)
        self.browser.titleChanged.connect(self.on_title_changed)
        self.browser.urlChanged.connect(self.on_url_changed)
        self.browser.loadFinished.connect(self.on_load_finished)

        self.browser.setUrl(QUrl(PORTAL_WORK_URL))
        layout.addWidget(self.browser)
        self.resize(1050, 800)

        self.listener = StdinListener()
        self.listener.sync_signal.connect(self.run_sync_extraction)
        self.listener.quit_signal.connect(QApplication.instance().quit)
        self.listener.auto_login_signal.connect(self.start_auto_login)
        threading.Thread(target=self.listener.listen, daemon=True).start()

    # -----------------------------------------------------------------------
    # Sayfa Yüklendi
    # -----------------------------------------------------------------------
    def on_load_finished(self, ok: bool):
        if not ok:
            return

        url = self.browser.url().toString().lower()

        # Her sayfada autofill çalıştır (login sayfasında kullanıcı/şifre doldurur)
        autofill_js = get_dogruer_autofill_js()
        if autofill_js:
            self.browser.page().runJavaScript(autofill_js)

        # AUTO_LOGIN aktifse ve login sayfasındaysak → butona tıkla
        if self._auto_login_active and self._click_login_pending:
            is_login_page = (
                "account/login" in url or
                "/login" in url or
                "signin" in url
            )
            if is_login_page:
                self._click_login_pending = False
                print("AUTO_AUTH_STATUS:✍️ Kullanıcı adı ve şifre dolduruldu, giriş yapılıyor...", flush=True)
                # Autofill'in bitmesi için 1.8 sn bekle, sonra butona tıkla
                QTimer.singleShot(1800, self._click_login_button)

        # Auto sync bekliyorsa ve WorkFollowUp yüklendiyse başlat
        if self._auto_sync_pending and ("workfollowup" in url or "workreport" in url):
            self._auto_sync_pending = False
            print("AUTO_AUTH_STATUS:✅ Giriş tamamlandı! Evrim verileri çekiliyor...", flush=True)
            print("AUTO_LOGIN_SUCCESS", flush=True)
            QTimer.singleShot(1500, self.run_sync_extraction)

    # -----------------------------------------------------------------------
    # URL Değişimi — WorkFollowUp değilse yönlendir, 2FA'yı tespit et
    # -----------------------------------------------------------------------
    def on_url_changed(self, qurl: QUrl):
        if not self._auto_login_active:
            return

        url = qurl.toString().lower()

        # Login sayfasına düştük — click_pending'i aç
        if "account/login" in url or ("/login" in url and "dogruer.online" in url):
            self._click_login_pending = True
            print("AUTO_AUTH_STATUS:🔐 Giriş sayfası yükleniyor...", flush=True)
            return

        # 2FA: Mail OTP sayfası
        if any(k in url for k in MAIL_OTP_URL_KEYS):
            print("AUTO_AUTH_STATUS:📬 Mail doğrulama kodu sayfası — Outlook'tan kod okunuyor...", flush=True)
            QTimer.singleShot(800, self._handle_mail_otp_page)
            return

        # 2FA: SMS OTP sayfası
        if any(k in url for k in SMS_OTP_URL_KEYS):
            print("AUTO_AUTH_STATUS:📱 SMS doğrulama kodu bekleniyor — lütfen kodu girin...", flush=True)
            QTimer.singleShot(500, self._show_sms_popup)
            return

        # WorkFollowUp'a ulaştık — giriş tamamlandı
        if "workfollowup" in url or "workreport" in url:
            self._auto_sync_pending = True   # load_finished'da sync başlar
            return

        # Giriş sonrası anasayfaya düşüldü (WorkFollowUp değil, 2FA değil)
        # → WorkFollowUp'a yönlendir
        if "dogruer.online" in url and self._2fa_handled:
            is_2fa = any(k in url for k in MAIL_OTP_URL_KEYS + SMS_OTP_URL_KEYS)
            is_login = "account/login" in url or "/login" in url
            is_work  = "workfollowup" in url or "workreport" in url
            if not is_2fa and not is_login and not is_work:
                print("AUTO_AUTH_STATUS:🔀 İş Takip sayfasına yönlendiriliyor...", flush=True)
                QTimer.singleShot(600, lambda: self.browser.setUrl(QUrl(PORTAL_WORK_URL)))

    # -----------------------------------------------------------------------
    # Login butonu tıklama
    # -----------------------------------------------------------------------
    def _click_login_button(self):
        js = f"""
        (function() {{
            let btn = document.querySelector("{SUBMIT_SELECTORS}");
            if (btn) {{ btn.click(); return "clicked"; }}
            // Form'a submit gönder
            let form = document.querySelector("form");
            if (form) {{ form.submit(); return "form_submit"; }}
            return "not_found";
        }})();
        """
        self.browser.page().runJavaScript(js,
            lambda r: print(f"AUTO_AUTH_STATUS:🖱️ Giriş butonu: {r}", flush=True)
        )

    # -----------------------------------------------------------------------
    # Mail OTP — URL tabanlı tespit başarısızsa DOM ile tekrar dene
    # -----------------------------------------------------------------------
    def _handle_mail_otp_page(self):
        """Mail OTP sayfasında Outlook'tan kodu oku ve doldur."""
        # DOM'da mail OTP inputu var mı?
        js = f"(function(){{ return document.querySelector('{MAIL_OTP_SELECTORS}') ? 'yes' : 'no'; }})();"
        def _cb(result):
            # DOM'da input bulundu ya da URL zaten mail OTP — Outlook'u oku
            threading.Thread(target=self._fetch_and_fill_mail_otp, daemon=True).start()
        self.browser.page().runJavaScript(js, _cb)

    def _fetch_and_fill_mail_otp(self):
        """Arka planda Outlook'tan OTP kodunu okur ve doldurur."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
            from tools.dogruer_online_bridge.evrim_imap_reader import EvrimImapReader
            reader = EvrimImapReader()
            code = reader.fetch_latest_otp(
                timeout_seconds=90,
                on_progress=lambda m: print(f"AUTO_AUTH_STATUS:{m}", flush=True)
            )
            if code:
                print(f"AUTO_AUTH_STATUS:✅ Mail kodu alındı, dolduruluyor...", flush=True)
                self._2fa_handled = True
                QTimer.singleShot(0, lambda: self._fill_otp_code(code, MAIL_OTP_SELECTORS))
            else:
                print("AUTO_AUTH_STATUS:⚠️ Mail kodu alınamadı. Lütfen manuel girin.", flush=True)
        except Exception as e:
            print(f"AUTO_AUTH_STATUS:⚠️ Mail OTP hatası: {e}", flush=True)

    # -----------------------------------------------------------------------
    # SMS OTP Popup — DOM tabanlı tespit
    # -----------------------------------------------------------------------
    def _show_sms_popup(self):
        """SMS OTP popup'ını göster; kod girilince doldur."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
            from tools.dogruer_online_bridge.evrim_auto_auth import SmsOtpDialog
            dlg = SmsOtpDialog(None)
            result = dlg.exec()
            if result and dlg.otp_code:
                self._2fa_handled = True
                print("AUTO_AUTH_STATUS:✅ SMS kodu girildi, dolduruluyor...", flush=True)
                self._fill_otp_code(dlg.otp_code, SMS_OTP_SELECTORS)
            else:
                print("AUTO_LOGIN_SMS_CANCELLED", flush=True)
        except Exception as e:
            print(f"AUTO_AUTH_STATUS:⚠️ SMS popup hatası: {e}", flush=True)

    # -----------------------------------------------------------------------
    # OTP Kodunu Sayfaya Yaz & Submit
    # -----------------------------------------------------------------------
    def _fill_otp_code(self, code: str, selector_css: str):
        js = f"""
        (function() {{
            let inp = document.querySelector('{selector_css}');
            if (!inp) {{
                // Tüm text/number inputları tara
                inp = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])'))
                     .find(el => el.maxLength === 6 || el.placeholder.match(/\\d/));
            }}
            if (inp) {{
                inp.value = '{code}';
                inp.dispatchEvent(new Event('input',  {{bubbles:true}}));
                inp.dispatchEvent(new Event('change', {{bubbles:true}}));
                inp.dispatchEvent(new KeyboardEvent('keyup', {{bubbles:true}}));
            }}
            setTimeout(function() {{
                let btn = document.querySelector('{SUBMIT_SELECTORS}');
                if (btn) btn.click();
            }}, 700);
            return inp ? 'filled' : 'input_not_found';
        }})();
        """
        self.browser.page().runJavaScript(js,
            lambda r: print(f"AUTO_AUTH_STATUS:📝 OTP fill: {r}", flush=True)
        )

    # -----------------------------------------------------------------------
    # Otomatik Giriş Başlat — stdin'den AUTO_LOGIN gelince çağrılır
    # -----------------------------------------------------------------------
    def start_auto_login(self):
        """AUTO_LOGIN stdin komutu geldiğinde çağrılır."""
        self._auto_login_active   = True
        self._click_login_pending = True
        self._auto_sync_pending   = False
        self._2fa_handled         = False
        print("AUTO_LOGIN_STARTED", flush=True)
        print("AUTO_AUTH_STATUS:🔐 Otomatik giriş başlatıldı, portal yükleniyor...", flush=True)
        # Portalı yenile — cookie yoksa login sayfasına yönlendirir
        QTimer.singleShot(300, lambda: self.browser.setUrl(QUrl(PORTAL_WORK_URL)))

    # -----------------------------------------------------------------------
    # Mevcut metodlar (değiştirilmedi)
    # -----------------------------------------------------------------------
    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.downloadFileName())
        file_path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", default_path)
        if file_path:
            download_item.setDownloadDirectory(os.path.dirname(file_path))
            download_item.setDownloadFileName(os.path.basename(file_path))
            download_item.accept()

    def on_title_changed(self, title):
        if "DOGRUER_SYNC_DONE:" in title:
            self.browser.page().runJavaScript(
                "document.body.getAttribute('data-sync-result')",
                self.on_sync_data_arrived
            )

    def on_sync_data_arrived(self, json_str):
        if json_str:
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0:
                    out_dir  = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, "evrim_live_data.json")
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"SYNC_SUCCESS:{len(data)}", flush=True)
                    self._auto_login_active = False   # İş bitti, state'i sıfırla
            except Exception:
                pass

    def run_sync_extraction(self):
        js_path      = os.path.join(os.path.dirname(__file__), "dogruer_sync.js")
        sync_js_code = ""
        if os.path.exists(js_path):
            with open(js_path, "r", encoding="utf-8") as f:
                sync_js_code = f.read()
        if sync_js_code:
            self.browser.page().runJavaScript(sync_js_code)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = DogruerPortalEmbed()
    window.show()
    sys.exit(app.exec())
