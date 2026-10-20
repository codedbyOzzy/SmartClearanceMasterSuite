# -*- coding: utf-8 -*-
"""
🏛️ SmartClearance MasterSuite - Modern PyQt6 Başlatıcı (app_pyqt.py)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
"""

import sys
import os
import atexit

# Root ve yerel site-packages dizinlerini sys.path'e ekle
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
for _pkg_sub in [
    "Lib/site-packages",
    "python-embed/Lib/site-packages",
    "python-embed/Lib/site-packages/win32",
    "python-embed/Lib/site-packages/win32/lib",
    "python-embed/Lib/site-packages/Pythonwin",
    "Lib/site-packages/win32",
    "Lib/site-packages/win32/lib",
    "Lib/site-packages/Pythonwin",
]:
    _p = os.path.join(_root_dir, _pkg_sub.replace("/", os.sep))
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.append(_p)

for _dll_sub in [
    "python-embed/Lib/site-packages/pywin32_system32",
    "Lib/site-packages/pywin32_system32",
]:
    _dp = os.path.join(_root_dir, _dll_sub.replace("/", os.sep))
    if os.path.exists(_dp):
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(_dp)
            except Exception:
                pass
        os.environ["PATH"] = _dp + os.pathsep + os.environ.get("PATH", "")

# HANKOOK APEX & HORIZON dizinlerini sys.path'e dahil et
for _suite_sub in ["HANKOOK_OPERASYON_MASASI", "standalone_global_tracker"]:
    _sp = os.path.join(_root_dir, _suite_sub)
    if os.path.exists(_sp) and _sp not in sys.path:
        sys.path.insert(0, _sp)

# QtWebEngineWidgets, QApplication oluşturulmadan önce yüklenmelidir
try:
    import PyQt6.QtWebEngineWidgets
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QLocale, qInstallMessageHandler, QtMsgType
from PyQt6.QtGui import QIcon

import ctypes

def qt_message_filter(mode, context, message):
    # Windows DPI awareness ve Chromium Permissions-Policy konsol gürültülerini sustur
    if "SetProcessDpiAwarenessContext" in message:
        return
    if "Permissions-Policy" in message or "payment" in message:
        return
    # Web sitelerinin (GLP, QNB, Dogruer) ürettiği 3. taraf JS ve WebEngine konsol gürültülerini sustur
    if any(kw in message for kw in (
        "Uncaught ReferenceError", "Uncaught TypeError", "Uncaught SyntaxError",
        "screenfull", "ShowLoading", "matrix", "js:", "Console message:", "is not defined",
        "Cannot read properties", "reading 'matrix'"
    )):
        return
    if context and getattr(context, "category", None) and "webengine" in str(context.category).lower():
        return
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtInfoMsg):
        return
    if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        if "Uncaught" in message or "is not defined" in message or "Cannot read properties" in message:
            return
        sys.stderr.write(f"[Qt] {message}\n")

PYQT_MUTEX_NAME = "Local\\DogruerMasterSuite_PyQt_v5_SingleInstance"
ERROR_ALREADY_EXISTS = 183
_pyqt_mutex_handle = None

def acquire_pyqt_single_instance():
    global _pyqt_mutex_handle
    if sys.platform != "win32":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, True, PYQT_MUTEX_NAME)
        if not handle:
            return False
        err = kernel32.GetLastError()
        if err == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        _pyqt_mutex_handle = handle
        return True
    except Exception:
        return True

def release_pyqt_single_instance():
    global _pyqt_mutex_handle
    if sys.platform != "win32" or not _pyqt_mutex_handle:
        _pyqt_mutex_handle = None
        return
    try:
        ctypes.windll.kernel32.CloseHandle(_pyqt_mutex_handle)
    except Exception:
        pass
    _pyqt_mutex_handle = None

from smartclearance_master_suite_pyqt.theme import MODERN_THEME_QSS, get_dark_palette
from smartclearance_master_suite_pyqt.auth.login_dialog import prompt_login_dialog
from smartclearance_master_suite_pyqt.main_window import MainWindow

def main():
    # 0. Windows Çoklu Monitör / Laptop Dinamik DPI Farkındalığı (Per-Monitor V2)
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    # Konsol gürültülerini, Chromium Permissions-Policy ve DPI uyarılarını sustur
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging --log-level=3 --disable-gpu-shader-disk-cache --no-sandbox"
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false;qt.webenginecontext.*=false;js.*=false;*.debug=false"

    try:
        qInstallMessageHandler(qt_message_filter)
    except Exception:
        pass

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("SmartClearance MasterSuite")
    app.setOrganizationName("Dogruer Gumruk Musavirligi")
    
    dark_pal = get_dark_palette()
    if dark_pal:
        app.setPalette(dark_pal)
    app.setStyleSheet(MODERN_THEME_QSS)

    # 1. Tekil Kopya (Single Instance) Kilit Kontrolü
    if not acquire_pyqt_single_instance():
        QMessageBox.warning(
            None,
            "Uygulama Zaten Açık",
            "SmartClearance MasterSuite (PyQt6) zaten açık veya arka planda çalışıyor.\n\n"
            "Veri bozulması ve Excel/COM kilitlenmelerini önlemek amacıyla birden fazla kopya açılamaz."
        )
        sys.exit(0)

    atexit.register(release_pyqt_single_instance)
    app.aboutToQuit.connect(release_pyqt_single_instance)

    # 2. Oturum Çözümleme & Giriş Ekranı (Login Gate)
    user = prompt_login_dialog()
    if not user:
        release_pyqt_single_instance()
        sys.exit(0)

    # 3. Ana Pencereyi Başlat
    main_win = MainWindow(current_user=user)
    main_win.show()

    exit_code = app.exec()
    release_pyqt_single_instance()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

