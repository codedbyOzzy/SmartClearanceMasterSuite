"""
================================================================================
SMARTCLEARANCE MASTER SUITE — HANKOOK APEX & GLOBAL HORIZON PRO
================================================================================
Marka       : SmartClearance
Tasarım     : Seamless Linear / Dark Obsidian Suite Architecture
Teknoloji   : PyQt6 + QStackedWidget + QPropertyAnimation + QtWebEngineCore
Modüller    :
  [1] SmartClearance APEX    : Gümrük Operasyon Masası, Sabah Brifingi & Evrak Stüdyosu
  [2] SmartClearance HORIZON : Küresel Konteyner Radarı, Canlı Rota Haritası & AIS Takip
================================================================================
"""

import os
import sys
import argparse

# Yolları bağla (Dinamik ve Taşınabilir Yol Çözümleme)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. APEX dizinini belirle
if os.path.exists(os.path.join(CURRENT_DIR, "smartclearance_apex.py")):
    APEX_DIR = CURRENT_DIR
elif os.path.exists(os.path.join(CURRENT_DIR, "HANKOOK_OPERASYON_MASASI", "smartclearance_apex.py")):
    APEX_DIR = os.path.join(CURRENT_DIR, "HANKOOK_OPERASYON_MASASI")
else:
    APEX_DIR = r"C:\HANKOOK_OPERASYON_MASASI"

# 2. HORIZON dizinini belirle
cand_horizon = [
    os.path.join(CURRENT_DIR, "standalone_global_tracker"),
    os.path.join(os.path.dirname(CURRENT_DIR), "standalone_global_tracker"),
    os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), "standalone_global_tracker"),
    os.path.join(CURRENT_DIR, "Dogruer_MasterSuite_Workspace", "standalone_global_tracker"),
    r"c:\Users\ozan.gemici\Downloads\Telegram Desktop\v4.82Dogruer_MasterSuite_Workspace\v4.0Dogruer_MasterSuite_Workspace\Dogruer_MasterSuite_Workspace\standalone_global_tracker"
]
HORIZON_DIR = next((p for p in cand_horizon if os.path.exists(p)), cand_horizon[-1])
HORIZON_PARENT = os.path.dirname(HORIZON_DIR)

for path in [APEX_DIR, HORIZON_DIR, HORIZON_PARENT]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

import ctypes

try:
    import PyQt6.QtWebEngineWidgets
except Exception:
    pass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont

from smartclearance_apex import SmartClearanceApex, APEX_STYLESHEET
from smartclearance_horizon import SmartClearanceHorizonWindow
from apex_core.apex_suite_overlay import SuiteTransitionOverlay


