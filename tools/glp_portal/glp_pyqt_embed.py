import sys
import os
import json
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript, QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6 import QtCore

def get_glp_autofill_js():
    config_path = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("glp_autofill", True):
                    u = cfg.get("glp_user", "").replace('\\', '\\\\').replace('"', '\\"')
                    p = cfg.get("glp_pass", "").replace('\\', '\\\\').replace('"', '\\"')
                    if u and p:
                        return f"""
                        (function() {{
                            function tryFill() {{
                                let uField = document.getElementById('id') || document.querySelector("input[name='id']");
                                let pField = document.getElementById('password') || document.querySelector("input[name='password']");
                                let rField = document.getElementById('rememberId');
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
                            setTimeout(tryFill, 3000);
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
        popup.resize(1000, 850)
        
        def handle_print():
            file_path, _ = QFileDialog.getSaveFileName(popup, "PDF Kaydet", "Belge.pdf", "PDF Dosyaları (*.pdf)")
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
    quit_signal = pyqtSignal()
    
    def listen(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line or "QUIT" in line:
                    self.quit_signal.emit()
                    break
            except:
                self.quit_signal.emit()
                break

class GLPPortalEmbed(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLP_PYQT_EMBED_WINDOW")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Kalıcı Profil & Çerez Depolama
        base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "GLP_Profile")
        storage_dir = os.path.join(base_dir, "Storage")
        cache_dir = os.path.join(base_dir, "Cache")
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        self.browser = PopupWebEngineView()
        self.profile = QWebEngineProfile("SmartClearance_GLP_Storage", self.browser)
        self.profile.setPersistentStoragePath(storage_dir)
        self.profile.setCachePath(cache_dir)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.page = SilentWebEnginePage(self.profile, self.browser)
        self.browser.setPage(self.page)
        
        self.browser.page().profile().downloadRequested.connect(self.on_download_requested)
        
        def on_load_finished(ok):
            if ok:
                autofill_js = get_glp_autofill_js()
                if autofill_js:
                    self.browser.page().runJavaScript(autofill_js)

        self.browser.loadFinished.connect(on_load_finished)
        self.browser.setUrl(QUrl("https://glp.hankooktech.com/login.html?redirectUrl=%2FMAIN%2Fmain.html%3Flang%3Dko"))
        layout.addWidget(self.browser)
        self.resize(1000, 800)
        
        self.listener = StdinListener()
        self.listener.quit_signal.connect(QApplication.instance().quit)
        threading.Thread(target=self.listener.listen, daemon=True).start()

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.downloadFileName())
        file_path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", default_path)
        if file_path:
            download_item.setDownloadDirectory(os.path.dirname(file_path))
            download_item.setDownloadFileName(os.path.basename(file_path))
            download_item.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = GLPPortalEmbed()
    window.show()
    sys.exit(app.exec())
