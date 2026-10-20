"""
actions_tab.py — Yeniden tasarım: her aksiyon ne yapacağını açıkça gösterir
"""

import os, shutil, datetime, subprocess, openpyxl
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QSizePolicy, QFileDialog, QGridLayout,
    QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from .theme import (
    BG_BASE, BG_PANEL, BORDER, TEXT_PRIMARY, TEXT_DIM, TEXT_WHITE,
    STATUS_RED, STATUS_BLUE, STATUS_GREEN, ACCENT,
)

# ─── Dosya yolları ────────────────────────────────────────────────────────────
OTONOM_SABLON_DOLU  = r"C:\OTONOMAKTARIM_AYARLAR\Otonom_Sablon_Dolu.xlsx"
OTONOM_SABLON       = r"C:\OTONOMAKTARIM_AYARLAR\Otonom_Sablon.xlsx"
MASTERGTIP_VARSAYILAN = r"C:\Users\ozan.gemici\Downloads\mastergtip (16).xls"
ONCELIKLI_KLASOR    = r"C:\Users\ozan.gemici\Downloads\HANKOOK_ONCELIKLI_DOSYALAR"


def dosya_durumu(yol: str) -> tuple[str, str]:
    """Dosya var mı? (işaret, renk)"""
    if os.path.exists(yol):
        return "✓  Mevcut", "#22C55E"
    return "✗  Bulunamadı", "#EF4444"


# ─── Arka plan thread'i ───────────────────────────────────────────────────────
class CopyOtonomThread(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool, str)

    def __init__(self, kaynak, hedef):
        super().__init__()
        self.kaynak = kaynak
        self.hedef  = hedef

    def run(self):
        try:
            if not os.path.exists(self.kaynak):
                self.done.emit(False, f"Kaynak bulunamadı: {self.kaynak}")
                return
            try:
                with open(self.hedef, 'a'):
                    pass
            except PermissionError:
                self.done.emit(False,
                    f"{os.path.basename(self.hedef)} şu anda açık. Kapatın ve tekrar deneyin.")
                return
            shutil.copy2(self.kaynak, self.hedef)
            self.done.emit(True, f"Kopyalandı → {self.hedef}")
        except Exception as e:
            self.done.emit(False, str(e))


class MasterDataThread(QThread):
    log  = pyqtSignal(str)
    done = pyqtSignal(bool, str)

    def __init__(self, mastergtip_yolu: str, aktarim_klasoru: str):
        super().__init__()
        self.mastergtip  = mastergtip_yolu
        self.klasor      = aktarim_klasoru

    def run(self):
        try:
            import pandas as pd, re

            if not os.path.exists(self.mastergtip):
                self.done.emit(False, f"Mastergtip dosyası bulunamadı: {self.mastergtip}")
                return

            df = pd.read_html(self.mastergtip)[0]
            master = set()
            for raw in df.iloc[:, 0].astype(str):
                c = re.sub(r'[^\w]', '', raw).strip()
                if c.isdigit():
                    master.add(c)
            self.log.emit(f"Mastergtip okundu: {len(master)} CMMF kodu.")

            if not os.path.exists(self.klasor):
                self.done.emit(False, f"Aktarım klasörü bulunamadı: {self.klasor}")
                return

            eksik  = {}
            tamam  = 0
            dosya_sayisi = 0

            for root, _, files in os.walk(self.klasor):
                for f in files:
                    if not f.endswith("_Aktarim.xlsx"):
                        continue
                    dosya_sayisi += 1
                    wb = openpyxl.load_workbook(os.path.join(root, f), data_only=True)
                    for row in wb.active.iter_rows(min_row=2, values_only=True):
                        cmmf = str(row[8]).strip() if len(row) > 8 and row[8] else None
                        if not cmmf or cmmf == "None":
                            continue
                        if cmmf in master:
                            tamam += 1
                        else:
                            eksik.setdefault(cmmf, []).append(f)

            self.log.emit(f"Taranan aktarım exceli: {dosya_sayisi} dosya — {tamam} CMMF OK.")

            if eksik:
                self.log.emit(f"UYARI: {len(eksik)} CMMF masterdatada yok:")
                for c, fs in eksik.items():
                    self.log.emit(f"  CMMF {c}  ←  {', '.join(set(fs))}")
                self.done.emit(False, f"{len(eksik)} eksik CMMF bulundu.")
            else:
                self.done.emit(True, "Tüm CMMF kodları masterdatada mevcut.")

        except Exception as e:
            self.done.emit(False, str(e))