class SmartClearanceMasterSuite(QMainWindow):
    """Apex ve Horizon sistemlerini tek pencerede, dinamik çoklu ekran adaptasyonuyla sunan ana çatı."""

    def __init__(self, initial_system="APEX"):
        super().__init__()
        self.setMinimumSize(960, 560)
        self.setStyleSheet(APEX_STYLESHEET)

        # Aktif ekranın çalışma alanına (taskbar hariç) göre dinamik başlatma
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if avail:
            init_w = min(1480, max(960, int(avail.width() * 0.94)))
            init_h = min(880, max(560, int(avail.height() * 0.92)))
            self.resize(init_w, init_h)
            # Ekran ortasına yerleştir
            self.move(
                avail.left() + max(0, (avail.width() - init_w) // 2),
                avail.top() + max(0, (avail.height() - init_h) // 2)
            )
        else:
            self.resize(1360, 800)

        # Ana Stack (Sayfa Değiştirici)
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        # 1. Modül: SmartClearance APEX (Gümrük Operasyon Masası)
        self.apex_window = SmartClearanceApex()
        self.apex_window.setWindowFlags(Qt.WindowType.Widget)
        self.stack.addWidget(self.apex_window)

        # 2. Modül: SmartClearance HORIZON (Küresel Konteyner Radarı)
        self.horizon_window = SmartClearanceHorizonWindow()
        self.horizon_window.setWindowFlags(Qt.WindowType.Widget)
        self.stack.addWidget(self.horizon_window)

        # İki yönlü sistem geçiş sinyalleri
        self.apex_window.appSwitchRequested.connect(self.switch_to_system)
        self.horizon_window.appSwitchRequested.connect(self.switch_to_system)

        # 1 Saniyelik Sinematik Geçiş Perdesi (Overlay)
        self.overlay = SuiteTransitionOverlay(self)
        self.overlay.transitionCompleted.connect(self._on_transition_finished)

        self._current_screen_name = None

        # Başlangıç Modu Belirleme
        if initial_system.upper() == "HORIZON":
            self.stack.setCurrentIndex(1)
            self.setWindowTitle("SmartClearance Horizon — Küresel Konteyner & Canlı Rota Radarı v1.0 Pro")
        else:
            self.stack.setCurrentIndex(0)
            self.setWindowTitle("SmartClearance Apex — Gümrük Operasyon Masası & Evrak Stüdyosu")

    def showEvent(self, event):
        super().showEvent(event)
        wh = self.windowHandle()
        if wh:
            try:
                wh.screenChanged.connect(self._on_screen_changed)
            except Exception:
                pass
            scr = wh.screen()
            if scr:
                self._current_screen_name = scr.name()
                self._on_screen_changed(scr)

    def moveEvent(self, event):
        super().moveEvent(event)
        wh = self.windowHandle()
        if wh:
            scr = wh.screen()
            if scr and scr.name() != self._current_screen_name:
                self._current_screen_name = scr.name()
                self._on_screen_changed(scr)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._on_screen_changed(self.screen())

    def _on_screen_changed(self, new_screen):
        """Pencere monitörler (Laptop <-> Harici Monitör) arasında taşındığında kendini otomatik adapte eder."""
        if not new_screen:
            return

        avail = new_screen.availableGeometry()

        if self.isMaximized():
            QTimer.singleShot(60, self.showMaximized)
            return

        geo = self.geometry()
        new_w = geo.width()
        new_h = geo.height()
        changed = False

        # Ekran genişliğinden büyükse ekrana sığdır (%95)
        max_w = int(avail.width() * 0.96)
        if new_w > max_w:
            new_w = max(self.minimumWidth(), max_w)
            changed = True

        # Ekran yüksekliğinden büyükse (Laptop: 816px / Monitör: 1032px) ekrana sığdır (%92)
        max_h = int(avail.height() * 0.94)
        if new_h > max_h:
            new_h = max(self.minimumHeight(), max_h)
            changed = True

        # Ekran sınırları dışına taşan pencereleri görünür alana çek
        new_x = geo.x()
        new_y = geo.y()

        if new_x < avail.left() or (new_x + new_w) > avail.right():
            new_x = max(avail.left(), min(new_x, avail.right() - new_w))
            changed = True

        if new_y < avail.top() or (new_y + new_h) > avail.bottom():
            new_y = max(avail.top(), min(new_y, avail.bottom() - new_h))
            changed = True

        if changed:
            self.setGeometry(new_x, new_y, new_w, new_h)

        # Alt modüllerin (Apex & Horizon) ekran adaptörlerini tetikle
        if hasattr(self, "horizon_window") and hasattr(self.horizon_window, "_on_screen_changed"):
            self.horizon_window._on_screen_changed(new_screen)
        if hasattr(self, "apex_window") and hasattr(self.apex_window, "_on_screen_changed"):
            self.apex_window._on_screen_changed(new_screen)

        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.resize(self.size())
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.resize(self.size())

    def switch_to_system(self, target_system):
        """1 saniyelik sinematik animasyonu başlatır ve ardından sistemi değiştirir."""
        target = target_system.upper()
        current_idx = self.stack.currentIndex()
        if (target == "APEX" and current_idx == 0) or (target == "HORIZON" and current_idx == 1):
            return

        self.overlay.resize(self.size())
        self.overlay.start_transition(target)

    def _on_transition_finished(self, target_system):
        if target_system == "HORIZON":
            self.stack.setCurrentIndex(1)
            self.setWindowTitle("SmartClearance Horizon — Küresel Konteyner & Canlı Rota Radarı v1.0 Pro")
        else:
            self.stack.setCurrentIndex(0)
            self.setWindowTitle("SmartClearance Apex — Gümrük Operasyon Masası & Evrak Stüdyosu")


def main():
    parser = argparse.ArgumentParser(description="SmartClearance Master Suite")
    parser.add_argument("--system", default="APEX", choices=["APEX", "HORIZON"], help="Başlangıç sistemi")
    args, unknown = parser.parse_known_args()

    # 1. Windows Çoklu Monitör / Laptop Dinamik DPI Farkındalığı (Per-Monitor V2)
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app_font = QFont("Segoe UI", 9)
    app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(app_font)

    suite = SmartClearanceMasterSuite(initial_system=args.system)
    suite.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

