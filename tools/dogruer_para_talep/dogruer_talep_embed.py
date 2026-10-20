import sys
import os
import json
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript, QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6 import QtCore

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
        popup.show()
        self.popups.append(popup)
        return popup

class SilentWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        pass

class StdinListener(QObject):
    inject_signal = pyqtSignal()
    fill_signal = pyqtSignal(str)
    reload_signal = pyqtSignal()
    quit_signal = pyqtSignal()
    
    def listen(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    self.quit_signal.emit()
                    break
                line = line.strip()
                if line.startswith("FILL_FORM:"):
                    payload = line.split("FILL_FORM:", 1)[1].strip()
                    self.fill_signal.emit(payload)
                elif line == "INJECT":
                    self.inject_signal.emit()
                elif line == "RELOAD":
                    self.reload_signal.emit()
                elif line == "QUIT":
                    self.quit_signal.emit()
                    break
            except Exception:
                self.quit_signal.emit()
                break

class DogruerTalepEmbed(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TALEP_PYQT_EMBED_WINDOW")
        
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Paylaşımlı Doğruer oturum profili
        app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        storage_path = os.path.join(app_data, "SmartClearance", "Dogruer_Profile")
        os.makedirs(storage_path, exist_ok=True)
        
        self.profile = QWebEngineProfile("DogruerProfile", self)
        self.profile.setPersistentStoragePath(storage_path)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        
        self.page = SilentWebEnginePage(self.profile, self)
        self.browser = PopupWebEngineView(self)
        self.browser.setPage(self.page)
        
        self.browser.page().profile().downloadRequested.connect(self.on_download_requested)
        
        # JS Otomasyon Scripti
        js_path = os.path.join(os.path.dirname(__file__), "dogruer_para_talep_doldurucu.js")
        self.js_code = ""
        if os.path.exists(js_path):
            with open(js_path, "r", encoding="utf-8") as f:
                self.js_code = f.read()
                
            script = QWebEngineScript()
            script.setName("DogruerTalepDoldurucu")
            script.setSourceCode(self.js_code)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            self.page.profile().scripts().insert(script)

        def on_load_finished(ok):
            if ok:
                autofill_js = get_dogruer_autofill_js()
                if autofill_js:
                    self.browser.page().runJavaScript(autofill_js)
                if self.js_code:
                    self.browser.page().runJavaScript(self.js_code)

        self.browser.loadFinished.connect(on_load_finished)
        self.browser.setUrl(QUrl("https://dogruer.online/ACC/MoneyRequest/Add"))
        layout.addWidget(self.browser)
        self.resize(1100, 850)
        
        self.listener = StdinListener()
        self.listener.inject_signal.connect(self.manual_inject)
        self.listener.fill_signal.connect(self.fill_form_data)
        self.listener.reload_signal.connect(self.reload_page)
        self.listener.quit_signal.connect(QApplication.instance().quit)
        threading.Thread(target=self.listener.listen, daemon=True).start()

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.downloadFileName())
        file_path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", default_path)
        if file_path:
            download_item.setDownloadDirectory(os.path.dirname(file_path))
            download_item.setDownloadFileName(os.path.basename(file_path))
            download_item.accept()

    def manual_inject(self):
        if self.js_code:
            self.browser.page().runJavaScript(self.js_code)

    def reload_page(self):
        self.browser.setUrl(QUrl("https://dogruer.online/ACC/MoneyRequest/Add"))

    def fill_form_data(self, json_payload):
        if self.js_code:
            self.browser.page().runJavaScript(self.js_code)

        # Doğrudan JS fonksiyonunu tetikle ve form alanlarını otomatik doldur
        fill_js = f"""
        (function() {{
            let data = {json_payload};
            window.__LAST_TALEP_DATA = data;
            if (typeof window.fillMoneyRequestForm === 'function') {{
                window.fillMoneyRequestForm(data);
            }} else {{
                let tries = 0;
                let iv = setInterval(() => {{
                    tries++;
                    if (typeof window.fillMoneyRequestForm === 'function') {{
                        window.fillMoneyRequestForm(data);
                        clearInterval(iv);
                    }} else if (tries > 25) {{
                        clearInterval(iv);
                    }}
                }}, 250);
            }}
        }})();
        """
        self.browser.page().runJavaScript(fill_js)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = DogruerTalepEmbed()
    window.show()
    sys.exit(app.exec())
