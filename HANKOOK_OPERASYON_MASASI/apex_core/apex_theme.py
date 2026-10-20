"""
apex_theme.py — SmartClearance Apex Ultra-Clean Linear & Dark Obsidian Tasarım Sistemi
"""

# ─── Renk Paleti (Linear / Dark Obsidian) ─────────────────────────────────────
BG_DEEP       = "#090d16"   # En koyu arka plan (Pencere tabanı)
BG_BASE       = "#0d1320"   # Panel tabanı
BG_CARD       = "#121929"   # Kart ve panel arka planı
BG_CARD_HOVER = "#182238"   # Hover kart
BG_INPUT      = "#141c2e"   # Giriş kutusu arka planı
BORDER_SUBTLE = "rgba(255, 255, 255, 0.07)"
BORDER_FOCUS  = "#38bdf8"

TEXT_WHITE    = "#f8fafc"
TEXT_PRIMARY  = "#e2e8f0"
TEXT_MUTED    = "#94a3b8"
TEXT_DIM      = "#64748b"

# Durum ve Vurgu Renkleri
COLOR_RED     = "#f43f5e"   # Demuraj Riski / Acil
COLOR_ORANGE  = "#fb923c"   # Banka ID Bekliyor
COLOR_PURPLE  = "#c084fc"   # TAREKS Denetim
COLOR_YELLOW  = "#facc15"   # Ordino Bekliyor
COLOR_CYAN    = "#38bdf8"   # ETA Yaklaşan / Vurgu
COLOR_GREEN   = "#34d399"   # Tescilli / Başarılı
COLOR_SLATE   = "#64748b"   # Dosya Yok / Nötr

# ─── Ana QSS Teması ───────────────────────────────────────────────────────────
APEX_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI';
    font-size: 12px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
}}
QSplitter::handle:hover {{
    background-color: {COLOR_CYAN};
}}
QSplitter::handle:horizontal {{
    width: 6px;
}}
QSplitter::handle:vertical {{
    height: 6px;
}}

/* ── Tab Bar ── */
QTabWidget::pane {{
    border: 1px solid {BORDER_SUBTLE};
    background-color: {BG_BASE};
    border-radius: 8px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: {BG_DEEP};
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 600;
    padding: 7px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid transparent;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    color: {TEXT_WHITE};
    background-color: {BG_BASE};
    border: 1px solid {BORDER_SUBTLE};
    border-bottom: 2px solid {COLOR_CYAN};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_WHITE};
    background-color: {BG_CARD};
}}

/* ── Tablo ── */
QTableWidget {{
    background-color: {BG_BASE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.03);
    selection-background-color: rgba(56, 189, 248, 0.12);
    selection-color: {TEXT_WHITE};
    outline: none;
    font-size: 11.5px;
}}
QTableWidget::item {{
    padding: 5px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}}
QTableWidget::item:selected {{
    background-color: rgba(56, 189, 248, 0.14);
    border-left: 2px solid {COLOR_CYAN};
}}
QTableWidget::item:hover {{
    background-color: rgba(255, 255, 255, 0.02);
}}
QHeaderView::section {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    padding: 7px 8px;
    border: none;
    border-bottom: 1px solid {BORDER_SUBTLE};
}}

/* ── Giriş Kutuları ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_WHITE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11.5px;
    selection-background-color: {COLOR_CYAN};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLOR_CYAN};
    background-color: #172136;
}}

/* ── Butonlar ── */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_WHITE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 11.5px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {BG_CARD_HOVER};
    border: 1px solid rgba(255, 255, 255, 0.18);
}}
QPushButton:pressed {{
    background-color: #111726;
}}
QPushButton#btnPrimary {{
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
    font-weight: 700;
}}
QPushButton#btnPrimary:hover {{
    background-color: #0369a1;
    border-color: #7dd3fc;
}}
QPushButton#btnSuccess {{
    background-color: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.4);
    font-weight: 700;
}}
QPushButton#btnSuccess:hover {{
    background-color: rgba(16, 185, 129, 0.25);
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: {BG_DEEP};
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #334155;
    border-radius: 3px;
    min-height: 25px;
}}
QScrollBar::handle:vertical:hover {{
    background: #475569;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {BG_DEEP};
    height: 6px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #334155;
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    height: 0px;
}}
"""
