"""
theme.py — Merkezi renk ve stil sistemi
"""

# ─── Renk Paleti ───────────────────────────────────────────────────────────────
BG_BASE      = "#12151C"   # Ana arka plan
BG_PANEL     = "#1A1E28"   # Panel / card arka planı
BG_HEADER    = "#0E1117"   # Üst bant
BG_ROW_ALT   = "#1E2330"   # Tablo alternatif satır
BORDER       = "#2A3044"   # İnce kenarlık

TEXT_PRIMARY = "#D8DCE8"   # Ana metin
TEXT_DIM     = "#6B7280"   # İkincil metin / etiket
TEXT_WHITE   = "#FFFFFF"

# Durum renkleri — tutucu, mesleki
STATUS_RED    = "#C0392B"   # Kırmızı — Acil / Demuraj
STATUS_ORANGE = "#D35400"   # Turuncu — Banka ID
STATUS_PURPLE = "#7D3C98"   # Mor — TAREKS
STATUS_YELLOW = "#B7950B"   # Altın — Ordino
STATUS_BLUE   = "#1A5276"   # Lacivert — ETA
STATUS_GRAY   = "#4A5568"   # Gri — Kapalı/Pasif
STATUS_GREEN  = "#1E8449"   # Yeşil — Tamamlanan

# Vurgu — ince kullanım
ACCENT       = "#3B82F6"    # Buton / seçim

# ─── Stil Sabit Dizileri ───────────────────────────────────────────────────────
TAB_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}
QTabWidget::pane {{
    border: none;
    background-color: {BG_BASE};
}}
QTabBar::tab {{
    background-color: {BG_HEADER};
    color: {TEXT_DIM};
    font-size: 12px;
    font-weight: 500;
    padding: 9px 24px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    letter-spacing: 0.5px;
}}
QTabBar::tab:selected {{
    color: {TEXT_WHITE};
    border-bottom: 2px solid {ACCENT};
    background-color: {BG_PANEL};
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
    background-color: {BG_PANEL};
}}
QStatusBar {{
    background-color: {BG_HEADER};
    color: {TEXT_DIM};
    font-size: 11px;
    border-top: 1px solid {BORDER};
}}
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{
    background: {BG_PANEL};
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
}}
"""

HEADER_STYLE = f"""
    background-color: {BG_HEADER};
    border-bottom: 1px solid {BORDER};
"""

BUTTON_PRIMARY = f"""
QPushButton {{
    background-color: {ACCENT};
    color: {TEXT_WHITE};
    font-weight: 600;
    font-size: 12px;
    border-radius: 4px;
    padding: 7px 18px;
    border: none;
}}
QPushButton:hover {{ background-color: #2563EB; }}
QPushButton:pressed {{ background-color: #1D4ED8; }}
QPushButton:disabled {{ background-color: #374151; color: {TEXT_DIM}; }}
"""

BUTTON_GHOST = f"""
QPushButton {{
    background-color: transparent;
    color: {TEXT_DIM};
    font-weight: 500;
    font-size: 11px;
    border-radius: 4px;
    padding: 5px 14px;
    border: 1px solid {BORDER};
}}
QPushButton:hover {{ color: {TEXT_PRIMARY}; border-color: #4B5563; }}
QPushButton:checked {{ background-color: {BG_PANEL}; color: {TEXT_WHITE}; border-color: {ACCENT}; }}
"""
