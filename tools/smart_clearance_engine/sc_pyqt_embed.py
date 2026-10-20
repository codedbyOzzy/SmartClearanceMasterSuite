# -*- coding: utf-8 -*-
"""
sc_pyqt_embed.py — SmartClearance Gömülü WebEngine Penceresi
Doğruer MasterSuite içinde doğrudan Excel Aktarım & Master Data Kontrol ekranlarını render eder.
"""
import sys
import os
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6 import QtCore

class StdinListener(QObject):
    navigate_signal = pyqtSignal(str)
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
                if line.startswith("NAVIGATE:"):
                    url = line.split("NAVIGATE:", 1)[1].strip()
                    self.navigate_signal.emit(url)
                elif line == "RELOAD":
                    self.reload_signal.emit()
                elif line == "QUIT":
                    self.quit_signal.emit()
                    break
            except Exception:
                break

class SmartClearanceEmbedWindow(QMainWindow):
    def __init__(self, initial_url="http://127.0.0.1:8050/excel-aktarim?embedded=1"):
        super().__init__()
        self.setWindowTitle("SC_ENGINE_PYQT_EMBED_WINDOW")
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.browser = QWebEngineView()
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.downloadRequested.connect(self.on_download_requested)

        self.browser.setUrl(QUrl(initial_url))
        layout.addWidget(self.browser)
        self.resize(1100, 800)

        # IPC Listener
        self.listener = StdinListener()
        self.listener.navigate_signal.connect(self.navigate_to)
        self.listener.reload_signal.connect(self.browser.reload)
        self.listener.quit_signal.connect(QApplication.instance().quit)
        threading.Thread(target=self.listener.listen, daemon=True).start()

    def navigate_to(self, url_str):
        self.browser.setUrl(QUrl(url_str))

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        default_name = download_item.downloadFileName() or "aktarim.xlsx"
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyasını Kaydet", default_path, "Excel Dosyaları (*.xlsx);;Tüm Dosyalar (*.*)"
        )
        if file_path:
            download_item.setDownloadDirectory(os.path.dirname(file_path))
            download_item.setDownloadFileName(os.path.basename(file_path))
            download_item.accept()

            def _on_state_changed(state):
                if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Icon.Information)
                    msg_box.setWindowTitle("İndirme Tamamlandı")
                    msg_box.setText(f"✅ Excel başarıyla kaydedildi:\n{os.path.basename(file_path)}")
                    btn_open = msg_box.addButton("Dosyayı Aç", QMessageBox.ButtonRole.AcceptRole)
                    msg_box.addButton("Kapat", QMessageBox.ButtonRole.RejectRole)
                    msg_box.exec()
                    if msg_box.clickedButton() == btn_open:
                        try:
                            os.startfile(file_path)
                        except Exception:
                            pass

            download_item.stateChanged.connect(_on_state_changed)
        else:
            download_item.cancel()

def main():
    initial_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8050/excel-aktarim?embedded=1"
    app = QApplication(sys.argv)
    win = SmartClearanceEmbedWindow(initial_url)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
