"""
apex_stepper.py — SmartClearance Apex Görsel İş Akışı ve İlerleme Şeridi (Linear Stepper)
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt
from .apex_theme import (
    BG_CARD, BG_INPUT, BORDER_SUBTLE, TEXT_WHITE, TEXT_PRIMARY, TEXT_MUTED,
    COLOR_CYAN, COLOR_GREEN, COLOR_RED, COLOR_ORANGE, COLOR_SLATE
)

STEPS = [
    {"num": 1, "title": "Seyirde",      "sub": "ETA Takip"},
    {"num": 2, "title": "Limanda",      "sub": "Tahliye"},
    {"num": 3, "title": "Ordino",       "sub": "Acenta"},
    {"num": 4, "title": "TAREKS",       "sub": "Denetim"},
    {"num": 5, "title": "Tescil/Banka", "sub": "Beyanname"},
    {"num": 6, "title": "Kapanış",      "sub": "Liman Çıkış"}
]


class ApexStepperWidget(QFrame):
    """Her dosya için 'Hangi adımdayım, sırada ne var?' sorusunu görselleştiren şerit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            ApexStepperWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # ── 1. Üst Başlık & Aşama Rozeti ──────────────────────────────────────
        header_box = QHBoxLayout()
        header_box.setSpacing(6)

        lbl_title = QLabel("OPERASYON SÜREÇ İLERLEMESİ")
        lbl_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.8px;")
        header_box.addWidget(lbl_title)
        header_box.addStretch(1)

        self.lbl_stage_badge = QLabel("Aşama 1 / 6")
        self.lbl_stage_badge.setStyleSheet(f"""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid rgba(56, 189, 248, 0.25);
        """)
        header_box.addWidget(self.lbl_stage_badge)
        main_layout.addLayout(header_box)

        # ── 2. Stepper Düğümleri (6 Adım) ──────────────────────────────────────
        self.nodes_box = QHBoxLayout()
        self.nodes_box.setSpacing(4)

        self.node_widgets = []
        for idx, s in enumerate(STEPS):
            node = self._create_step_node(s["num"], s["title"], s["sub"])
            self.nodes_box.addWidget(node)
            self.node_widgets.append(node)

            if idx < len(STEPS) - 1:
                line = QFrame()
                line.setFixedHeight(2)
                line.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
                self.nodes_box.addWidget(line, 1)

        main_layout.addLayout(self.nodes_box)

        # ── 3. "Sıradaki Hamle" Rehber Kutusu ─────────────────────────────────
        self.action_box = QFrame()
        self.action_box.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_INPUT};
                border: 1px solid rgba(56, 189, 248, 0.2);
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        action_layout = QHBoxLayout(self.action_box)
        action_layout.setContentsMargins(8, 4, 8, 4)
        action_layout.setSpacing(8)

        self.lbl_action_icon = QLabel("💡")
        self.lbl_action_icon.setStyleSheet("font-size: 14px;")
        action_layout.addWidget(self.lbl_action_icon)

        self.lbl_action_text = QLabel("Dosya seçildiğinde sıradaki operasyon adımı burada gösterilecektir.")
        self.lbl_action_text.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: 600;")
        self.lbl_action_text.setWordWrap(True)
        action_layout.addWidget(self.lbl_action_text, 1)

        main_layout.addWidget(self.action_box)

    def _create_step_node(self, num, title, sub):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel(str(num))
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            background-color: {BG_INPUT};
            color: {TEXT_MUTED};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 11px;
            font-size: 10px;
            font-weight: 700;
        """)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 600;")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_s = QLabel(sub)
        lbl_s.setStyleSheet("color: #64748b; font-size: 9px;")
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_t, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_s, 0, Qt.AlignmentFlag.AlignCenter)

        w.badge = badge
        w.lbl_title = lbl_t
        w.lbl_sub = lbl_s
        return w

    def set_stage(self, stage: int, next_action: str, durum: str = ""):
        """Belirtilen aşamaya göre düğümleri ve eylem kutusunu günceller."""
        stage = max(1, min(6, stage))
        self.lbl_stage_badge.setText(f"Aşama {stage} / 6")

        for idx, node in enumerate(self.node_widgets):
            step_num = idx + 1
            if step_num < stage:
                # Geçilmiş / Tamamlanmış aşama
                node.badge.setText("✓")
                node.badge.setStyleSheet(f"""
                    background-color: rgba(52, 211, 153, 0.15);
                    color: {COLOR_GREEN};
                    border: 1px solid {COLOR_GREEN};
                    border-radius: 11px;
                    font-size: 10px;
                    font-weight: 800;
                """)
                node.lbl_title.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 10px; font-weight: 600;")
            elif step_num == stage:
                # Aktif aşama
                color = COLOR_RED if "DEMURAJ" in durum else (COLOR_ORANGE if "BANKA" in durum else COLOR_CYAN)
                bg_c = "rgba(244, 63, 94, 0.18)" if "DEMURAJ" in durum else ("rgba(251, 146, 60, 0.18)" if "BANKA" in durum else "rgba(56, 189, 248, 0.18)")
                node.badge.setText(str(step_num))
                node.badge.setStyleSheet(f"""
                    background-color: {bg_c};
                    color: {color};
                    border: 1.5px solid {color};
                    border-radius: 11px;
                    font-size: 10px;
                    font-weight: 800;
                """)
                node.lbl_title.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 700;")
            else:
                # Bekleyen aşama
                node.badge.setText(str(step_num))
                node.badge.setStyleSheet(f"""
                    background-color: {BG_INPUT};
                    color: {COLOR_SLATE};
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 11px;
                    font-size: 10px;
                    font-weight: 600;
                """)
                node.lbl_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 500;")

        # Eylem Kutusu Metni ve Rengi
        if "DEMURAJ" in durum:
            self.lbl_action_icon.setText("🚨")
            self.action_box.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(244, 63, 94, 0.08);
                    border: 1px solid rgba(244, 63, 94, 0.35);
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """)
            self.lbl_action_text.setStyleSheet("color: #fda4af; font-size: 11px; font-weight: 600;")
        elif "BANKA" in durum:
            self.lbl_action_icon.setText("🏦")
            self.action_box.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(251, 146, 60, 0.08);
                    border: 1px solid rgba(251, 146, 60, 0.35);
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """)
            self.lbl_action_text.setStyleSheet("color: #fed7aa; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_action_icon.setText("💡")
            self.action_box.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_INPUT};
                    border: 1px solid rgba(56, 189, 248, 0.25);
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """)
            self.lbl_action_text.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: 600;")

        self.lbl_action_text.setText(f"SIRADAKİ HAMLE: {next_action}")