# ─── Ana widget ───────────────────────────────────────────────────────────────
class ActionsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_BASE};")
        self._threads = []   # thread referansları tutulur (GC'den korunmak için)
        self._build_ui()
        # Başlangıçta dosya durumlarını kontrol et
        QTimer.singleShot(300, self._refresh_file_status)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 16)
        outer.setSpacing(16)

        lbl = QLabel("OPERASYON AKSİYONLARI")
        lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700; letter-spacing: 2px;"
        )
        outer.addWidget(lbl)
        outer.addWidget(self._sep())

        # ── 2 Aksiyon Kartı (Robot + Master Data) üst sıra ──────────────────
        grid = QGridLayout()
        grid.setSpacing(12)

        # Kart 1: Robot Şablon
        c1, self.btn_robot = self._kart(
            "ROBOT ŞABLON GÜNCELLE",
            accent=STATUS_GREEN,
            btn_label="Güncelle",
        )
        # Kart içine dosya yolu göstergeleri ekle
        c1_lay = c1.layout()

        lbl_k = QLabel("KAYNAK DOSYA")
        lbl_k.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px; margin-top:6px;")
        c1_lay.insertWidget(1, lbl_k)

        self.lbl_kaynak_yol = QLabel(os.path.basename(OTONOM_SABLON_DOLU))
        self.lbl_kaynak_yol.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-family: Consolas;")
        c1_lay.insertWidget(2, self.lbl_kaynak_yol)

        self.lbl_kaynak_durum = QLabel("")
        self.lbl_kaynak_durum.setStyleSheet("font-size: 10px;")
        c1_lay.insertWidget(3, self.lbl_kaynak_durum)

        lbl_h = QLabel("HEDEF DOSYA")
        lbl_h.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px; margin-top:4px;")
        c1_lay.insertWidget(4, lbl_h)

        self.lbl_hedef_yol = QLabel(os.path.basename(OTONOM_SABLON))
        self.lbl_hedef_yol.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-family: Consolas;")
        c1_lay.insertWidget(5, self.lbl_hedef_yol)

        self.lbl_hedef_durum = QLabel("")
        self.lbl_hedef_durum.setStyleSheet("font-size: 10px;")
        c1_lay.insertWidget(6, self.lbl_hedef_durum)

        # Kart 2: Master Data
        c2, self.btn_master = self._kart(
            "MASTER DATA KONTROL",
            accent=STATUS_BLUE,
            btn_label="Kontrol Et",
        )
        c2_lay = c2.layout()

        lbl_mgt = QLabel("MASTERGTİP DOSYASI")
        lbl_mgt.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px; margin-top:6px;")
        c2_lay.insertWidget(1, lbl_mgt)

        self.lbl_mgt_yol = QLabel(os.path.basename(MASTERGTIP_VARSAYILAN))
        self.lbl_mgt_yol.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-family: Consolas;")
        c2_lay.insertWidget(2, self.lbl_mgt_yol)

        self.lbl_mgt_durum = QLabel("")
        self.lbl_mgt_durum.setStyleSheet("font-size: 10px;")
        c2_lay.insertWidget(3, self.lbl_mgt_durum)

        lbl_ak = QLabel("AKTARIM KLASÖRü")
        lbl_ak.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px; margin-top:4px;")
        c2_lay.insertWidget(4, lbl_ak)

        # Klasör seç satırı
        klasor_row = QWidget()
        kl_lay = QHBoxLayout(klasor_row)
        kl_lay.setContentsMargins(0, 0, 0, 0)
        kl_lay.setSpacing(6)

        self.lbl_klasor = QLabel(os.path.basename(ONCELIKLI_KLASOR))
        self.lbl_klasor.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-family: Consolas;")
        kl_lay.addWidget(self.lbl_klasor, stretch=1)

        btn_sec = QPushButton("Değiştir")
        btn_sec.setFixedHeight(22)
        btn_sec.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 2px;
                padding: 0 8px;
                font-size: 9px;
            }}
            QPushButton:hover {{ color: {TEXT_WHITE}; }}
        """)
        btn_sec.clicked.connect(self._klasor_sec)
        kl_lay.addWidget(btn_sec)
        c2_lay.insertWidget(5, klasor_row)

        self.lbl_klasor_durum = QLabel("")
        self.lbl_klasor_durum.setStyleSheet("font-size: 10px;")
        c2_lay.insertWidget(6, self.lbl_klasor_durum)

        self._aktarim_klasoru = ONCELIKLI_KLASOR
        self._mastergtip_yolu = MASTERGTIP_VARSAYILAN

        # Kart 3: Klasör Aç
        c3, self.btn_klasor = self._kart(
            "ÖNCELİKLİ DOSYALAR",
            accent=ACCENT,
            btn_label="Windows Gezgini'nde Aç",
        )
        c3_lay = c3.layout()
        lbl_klasor_yol = QLabel(ONCELIKLI_KLASOR)
        lbl_klasor_yol.setWordWrap(True)
        lbl_klasor_yol.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-family: Consolas; margin-top:6px;")
        c3_lay.insertWidget(1, lbl_klasor_yol)

        grid.addWidget(c1, 0, 0)
        grid.addWidget(c2, 0, 1)
        grid.addWidget(c3, 0, 2)
        outer.addLayout(grid)

        outer.addWidget(self._sep())

        # Log
        lbl_log = QLabel("İŞLEM LOGU")
        lbl_log.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
        )
        outer.addWidget(lbl_log)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_PANEL};
                color: {TEXT_PRIMARY};
                font-family: 'Consolas', monospace;
                font-size: 11px;
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 10px 14px;
            }}
        """)
        outer.addWidget(self.log_box, stretch=1)

        self.btn_robot.clicked.connect(self._robot_guncelle)
        self.btn_master.clicked.connect(self._master_kontrol)
        self.btn_klasor.clicked.connect(self._klasor_ac)

    @staticmethod
    def _kart(baslik: str, accent: str, btn_label: str) -> tuple:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER};
                border-top: 2px solid {accent};
                border-radius: 4px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        lbl = QLabel(baslik)
        lbl.setStyleSheet(
            f"color: {TEXT_WHITE}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;"
        )
        lay.addWidget(lbl)

        lay.addStretch()

        btn = QPushButton(btn_label)
        btn.setFixedHeight(28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {accent};
                border: 1px solid {accent};
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {accent}; color: {TEXT_WHITE}; }}
            QPushButton:disabled {{ border-color: #374151; color: #374151; }}
        """)
        lay.addWidget(btn)

        return card, btn

    @staticmethod
    def _sep():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER}; border: none;")
        return line

    def _refresh_file_status(self):
        """Başlangıçta ve her güncellemede dosya durumlarını kontrol eder."""
        def set_lbl(lbl, yol):
            txt, clr = dosya_durumu(yol)
            lbl.setText(txt)
            lbl.setStyleSheet(f"color: {clr}; font-size: 10px;")

        set_lbl(self.lbl_kaynak_durum, OTONOM_SABLON_DOLU)
        set_lbl(self.lbl_hedef_durum,  OTONOM_SABLON)
        set_lbl(self.lbl_mgt_durum,    self._mastergtip_yolu)
        set_lbl(self.lbl_klasor_durum, self._aktarim_klasoru)

        # Butonları dosya var/yok durumuna göre etkinleştir/devre dışı bırak
        self.btn_robot.setEnabled(os.path.exists(OTONOM_SABLON_DOLU))
        self.btn_master.setEnabled(
            os.path.exists(self._mastergtip_yolu) and
            os.path.exists(self._aktarim_klasoru)
        )

    def update_data(self, rows, kpis):
        self._refresh_file_status()

    def _log(self, msg: str, color: str = None):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        if color:
            self.log_box.append(
                f'<span style="color:{TEXT_DIM}">[{ts}]</span>'
                f'  <span style="color:{color}">{msg}</span>'
            )
        else:
            self.log_box.append(f'<span style="color:{TEXT_DIM}">[{ts}]</span>  {msg}')

    # ── Aksiyon 1: Robot Şablon ───────────────────────────────────────────────
    def _robot_guncelle(self):
        self.btn_robot.setEnabled(False)
        self._log(f"Kopyalanıyor: {OTONOM_SABLON_DOLU}")
        self._log(f"         → : {OTONOM_SABLON}")
        t = CopyOtonomThread(OTONOM_SABLON_DOLU, OTONOM_SABLON)
        t.log.connect(self._log)
        t.done.connect(self._robot_done)
        t.start()
        self._threads.append(t)

    def _robot_done(self, ok: bool, msg: str):
        self.btn_robot.setEnabled(True)
        clr = STATUS_GREEN if ok else STATUS_RED
        self._log(("OK: " if ok else "HATA: ") + msg, color=clr)
        self._refresh_file_status()

    # ── Aksiyon 2: Master Data ────────────────────────────────────────────────
    def _klasor_sec(self):
        klasor = QFileDialog.getExistingDirectory(
            self, "Aktarım Klasörünü Seç", self._aktarim_klasoru
        )
        if klasor:
            self._aktarim_klasoru = klasor
            self.lbl_klasor.setText(os.path.basename(klasor))
            self._refresh_file_status()

    def _master_kontrol(self):
        self.btn_master.setEnabled(False)
        self._log(f"Mastergtip: {os.path.basename(self._mastergtip_yolu)}")
        self._log(f"Aktarım klasörü: {self._aktarim_klasoru}")
        t = MasterDataThread(self._mastergtip_yolu, self._aktarim_klasoru)
        t.log.connect(self._log)
        t.done.connect(self._master_done)
        t.start()
        self._threads.append(t)

    def _master_done(self, ok: bool, msg: str):
        self.btn_master.setEnabled(True)
        clr = STATUS_GREEN if ok else STATUS_RED
        self._log(("OK: " if ok else "UYARI: ") + msg, color=clr)

    # ── Aksiyon 3: Klasör Aç ─────────────────────────────────────────────────
    def _klasor_ac(self):
        if os.path.exists(ONCELIKLI_KLASOR):
            subprocess.Popen(f'explorer "{ONCELIKLI_KLASOR}"')
            self._log("Klasör açıldı.")
        else:
            self._log(f"HATA: Klasör bulunamadı: {ONCELIKLI_KLASOR}", color=STATUS_RED)
