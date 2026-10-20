# -*- coding: utf-8 -*-
"""
horizon_view.py — SmartClearance HORIZON (Küresel Konteyner Radarı & Leaflet AIS Haritası) Entegrasyon Görünümü
"""

import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_view import BaseView

# HORIZON Modülünü yükle
_horizon_import_error = ""
try:
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _horizon_path = os.path.join(_root, "standalone_global_tracker")
    if os.path.exists(_horizon_path) and _horizon_path not in sys.path:
        sys.path.insert(0, _horizon_path)

    from smartclearance_horizon import SmartClearanceHorizonWindow
    HAS_HORIZON = True
except Exception as e:
    HAS_HORIZON = False
    _horizon_import_error = str(e)


class HorizonView(BaseView):
    """SmartClearance Horizon (Küresel Konteyner Radarı & Leaflet AIS Haritası) Görünümü."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.horizon_widget = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if HAS_HORIZON:
            try:
                self.horizon_widget = SmartClearanceHorizonWindow()
                self.horizon_widget.setWindowFlags(Qt.WindowType.Widget)

                # Sistem geçiş sinyalini MasterSuite ana penceresine bağla
                if hasattr(self.horizon_widget, "appSwitchRequested"):
                    self.horizon_widget.appSwitchRequested.connect(self._on_app_switch)

                layout.addWidget(self.horizon_widget)
            except Exception as ex:
                lbl_err = QLabel(f"Horizon bileşeni oluşturulurken hata oluştu:\n{ex}", self)
                lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_err.setStyleSheet("color: #ef4444; font-size: 12px; padding: 20px;")
                layout.addWidget(lbl_err)
        else:
            lbl_err = QLabel(
                f"SmartClearance Horizon modülü bulunamadı:\n{_horizon_import_error}",
                self
            )
            lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_err.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 600; padding: 20px;")
            layout.addWidget(lbl_err)

    def _on_app_switch(self, target_system: str):
        target = target_system.upper()
        if target == "APEX" and self.main_window:
            self.main_window.switch_tab("APEX")
    def _on_screen_changed(self, new_screen=None):
        if self.horizon_widget and hasattr(self.horizon_widget, "_on_screen_changed"):
            try:
                self.horizon_widget._on_screen_changed(new_screen)
            except Exception:
                pass
        self.updateGeometry()
        self.update()

    def focus_shipment(self, query: str):
        """Cockpit veya dış bir görünümden gelen gemi, konşimento veya konteyneri arayıp odaklar."""
        if not self.horizon_widget or not query:
            return
        query = str(query).strip()
        if hasattr(self.horizon_widget, "txt_search"):
            self.horizon_widget.txt_search.setText(query)

        # Tabloda eşleşen satırı seçip haritayı odakla
        table = getattr(self.horizon_widget, "table", None)
        if table:
            for row in range(table.rowCount()):
                match = False
                for col in range(min(5, table.columnCount())):
                    item = table.item(row, col)
                    if item and query.lower() in item.text().lower():
                        match = True
                        break
                if match:
                    table.selectRow(row)
                    if hasattr(self.horizon_widget, "_on_row_selected"):
                        self.horizon_widget._on_row_selected(row)
                    break

    def on_activate(self):
        """Sekme aktifleştiğinde harita ve tablo boyutunu kontrol et."""
        if self.horizon_widget and hasattr(self.horizon_widget, "splitter"):
            try:
                tot = self.horizon_widget.width()
                if tot > 600:
                    left_w = int(tot * 0.67)
                    right_w = max(tot - left_w, 420)
                    self.horizon_widget.splitter.setSizes([left_w, right_w])
            except Exception:
                pass
