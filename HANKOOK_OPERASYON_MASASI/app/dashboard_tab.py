"""
dashboard_tab.py  — Yeniden tasarım: kurumsal / minimal
"""

import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt

from .data_loader import Durum
from .theme import (
    BG_BASE, BG_PANEL, BORDER, TEXT_PRIMARY, TEXT_DIM, TEXT_WHITE,
    STATUS_RED, STATUS_ORANGE, STATUS_PURPLE,
    STATUS_YELLOW, STATUS_BLUE, STATUS_GRAY,
)


KPI_DEFS = [
    ("demuraj",   "DEMURAJ RİSKİ",    STATUS_RED,    "7+ gün limanda"),
    ("banka_id",  "BANKA ID BEKLER",   STATUS_ORANGE, "Tescil bekliyor"),
    ("tareks",    "TAREKS DENETİM",    STATUS_PURPLE, "Fiili denetimde"),
    ("ordino",    "ORDİNO BEKLER",     STATUS_YELLOW, "Ordino bekleniyor"),
    ("eta_7",     "ETA < 7 GÜN",       STATUS_BLUE,   "Gelecek hafta"),
    ("dosya_yok", "DOSYA AÇILMADI",    STATUS_GRAY,   "Atanmamış PO"),
]


class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value_labels = {}
        self.setStyleSheet(f"background-color: {BG_BASE};")
        self._build_ui()

    # ── UI İnşası ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(18)

        # Başlık satırı
        top_row = QHBoxLayout()
        lbl_title = QLabel("GÜNLÜK OPERASYON ÖZETİ")
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;"
            f" letter-spacing: 2px;"
        )
        top_row.addWidget(lbl_title)
        top_row.addStretch()
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        top_row.addWidget(self.lbl_meta)
        outer.addLayout(top_row)

        # İnce yatay çizgi
        outer.addWidget(self._separator())

        # KPI Kartları — 6 kart, tek satır
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        for key, label, color, sub in KPI_DEFS:
            card, val_lbl = self._make_kpi_card(label, color, sub)
            self._value_labels[key] = val_lbl
            kpi_row.addWidget(card)
        outer.addLayout(kpi_row)

        outer.addWidget(self._separator())

        # Brifing başlığı
        lbl_brifing_title = QLabel("GÜNLÜK OPERASYON BRİFİNGİ")
        lbl_brifing_title.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 11px; font-weight: 700; letter-spacing: 2px;"
        )
        outer.addWidget(lbl_brifing_title)

        # Brifing scroll alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {BG_BASE}; }}")

        inner = QWidget()
        inner.setStyleSheet(f"background: {BG_BASE};")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 8, 0)

        self.lbl_brifing = QLabel("Veri yükleniyor...")
        self.lbl_brifing.setWordWrap(True)
        self.lbl_brifing.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_brifing.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_brifing.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_PRIMARY};
                font-size: 12px;
                line-height: 1.8;
                background-color: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 16px 20px;
            }}
        """)
        inner_lay.addWidget(self.lbl_brifing)
        inner_lay.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)

    @staticmethod
    def _make_kpi_card(label: str, color: str, sub: str):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER};
                border-top: 3px solid {color};
                border-radius: 4px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setFixedHeight(90)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        lbl_name = QLabel(label)
        lbl_name.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;"
        )
        lay.addWidget(lbl_name)

        lbl_val = QLabel("—")
        lbl_val.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")
        lay.addWidget(lbl_val)

        lbl_sub = QLabel(sub)
        lbl_sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px;")
        lay.addWidget(lbl_sub)

        return card, lbl_val

    @staticmethod
    def _separator():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER}; border: none;")
        return line

    # ── Veri güncellemesi ──────────────────────────────────────────────────────
    def update_data(self, rows: list, kpis: dict):
        self.lbl_meta.setText(
            f"Güncelleme: {kpis.get('tarih', '—')}   |   "
            f"Toplam aktif: {kpis.get('toplam', 0)}"
        )
        for key, _, _, _ in KPI_DEFS:
            lbl = self._value_labels.get(key)
            if lbl:
                lbl.setText(str(kpis.get(key, 0)))
        self._update_brifing(rows)

    def _update_brifing(self, rows: list):
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        parts = []

        def section(color, label, items, formatter):
            if not items:
                return
            parts.append(
                f"<p style='margin:0 0 4px 0;'>"
                f"<span style='color:{color}; font-size:10px; font-weight:700; "
                f"letter-spacing:1.5px;'>&#9632; {label} ({len(items)})</span></p>"
            )
            for r in items:
                parts.append(
                    f"<p style='margin:0 0 2px 14px; color:{TEXT_DIM}; font-size:11px;'>"
                    f"{formatter(r)}</p>"
                )
            parts.append("<p style='margin:0 0 10px 0;'></p>")

        dem  = [r for r in rows if r["durum"] == Durum.DEMURAJ_RISKI]
        bank = [r for r in rows if r["durum"] == Durum.BANKA_ID_BEKLER]
        tar  = [r for r in rows if r["durum"] == Durum.TAREKS_DENETIM]
        ord_ = [r for r in rows if r["durum"] == Durum.ORDINO_BEKLER]
        eta_ = [r for r in rows if r["durum"] == Durum.ETA_YAKLASAN]
        tes  = [r for r in rows if r["durum"] == Durum.TESCIL_BEKLER]

        header = (
            f"<p style='margin:0 0 12px 0; color:{TEXT_DIM}; font-size:10px; "
            f"letter-spacing:1px;'>{today_str}</p>"
        )
        parts.append(header)

        section(STATUS_RED, "DEMURAJ RİSKİ", dem,
                lambda r: f"<b style='color:{TEXT_PRIMARY}'>{r['dosya_no']}</b>"
                          f"  {r['gemi']}  —  Varış: {r['varis']}  —  "
                          f"<b style='color:{STATUS_RED}'>{r['gun_gecti']} gün geçti</b>")

        section(STATUS_ORANGE, "BANKA ID BEKLEYEN", bank,
                lambda r: f"<b style='color:{TEXT_PRIMARY}'>{r['dosya_no']}</b>"
                          f"  {r['gemi']}  —  PO: {r['po']}")

        section(STATUS_PURPLE, "TAREKS FİİLİ DENETİMDE", tar,
                lambda r: f"<b style='color:{TEXT_PRIMARY}'>{r['dosya_no']}</b>"
                          f"  {r['gemi']}  —  {r['fiili_denetim']}  —  {r['aciklama']}")

        section(STATUS_YELLOW, "ORDİNO BEKLEYEN", ord_,
                lambda r: f"<b style='color:{TEXT_PRIMARY}'>{r['dosya_no']}</b>"
                          f"  {r['gemi']}  —  Varış: {r['varis']}")

        section(STATUS_BLUE, "YAKLAŞAN ETA (7 GÜN)", eta_,
                lambda r: f"<b style='color:{TEXT_PRIMARY}'>{r['dosya_no']}</b>"
                          f"  {r['gemi']}  —  ETA: {r['eta']}  —  {r['gun_gecti']} gün kaldı")

        section(STATUS_GRAY, "TESCİL / KAPANIŞ BEKLEYEN", tes,
                lambda r: f"<b style='color:{TEXT_PRIMARY}'>{r['dosya_no']}</b>"
                          f"  —  Tescil: {r['tescil']}")

        if not any([dem, bank, tar, ord_, eta_, tes]):
            parts.append(
                f"<p style='color:{TEXT_DIM}; font-size:12px;'>"
                "Bugün için bekleyen kritik operasyon bulunmuyor.</p>"
            )

        self.lbl_brifing.setText("".join(parts))
