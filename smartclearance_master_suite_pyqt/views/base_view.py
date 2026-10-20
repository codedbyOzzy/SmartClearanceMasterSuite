# -*- coding: utf-8 -*-
"""
🏛️ SmartClearance MasterSuite - Temel Görünüm Sınıfı (BaseView PyQt6)
Tüm 17 sekme için ortak arayüz, veri köprüsü ve yaşam döngüsü metodları.
"""

from PyQt6.QtWidgets import QWidget, QMessageBox, QApplication
from PyQt6.QtCore import Qt
from datetime import datetime
import re

class BaseView(QWidget):
    """Tüm MasterSuite PyQt6 sekme görünümleri için temel sınıf."""
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window

    @property
    def app(self):
        return self.main_window

    @property
    def engine(self):
        return getattr(self.main_window, "engine", None)

    @property
    def config(self):
        return getattr(self.main_window, "config", {})

    @property
    def current_user(self):
        return getattr(self.main_window, "current_user", {})

    def on_activate(self):
        """Sekme ekranda görüntülendiğinde tetiklenir."""
        pass

    def on_deactivate(self):
        """Sekmeden başka bir sekmeye geçildiğinde tetiklenir."""
        pass

    def _on_screen_changed(self, new_screen=None):
        """Pencere ekran değiştirdiğinde alt sınıflar bu metodu ezerek arayüzü uyarlar."""
        for attr in ("browser", "web_view", "table", "tree_gtb", "tree_kantar", "splitter"):
            w = getattr(self, attr, None)
            if w and hasattr(w, "updateGeometry"):
                try:
                    w.updateGeometry()
                    w.update()
                except Exception:
                    pass
        self.updateGeometry()
        self.update()

    def switch_tab(self, tab_code):
        if hasattr(self.main_window, "switch_tab"):
            self.main_window.switch_tab(tab_code)

    def set_header_subtitle(self, text):
        if hasattr(self.main_window, "header"):
            self.main_window.header.lbl_subtitle.setText(text)

    def _create_styled_msgbox(self, icon, title, msg, buttons=QMessageBox.StandardButton.Ok):
        mb = QMessageBox(icon, title, str(msg), buttons, self)
        mb.setStyleSheet("""
            QMessageBox {
                background-color: #0d1322;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QLabel {
                color: #f8fafc;
                font-size: 12px;
                font-weight: 500;
                background-color: transparent;
                min-height: 40px;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
                padding: 7px 22px;
                border-radius: 6px;
                border: 1px solid #3b82f6;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        return mb

    def show_info(self, title, msg):
        mb = self._create_styled_msgbox(QMessageBox.Icon.Information, title, msg)
        mb.exec()

    def show_warning(self, title, msg):
        mb = self._create_styled_msgbox(QMessageBox.Icon.Warning, title, msg)
        mb.exec()

    def show_error(self, title, msg):
        mb = self._create_styled_msgbox(QMessageBox.Icon.Critical, title, msg)
        mb.exec()

    def ask_yes_no(self, title, msg):
        mb = self._create_styled_msgbox(
            QMessageBox.Icon.Question, title, msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        mb.setDefaultButton(QMessageBox.StandardButton.No)
        return mb.exec() == QMessageBox.StandardButton.Yes

    def copy_to_clipboard(self, text, show_msg=False):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        if show_msg:
            self.show_info("Kopyalandı", f"Metin panoya kopyalandı:\n{text[:100]}")

    @staticmethod
    def format_check_time(val) -> str:
        """Tarih ve zaman bilgisini saat bazlı ve yüksek okunurluklu formata dönüştürür."""
        if not val or str(val).strip() in ("—", "-", "None", "null", ""):
            return "—"
        s = str(val).strip()

        # 1. DD.MM.YYYY HH:MM or DD.MM.YYYY HH:MM:SS
        m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}:\d{2}(?::\d{2})?)', s)
        if m:
            day, month, year, time_part = m.groups()
            today = datetime.now()
            if int(day) == today.day and int(month) == today.month and int(year) == today.year:
                return time_part
            return f"{day.zfill(2)}.{month.zfill(2)} {time_part}"

        # 2. ISO timestamp: 2026-09-17T11:09:30 or 2026-09-17 11:09:30
        if "T" in s or (len(s) >= 19 and s[4] == "-" and s[7] == "-"):
            try:
                clean_iso = s.replace("Z", "").split("+")[0]
                if "." in clean_iso:
                    clean_iso = clean_iso.split(".")[0]
                clean_iso = clean_iso.replace("T", " ")
                dt = datetime.strptime(clean_iso[:19], "%Y-%m-%d %H:%M:%S")
                today = datetime.now().date()
                if dt.date() == today:
                    return dt.strftime("%H:%M:%S")
                return dt.strftime("%d.%m %H:%M")
            except Exception:
                pass

        # 3. Sadece saat: HH:MM veya HH:MM:SS
        if re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', s):
            return s

        return s

