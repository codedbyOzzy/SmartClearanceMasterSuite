# -*- coding: utf-8 -*-
"""
🏛️ SmartClearance MasterSuite - Swiss Executive QSS Tema Motoru
Cenevre / Basel Özel Bankacılık & Kurumsal Ağırbaşlı (Platin & Gece Laciverti) Tasarım Sistemi.
"""

MODERN_THEME_QSS = """
/* ================= GLOBAL AYARLAR ================= */
* {
    font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #0c1017;
    color: #f1f5f9;
}

QLabel {
    color: #f1f5f9;
}

QWidget#CentralContainer {
    background-color: #0c1017;
}

/* ================= HEADER BAR ================= */
QWidget#HeaderWidget {
    background-color: #0e131d;
    border-bottom: 1px solid #1c2433;
}

QLabel#HeaderTitle {
    font-size: 15px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: 0.3px;
}

QLabel#HeaderSubtitle {
    font-size: 11px;
    color: #8b9bb4;
    font-weight: 500;
}

/* ================= SIDEBAR ================= */
QWidget#SidebarWidget {
    background-color: #0a0e16;
    border-right: 1px solid #1c2433;
}

QLabel#SidebarBrand {
    font-size: 14px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: 0.5px;
}

QLabel#SidebarVersion {
    background-color: #162032;
    color: #38bdf8;
    font-size: 9px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid #283a58;
}

QPushButton#SidebarToggleBtn {
    background-color: #121824;
    color: #94a3b8;
    border: 1px solid #1c2433;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 10px;
}
QPushButton#SidebarToggleBtn:hover {
    background-color: #1a2233;
    color: #ffffff;
    border-color: #38bdf8;
}

QLabel#SidebarCategory {
    font-size: 9px;
    font-weight: 800;
    color: #62728d;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    padding: 10px 14px 4px 14px;
}

QPushButton#SidebarNavBtn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-align: left;
    padding: 8px 14px;
    margin: 1px 8px;
}
QPushButton#SidebarNavBtn:hover {
    background-color: #131926;
    color: #f8fafc;
}
QPushButton#SidebarNavBtn[active="true"] {
    background-color: #162032;
    color: #38bdf8;
    font-weight: 700;
    border-left: 3px solid #38bdf8;
}

QWidget#SidebarUserBox {
    background-color: #0e131d;
    border: 1px solid #1c2433;
    border-radius: 8px;
    padding: 8px;
    margin: 8px;
}

/* ================= METRIC KPI CARDS ================= */
QFrame#MetricCard {
    background-color: #111622;
    border: 1px solid #1c2433;
    border-radius: 8px;
}
QFrame#MetricCard:hover {
    border-color: #38bdf8;
    background-color: #141b2a;
}

QLabel#MetricCardTitle {
    font-size: 10px;
    font-weight: 700;
    color: #8b9bb4;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#MetricCardValue {
    font-size: 20px;
    font-weight: 800;
    color: #f8fafc;
}

QLabel#MetricCardSubtitle {
    font-size: 10px;
    color: #62728d;
    font-weight: 500;
}

/* ================= BUTTONS ================= */
QPushButton {
    background-color: #151b28;
    color: #e2e8f0;
    border: 1px solid #232c3d;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #1d2638;
    border-color: #d4af37;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #0e131d;
}

QPushButton#PrimaryBtn {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
    font-weight: 700;
}
QPushButton#PrimaryBtn:hover {
    background-color: #0369a1;
    border-color: #38bdf8;
    color: #ffffff;
}
QPushButton#PrimaryBtn:pressed {
    background-color: #0c4a6e;
}

QPushButton#SuccessBtn {
    background-color: #0f3d2e;
    color: #34d399;
    border: 1px solid #10b981;
    font-weight: 600;
}
QPushButton#SuccessBtn:hover {
    background-color: #134e3b;
    color: #6ee7b7;
}

QPushButton#ExcelBtn {
    background-color: #151d2a;
    color: #e2e8f0;
    border: 1px solid #2a374f;
    font-weight: 600;
}
QPushButton#ExcelBtn:hover {
    background-color: #1e283a;
    border-color: #38bdf8;
    color: #ffffff;
}

QPushButton#DangerBtn {
    background-color: #3d1418;
    color: #f87171;
    border: 1px solid #ef4444;
}
QPushButton#DangerBtn:hover {
    background-color: #4f1a20;
    color: #fca5a5;
}

QPushButton#StageTabBtn {
    background-color: #0f1420;
    color: #8b9bb4;
    border: 1px solid #1c2433;
    border-radius: 6px;
    font-size: 11px;
    padding: 5px 12px;
}
QPushButton#StageTabBtn:hover {
    background-color: #151c2c;
    color: #f8fafc;
    border-color: #38bdf8;
}
QPushButton#StageTabBtn[active="true"] {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #38bdf8;
}

/* ================= INPUTS ================= */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f1420;
    color: #f8fafc;
    border: 1px solid #232c3d;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1.5px solid #38bdf8;
    background-color: #131928;
}

QComboBox {
    background-color: #0f1420;
    color: #f8fafc;
    border: 1px solid #232c3d;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 11px;
}
QComboBox:hover {
    border-color: #d4af37;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 0px;
}
QComboBox QAbstractItemView {
    background-color: #0e131d;
    color: #f8fafc;
    selection-background-color: #d4af37;
    selection-color: #0a0e16;
    border: 1px solid #232c3d;
}

/* ================= TABLES ================= */
QTableWidget, QTableView {
    background-color: #0e131d;
    alternate-background-color: #111724;
    color: #e2e8f0;
    gridline-color: #182030;
    border: 1px solid #1c2433;
    border-radius: 8px;
    selection-background-color: #1c2436;
    selection-color: #ffffff;
    font-size: 11px;
}

QTableWidget::item {
    padding: 5px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #1c2436;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #131a29;
    color: #f1f5f9;
    font-size: 11.5px;
    font-weight: 700;
    padding: 8px 6px;
    border: none;
    border-right: 1px solid #1c2433;
    border-bottom: 2px solid #28374d;
}

/* ================= TAB WIDGET ================= */
QTabWidget::pane {
    border: 1px solid #1c2433;
    background-color: #0e131d;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #111622;
    color: #8b9bb4;
    padding: 7px 14px;
    font-size: 11px;
    font-weight: 600;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #182030;
    color: #d4af37;
    font-weight: 700;
    border-top: 2px solid #d4af37;
}
QTabBar::tab:hover:!selected {
    background-color: #151c2c;
    color: #f8fafc;
}

/* ================= SCROLL BARS ================= */
QScrollBar:vertical {
    border: none;
    background-color: #0a0e16;
    width: 7px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #232c3d;
    min-height: 24px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background-color: #384660;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #0a0e16;
    height: 7px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #232c3d;
    min-width: 24px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #384660;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ================= SPLITTER ================= */
QSplitter::handle {
    background-color: #1c2433;
}
QSplitter::handle:hover {
    background-color: #d4af37;
}

/* ================= MENUS ================= */
QMenu {
    background-color: #0e131d;
    color: #f8fafc;
    border: 1px solid #232c3d;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px 6px 26px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #d4af37;
    color: #0a0e16;
    font-weight: 600;
}
QMenu::separator {
    height: 1px;
    background-color: #1c2433;
    margin: 4px 8px;
}

/* ================= STATUS BAR ================= */
QWidget#StatusBarWidget {
    background-color: #080c14;
    border-top: 1px solid #1c2433;
}

/* ================= SCROLL AREAS ================= */
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ================= MESSAGE BOX & SYSTEM DIALOGS ================= */
QMessageBox {
    background-color: #0e131d;
    border: 1px solid #232c3d;
    border-radius: 8px;
}

QMessageBox QLabel {
    color: #f8fafc;
    font-size: 12px;
    font-weight: 500;
    min-height: 40px;
    background-color: transparent;
}

QMessageBox QLabel#qt_msgbox_label {
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
}

QMessageBox QLabel#qt_msgbox_informativelabel {
    color: #8b9bb4;
    font-size: 11px;
}

QMessageBox QPushButton {
    background-color: #d4af37;
    color: #0a0e16;
    font-size: 11px;
    font-weight: 700;
    padding: 7px 22px;
    border-radius: 6px;
    border: 1px solid #c29e2f;
    min-width: 80px;
    min-height: 24px;
}

QMessageBox QPushButton:hover {
    background-color: #e5c158;
}

QMessageBox QPushButton:pressed {
    background-color: #b89528;
}
"""


def get_dark_palette():
    """Swiss Executive koyu renk paleti üretir."""
    try:
        from PyQt6.QtGui import QPalette, QColor
        palette = QPalette()
        dark_bg = QColor("#0c1017")
        dark_surface = QColor("#0e131d")
        card_bg = QColor("#111622")
        light_text = QColor("#f1f5f9")
        dim_text = QColor("#8b9bb4")
        accent = QColor("#d4af37")

        palette.setColor(QPalette.ColorRole.Window, dark_bg)
        palette.setColor(QPalette.ColorRole.WindowText, light_text)
        palette.setColor(QPalette.ColorRole.Base, dark_surface)
        palette.setColor(QPalette.ColorRole.AlternateBase, card_bg)
        palette.setColor(QPalette.ColorRole.ToolTipBase, card_bg)
        palette.setColor(QPalette.ColorRole.ToolTipText, light_text)
        palette.setColor(QPalette.ColorRole.Text, light_text)
        palette.setColor(QPalette.ColorRole.Button, card_bg)
        palette.setColor(QPalette.ColorRole.ButtonText, light_text)
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0a0e16"))
        palette.setColor(QPalette.ColorRole.PlaceholderText, dim_text)
        return palette
    except Exception:
        return None

