# -*- coding: utf-8 -*-
"""
apex_view.py — SmartClearance APEX (Hankook Gümrük Masası & Evrak Stüdyosu) Entegrasyon Görünümü
"""

import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .base_view import BaseView

# APEX Modülünü yükle
_apex_import_error = ""
try:
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _apex_path = os.path.join(_root, "HANKOOK_OPERASYON_MASASI")
    if os.path.exists(_apex_path) and _apex_path not in sys.path:
        sys.path.insert(0, _apex_path)

    from smartclearance_apex import SmartClearanceApex
    HAS_APEX = True
except Exception as e:
    HAS_APEX = False
    _apex_import_error = str(e)


class ApexView(BaseView):
    """SmartClearance Apex (Hankook Gümrük Operasyon Masası & Evrak Stüdyosu) Görünümü."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.apex_widget = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if HAS_APEX:
            try:
                self.apex_widget = SmartClearanceApex()
                self.apex_widget.setWindowFlags(Qt.WindowType.Widget)

                # Sistem geçiş sinyalini MasterSuite ana penceresine bağla
                if hasattr(self.apex_widget, "appSwitchRequested"):
                    self.apex_widget.appSwitchRequested.connect(self._on_app_switch)

                layout.addWidget(self.apex_widget)
            except Exception as ex:
                lbl_err = QLabel(f"Apex bileşeni oluşturulurken hata oluştu:\n{ex}", self)
                lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_err.setStyleSheet("color: #ef4444; font-size: 12px; padding: 20px;")
                layout.addWidget(lbl_err)
        else:
            lbl_err = QLabel(
                f"SmartClearance Apex modülü bulunamadı:\n{_apex_import_error}",
                self
            )
            lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_err.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 600; padding: 20px;")
            layout.addWidget(lbl_err)

    def _on_app_switch(self, target_system: str):
        target = target_system.upper()
        if target == "HORIZON" and self.main_window:
            self.main_window.switch_tab("HORIZON")
        elif target in ["SUITE", "COCKPIT"] and self.main_window:
            self.main_window.switch_tab("COCKPIT")

    def _on_screen_changed(self, new_screen=None):
        if self.apex_widget and hasattr(self.apex_widget, "_on_screen_changed"):
            try:
                self.apex_widget._on_screen_changed(new_screen)
            except Exception:
                pass
        self.updateGeometry()
        self.update()

    def on_activate(self):
        """Sekme aktifleştiğinde Apex veri akışını kontrol et ve yenile."""
        if self.apex_widget and hasattr(self.apex_widget, "_start_loading"):
            try:
                self.apex_widget._start_loading()
            except Exception:
                pass
