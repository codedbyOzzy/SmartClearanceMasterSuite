"""
shipments_tab.py  — Yeniden tasarım: temiz, okunaklı tablo
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QPushButton, QAbstractItemView, QDialog,
    QTextEdit, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QBrush

from .data_loader import Durum
from .theme import (
    BG_BASE, BG_PANEL, BG_ROW_ALT, BORDER, TEXT_PRIMARY, TEXT_DIM, TEXT_WHITE,
    STATUS_RED, STATUS_ORANGE, STATUS_PURPLE, STATUS_YELLOW,
    STATUS_BLUE, STATUS_GRAY, ACCENT,
    BUTTON_GHOST,
)


# Durum → (satır arka plan, durum badge rengi, durum metni)
DURUM_MAP = {
    Durum.DEMURAJ_RISKI:   ("#1F1010", STATUS_RED,    "DEMURAJ"),
    Durum.BANKA_ID_BEKLER: ("#1A1208", STATUS_ORANGE, "BANKA ID"),
    Durum.TAREKS_DENETIM:  ("#160F1F", STATUS_PURPLE, "TAREKS"),
    Durum.ORDINO_BEKLER:   ("#191600", STATUS_YELLOW, "ORDİNO"),
    Durum.ETA_YAKLASAN:    ("#0D1520", STATUS_BLUE,   "ETA"),
    Durum.TESCIL_BEKLER:   (BG_PANEL,  STATUS_GRAY,   "TESCİL"),
    Durum.DOSYA_YOK:       (BG_BASE,   "#374151",     "—"),
    Durum.NORMAL:          (BG_BASE,   "#374151",     "—"),
}

# (Başlık, data_key, genişlik, hizalama)
COLUMNS = [
    ("DOSYA NO",   "dosya_no",      110, Qt.AlignmentFlag.AlignLeft),
    ("PO",         "po",            120, Qt.AlignmentFlag.AlignLeft),
    ("GEMİ",       "gemi",          180, Qt.AlignmentFlag.AlignLeft),
    ("LİMAN",      "liman",          80, Qt.AlignmentFlag.AlignCenter),
    ("VARIŞ",      "varis",          88, Qt.AlignmentFlag.AlignCenter),
    ("ETA",        "eta",            88, Qt.AlignmentFlag.AlignCenter),
    ("ORDİNO",     "ordino",         88, Qt.AlignmentFlag.AlignCenter),
    ("TAREKS",     "tareks_s",       88, Qt.AlignmentFlag.AlignCenter),
    ("DURUM",      "durum_label",   110, Qt.AlignmentFlag.AlignCenter),
    ("GÜN",        "gun_gecti",      52, Qt.AlignmentFlag.AlignCenter),
    ("NOT",        "aciklama",      220, Qt.AlignmentFlag.AlignLeft),
]

FILTER_DEFS = [
    ("Tümü",       None,                 None),
    ("Demuraj",    Durum.DEMURAJ_RISKI,  STATUS_RED),
    ("Banka ID",   Durum.BANKA_ID_BEKLER,STATUS_ORANGE),
    ("TAREKS",     Durum.TAREKS_DENETIM, STATUS_PURPLE),
    ("Ordino",     Durum.ORDINO_BEKLER,  STATUS_YELLOW),
    ("ETA < 7g",   Durum.ETA_YAKLASAN,   STATUS_BLUE),
    ("Dosya Yok",  Durum.DOSYA_YOK,      STATUS_GRAY),
]


class ShipmentsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_rows = []
        self._active_filter = None
        self.setStyleSheet(f"background-color: {BG_BASE};")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Üst toolbar ──────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet(f"background-color: {BG_PANEL}; border-bottom: 1px solid {BORDER};")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        tb_lay.setSpacing(8)

        # Filtre butonları
        self._filter_btns = []
        for label, durum, color in FILTER_DEFS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            if color:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {TEXT_DIM};
                        font-size: 11px;
                        font-weight: 500;
                        border-radius: 3px;
                        padding: 4px 12px;
                        border: 1px solid {BORDER};
                    }}
                    QPushButton:hover {{ color: {TEXT_PRIMARY}; border-color: {color}; }}
                    QPushButton:checked {{
                        background-color: transparent;
                        color: {color};
                        border-color: {color};
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {TEXT_DIM};
                        font-size: 11px;
                        font-weight: 500;
                        border-radius: 3px;
                        padding: 4px 12px;
                        border: 1px solid {BORDER};
                    }}
                    QPushButton:hover {{ color: {TEXT_PRIMARY}; }}
                    QPushButton:checked {{
                        background-color: {BG_BASE};
                        color: {TEXT_WHITE};
                        border-color: {ACCENT};
                        font-weight: 700;
                    }}
                """)
            btn.clicked.connect(lambda checked, d=durum, b=btn: self._set_filter(d, b))
            self._filter_btns.append(btn)
            tb_lay.addWidget(btn)
        self._filter_btns[0].setChecked(True)

        tb_lay.addStretch()

        # Arama
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Ara: Dosya No / PO / Gemi...")
        self.search_box.setFixedWidth(240)
        self.search_box.setFixedHeight(28)
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_BASE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)
        self.search_box.textChanged.connect(self._filter_table)
        tb_lay.addWidget(self.search_box)

        layout.addWidget(toolbar)

        # ── Tablo ────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._show_detail)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for i, (_, _, width, _) in enumerate(COLUMNS):
            self.table.setColumnWidth(i, width)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_BASE};
                color: {TEXT_PRIMARY};
                font-size: 12px;
                border: none;
                outline: none;
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background-color: {BG_PANEL};
                color: {TEXT_DIM};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 7px 6px;
                border: none;
                border-right: 1px solid {BORDER};
                border-bottom: 1px solid {BORDER};
            }}
            QTableWidget::item {{
                padding: 0 6px;
                border-bottom: 1px solid {BG_PANEL};
            }}
            QTableWidget::item:selected {{
                background-color: #1E3A5F;
                color: {TEXT_WHITE};
            }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.table)

        # ── Durum çubuğu ─────────────────────────────────────────────────────
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet(
            f"background-color: {BG_PANEL}; border-top: 1px solid {BORDER};"
        )
        sb_lay = QHBoxLayout(self.status_bar)
        sb_lay.setContentsMargins(16, 0, 16, 0)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        sb_lay.addWidget(self.lbl_status)
        layout.addWidget(self.status_bar)

    # ── Veri ─────────────────────────────────────────────────────────────────
    def update_data(self, rows: list, kpis: dict):
        self._all_rows = rows
        self._render_table(rows)
        self.lbl_status.setText(
            f"Toplam {len(rows)} aktif kayıt   |   "
            f"Demuraj: {kpis.get('demuraj',0)}   "
            f"Banka ID: {kpis.get('banka_id',0)}   "
            f"TAREKS: {kpis.get('tareks',0)}   "
            f"Ordino: {kpis.get('ordino',0)}   "
            f"ETA<7g: {kpis.get('eta_7',0)}"
        )

    def _render_table(self, rows: list):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))

        bold_font = QFont("Segoe UI", 10)
        bold_font.setWeight(QFont.Weight.DemiBold)

        mono_font = QFont("Consolas", 10)

        for row_idx, data in enumerate(rows):
            durum = data["durum"]
            bg_hex, badge_color, durum_text = DURUM_MAP.get(
                durum, (BG_BASE, STATUS_GRAY, "—")
            )
            bg = QColor(bg_hex)
            fg = QColor(TEXT_PRIMARY)

            col_values = [
                data["dosya_no"],
                data["po"],
                data["gemi"],
                data["liman"],
                data["varis"],
                data["eta"],
                data["ordino"],
                data["tareks_s"],
                durum_text,
                str(data["gun_gecti"]) if data["gun_gecti"] else "—",
                data["aciklama"],
            ]

            for col_idx, (_, _, _, align) in enumerate(COLUMNS):
                val = col_values[col_idx]
                item = QTableWidgetItem(val)
                item.setBackground(QBrush(bg))
                item.setTextAlignment(int(align) | int(Qt.AlignmentFlag.AlignVCenter))

                if col_idx == 0:  # Dosya no bold + mono
                    item.setFont(mono_font)
                    item.setForeground(QBrush(QColor(TEXT_WHITE)))
                elif col_idx == 8:  # Durum badge rengi
                    item.setForeground(QBrush(QColor(badge_color)))
                    item.setFont(bold_font)
                elif col_idx == 9:  # Gün sayısı
                    if durum in (Durum.DEMURAJ_RISKI,):
                        item.setForeground(QBrush(QColor(STATUS_RED)))
                        item.setFont(bold_font)
                    else:
                        item.setForeground(QBrush(QColor(TEXT_DIM)))
                elif col_idx == 10:  # Not
                    item.setForeground(QBrush(QColor(TEXT_DIM)))
                else:
                    item.setForeground(QBrush(fg))

                item.setData(Qt.ItemDataRole.UserRole, data)
                self.table.setItem(row_idx, col_idx, item)

        self.table.setSortingEnabled(True)

    def _filter_table(self, text: str = ""):
        text = text.strip().lower()
        rows = self._all_rows

        if self._active_filter:
            rows = [r for r in rows if r["durum"] == self._active_filter]

        if text:
            rows = [r for r in rows
                    if text in r["dosya_no"].lower()
                    or text in r["po"].lower()
                    or text in r["gemi"].lower()
                    or text in r["aciklama"].lower()]

        self._render_table(rows)

    def _set_filter(self, durum, clicked_btn):
        self._active_filter = durum
        for btn in self._filter_btns:
            btn.setChecked(btn == clicked_btn)
        self._filter_table(self.search_box.text())

    def _show_detail(self, index):
        item = self.table.item(index.row(), 0)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detay — {data['dosya_no']}")
        dlg.setMinimumSize(460, 380)
        dlg.setStyleSheet(f"background-color: {BG_PANEL}; color: {TEXT_PRIMARY};")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        rows_data = [
            ("Dosya No",     data["dosya_no"]),
            ("PO",           data["po"]),
            ("Gemi",         data["gemi"]),
            ("Liman",        data["liman"]),
            ("Varış",        data["varis"]),
            ("ETA",          data["eta"]),
            ("Ordino",       data["ordino"]),
            ("TAREKS Sonuç", data["tareks_s"]),
            ("Fiili Denetim",data["fiili_denetim"]),
            ("Tescil",       data["tescil"]),
            ("Not",          data["aciklama"]),
        ]

        for lbl, val in rows_data:
            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(0)

            lbl_w = QLabel(lbl)
            lbl_w.setFixedWidth(130)
            lbl_w.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")

            val_w = QLabel(str(val))
            val_w.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: 500;")
            val_w.setWordWrap(True)

            row_lay.addWidget(lbl_w)
            row_lay.addWidget(val_w, stretch=1)
            lay.addWidget(row_w)

        lay.addStretch()

        close_btn = QPushButton("Kapat")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_BASE};
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 6px 20px;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {TEXT_WHITE}; }}
        """)
        close_btn.clicked.connect(dlg.close)
        lay.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()
