"""
================================================================================
SMARTCLEARANCE HORIZON — KÜRESEL KONTEYNER & CANLI ETA VARIŞ RADARI (v1.0 Pro)
================================================================================
Marka       : SmartClearance
Tasarım     : Dark Obsidian / Modern Maritime Aesthetic
Teknoloji   : PyQt6 + QtWebEngineCore + Leaflet Dark Maritime
Özellikler  :
  - Esnek, Ayarlanabilir Genişlikli (QSplitter) Çift Panel
  - Kırpılmayan, Genişletilebilir ve Sıralanabilir Yük Tablosu (Interactive Columns)
  - İnteraktif Gömülü Koyu Rota Haritası (CMA CGM GeoJSON & Anlık AIS Konumu)
  - Sıfır Hata Garantili Yerel Leaflet Motoru & Güvenli JS Yaşam Döngüsü
  - Linear Tarzı KPI Sayaç Kartları ve Akıllı Arama
================================================================================
"""

import os
import sys
import json
import time
import math
import re
from datetime import datetime, date

# Ana dizin import yolu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer, QSize, QPoint, QEvent
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QScrollArea, QDialog, QFileDialog,
    QMessageBox, QMenu, QProgressBar, QCheckBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# global_eta_radar'dan mevcut motorları ve yardımcı fonksiyonları miras al
from global_eta_radar import (
    GlobalTrackingRouter, load_config, save_config, load_cache, save_cache,
    resolve_excel_path, compute_eta_diff, parse_date, normalize_turkish,
    CARRIER_PREFIX_MAP, openpyxl, Font, PatternFill, Alignment, Border, Side
)
from horizon_pdf_generator import HorizonPdfGenerator

MAP_HTML_PATH = os.path.join(BASE_DIR, "horizon_map_template.html")


# ==============================================================================
# LINEAR / APPLE DARK QSS TEMASI (FERAH & GELİŞMİŞ)
# ==============================================================================

HORIZON_STYLESHEET = """
QWidget {
    background-color: #080b11;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
    font-size: 13px;
}

/* Header */
#headerFrame {
    background-color: #0f1523;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 10px 16px;
}

#brandTitle {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
}

#brandBadge {
    background-color: #0284c7;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.5px;
}

QPushButton#brandBadgeBtn {
    background-color: #0284c7;
    color: #ffffff;
    font-size: 10.5px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 5px;
    border: 1px solid #38bdf8;
    letter-spacing: 0.5px;
}
QPushButton#brandBadgeBtn:hover {
    background-color: #0369a1;
    border-color: #7dd3fc;
}

#statusPill {
    background-color: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
}

/* Linear KPI Kartları */
.kpiCard {
    background-color: #111726;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    padding: 10px 16px;
}
.kpiTitle {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.kpiValue {
    font-size: 22px;
    font-weight: 800;
    color: #f8fafc;
    margin-top: 2px;
}

/* Butonlar */
QPushButton {
    background-color: #1a2336;
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    padding: 7px 13px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #243049;
    border-color: rgba(255, 255, 255, 0.22);
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton#btnPrimary {
    background-color: #0284c7;
    border-color: #0369a1;
    color: #ffffff;
}
QPushButton#btnPrimary:hover {
    background-color: #0369a1;
}

/* Arama Kutusu */
QLineEdit {
    background-color: #111726;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 7px;
    padding: 6px 12px;
    color: #f8fafc;
    font-size: 12px;
}
QLineEdit:focus {
    border-color: #38bdf8;
    background-color: #131b2e;
}

/* Filtre Hapları */
QPushButton.filterPill {
    background-color: transparent;
    color: #94a3b8;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton.filterPill:hover {
    color: #f8fafc;
    background-color: rgba(255, 255, 255, 0.05);
}
QPushButton.filterPill[selected="true"] {
    background-color: rgba(56, 189, 248, 0.16);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 0.45);
}

/* Tablo */
QTableWidget {
    background-color: #0b0f19;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.03);
    selection-background-color: rgba(56, 189, 248, 0.16);
    selection-color: #ffffff;
    outline: none;
}
QHeaderView::section {
    background-color: #101624;
    color: #94a3b8;
    font-weight: 700;
    font-size: 11px;
    padding: 8px 8px;
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 0.04);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background-color: #151e32;
    color: #38bdf8;
}
QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

/* QSplitter Handle (Kullanıcı Tarafından Kolayca Çekilebilen Ayırıcı) */
QSplitter::handle:horizontal {
    background-color: #151d2e;
    width: 7px;
    margin: 0px 1px;
    border-left: 1px solid rgba(255, 255, 255, 0.08);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
QSplitter::handle:horizontal:hover {
    background-color: #0284c7;
    border-color: #38bdf8;
}

/* Sağ Panel (Kokpit) */
#rightCockpit {
    background-color: #0e1422;
}
#shipmentCard {
    background-color: #131b2c;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 12px;
}

QScrollBar:vertical {
    background: #080b11;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #1e293b;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #38bdf8;
}
QScrollBar:horizontal {
    background: #080b11;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #1e293b;
    border-radius: 4px;
}
"""


# ==============================================================================
# ARKA PLAN TARAMA İŞÇİSİ (QTHREAD)
# ==============================================================================

class BackgroundScanner(QThread):
    progress_signal = pyqtSignal(str, int, int)
    completed_signal = pyqtSignal(list, int, int)

    def __init__(self, router, mode="excel", target_path="", existing_data=None):
        super().__init__()
        self.router = router
        self.mode = mode
        self.target_path = target_path
        self.existing_data = existing_data or []

    def run(self):
        if self.mode == "memory":
            self._scan_memory()
        elif self.mode == "excel":
            self._scan_excel()

    def _scan_memory(self):
        targets = []
        for it in self.existing_data:
            if not it.get("is_active", True):
                continue
            cntr = it.get("container_no", "")
            bl = it.get("bl_no", "")
            carrier = it.get("carrier", "")
            q = cntr if cntr and cntr != "—" else bl
            if q and q != "—":
                c = self.router.detect_carrier(q, acenta_hint=carrier)
                if c in ["HAPAG", "MSC", "CMA-CGM"]:
                    targets.append((q, it, c))

        total = len(targets)
        success_count = 0
        for i, (q, it, c) in enumerate(targets, 1):
            self.progress_signal.emit(f"[{i}/{total}] {q} ({c}) canlı taranıyor...", i, total)
            res = self.router.track(q, acenta_hint=it.get("carrier"), excel_eta=it.get("excel_eta"))
            if res and res.get("success") and res.get("items"):
                fresh = res["items"][0]
                it["carrier"] = fresh.get("carrier", it.get("carrier"))
                it["live_eta"] = fresh.get("live_eta", it.get("live_eta"))
                it["eta_diff"] = fresh.get("eta_diff", it.get("eta_diff"))
                it["diff_tag"] = fresh.get("diff_tag", it.get("diff_tag"))
                it["kalan_gun"] = fresh.get("kalan_gun", it.get("kalan_gun"))
                it["vessel"] = fresh.get("vessel", it.get("vessel"))
                it["pod"] = fresh.get("pod", it.get("pod"))
                it["pol"] = fresh.get("pol", it.get("pol"))
                it["transshipments"] = fresh.get("transshipments", it.get("transshipments"))
                it["source"] = fresh.get("source", it.get("source"))
                it["vessel_lat"] = fresh.get("vessel_lat")
                it["vessel_lng"] = fresh.get("vessel_lng")
                it["vessel_position"] = fresh.get("vessel_position")
                it["current_moves"] = fresh.get("current_moves")
                it["provisional_moves"] = fresh.get("provisional_moves")
                success_count += 1
            time.sleep(0.3)

        save_cache(self.existing_data)
        self.completed_signal.emit(self.existing_data, success_count, total)

    def _scan_excel(self):
        if not openpyxl:
            return
        path = resolve_excel_path(self.target_path)
        if not path or not os.path.exists(path):
            return

        try:
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            ws = wb.active
        except Exception:
            return

        row_tasks = []
        today = datetime.now().date()
        for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if r_idx == 1 or not row or len(row) < 5:
                continue

            c_val = str(row[4]).strip() if len(row) > 4 and row[4] else ""
            f_val = str(row[5]).strip() if len(row) > 5 and row[5] else ""
            t_val = row[19] if len(row) > 19 else ""
            u_val = str(row[20]).strip() if len(row) > 20 and row[20] else ""
            gemi_val = str(row[22]).strip() if len(row) > 22 and row[22] else ""
            dosya_val = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            dosya_no = str(row[0]).strip() if len(row) > 0 and row[0] else ""

            if not any([c_val, f_val, u_val, dosya_no]):
                continue

            query_num = u_val if (u_val and len(u_val) >= 7) else f_val
            if not query_num or len(query_num) < 5:
                continue

            # 1. Kapanış, Liman Çıkış ve Sevk Durumları (Gümrük & Nakliye Kapanışı)
            kapanis = row[13] if len(row) > 13 else None
            cikis = row[15] if len(row) > 15 else None
            acik1 = str(row[16] or "").strip() if len(row) > 16 else ""
            acik2 = str(row[17] or "").strip() if len(row) > 17 else ""
            varis_raw = row[18] if len(row) > 18 else None

            is_closed = bool(
                kapanis or cikis or
                any(k in acik1.lower() for k in ["sevk", "kapandı", "tamam", "teslim"]) or
                any(k in acik2.lower() for k in ["sevk", "kapandı", "tamam", "teslim"])
            )

            # 2. Tarihsel Analiz (Anlık Tarih / Saat / Yıl Zekası)
            varis_d = parse_date(varis_raw)
            eta_d = parse_date(t_val)
            ref_d = eta_d or varis_d

            # Excel Tarihi: Sütun T (ETA) doluysa onu al, boşsa Sütun S (VARIŞ TARİHİ) al!
            excel_date_val = t_val if (t_val and str(t_val).strip() != "") else varis_raw

            is_expired = False
            if is_closed:
                is_active = False
            elif ref_d:
                days_diff = (ref_d - today).days
                # 30 günden daha eski varış/ETA olup gümrük hareketi kalmayanlar arşivdir
                if days_diff < -30:
                    is_expired = True
                    is_active = False
                else:
                    is_active = True
            else:
                # ETA veya varış girilmemiş ama dosya açık (kapanış/çıkış yok) -> AKTİF!
                is_active = True

            row_tasks.append({
                "row_num": r_idx,
                "dosya": f"{dosya_val} ({dosya_no})" if dosya_no else dosya_val,
                "carrier": c_val,
                "bl_hint": f_val,
                "cntr_hint": u_val,
                "gemi": gemi_val,
                "excel_eta": excel_date_val,
                "query_num": query_num,
                "is_active": is_active,
                "ref_date": ref_d.strftime("%Y-%m-%d") if ref_d else None
            })
        wb.close()

        existing_map = {}
        bl_cache = {}
        for it in self.existing_data:
            q = it.get("container_no") or it.get("bl_no")
            if q and it.get("live_eta") not in ("—", ""):
                existing_map[q] = it
                bl_ref = it.get("bl_no")
                if bl_ref and bl_ref != "—":
                    bl_cache[bl_ref] = it

        query_cache = {}
        live_targets = []
        seen = set()

        for t in row_tasks:
            # SADECE aktif yükleri canlı tara! Kapanmış/eski yüklerle zaman kaybetme
            if not t.get("is_active", True):
                continue
            q = t["query_num"]
            b_hint = t.get("bl_hint", "")
            gemi_h = t.get("gemi", "")
            if q not in seen:
                seen.add(q)
                c = self.router.detect_carrier(q, acenta_hint=t["carrier"], bl_hint=b_hint, gemi_hint=gemi_h)
                if c in ["HAPAG", "MSC", "CMA-CGM"]:
                    if q in existing_map:
                        query_cache[q] = {"success": True, "items": [existing_map[q]]}
                        if b_hint and b_hint != "—":
                            bl_cache[b_hint] = existing_map[q]
                    else:
                        live_targets.append((q, t, c))

        tot_live = len(live_targets)
        for i, (q, t, c) in enumerate(live_targets, 1):
            b_hint = t.get("bl_hint", "")
            gemi_h = t.get("gemi", "")

            # --- B/L SMART INHERITANCE (Rate Limit & DataDome 403 Blokajını Önleme) ---
            # Aynı konşimentoya ait bir kardeş konteyner zaten canlı veriyi çektiyse,
            # sunucuya tekrar istek atıp kotayı tüketme; o canlı veriyi anında devral!
            if b_hint and b_hint != "—" and b_hint in bl_cache:
                shared_item = dict(bl_cache[b_hint])
                shared_item["container_no"] = q
                shared_item["source"] = f"{c} (B/L Paylaşımlı Canlı Veri)"
                query_cache[q] = {"success": True, "items": [shared_item]}
                continue

            self.progress_signal.emit(f"[{i}/{tot_live}] {q} ({c}) taranıyor...", i, tot_live)
            res = self.router.track(q, acenta_hint=t["carrier"], excel_eta=t["excel_eta"], bl_hint=b_hint, gemi_hint=gemi_h)
            query_cache[q] = res

            # Başarılı sorguyu B/L önbelleğine kaydet ki aynı konşimentodaki diğer konteynerler
            # API sınırına takılmadan veriyi hemen devralsın!
            if res and res.get("success") and res.get("items"):
                first_it = res["items"][0]
                if b_hint and b_hint != "—":
                    bl_cache[b_hint] = first_it
                bl_res = first_it.get("bl_no")
                if bl_res and bl_res != "—":
                    bl_cache[bl_res] = first_it

            sleep_time = 0.8 if c == "CMA-CGM" else 0.3
            time.sleep(sleep_time)

        collected = []
        success_count = 0
        for t in row_tasks:
            q = t["query_num"]
            b_hint = t.get("bl_hint", "")
            gemi_val = t.get("gemi", "")
            c_det = self.router.detect_carrier(q, acenta_hint=t["carrier"], bl_hint=b_hint, gemi_hint=gemi_val)
            dosya_tag = f"{t['dosya']} (S.{t['row_num']})" if t['dosya'] else f"Satır {t['row_num']}"

            raw_ex = t["excel_eta"]
            if raw_ex:
                if isinstance(raw_ex, (datetime, date)):
                    ex_eta_s = raw_ex.strftime("%d.%m.%Y")
                else:
                    d_parsed = parse_date(raw_ex)
                    ex_eta_s = d_parsed.strftime("%d.%m.%Y") if d_parsed else str(raw_ex)[:10]
            else:
                ex_eta_s = "—"

            res = query_cache.get(q)

            # Doğrudan sorgu başarısız olsa bile, aynı B/L'deki kardeş konteyner canlı veriyi çektiyse devral!
            if (not res or not res.get("success")) and b_hint and b_hint != "—" and b_hint in bl_cache:
                shared_item = dict(bl_cache[b_hint])
                shared_item["container_no"] = t["cntr_hint"] or q
                shared_item["source"] = f"{c_det} (B/L Paylaşımlı Canlı Veri)"
                res = {"success": True, "items": [shared_item]}

            if res and res.get("success") and res.get("items"):
                fresh = dict(res["items"][0])
                fresh["dosya"] = dosya_tag
                fresh["excel_eta"] = ex_eta_s
                fresh["is_active"] = t.get("is_active", True)
                fresh["ref_date"] = t.get("ref_date")
                if fresh.get("live_eta") not in ("—", ""):
                    if fresh.get("eta_diff") == "Planlı Sefer":
                        pass # Adapter already set it as Planlı Sefer
                    else:
                        diff_res = compute_eta_diff(t["excel_eta"], fresh["live_eta"])
                        fresh["eta_diff"] = diff_res["diff_text"]
                        fresh["diff_tag"] = diff_res["diff_tag"]
                if fresh.get("bl_no") in ("—", "") and t["bl_hint"]:
                    fresh["bl_no"] = t["bl_hint"]
                if fresh.get("container_no") in ("—", "") and t["cntr_hint"]:
                    fresh["container_no"] = t["cntr_hint"]
                collected.append(fresh)
                success_count += 1
            else:

                err_msg = res.get("error") if res else "API Bekleniyor"
                collected.append({
                    "dosya": dosya_tag,
                    "carrier": c_det if c_det != "UNKNOWN" else (t["carrier"] or "DİĞER"),
                    "container_no": t["cntr_hint"] or "—",
                    "bl_no": t["bl_hint"] or "—",
                    "excel_eta": ex_eta_s,
                    "live_eta": "—",
                    "eta_diff": "Bekleniyor",
                    "diff_tag": "tag_pending",
                    "kalan_gun": "—",
                    "vessel": gemi_val or "—",
                    "pod": "—",
                    "transshipments": "—",
                    "source": f"{c_det} ({str(err_msg)[:25]})",
                    "is_active": t.get("is_active", True),
                    "ref_date": t.get("ref_date")
                })

        save_cache(collected)
        self.completed_signal.emit(collected, success_count, len(row_tasks))


# ==============================================================================
# SMARTCLEARANCE HORIZON ANA PENCERESİ (PYQT6)
# ==============================================================================

class SmartClearanceHorizonWindow(QMainWindow):
    appSwitchRequested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartClearance Horizon — Küresel Konteyner & Canlı Rota Radarı v1.0 Pro")
        self.setMinimumSize(920, 540)
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if avail:
            self.resize(min(1480, max(920, int(avail.width() * 0.94))), min(880, max(540, int(avail.height() * 0.92))))
        else:
            self.resize(1360, 800)

        self.config = load_config()
        self.router = GlobalTrackingRouter(self.config)
        self.results_data = []
        self.status_filter = "AKTIF"
        self.active_filter = "Tümü"
        self.search_query = ""
        self.scanner_thread = None
        self.status_buttons = {}

        # Harita Yaşam Döngüsü Kontrolü (Hata Önleyici)
        self.map_ready = False
        self.pending_map_data = None
        self._current_screen_name = None

        # Horizon PDF Motoru
        self.pdf_generator = HorizonPdfGenerator(self)
        self.pdf_generator.finished.connect(self._on_pdf_generation_finished)

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Üst Başlık (Header)
        main_layout.addWidget(self._create_header())

        # 2. Linear KPI Sayaç Kartları
        main_layout.addWidget(self._create_kpi_bar())

        # 3. Ana Bölünmüş Alan (Master-Detail QSplitter)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # Sol Panel (Yük Tablosu)
        left_panel = self._create_left_panel()
        self.splitter.addWidget(left_panel)

        # Sağ Panel (Harita & Sefer Kokpiti)
        right_panel = self._create_right_cockpit()
        self.splitter.addWidget(right_panel)

        # Sol panel geniş, sağ panel kompakt (%60 / %40 dağılım)
        self.splitter.setSizes([860, 480])
        main_layout.addWidget(self.splitter, 1)

        # 4. Alt Durum Çubuğu (Status Bar)
        main_layout.addWidget(self._create_status_bar())

    def showEvent(self, event):
        super().showEvent(event)
        wh = self.windowHandle()
        if wh:
            try:
                wh.screenChanged.connect(self._on_screen_changed)
            except Exception:
                pass
            scr = wh.screen()
            if scr:
                self._current_screen_name = scr.name()
                self._on_screen_changed(scr)
        else:
            self._on_screen_changed(None)

    def moveEvent(self, event):
        super().moveEvent(event)
        wh = self.windowHandle()
        if wh:
            scr = wh.screen()
            if scr and scr.name() != getattr(self, "_current_screen_name", None):
                self._current_screen_name = scr.name()
                self._on_screen_changed(scr)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._on_screen_changed(self.screen())

    def _on_screen_changed(self, new_screen=None):
        """Laptop ve büyük monitör geçişlerinde pencere boyutu, splitter ve haritayı dinamik uyarlar."""
        if not new_screen:
            new_screen = self.screen() or QApplication.primaryScreen()

        if new_screen and not self.isMaximized():
            avail = new_screen.availableGeometry()
            geo = self.geometry()
            new_w = geo.width()
            new_h = geo.height()
            changed = False

            max_w = int(avail.width() * 0.96)
            if new_w > max_w:
                new_w = max(self.minimumWidth(), max_w)
                changed = True

            max_h = int(avail.height() * 0.94)
            if new_h > max_h:
                new_h = max(self.minimumHeight(), max_h)
                changed = True

            new_x = geo.x()
            new_y = geo.y()
            if new_x < avail.left() or (new_x + new_w) > avail.right():
                new_x = max(avail.left(), min(new_x, avail.right() - new_w))
                changed = True
            if new_y < avail.top() or (new_y + new_h) > avail.bottom():
                new_y = max(avail.top(), min(new_y, avail.bottom() - new_h))
                changed = True

            if changed:
                self.setGeometry(new_x, new_y, new_w, new_h)

        # Splitter oranını ekran genişliğine göre orantıla
        if hasattr(self, "splitter") and self.splitter:
            tot = self.splitter.width() or self.width()
            if tot > 300:
                left_w = int(tot * 0.60)
                right_w = max(tot - left_w, 360)
                self.splitter.setSizes([left_w, right_w])

        # Harita WebEngine boyutunu ve Leaflet canvas'ını tazele
        if hasattr(self, "web_view") and self.web_view:
            self.web_view.updateGeometry()
            if hasattr(self.web_view, "page"):
                self.web_view.page().runJavaScript("if (typeof map !== 'undefined' && map) { map.invalidateSize(); }")

        self.updateGeometry()
        self.update()

    # --------------------------------------------------------------------------
    # UI BİLEŞENLERİ
    # --------------------------------------------------------------------------

    def _create_header(self):
        hdr = QFrame()
        hdr.setObjectName("headerFrame")
        layout = QHBoxLayout(hdr)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Sol Marka & Sistem Değiştirici
        title_box = QHBoxLayout()
        title_box.setSpacing(8)
        lbl_title = QLabel("SMARTCLEARANCE")
        lbl_title.setObjectName("brandTitle")

        self.btn_app_switch = QPushButton("HORIZON ▾")
        self.btn_app_switch.setObjectName("brandBadgeBtn")
        self.btn_app_switch.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_app_switch.setToolTip("SmartClearance sistemleri arasında geçiş yap")
        self.btn_app_switch.clicked.connect(self._show_app_switch_menu)

        title_box.addWidget(lbl_title)
        title_box.addWidget(self.btn_app_switch)
        layout.addLayout(title_box)

        lbl_status_pill = QLabel("🟢 3 Armatör Canlı Bağlı (MSC • Hapag • CMA CGM)")
        lbl_status_pill.setObjectName("statusPill")
        layout.addWidget(lbl_status_pill)

        layout.addStretch(1)

        # Arama Çubuğu
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Konteyner, B/L veya Gemi ara...")
        self.txt_search.setFixedWidth(260)
        self.txt_search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.txt_search)

        # Eylem Butonları
        btn_scan = QPushButton("⚡ Canlı Yenile")
        btn_scan.setObjectName("btnPrimary")
        btn_scan.clicked.connect(self._refresh_memory_live)
        layout.addWidget(btn_scan)

        btn_excel_scan = QPushButton("📁 Excel Tara")
        btn_excel_scan.clicked.connect(self._scan_excel)
        layout.addWidget(btn_excel_scan)

        btn_export = QPushButton("📊 Excel Aktar")
        btn_export.clicked.connect(self._export_excel)
        layout.addWidget(btn_export)

        btn_pdf = QPushButton("📄 PDF Bülten")
        btn_pdf.setObjectName("btnPrimary")
        btn_pdf.clicked.connect(self._show_pdf_menu)
        layout.addWidget(btn_pdf)

        btn_settings = QPushButton("⚙️ Ayarlar")
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

        return hdr

    def _show_app_switch_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b111e;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 9px 20px;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11.5px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 8px;
            }
        """)
        a_apex = menu.addAction("⚡ SmartClearance APEX  (Gümrük Operasyon Masası)")
        menu.addSeparator()
        a_horizon = menu.addAction("🚢 SmartClearance HORIZON  (Aktif)")
        a_horizon.setEnabled(False)

        pos = self.btn_app_switch.mapToGlobal(QPoint(0, self.btn_app_switch.height() + 4))
        act = menu.exec(pos)
        if act == a_apex:
            self._trigger_app_switch("APEX")

    def _trigger_app_switch(self, target):
        if self.receivers(self.appSwitchRequested) > 0:
            self.appSwitchRequested.emit(target)
        else:
            try:
                import subprocess
                suite_script = r"C:\HANKOOK_OPERASYON_MASASI\smartclearance_suite.py"
                subprocess.Popen([sys.executable, suite_script, "--system", target])
                self.close()
            except Exception as e:
                QMessageBox.warning(self, "Sistem Geçişi", f"SmartClearance Suite başlatılamadı:\n{e}")

    def _create_kpi_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #0a0e17; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 8px 16px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self.card_total = self._make_kpi_card("TOPLAM TAKİP", "0", "#f8fafc")
        self.card_delayed = self._make_kpi_card("RÖTAR TESPİT EDİLENLER", "0", "#f43f5e")
        self.card_ontime = self._make_kpi_card("ERKEN / ZAMANINDA", "0", "#10b981")
        self.card_live = self._make_kpi_card("CANLI BAĞLI YÜKLER", "0", "#38bdf8")

        layout.addWidget(self.card_total["frame"])
        layout.addWidget(self.card_delayed["frame"])
        layout.addWidget(self.card_ontime["frame"])
        layout.addWidget(self.card_live["frame"])

        return bar

    def _make_kpi_card(self, title, val, color):
        frame = QFrame()
        frame.setProperty("class", "kpiCard")
        l = QVBoxLayout(frame)
        l.setContentsMargins(14, 8, 14, 8)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "kpiTitle")
        lbl_v = QLabel(val)
        lbl_v.setProperty("class", "kpiValue")
        lbl_v.setStyleSheet(f"color: {color};")

        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return {"frame": frame, "val": lbl_v}

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 8, 10)
        layout.setSpacing(8)

        # Filtre Hapları Barı
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(6)

        # 1. Durum Filtresi (Aktif Takip vs Tüm Arşiv)
        self.status_buttons = {}
        for s_code, s_label in [("AKTIF", "🟢 Aktif Yükler"), ("TUMU", "📦 Tüm Arşiv")]:
            btn = QPushButton(s_label)
            btn.setProperty("class", "filterPill")
            btn.setProperty("selected", "true" if s_code == "AKTIF" else "false")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda ch, code=s_code: self._set_status_filter(code))
            filter_bar.addWidget(btn)
            self.status_buttons[s_code] = btn

        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.VLine)
        sep_line.setStyleSheet("background-color: rgba(255,255,255,0.12); width: 1px; margin: 3px 6px;")
        filter_bar.addWidget(sep_line)

        # 2. Armatör Filtreleri
        self.filter_buttons = {}
        for f_name in ["Tümü", "MSC", "HAPAG-LLOYD", "CMA CGM", "DİĞER"]:
            btn = QPushButton(f_name)
            btn.setProperty("class", "filterPill")
            btn.setProperty("selected", "true" if f_name == "Tümü" else "false")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda ch, name=f_name: self._set_filter(name))
            filter_bar.addWidget(btn)
            self.filter_buttons[f_name] = btn
        filter_bar.addStretch(1)

        # Esnek Görünüm Bilgisi
        lbl_hint = QLabel("💡 Sütun başlıklarını sürükleyip genişletebilir veya tıklayıp sıralayabilirsiniz")
        lbl_hint.setStyleSheet("font-size: 10px; color: #64748b;")
        filter_bar.addWidget(lbl_hint)

        layout.addLayout(filter_bar)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Dosya No", "Armatör", "Konteyner No", "B/L No",
            "Excel ETA", "Canlı ETA", "Sapma Durumu", "Kalan Gün"
        ])

        # Sütun Genişlikleri (Ferah & Kırpılmayan Genişlik Modu)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

        self.table.setColumnWidth(0, 140)  # Dosya No
        self.table.setColumnWidth(1, 110)  # Armatör
        self.table.setColumnWidth(2, 140)  # Konteyner No
        self.table.setColumnWidth(3, 140)  # B/L No
        self.table.setColumnWidth(4, 95)   # Excel ETA
        self.table.setColumnWidth(5, 105)  # Canlı ETA
        self.table.setColumnWidth(6, 125)  # Sapma
        self.table.setColumnWidth(7, 110)  # Kalan Gün

        # Satır Yüksekliği & Genel Ayarlar
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setVisible(False)  # Soldaki gereksiz 1, 2, 3.. sütununu kaldırıp alandan tasarruf et
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.doubleClicked.connect(self._on_table_double_click)

        layout.addWidget(self.table)
        return panel

    def _create_right_cockpit(self):
        cockpit = QWidget()
        cockpit.setObjectName("rightCockpit")
        layout = QVBoxLayout(cockpit)
        layout.setContentsMargins(8, 10, 12, 10)
        layout.setSpacing(10)

        # 1. Seçili Yük Kartı
        self.card_selected = QFrame()
        self.card_selected.setObjectName("shipmentCard")
        c_layout = QVBoxLayout(self.card_selected)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(4)

        self.lbl_card_cntr = QLabel("Lütfen listeden bir yük seçin")
        self.lbl_card_cntr.setStyleSheet("font-size: 15px; font-weight: 800; color: #f8fafc;")
        self.lbl_card_vessel = QLabel("Gemi / Rota Bilgisi Bekleniyor")
        self.lbl_card_vessel.setStyleSheet("font-size: 12px; color: #38bdf8; font-weight: 600;")
        self.lbl_card_meta = QLabel("—")
        self.lbl_card_meta.setStyleSheet("font-size: 11px; color: #94a3b8;")

        # Boş Konteyner İade (Empty Return) Durumu
        self.lbl_card_empty_return = QLabel("🔄 Boş İade Durumu: Bekleniyor")
        self.lbl_card_empty_return.setStyleSheet("font-size: 11px; color: #94a3b8; padding-top: 2px;")

        card_btn_box = QHBoxLayout()
        card_btn_box.setContentsMargins(0, 4, 0, 0)
        card_btn_box.setSpacing(8)

        self.btn_card_pdf = QPushButton("📄 Horizon Sefer Bülteni")
        self.btn_card_pdf.setStyleSheet("background-color: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); font-weight: 700; padding: 4px 10px; font-size: 11px;")
        self.btn_card_pdf.clicked.connect(self._export_single_pdf)
        card_btn_box.addWidget(self.btn_card_pdf)
        card_btn_box.addStretch(1)

        c_layout.addWidget(self.lbl_card_cntr)
        c_layout.addWidget(self.lbl_card_vessel)
        c_layout.addWidget(self.lbl_card_meta)
        c_layout.addWidget(self.lbl_card_empty_return)
        c_layout.addLayout(card_btn_box)
        layout.addWidget(self.card_selected)

        # 2. Gömülü Koyu Harita (QWebEngineView)
        map_hdr_box = QHBoxLayout()
        map_title = QLabel("🗺️ CANLI SEYİR & ROTA HARİTASI")
        map_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        map_hdr_box.addWidget(map_title)
        map_hdr_box.addStretch(1)

        btn_reset_zoom = QPushButton("⟲ Odakla")
        btn_reset_zoom.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_reset_zoom.clicked.connect(self._recenter_map)
        map_hdr_box.addWidget(btn_reset_zoom)
        layout.addLayout(map_hdr_box)

        self.web_map = QWebEngineView()
        self.web_map.setStyleSheet("border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: #080b11;")

        # Yerel dosya ve ağ yetkilerini güvenle aç
        settings = self.web_map.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self.web_map.loadFinished.connect(self._on_map_load_finished)

        if os.path.exists(MAP_HTML_PATH):
            self.web_map.setUrl(QUrl.fromLocalFile(MAP_HTML_PATH))
        layout.addWidget(self.web_map, 1)

        # 3. Dikey Sefer Zaman Çizelgesi (Milestones)
        milestone_header = QLabel("📍 SEFER ZAMAN ÇİZELGESİ (MILESTONES)")
        milestone_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        layout.addWidget(milestone_header)

        self.scroll_milestones = QScrollArea()
        self.scroll_milestones.setWidgetResizable(True)
        self.scroll_milestones.setFixedHeight(150)
        self.scroll_milestones.setStyleSheet("border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; background: #0b0f18;")

        self.milestone_container = QWidget()
        self.milestone_layout = QVBoxLayout(self.milestone_container)
        self.milestone_layout.setContentsMargins(8, 8, 8, 8)
        self.milestone_layout.setSpacing(4)
        self.scroll_milestones.setWidget(self.milestone_container)
        layout.addWidget(self.scroll_milestones)

        return cockpit

    def _create_status_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #080b11; border-top: 1px solid rgba(255, 255, 255, 0.05); padding: 5px 16px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)

        self.lbl_status = QLabel("✅ SmartClearance Horizon hazır.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1e293b; border-radius: 4px; } QProgressBar::chunk { background: #0284c7; border-radius: 4px; }")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch(1)

        self.lbl_last_check = QLabel("Son Güncelleme: —")
        self.lbl_last_check.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_last_check)

        return bar

    # --------------------------------------------------------------------------
    # HARİTA YAŞAM DÖNGÜSÜ & GÜVENLİ İLETİŞİM
    # --------------------------------------------------------------------------

    def _on_map_load_finished(self, ok):
        self.map_ready = True
        if self.pending_map_data:
            self._dispatch_map_data(self.pending_map_data)
            self.pending_map_data = None

    def _dispatch_map_data(self, map_payload):
        if not map_payload:
            return
        payload_json = json.dumps(map_payload, ensure_ascii=False)
        js_code = f"if (typeof updateRoute === 'function') {{ updateRoute({payload_json}); }}"
        self.web_map.page().runJavaScript(js_code)

    def _recenter_map(self):
        if self.results_data:
            sel = self.table.selectionModel().selectedRows()
            if sel:
                row = sel[0].row()
                cntr = self.table.item(row, 2).text()
                bl = self.table.item(row, 3).text()
                for it in self.results_data:
                    if (it.get("container_no") == cntr) or (it.get("bl_no") == bl):
                        payload = self._build_map_payload(it)
                        self._dispatch_map_data(payload)
                        break

    # --------------------------------------------------------------------------
    # VERİ VE TABLO YÖNETİMİ
    # --------------------------------------------------------------------------

    def _load_initial_data(self):
        cached = load_cache()
        if cached and isinstance(cached, dict):
            self.results_data = cached.get("items", [])
            last_dt = cached.get("last_check", "")
            if last_dt:
                self.lbl_last_check.setText(f"Son Güncelleme: {last_dt}")

            # Varolan hafıza/önbellek verisinde is_active yoksa akıllı tarih kontrolüyle ata
            today = datetime.now().date()
            for it in self.results_data:
                if "is_active" not in it:
                    raw_d = it.get("live_eta") or it.get("excel_eta")
                    d = parse_date(raw_d)
                    diff_s = str(it.get("kalan_gun", ""))
                    if "Gecikti" in diff_s:
                        try:
                            m = re.search(r'\d+', diff_s)
                            if m and int(m.group()) > 30:
                                it["is_active"] = False
                                continue
                        except Exception:
                            pass
                    if d and (d - today).days < -30:
                        it["is_active"] = False
                    else:
                        it["is_active"] = True
        self._populate_table()

    def _set_status_filter(self, code):
        self.status_filter = code
        for btn_code, btn in self.status_buttons.items():
            is_sel = (btn_code == code)
            btn.setProperty("selected", "true" if is_sel else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._populate_table()

    def _set_filter(self, name):
        self.active_filter = name
        for btn_name, btn in self.filter_buttons.items():
            is_sel = (btn_name == name)
            btn.setProperty("selected", "true" if is_sel else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._populate_table()

    def _on_search_changed(self, text):
        self.search_query = text.strip().upper()
        self._populate_table()

    def _populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        q = self.search_query
        f = self.active_filter.upper()
        s_mode = getattr(self, "status_filter", "AKTIF")
        today = datetime.now().date()

        # Sayımlar
        active_count = sum(1 for it in self.results_data if it.get("is_active", True))
        archive_count = len(self.results_data)

        # Durum Buton Metinlerini Canlı Güncelle
        if hasattr(self, "status_buttons"):
            if "AKTIF" in self.status_buttons:
                self.status_buttons["AKTIF"].setText(f"🟢 Aktif Yükler ({active_count})")
            if "TUMU" in self.status_buttons:
                self.status_buttons["TUMU"].setText(f"📦 Tüm Arşiv ({archive_count})")

        delayed_cnt = 0
        ontime_cnt = 0
        live_cnt = 0
        matched_items = []

        # --- KANTAR ÇAPRAZ KONTROL (CROSS-CHECK) ---
        # Eğer armatör API'si konteynerin indiğini gecikmeli veriyorsa ama bizde kantar
        # tikesi çıkmışsa, %100 limandadır. Kantar durumunu baz alarak üzerine yazarız.
        kantar_hazir_set = set()
        try:
            import json, os
            k_file = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "kantar_takip_storage.json")
            if os.path.exists(k_file):
                with open(k_file, "r", encoding="utf-8") as _kf:
                    _kd = json.load(_kf)
                    for _k in _kd:
                        if _k.get("hazir"):
                            kantar_hazir_set.add(str(_k.get("konteyner_no", "")).upper())
        except Exception:
            pass

        for it in self.results_data:
            is_act = it.get("is_active", True)
            if s_mode == "AKTIF" and not is_act:
                continue

            c = (it.get("carrier") or "").upper()
            cntr = (it.get("container_no") or "").upper()
            bl = (it.get("bl_no") or "").upper()
            dosya = (it.get("dosya") or "").upper()
            vessel = (it.get("vessel") or "").upper()
            
            # --- OVERRIDE ---
            if cntr in kantar_hazir_set:
                it["eta_diff"] = "✅ Varmış"
                it["diff_tag"] = "tag_arrived"
                it["kalan_gun"] = "Limana İndi (Kantar Çapraz Kontrolü)"
                
            diff_tag = it.get("diff_tag", "")

            if diff_tag == "tag_delayed":
                delayed_cnt += 1
            elif diff_tag in ("tag_ontime", "tag_early"):
                ontime_cnt += 1

            if it.get("live_eta") not in ("—", ""):
                live_cnt += 1

            if f != "TÜMÜ":
                if f == "MSC" and "MSC" not in c:
                    continue
                elif f == "HAPAG-LLOYD" and "HAPAG" not in c:
                    continue
                elif f == "CMA CGM" and "CMA" not in c:
                    continue
                elif f == "DİĞER" and any(k in c for k in ["MSC", "HAPAG", "CMA"]):
                    continue

            if q:
                combined = f"{cntr} {bl} {dosya} {vessel} {c}"
                if q not in combined:
                    continue

            matched_items.append(it)

        # Bugünden en yakına doğru akıllı sıralama (Bugün > Gelecek Seferler > Limana İnenler)
        def _proximity_key(it):
            kalan = str(it.get("kalan_gun", ""))
            raw_d = it.get("live_eta") or it.get("excel_eta")
            d = parse_date(raw_d)
            if not d:
                return (3, 9999)
            diff = (d - today).days
            if "Bugün" in kalan or diff == 0:
                return (0, 0)         # Bugün varışlar
            elif diff > 0:
                return (1, diff)      # Gelecek seferler (en yakın önce: 1 gün, 2 gün, 5 gün...)
            else:
                return (2, abs(diff)) # Limana inmiş / geçmiş varışlar (yakından uzağa)

        matched_items.sort(key=_proximity_key)

        # KPI Sayaçlarını Güncelle
        total_shown = active_count if s_mode == "AKTIF" else archive_count
        self.card_total["val"].setText(str(total_shown))
        self.card_delayed["val"].setText(str(delayed_cnt))
        self.card_ontime["val"].setText(str(ontime_cnt))
        self.card_live["val"].setText(str(live_cnt))

        # Tablo Doldurma
        self.table.setRowCount(len(matched_items))
        for r, it in enumerate(matched_items):
            self.table.setItem(r, 0, self._create_item(it.get("dosya", "—")))

            # Armatör Rozeti
            carrier_item = self._create_item(it.get("carrier", "—"))
            c_name = it.get("carrier", "")
            if "MSC" in c_name:
                carrier_item.setForeground(QColor("#fbbf24"))
            elif "HAPAG" in c_name:
                carrier_item.setForeground(QColor("#ea580c"))
            elif "CMA" in c_name:
                carrier_item.setForeground(QColor("#38bdf8"))
            self.table.setItem(r, 1, carrier_item)

            self.table.setItem(r, 2, self._create_item(it.get("container_no", "—"), bold=True))
            self.table.setItem(r, 3, self._create_item(it.get("bl_no", "—")))
            self.table.setItem(r, 4, self._create_item(it.get("excel_eta", "—")))

            # Canlı ETA
            live_eta_item = self._create_item(it.get("live_eta", "—"), bold=True)
            if it.get("live_eta") not in ("—", ""):
                live_eta_item.setForeground(QColor("#38bdf8"))
            self.table.setItem(r, 5, live_eta_item)

            # Sapma Rozeti
            diff_text = it.get("eta_diff", "—")
            diff_item = self._create_item(diff_text, bold=True)
            if "Rötar" in diff_text or ("+") in diff_text and "Varmış" not in diff_text:
                diff_item.setForeground(QColor("#f43f5e"))
            elif "Erken" in diff_text or "Zamanında" in diff_text or "Aynı Gün" in diff_text or "Varmış" in diff_text:
                diff_item.setForeground(QColor("#10b981"))
            self.table.setItem(r, 6, diff_item)

            # Kalan Gün / Varış Durumu
            kalan_text = it.get("kalan_gun", "—")
            kalan_item = self._create_item(kalan_text, bold=True)
            if "Limana İndi" in kalan_text:
                kalan_item.setForeground(QColor("#38bdf8"))
            elif "Bugün" in kalan_text:
                kalan_item.setForeground(QColor("#10b981"))
            elif "Gecikti" in kalan_text:
                kalan_item.setForeground(QColor("#f43f5e"))
            self.table.setItem(r, 7, kalan_item)

        self.table.setSortingEnabled(True)

        # İlk satırı otomatik seç ve kokpite yükle
        if matched_items:
            self.table.selectRow(0)
            self._update_cockpit(matched_items[0])

    def _create_item(self, text, bold=False):
        it = QTableWidgetItem(str(text))
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if bold:
            f = it.font()
            f.setBold(True)
            it.setFont(f)
        return it

    def _on_row_selected(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return
        row = sel[0].row()
        dosya = self.table.item(row, 0).text()
        cntr = self.table.item(row, 2).text()
        bl = self.table.item(row, 3).text()

        for it in self.results_data:
            if it.get("dosya") == dosya and (it.get("container_no") == cntr or it.get("bl_no") == bl):
                self._update_cockpit(it)
                break

    # --------------------------------------------------------------------------
    # SAĞ KOKPİT (HARİTA & ZAMAN ÇİZELGESİ)
    # --------------------------------------------------------------------------

    def _update_cockpit(self, it):
        cntr = it.get("container_no") or "—"
        bl = it.get("bl_no") or "—"
        carrier = it.get("carrier") or "—"
        vessel = it.get("vessel") or "—"
        pod = it.get("pod") or "—"
        live_eta = it.get("live_eta") or "—"
        diff = it.get("eta_diff") or "—"
        kalan = it.get("kalan_gun") or "—"

        # 1. Kart Başlığı
        flag_info = self._resolve_vessel_flag(vessel, carrier)
        vessel_display = f"{vessel}  {flag_info['flag_emoji']} ({flag_info['flag_country']})" if (vessel and vessel != "—") else vessel
        self.lbl_card_cntr.setText(f"📦 {cntr}  •  {carrier}")
        self.lbl_card_vessel.setText(f"🚢 Gemi: {vessel_display}")
        self.lbl_card_meta.setText(f"B/L: {bl}  |  Tahliye Limanı: {pod}  |  ETA: {live_eta} ({diff})  |  {kalan}")

        # Boş Konteyner İade (Empty Return) Durumu
        empty_date = it.get("empty_return_date")
        empty_addr = it.get("empty_return_address")
        if empty_addr and str(empty_date)[:4] not in ("0001", "None", ""):
            clean_d = str(empty_date)[:10]
            self.lbl_card_empty_return.setText(f"🔄 Boş İade Deposu: {empty_addr} • Son Tarih: {clean_d}")
            self.lbl_card_empty_return.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 700; padding-top: 2px;")
        elif it.get("vessel_lat") or "Seyir" in str(it.get("vessel_status", "")) or it.get("kalan_gun") not in ("—", "Bugün Varış", "Limana İndi"):
            self.lbl_card_empty_return.setText(f"⏳ Boş İade: Gemi Seyrinde (Varış sonrası {pod} deposu atanacak)")
            self.lbl_card_empty_return.setStyleSheet("font-size: 11px; color: #94a3b8; padding-top: 2px;")
        else:
            self.lbl_card_empty_return.setText(f"📍 Boş İade: {pod} Liman Boşaltma Sürecinde Takip Ediliyor")
            self.lbl_card_empty_return.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600; padding-top: 2px;")

        # 2. Harita Verisini Hazırla ve WebEngine'e Gönder (Hata Korumalı)
        map_payload = self._build_map_payload(it)
        if self.map_ready:
            self._dispatch_map_data(map_payload)
        else:
            self.pending_map_data = map_payload

        # 3. Sefer Zaman Çizelgesini Doldur
        self._populate_milestones(it, map_payload)

    # --------------------------------------------------------------------------
    # KÜRESEL GEMİ BAYRAK VERİTABANI & ARMATÖR ÇÖZÜMLEME MOTORU
    # --------------------------------------------------------------------------

    VESSEL_EXACT_REGISTRY = {
        # MAERSK
        "MAERSK LEBU": ("🇸🇬", "Singapur", "SG"),
        "MAERSK SIRAC": ("🇸🇬", "Singapur", "SG"),
        "MAERSK ESSEN": ("🇩🇰", "Danimarka", "DK"),
        "COLUMBINE MAERSK": ("🇩🇰", "Danimarka", "DK"),
        "MAERSK MC-KINNEY MOLLER": ("🇩🇰", "Danimarka", "DK"),
        "MAERSK MADRID": ("🇩🇰", "Danimarka", "DK"),

        # MSC (MEDITERRANEAN SHIPPING COMPANY)
        "MSC MIRJA": ("🇵🇦", "Panama", "PA"),
        "MSC ZOE": ("🇵🇦", "Panama", "PA"),
        "MSC TURKIYE": ("🇱🇷", "Liberya", "LR"),
        "MSC TÜRKİYE": ("🇱🇷", "Liberya", "LR"),
        "MSC OSCAR": ("🇵🇦", "Panama", "PA"),
        "MSC MAYA": ("🇵🇦", "Panama", "PA"),
        "MSC ANNA": ("🇱🇷", "Liberya", "LR"),
        "MSC AMELIA": ("🇵🇦", "Panama", "PA"),
        "MSC DANIELA": ("🇵🇦", "Panama", "PA"),
        "MSC JADE": ("🇱🇷", "Liberya", "LR"),
        "MSC LEANNE": ("🇵🇦", "Panama", "PA"),
        "MSC GULSUN": ("🇵🇦", "Panama", "PA"),
        "MSC TINA": ("🇱🇷", "Liberya", "LR"),
        "MSC ISABELLA": ("🇵🇦", "Panama", "PA"),
        "MSC PALOMA": ("🇵🇦", "Panama", "PA"),

        # CMA CGM
        "CMA CGM DOLPHIN": ("🇲🇹", "Malta", "MT"),
        "CMA CGM ALTAMIRA": ("🇲🇹", "Malta", "MT"),
        "CMA CGM QUEST": ("🇲🇹", "Malta", "MT"),
        "CMA CGM SAHARA": ("🇲🇹", "Malta", "MT"),
        "CMA CGM JACQUES SAADE": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM ANTOINE DE SAINT EXUPERY": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM PALAIS ROYAL": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM CHAMPS ELYSEES": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM RIVOLI": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM LOUVRE": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM CONCORDE": ("🇫🇷", "Fransa", "FR"),
        "CMA CGM SORBONNE": ("🇫🇷", "Fransa", "FR"),

        # HAPAG-LLOYD
        "SOFIA EXPRESS": ("🇩🇪", "Almanya", "DE"),
        "ESSEN EXPRESS": ("🇩🇪", "Almanya", "DE"),
        "AL DHAIL": ("🇲🇭", "Marshall Adaları", "MH"),
        "AL MURABBA": ("🇲🇭", "Marshall Adaları", "MH"),
        "AL JASRAH": ("🇲🇭", "Marshall Adaları", "MH"),
        "BERLIN EXPRESS": ("🇩🇪", "Almanya", "DE"),
        "HAMBURG EXPRESS": ("🇩🇪", "Almanya", "DE"),
        "BREMEN EXPRESS": ("🇩🇪", "Almanya", "DE"),
        "KOBE EXPRESS": ("🇩🇪", "Almanya", "DE"),
        "KYOTO EXPRESS": ("🇩🇪", "Almanya", "DE"),

        # COSCO SHIPPING
        "COSCO JAPAN": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO INDONESIA": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING UNIVERSE": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING NEBULA": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING GALAXY": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING SOLAR": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING STAR": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING PLANET": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING TAURUS": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING PISCES": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING VIRGO": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING GEMINI": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING ARIES": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING LEO": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING CAPRICORN": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING AQUARIUS": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING SAGITTARIUS": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING LIBRA": ("🇭🇰", "Hong Kong", "HK"),
        "COSCO SHIPPING SCORPIO": ("🇭🇰", "Hong Kong", "HK"),

        # YANG MING
        "YM WARMTH": ("🇱🇷", "Liberya", "LR"),
        "YM WELLSPRING": ("🇵🇦", "Panama", "PA"),
        "YM WINDOW": ("🇱🇷", "Liberya", "LR"),
        "YM WONDER": ("🇱🇷", "Liberya", "LR"),
        "YM WITNESS": ("🇱🇷", "Liberya", "LR"),
        "YM WHOLESOME": ("🇱🇷", "Liberya", "LR"),
        "YM WISDOM": ("🇱🇷", "Liberya", "LR"),
        "YM WORLD": ("🇱🇷", "Liberya", "LR"),
        "YM WINNER": ("🇱🇷", "Liberya", "LR"),
        "YM WELCOME": ("🇱🇷", "Liberya", "LR"),
        "YM TOTALITY": ("🇱🇷", "Liberya", "LR"),
        "YM TRIUMPH": ("🇱🇷", "Liberya", "LR"),
        "YM TARGET": ("🇱🇷", "Liberya", "LR"),

        # ONE (OCEAN NETWORK EXPRESS)
        "ONE APUS": ("🇯🇵", "Japonya", "JP"),
        "ONE OLYMPUS": ("🇯🇵", "Japonya", "JP"),
        "ONE INGENUITY": ("🇸🇬", "Singapur", "SG"),
        "ONE INNOVATION": ("🇱🇷", "Liberya", "LR"),
        "ONE INFINITY": ("🇱🇷", "Liberya", "LR"),
        "ONE INTENSITY": ("🇱🇷", "Liberya", "LR"),
        "ONE INTEGRITY": ("🇱🇷", "Liberya", "LR"),
        "ONE STORK": ("🇯🇵", "Japonya", "JP"),
        "ONE COLUMBA": ("🇯🇵", "Japonya", "JP"),
        "ONE AQUILA": ("🇯🇵", "Japonya", "JP"),
        "ONE CRANE": ("🇯🇵", "Japonya", "JP"),

        # EVERGREEN
        "EVER GIVEN": ("🇵🇦", "Panama", "PA"),
        "EVER ACE": ("🇵🇦", "Panama", "PA"),
        "EVER ALOT": ("🇵🇦", "Panama", "PA"),
        "EVER ATOP": ("🇵🇦", "Panama", "PA"),
        "EVER ARIA": ("🇵🇦", "Panama", "PA"),
        "EVER ARM": ("🇵🇦", "Panama", "PA"),
        "EVER ART": ("🇵🇦", "Panama", "PA"),
        "EVER GLORY": ("🇵🇦", "Panama", "PA"),
        "EVER GOLDEN": ("🇵🇦", "Panama", "PA"),
        "EVER GOODS": ("🇵🇦", "Panama", "PA"),
        "EVER GOAL": ("🇵🇦", "Panama", "PA"),
        "EVER GENTLE": ("🇵🇦", "Panama", "PA"),
        "EVER GIFTED": ("🇵🇦", "Panama", "PA"),
        "EVER GRADE": ("🇵🇦", "Panama", "PA"),

        # ARKAS & TURKON (TÜRK BAYRAKLI TİCARİ FİLO)
        "PIERA": ("🇹🇷", "Türkiye", "TR"),
        "PIERRE A": ("🇹🇷", "Türkiye", "TR"),
        "BERNARD A": ("🇹🇷", "Türkiye", "TR"),
        "WANDA A": ("🇹🇷", "Türkiye", "TR"),
        "MATILDE A": ("🇹🇷", "Türkiye", "TR"),
        "LUCIE A": ("🇹🇷", "Türkiye", "TR"),
        "EMMA A": ("🇹🇷", "Türkiye", "TR"),
        "DANIEL A": ("🇹🇷", "Türkiye", "TR"),
        "TEOMAN A": ("🇹🇷", "Türkiye", "TR"),
        "GULSUN A": ("🇹🇷", "Türkiye", "TR"),
        "CINAR A": ("🇹🇷", "Türkiye", "TR"),
        "YALIM A": ("🇹🇷", "Türkiye", "TR"),
        "MEHMET KAHVECI": ("🇹🇷", "Türkiye", "TR"),
        "MUKADDES KALKAVAN": ("🇹🇷", "Türkiye", "TR"),
        "IBRAHIM DEVAL": ("🇹🇷", "Türkiye", "TR"),
        "LEYLA KALKAVAN": ("🇹🇷", "Türkiye", "TR"),
        "KASIF KALKAVAN": ("🇹🇷", "Türkiye", "TR"),

        # DİĞER FEEDER / KİRALIK KONTEYNER GEMİLERİ
        "GSL SUSAN": ("🇱🇷", "Liberya", "LR"),
        "IONIKOS": ("🇲🇹", "Malta", "MT"),
        "CONTSHIP VOW": ("🇱🇷", "Liberya", "LR"),
        "CONTSHIP CUP": ("🇱🇷", "Liberya", "LR"),
        "CONTSHIP GALA": ("🇱🇷", "Liberya", "LR"),
        "AS FLORIANA": ("🇵🇹", "Portekiz", "PT"),
        "AS PAULINA": ("🇵🇹", "Portekiz", "PT"),
    }

    def _resolve_vessel_flag(self, vessel_name: str, carrier_name: str = ""):
        """Bütün acentalardaki gemilerin tescil bayrağını çözer (Emoji, Ülke, Kod)."""
        v_raw = str(vessel_name or "").strip()
        c_raw = str(carrier_name or "").strip().upper()

        if not v_raw or v_raw in ("—", "-", "None", "NULL", "Gemi"):
            return {"flag_emoji": "🌐", "flag_country": "Uluslararası", "flag_code": "INT"}

        # Sefer kodu ve parantez temizliği: "MSC MIRJA (GT633W)" -> "MSC MIRJA"
        v_clean = re.sub(r"\(.*?\)", "", v_raw).strip()
        v_clean = re.sub(r"\s+", " ", v_clean).strip().upper()

        # 1. Doğrudan Tescil Sicili Eşleşmesi
        if v_clean in self.VESSEL_EXACT_REGISTRY:
            emoji, country, code = self.VESSEL_EXACT_REGISTRY[v_clean]
            return {"flag_emoji": emoji, "flag_country": country, "flag_code": code}

        # Sondaki numerik sefer kodunu kırparak tekrar kontrol et ("MAERSK LEBU 432W" -> "MAERSK LEBU")
        v_parts = v_clean.split()
        if len(v_parts) > 1 and re.match(r"^\d+[A-Z]?$", v_parts[-1]):
            v_sub = " ".join(v_parts[:-1])
            if v_sub in self.VESSEL_EXACT_REGISTRY:
                emoji, country, code = self.VESSEL_EXACT_REGISTRY[v_sub]
                return {"flag_emoji": emoji, "flag_country": country, "flag_code": code}

        # 2. Bütün Acentaları Kapsayan Akıllı Analiz (Heuristics & Carrier Intelligence)

        # Arkas / Turkon / Medkon / Türk armatörleri
        if "ARKAS" in c_raw or "TURKON" in c_raw or "MEDKON" in c_raw or "KASIF" in v_clean or "KALKAVAN" in v_clean:
            return {"flag_emoji": "🇹🇷", "flag_country": "Türkiye", "flag_code": "TR"}
        if len(v_parts) == 2 and v_parts[1] == "A":  # Örn: PIERRE A, BERNARD A, WANDA A
            return {"flag_emoji": "🇹🇷", "flag_country": "Türkiye", "flag_code": "TR"}

        # Maersk
        if "MAERSK" in v_clean or "MAERSK" in c_raw:
            return {"flag_emoji": "🇸🇬", "flag_country": "Singapur", "flag_code": "SG"}

        # MSC (Mediterranean Shipping Company)
        if "MSC" in v_clean or "MSC" in c_raw:
            if any(x in v_clean for x in ["TURKIYE", "TÜRKİYE", "ANNA", "JADE", "TINA"]):
                return {"flag_emoji": "🇱🇷", "flag_country": "Liberya", "flag_code": "LR"}
            return {"flag_emoji": "🇵🇦", "flag_country": "Panama", "flag_code": "PA"}

        # CMA CGM
        if "CMA" in v_clean or "CMA" in c_raw or "CGM" in v_clean:
            if any(x in v_clean for x in ["SAADE", "EXUPERY", "ROYAL", "ELYSEES", "RIVOLI", "LOUVRE", "CONCORDE", "SORBONNE"]):
                return {"flag_emoji": "🇫🇷", "flag_country": "Fransa", "flag_code": "FR"}
            return {"flag_emoji": "🇲🇹", "flag_country": "Malta", "flag_code": "MT"}

        # Hapag-Lloyd
        if "HAPAG" in c_raw or "LLOYD" in c_raw or "EXPRESS" in v_clean:
            if "AL DHAIL" in v_clean or "AL MURABBA" in v_clean or "AL JASRAH" in v_clean:
                return {"flag_emoji": "🇲🇭", "flag_country": "Marshall Adaları", "flag_code": "MH"}
            return {"flag_emoji": "🇩🇪", "flag_country": "Almanya", "flag_code": "DE"}

        # COSCO Shipping
        if "COSCO" in v_clean or "COSCO" in c_raw:
            return {"flag_emoji": "🇭🇰", "flag_country": "Hong Kong", "flag_code": "HK"}

        # ONE (Ocean Network Express)
        if v_clean.startswith("ONE ") or "ONE" in c_raw:
            return {"flag_emoji": "🇯🇵", "flag_country": "Japonya", "flag_code": "JP"}

        # Evergreen
        if "EVERGREEN" in c_raw or v_clean.startswith("EVER "):
            return {"flag_emoji": "🇵🇦", "flag_country": "Panama", "flag_code": "PA"}

        # Yang Ming
        if "YANG MING" in c_raw or v_clean.startswith("YM "):
            return {"flag_emoji": "🇱🇷", "flag_country": "Liberya", "flag_code": "LR"}

        # ZIM
        if "ZIM" in c_raw or "ZIM" in v_clean:
            return {"flag_emoji": "🇮🇱", "flag_country": "İsrail", "flag_code": "IL"}

        # Hyundai Merchant Marine (HMM)
        if "HMM" in c_raw or "HYUNDAI" in c_raw or v_clean.startswith("HMM "):
            return {"flag_emoji": "🇰🇷", "flag_country": "Güney Kore", "flag_code": "KR"}

        # Wan Hai Lines
        if "WAN HAI" in c_raw or v_clean.startswith("WAN HAI"):
            return {"flag_emoji": "🇸🇬", "flag_country": "Singapur", "flag_code": "SG"}

        # Grimaldi Lines
        if "GRIMALDI" in c_raw or "GRIMALDI" in v_clean:
            return {"flag_emoji": "🇮🇹", "flag_country": "İtalya", "flag_code": "IT"}

        # OOCL
        if "OOCL" in c_raw or v_clean.startswith("OOCL"):
            return {"flag_emoji": "🇭🇰", "flag_country": "Hong Kong", "flag_code": "HK"}

        # Uluslararası Ticari Denizcilik Açık Sicil Varsayılanı (Panama)
        return {"flag_emoji": "🇵🇦", "flag_country": "Panama (Açık Sicil)", "flag_code": "PA"}

    # --------------------------------------------------------------------------
    # KÜRESEL LİMAN VERİTABANI & DENİZ ROTA MOTORU (MSC, HAPAG, CMA, ONE...)
    # --------------------------------------------------------------------------

    GLOBAL_PORT_COORDS = {
        # Türkiye Limanları (Hankook Teslim & İthalat Limanları)
        "TREVY": (40.7686, 29.7420, "Evyap Port (Körfez)"),
        "EVYAP": (40.7686, 29.7420, "Evyap Port (Körfez)"),
        "TRYRM": (40.7650, 29.7550, "DP World Yarımca"),
        "YARIMCA": (40.7650, 29.7550, "DP World Yarımca"),
        "DP WORLD": (40.7650, 29.7550, "DP World Yarımca"),
        "TRDER": (40.7550, 29.8300, "Safi Derince Port"),
        "DERINCE": (40.7550, 29.8300, "Safi Derince Port"),
        "DERİNCE": (40.7550, 29.8300, "Safi Derince Port"),
        "TRIZT": (40.7600, 29.9200, "İzmit Port"),
        "IZMIT": (40.7600, 29.9200, "İzmit Port"),
        "İZMİT": (40.7600, 29.9200, "İzmit Port"),
        "KORFEZ": (40.7600, 29.7500, "Körfez Liman Bölgesi"),
        "KÖRFEZ": (40.7600, 29.7500, "Körfez Liman Bölgesi"),
        "TRGEB": (40.7667, 29.4333, "Gebze Yılport"),
        "GEBZE": (40.7667, 29.4333, "Gebze Yılport"),
        "YILPORT": (40.7667, 29.4333, "Gebze Yılport"),
        "TRAVC": (40.9700, 28.6900, "Ambarlı Limanı (Marport/Kumport)"),
        "AMBARLI": (40.9700, 28.6900, "Ambarlı Limanı (Marport/Kumport)"),
        "MARPORT": (40.9700, 28.6900, "Ambarlı Marport"),
        "KUMPORT": (40.9700, 28.6900, "Ambarlı Kumport"),
        "MARDAS": (40.9700, 28.6900, "Ambarlı Mardaş"),
        "TRHAY": (40.9950, 29.0180, "Haydarpaşa Port (İstanbul)"),
        "HAYDARPASA": (40.9950, 29.0180, "Haydarpaşa Port (İstanbul)"),
        "HAYDARPAŞA": (40.9950, 29.0180, "Haydarpaşa Port (İstanbul)"),
        "TRIST": (41.0082, 28.9784, "İstanbul"),
        "İSTANBUL": (41.0082, 28.9784, "İstanbul"),
        "ISTANBUL": (41.0082, 28.9784, "İstanbul"),
        "TRASY": (40.9200, 27.4700, "Asyaport (Tekirdağ)"),
        "ASYAPORT": (40.9200, 27.4700, "Asyaport (Tekirdağ)"),
        "TEKIRDAG": (40.9200, 27.4700, "Asyaport (Tekirdağ)"),
        "TEKİRDAĞ": (40.9200, 27.4700, "Asyaport (Tekirdağ)"),
        "TRGEM": (40.4300, 29.1500, "Gemlik Port (Borusan/Roda)"),
        "GEMLIK": (40.4300, 29.1500, "Gemlik Port (Borusan/Roda)"),
        "GEMLİK": (40.4300, 29.1500, "Gemlik Port (Borusan/Roda)"),
        "BORUSAN": (40.4300, 29.1500, "Gemlik Borusan Port"),
        "TRIZM": (38.4350, 27.1490, "İzmir Alsancak Port"),
        "IZMIR": (38.4350, 27.1490, "İzmir Alsancak Port"),
        "İZMİR": (38.4350, 27.1490, "İzmir Alsancak Port"),
        "ALSANCAK": (38.4350, 27.1490, "İzmir Alsancak Port"),
        "TRALI": (38.7997, 26.9667, "Aliağa / Nemrut Port"),
        "ALIAGA": (38.7997, 26.9667, "Aliağa / Nemrut Port"),
        "ALİAĞA": (38.7997, 26.9667, "Aliağa / Nemrut Port"),
        "NEMRUT": (38.7997, 26.9667, "Aliağa Nemrut"),
        "TRMER": (36.8000, 34.6333, "Mersin Uluslararası Limanı (MIP)"),
        "MERSIN": (36.8000, 34.6333, "Mersin Uluslararası Limanı (MIP)"),
        "MERSİN": (36.8000, 34.6333, "Mersin Uluslararası Limanı (MIP)"),
        "TRISK": (36.5872, 36.1735, "İskenderun Port (Limakport)"),
        "ISKENDERUN": (36.5872, 36.1735, "İskenderun Port (Limakport)"),
        "İSKENDERUN": (36.5872, 36.1735, "İskenderun Port (Limakport)"),
        "LIMAKPORT": (36.5872, 36.1735, "İskenderun Limakport"),

        # Güney Kore Limanları (Hankook Ana Üretim ve Yükleme Limanları)
        "KRPUS": (35.1028, 129.0403, "Busan Port (Güney Kore)"),
        "BUSAN": (35.1028, 129.0403, "Busan Port (Güney Kore)"),
        "PUSAN": (35.1028, 129.0403, "Busan Port (Güney Kore)"),
        "KRINC": (37.4563, 126.6170, "Incheon Port (Güney Kore)"),
        "INCHEON": (37.4563, 126.6170, "Incheon Port (Güney Kore)"),
        "KRKAN": (34.9080, 127.6975, "Gwangyang Port (Güney Kore)"),
        "GWANGYANG": (34.9080, 127.6975, "Gwangyang Port (Güney Kore)"),
        "KRUSN": (35.5080, 129.3780, "Ulsan Port (Güney Kore)"),
        "ULSAN": (35.5080, 129.3780, "Ulsan Port (Güney Kore)"),
        "KRPTK": (36.9800, 126.8500, "Pyeongtaek (Güney Kore)"),
        "PYEONGTAEK": (36.9800, 126.8500, "Pyeongtaek (Güney Kore)"),

        # Çin & Doğu Asya Limanları
        "CNSHA": (31.2304, 121.5000, "Shanghai Port (Çin)"),
        "SHANGHAI": (31.2304, 121.5000, "Shanghai Port (Çin)"),
        "YANGSHAN": (30.6200, 122.0600, "Shanghai Yangshan Port"),
        "CNNGB": (29.8683, 121.5440, "Ningbo-Zhoushan Port (Çin)"),
        "NINGBO": (29.8683, 121.5440, "Ningbo-Zhoushan Port (Çin)"),
        "CNSHK": (22.4819, 113.9142, "Shekou Port (Shenzhen, Çin)"),
        "SHEKOU": (22.4819, 113.9142, "Shekou Port (Shenzhen, Çin)"),
        "CNYTN": (22.5800, 114.2700, "Yantian Port (Shenzhen, Çin)"),
        "YANTIAN": (22.5800, 114.2700, "Yantian Port (Shenzhen, Çin)"),
        "SHENZHEN": (22.5400, 114.0500, "Shenzhen (Çin)"),
        "CNTAO": (36.0671, 120.3826, "Qingdao Port (Çin)"),
        "QINGDAO": (36.0671, 120.3826, "Qingdao Port (Çin)"),
        "CNXMN": (24.4798, 118.0894, "Xiamen Port (Çin)"),
        "XIAMEN": (24.4798, 118.0894, "Xiamen Port (Çin)"),
        "CNNSA": (22.7500, 113.6000, "Nansha Port (Guangzhou, Çin)"),
        "NANSHA": (22.7500, 113.6000, "Nansha Port (Guangzhou, Çin)"),
        "GUANGZHOU": (23.1291, 113.2644, "Guangzhou (Çin)"),
        "HKHKG": (22.3193, 114.1694, "Hong Kong Port"),
        "HONG KONG": (22.3193, 114.1694, "Hong Kong Port"),
        "HONGKONG": (22.3193, 114.1694, "Hong Kong Port"),

        # Güneydoğu Asya Limanları
        "SGSIN": (1.2644, 103.8220, "Singapore Hub Port"),
        "SINGAPORE": (1.2644, 103.8220, "Singapore Hub Port"),
        "MYTPP": (1.3600, 103.5500, "Tanjung Pelepas (Malezya)"),
        "TANJUNG PELEPAS": (1.3600, 103.5500, "Tanjung Pelepas (Malezya)"),
        "MYPKG": (2.9999, 101.3928, "Port Klang (Malezya)"),
        "PORT KLANG": (2.9999, 101.3928, "Port Klang (Malezya)"),
        "KLANG": (2.9999, 101.3928, "Port Klang (Malezya)"),
        "IDJKT": (-6.1010, 106.8820, "Jakarta / Tanjung Priok (Endonezya)"),
        "JAKARTA": (-6.1010, 106.8820, "Jakarta (Endonezya)"),
        "THLCH": (13.0800, 100.8800, "Laem Chabang (Tayland)"),
        "LAEM CHABANG": (13.0800, 100.8800, "Laem Chabang (Tayland)"),
        "VNSGN": (10.5300, 107.0300, "Cai Mep / Ho Chi Minh (Vietnam)"),
        "HO CHI MINH": (10.5300, 107.0300, "Cai Mep / Ho Chi Minh (Vietnam)"),

        # Hint Okyanusu & Kızıldeniz & Orta Doğu
        "LKCMB": (6.9497, 79.8436, "Colombo Port (Sri Lanka)"),
        "COLOMBO": (6.9497, 79.8436, "Colombo Port (Sri Lanka)"),
        "OMSLL": (16.9400, 54.0040, "Salalah Port (Umman)"),
        "SALALAH": (16.9400, 54.0040, "Salalah Port (Umman)"),
        "AEJEA": (25.0110, 55.0610, "Jebel Ali Port (Dubai, BAE)"),
        "JEBEL ALI": (25.0110, 55.0610, "Jebel Ali Port (Dubai, BAE)"),
        "DUBAI": (25.0110, 55.0610, "Dubai (BAE)"),
        "SAJED": (21.4858, 39.1925, "Jeddah Islamic Port (Suudi Arabistan)"),
        "JEDDAH": (21.4858, 39.1925, "Jeddah Islamic Port (Suudi Arabistan)"),
        "SAKAP": (22.5300, 39.0800, "King Abdullah Port (Suudi Arabistan)"),
        "KING ABDULLAH": (22.5300, 39.0800, "King Abdullah Port (Suudi Arabistan)"),
        "EGPSD": (31.2653, 32.3019, "Port Said (Mısır / Süveyş Kuzey Girişi)"),
        "PORT SAID": (31.2653, 32.3019, "Port Said (Mısır)"),
        "EGSUZ": (29.9737, 32.5599, "Suez Port (Süveyş Kanalı)"),
        "SUEZ": (29.9737, 32.5599, "Suez Port (Süveyş Kanalı)"),
        "EGALY": (31.2001, 29.9187, "Alexandria Port (Mısır)"),
        "ALEXANDRIA": (31.2001, 29.9187, "Alexandria Port (Mısır)"),
        "EGDAM": (31.4200, 31.8100, "Damietta Port (Mısır)"),
        "DAMIETTA": (31.4200, 31.8100, "Damietta Port (Mısır)"),
        "LBBEY": (33.9000, 35.5167, "Beirut Port (Lübnan)"),
        "BEIRUT": (33.9000, 35.5167, "Beirut Port (Lübnan)"),
        "SYLTK": (35.5167, 35.7833, "Lattakia Port (Suriye)"),
        "LATTAKIA": (35.5167, 35.7833, "Lattakia Port (Suriye)"),
        "ILASH": (31.8300, 34.6500, "Ashdod Port (İsrail)"),
        "ASHDOD": (31.8300, 34.6500, "Ashdod Port (İsrail)"),
        "ILHFA": (32.8200, 34.9900, "Haifa Port (İsrail)"),
        "HAIFA": (32.8200, 34.9900, "Haifa Port (İsrail)"),

        # Akdeniz & Avrupa Limanları
        "GRPIR": (37.9420, 23.6370, "Piraeus Port (Yunanistan)"),
        "PIRAEUS": (37.9420, 23.6370, "Piraeus Port (Yunanistan)"),
        "GRSKG": (40.6400, 22.9300, "Thessaloniki Port (Selanik)"),
        "THESSALONIKI": (40.6400, 22.9300, "Thessaloniki Port (Selanik)"),
        "SELANIK": (40.6400, 22.9300, "Thessaloniki Port (Selanik)"),
        "SIKOP": (45.5488, 13.7301, "Koper Port (Slovenya)"),
        "KOPER": (45.5488, 13.7301, "Koper Port (Slovenya)"),
        "ITTRS": (45.6500, 13.7700, "Trieste Port (İtalya)"),
        "TRIESTE": (45.6500, 13.7700, "Trieste Port (İtalya)"),
        "MTMLA": (35.8167, 14.5333, "Malta Freeport (Marsaxlokk)"),
        "MALTA": (35.8167, 14.5333, "Malta Freeport"),
        "MARSAXLOKK": (35.8167, 14.5333, "Malta Freeport (Marsaxlokk)"),
        "ITGIT": (38.4300, 15.9000, "Gioia Tauro (İtalya)"),
        "GIOIA TAURO": (38.4300, 15.9000, "Gioia Tauro (İtalya)"),
        "ITGOA": (44.4056, 8.9463, "Genoa Port (İtalya)"),
        "GENOA": (44.4056, 8.9463, "Genoa Port (İtalya)"),
        "ESVLC": (39.4699, -0.3763, "Valencia Port (İspanya)"),
        "VALENCIA": (39.4699, -0.3763, "Valencia Port (İspanya)"),
        "ESBCN": (41.3851, 2.1734, "Barcelona Port (İspanya)"),
        "BARCELONA": (41.3851, 2.1734, "Barcelona Port (İspanya)"),
        "ESALG": (36.1408, -5.4562, "Algeciras Port (İspanya)"),
        "ALGECIRAS": (36.1408, -5.4562, "Algeciras Port (İspanya)"),
        "MAPTM": (35.8800, -5.5000, "Tanger Med Port (Fas)"),
        "TANGER MED": (35.8800, -5.5000, "Tanger Med Port (Fas)"),
        "NLRTM": (51.9244, 4.4777, "Rotterdam Port (Hollanda)"),
        "ROTTERDAM": (51.9244, 4.4777, "Rotterdam Port (Hollanda)"),
        "BEANR": (51.2194, 4.4025, "Antwerp Port (Belçika)"),
        "ANTWERP": (51.2194, 4.4025, "Antwerp Port (Belçika)"),
        "DEHAM": (53.5511, 9.9937, "Hamburg Port (Almanya)"),
        "HAMBURG": (53.5511, 9.9937, "Hamburg Port (Almanya)"),
        "HUBUD": (47.4979, 19.0402, "Budapeşte Terminali (Macaristan)"),
        "BUDAPEST": (47.4979, 19.0402, "Budapeşte Terminali (Macaristan)")
    }

    # Asya -> Türkiye Deniz Seyir Koridoru Düğümleri (Navigable Choke Points)
    ASIA_TO_TURKEY_CORRIDOR = [
        (34.0, 128.5, "Kore Boğazı (Tsushima)"),
        (30.0, 123.5, "Doğu Çin Denizi"),
        (24.0, 119.5, "Tayvan Boğazı"),
        (18.0, 115.0, "Güney Çin Denizi"),
        (11.0, 110.0, "Vietnam Açıkları"),
        (4.5, 105.5, "Güney Çin Denizi Çıkışı"),
        (1.30, 104.30, "Singapur Boğazı Girişi"),
        (1.26, 103.82, "Singapur Boğazı"),
        (2.80, 101.20, "Malakka Boğazı"),
        (5.80, 96.00, "Malakka Kuzeybatı Çıkışı"),
        (5.80, 80.50, "Hint Okyanusu (Sri Lanka Güneyi)"),
        (9.50, 68.00, "Umman Denizi"),
        (12.50, 51.50, "Aden Körfezi Girişi (Sokotra)"),
        (12.58, 43.33, "Babülmendep Boğazı"),
        (16.00, 41.20, "Güney Kızıldeniz"),
        (21.00, 38.20, "Kızıldeniz Orta Hat"),
        (26.50, 35.00, "Kuzey Kızıldeniz"),
        (28.80, 33.00, "Süveyş Körfezi"),
        (29.95, 32.56, "Süveyş Kanalı Güney Girişi"),
        (31.27, 32.30, "Port Said (Süveyş Kuzey Çıkışı)"),
        (34.00, 29.50, "Doğu Akdeniz"),
        (36.20, 26.80, "Ege Denizi Girişi (Rodos/Kerpe)"),
        (37.80, 25.50, "Orta Ege Koridoru"),
        (39.50, 25.50, "Kuzey Ege Denizi"),
        (40.05, 26.20, "Çanakkale Boğazı Girişi (Kumkale)"),
        (40.20, 26.45, "Çanakkale Boğazı (Kilitbahir)"),
        (40.40, 26.70, "Çanakkale Boğazı Çıkışı (Gelibolu)"),
        (40.75, 27.80, "Marmara Denizi Batı"),
        (40.80, 28.60, "Marmara Denizi Açıkları (Ambarlı Açığı)"),
        (40.77, 29.50, "İzmit Körfezi Girişi (Osmangazi Köprüsü Yaklaşımı)")
    ]

    # Adriyatik & Orta Akdeniz -> Türkiye Deniz Seyir Koridoru Düğümleri
    ADRIATIC_TO_TURKEY_CORRIDOR = [
        (44.00, 14.50, "Kuzey Adriyatik Denizi"),
        (42.00, 16.80, "Orta Adriyatik Denizi"),
        (40.10, 18.90, "Otranto Boğazı"),
        (38.00, 20.50, "İyon Denizi"),
        (36.30, 23.00, "Mora Yarımadası Güneyi (Kithira Boğazı)"),
        (37.20, 24.80, "Güney Ege Denizi"),
        (39.20, 25.50, "Kuzey Ege Denizi"),
        (40.05, 26.20, "Çanakkale Boğazı Girişi"),
        (40.20, 26.45, "Çanakkale Boğazı"),
        (40.40, 26.70, "Çanakkale Boğazı Çıkışı"),
        (40.75, 27.80, "Marmara Denizi"),
        (40.77, 29.50, "İzmit Körfezi Girişi")
    ]

    def _resolve_port(self, text_str, hint_dosya=""):
        """Metin veya UN/LOCODE kodundan koordinat ve standart liman künyesi bulur."""
        if not text_str and not hint_dosya:
            return None
        raw = normalize_turkish(str(text_str or ""))

        # 1. Parantez içi 5 harfli UN/LOCODE ara: örn (KRPUS), (TRIZT), (TRGEB)
        m = re.search(r'\(([A-Z]{5})\)', raw)
        if m:
            code = m.group(1)
            if code in self.GLOBAL_PORT_COORDS:
                lat, lng, name = self.GLOBAL_PORT_COORDS[code]
                return {"lat": lat, "lng": lng, "name": name, "code": code}

        # 2. Tam veya alt kelime eşleşmesi (uzun anahtarlar öncelikli)
        sorted_keys = sorted(self.GLOBAL_PORT_COORDS.keys(), key=lambda k: -len(k))
        for k in sorted_keys:
            if k in raw:
                lat, lng, name = self.GLOBAL_PORT_COORDS[k]
                return {"lat": lat, "lng": lng, "name": name, "code": k}

        # 3. Dosya adından ipucu (örn: "DERİNCE (26-120185)")
        if hint_dosya:
            h_raw = normalize_turkish(str(hint_dosya))
            for k in sorted_keys:
                if k in h_raw:
                    lat, lng, name = self.GLOBAL_PORT_COORDS[k]
                    return {"lat": lat, "lng": lng, "name": name, "code": k}

        return None

    def _parse_transshipment_ports(self, trans_str, pol_name="", pod_name=""):
        """Aktarma dizgesindeki (-> veya ➔) ara limanları sırayla tespit eder."""
        if not trans_str or str(trans_str).strip() in ("—", "Direkt", "Direct", "None", ""):
            return []
        tokens = re.split(r'->|➔|,|/|;', str(trans_str))
        found_ports = []
        seen_names = {normalize_turkish(pol_name), normalize_turkish(pod_name)}
        for tok in tokens:
            clean = tok.strip()
            if not clean:
                continue
            p = self._resolve_port(clean)
            if p:
                norm_pname = normalize_turkish(p["name"])
                if norm_pname not in seen_names:
                    seen_names.add(norm_pname)
                    found_ports.append(p)
        return found_ports

    def _calc_segment_distance(self, p1, p2):
        lat1, lng1 = p1
        lat2, lng2 = p2
        avg_lat = math.radians((lat1 + lat2) / 2.0)
        dx = (lng2 - lng1) * math.cos(avg_lat)
        dy = (lat2 - lat1)
        return math.hypot(dx, dy)

    def _build_maritime_polyline(self, pol_pt, pod_pt, trans_ports=[]):
        """Deniz boğazları ve koridorları üzerinden kesintisiz gerçekçi seyir rotası üretir."""
        polyline = []
        polyline.append([pol_pt["lat"], pol_pt["lng"]])

        pol_lng = pol_pt["lng"]
        pod_lng = pod_pt["lng"]
        pol_lat = pol_pt["lat"]
        pod_lat = pod_pt["lat"]

        # Asya -> Türkiye / Doğu Akdeniz Rotası (Busan, Singapur, Çin -> İzmit Körfezi / Derince / Evyap)
        if pol_lng > 40 and pod_lng < 40:
            for lat, lng, name in self.ASIA_TO_TURKEY_CORRIDOR:
                if lng > pol_lng + 2:
                    continue
                if pod_lat < 33 and lng < pod_lng:
                    break
                polyline.append([lat, lng])

        # Adriyatik -> Türkiye Rotası (Koper, Trieste -> Gebze / İzmit)
        elif pol_lat > 42 and pol_lng < 20 and pod_lng > 25:
            for lat, lng, name in self.ADRIATIC_TO_TURKEY_CORRIDOR:
                polyline.append([lat, lng])

        # Son nokta: Varış Limanı (POD)
        polyline.append([pod_pt["lat"], pod_pt["lng"]])
        return polyline

    def _interpolate_vessel_position(self, polyline, it):
        """
        Armatör canlı AIS koordinatı sağlamamışsa, kalan gün / ETA süresine göre gemiyi deniz rotası üzerinde konumlandırır.
        """
        if it.get("vessel_lat") and it.get("vessel_lng"):
            return it["vessel_lat"], it["vessel_lng"], "Akdeniz Seyrinde (Canlı AIS)"

        if len(polyline) < 2:
            return None, None, None

        kalan = str(it.get("kalan_gun", ""))
        # Varış kontrolü
        if "Limana İndi" in kalan or "Bugün" in kalan:
            last = polyline[-1]
            return last[0], last[1], "Varış Limanında / Rıhtımda"

        # Kalan gün sayısı
        m = re.search(r'(\d+)\s*Gün', kalan)
        days_left = int(m.group(1)) if m else None

        # Sefer süresi tahmini: Asya-Türkiye ~38 gün, Adriyatik-Türkiye ~8 gün
        is_far_east = polyline[0][1] > 60
        total_voyage_days = 38 if is_far_east else 8

        if days_left is not None:
            progress = max(0.05, min(0.96, (total_voyage_days - days_left) / float(total_voyage_days)))
        else:
            progress = 0.65

        # Kümülatif segment mesafeleri
        cum_dists = [0.0]
        for i in range(len(polyline) - 1):
            d = self._calc_segment_distance(polyline[i], polyline[i+1])
            cum_dists.append(cum_dists[-1] + d)

        total_dist = cum_dists[-1]
        target_dist = total_dist * progress

        for i in range(len(cum_dists) - 1):
            if cum_dists[i] <= target_dist <= cum_dists[i+1]:
                seg_len = cum_dists[i+1] - cum_dists[i]
                frac = (target_dist - cum_dists[i]) / seg_len if seg_len > 0 else 0
                p_a = polyline[i]
                p_b = polyline[i+1]
                v_lat = p_a[0] + frac * (p_b[0] - p_a[0])
                v_lng = p_a[1] + frac * (p_b[1] - p_a[1])
                status_text = f"Deniz Seyrinde (ETA Rota Hesabı: {kalan})"
                return round(v_lat, 4), round(v_lng, 4), status_text

        mid = polyline[len(polyline)//2]
        return mid[0], mid[1], "Deniz Seyrinde"

    def _build_map_payload(self, it):
        vessel = it.get("vessel", "Gemi")
        live_eta = it.get("live_eta", "")
        pol_raw = it.get("pol", "")
        pod_raw = it.get("pod", "")
        dosya = it.get("dosya", "")

        points = []
        polyline = []
        v_lat = it.get("vessel_lat")
        v_lng = it.get("vessel_lng")
        v_status = None

        # 1. CMA CGM Orijinal GeoJSON rotası var mı?
        v_pos = it.get("vessel_position")
        if v_pos and isinstance(v_pos, dict):
            features = v_pos.get("PositionRoute", {}).get("Features", [])
            for feat in features:
                props = feat.get("Properties", {})
                code = (props.get("Code") or props.get("Name") or "").upper()
                dt = props.get("Date")

                p_res = self._resolve_port(code)
                if p_res:
                    points.append({"name": p_res["name"], "code": p_res["code"], "lat": p_res["lat"], "lng": p_res["lng"], "date": dt})
                    polyline.append([p_res["lat"], p_res["lng"]])

        # 2. Eğer GeoJSON yoksa (MSC, Hapag-Lloyd, ONE, Cosco veya GeoJSON'suz CMA CGM):
        if not points:
            # Kalkış Limanı (POL)
            pol_pt = self._resolve_port(pol_raw)
            if not pol_pt:
                c_name = str(it.get("carrier", "")).upper()
                if "KOPER" in str(pol_raw).upper() or "HUNGARY" in c_name or "WABERER" in c_name:
                    pol_pt = self._resolve_port("KOPER")
                else:
                    pol_pt = self._resolve_port("BUSAN")

            # Varış Limanı (POD)
            pod_pt = self._resolve_port(pod_raw, dosya)
            if not pod_pt:
                pod_pt = self._resolve_port("DERINCE")

            # Aktarma Limanları
            trans_ports = self._parse_transshipment_ports(
                it.get("transshipments", ""),
                pol_name=pol_pt["name"] if pol_pt else "",
                pod_name=pod_pt["name"] if pod_pt else ""
            )

            # Noktaları Diz
            if pol_pt:
                points.append({
                    "name": pol_pt["name"],
                    "code": pol_pt["code"],
                    "lat": pol_pt["lat"],
                    "lng": pol_pt["lng"],
                    "is_pol": True
                })

            for tp in trans_ports:
                points.append({
                    "name": tp["name"],
                    "code": tp["code"],
                    "lat": tp["lat"],
                    "lng": tp["lng"],
                    "is_intermediate": True
                })

            if pod_pt:
                points.append({
                    "name": pod_pt["name"],
                    "code": pod_pt["code"],
                    "lat": pod_pt["lat"],
                    "lng": pod_pt["lng"],
                    "is_pod": True
                })

            # Deniz Koridoru Polyline Çizgisi
            if pol_pt and pod_pt:
                polyline = self._build_maritime_polyline(pol_pt, pod_pt, trans_ports)

            # Gemi Konumu Hesapla / Canlı AIS Al
            v_lat, v_lng, v_status = self._interpolate_vessel_position(polyline, it)

        elif v_lat:
            v_status = "Akdeniz Seyrinde (Canlı AIS)"

        flag_info = self._resolve_vessel_flag(vessel, it.get("carrier", ""))

        return {
            "vessel_name": vessel,
            "vessel_flag_emoji": flag_info.get("flag_emoji", ""),
            "vessel_flag_country": flag_info.get("flag_country", ""),
            "vessel_flag_code": flag_info.get("flag_code", ""),
            "live_eta": live_eta,
            "vessel_lat": v_lat,
            "vessel_lng": v_lng,
            "vessel_status": v_status,
            "points": points,
            "polyline": polyline
        }

    def _populate_milestones(self, it, map_payload=None):
        while self.milestone_layout.count():
            w = self.milestone_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        pol = it.get("pol", "Yükleme Limanı")
        pod = it.get("pod", "Varış Limanı")
        vessel = it.get("vessel", "Gemi")
        live_eta = it.get("live_eta", "—")
        curr = it.get("current_moves") or []
        prov = it.get("provisional_moves") or []

        carrier = it.get("carrier", "")
        flag_info = self._resolve_vessel_flag(vessel, carrier)
        flag_emoji = flag_info.get("flag_emoji", "")
        flag_country = flag_info.get("flag_country", "")
        flag_suffix = f" {flag_emoji}" if flag_emoji else ""

        has_moves = False

        for m in curr:
            has_moves = True
            loc = m.get("Location") or m.get("LocationTerminal") or "Liman"
            dt_s = m.get("DateString") or m.get("Date", "")[:10]
            desc = m.get("StatusDescription") or "Ayrıldı"
            v = m.get("Vessel") or vessel
            v_flag_info = self._resolve_vessel_flag(v, carrier)
            v_flag_str = f" {v_flag_info.get('flag_emoji', '')}" if v_flag_info.get('flag_emoji') else ""
            self.milestone_layout.addWidget(self._make_milestone_item("✅", f"{loc} — {desc}", f"{dt_s} ({v}{v_flag_str})", "#34d399"))

        if it.get("vessel_lat"):
            has_moves = True
            self.milestone_layout.addWidget(self._make_milestone_item("📡", f"{vessel}{flag_suffix} — Deniz Seyrinde (Canlı AIS)", f"Konum: {it['vessel_lat']:.2f}°, {it['vessel_lng']:.2f}°  •  🚩 Bayrak: {flag_country}", "#38bdf8"))

        for m in prov:
            has_moves = True
            loc = m.get("Location") or m.get("LocationTerminal") or "Varış Limanı"
            dt_s = m.get("DateString") or m.get("Date", "")[:10]
            desc = m.get("StatusDescription") or "Planlanan Varış"
            self.milestone_layout.addWidget(self._make_milestone_item("🏁", f"{loc} — {desc}", f"Planlanan: {dt_s}", "#f59e0b"))

        # Eğer armatör API'si adım bazlı moves döndürmemişse (MSC, Hapag-Lloyd vb.):
        if not has_moves:
            pts = (map_payload or {}).get("points", [])
            pol_title = pts[0]["name"] if pts and pts[0].get("is_pol") else pol
            pod_title = pts[-1]["name"] if pts and pts[-1].get("is_pod") else pod

            self.milestone_layout.addWidget(self._make_milestone_item("🛫", f"Kalkış Limanı (POL): {pol_title}", "Yüklendi / Sefer Başladı", "#34d399"))

            # Ara aktarma limanları
            for pt in pts:
                if pt.get("is_intermediate"):
                    self.milestone_layout.addWidget(self._make_milestone_item("⚓", f"Ara Uğrak Limanı: {pt['name']}", "Aktarma / Liman Uğrağı", "#f59e0b"))

            # Seyir durumu
            v_lat = (map_payload or {}).get("vessel_lat")
            v_lng = (map_payload or {}).get("vessel_lng")
            v_status = (map_payload or {}).get("vessel_status") or "Deniz Seyrinde"
            coord_str = f"Konum: {v_lat:.2f}°, {v_lng:.2f}°  •  🚩 Bayrak: {flag_country}" if v_lat and v_lng else f"Seyir Rotasında  •  🚩 Bayrak: {flag_country}"
            self.milestone_layout.addWidget(self._make_milestone_item("🚢", f"{vessel}{flag_suffix} — {v_status}", coord_str, "#38bdf8"))

            self.milestone_layout.addWidget(self._make_milestone_item("🎯", f"Varış Limanı (POD): {pod_title}", f"Canlı ETA: {live_eta}", "#10b981"))

        # 4. Boş Konteyner İadesi (Empty Return) Adımı
        empty_date = it.get("empty_return_date")
        empty_addr = it.get("empty_return_address")
        if empty_addr and str(empty_date)[:4] not in ("0001", "None", ""):
            self.milestone_layout.addWidget(self._make_milestone_item("🔄", f"Boş İade Deposu: {empty_addr}", f"Son Teslim: {str(empty_date)[:10]}", "#38bdf8"))
        else:
            self.milestone_layout.addWidget(self._make_milestone_item("🔄", "Boş Konteyner İade (Empty Return)", f"Varış sonrası {pod} acenta deposuna teslim edilecektir", "#64748b"))

        self.milestone_layout.addStretch(1)

    def _make_milestone_item(self, icon, title, subtitle, color):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(4, 2, 4, 2)
        l.setSpacing(8)

        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(f"font-size: 13px; color: {color};")
        l.addWidget(lbl_icon)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 700; color: #f1f5f9;")
        lbl_s = QLabel(subtitle)
        lbl_s.setStyleSheet("font-size: 10px; color: #94a3b8;")
        text_box.addWidget(lbl_t)
        text_box.addWidget(lbl_s)
        l.addLayout(text_box, 1)

        return w

    # --------------------------------------------------------------------------
    # EYLEMLER & TARAMA
    # --------------------------------------------------------------------------

    def _refresh_memory_live(self):
        if not self.results_data:
            QMessageBox.information(self, "Bilgi", "Hafızada taranacak kayıt bulunamadı. Lütfen önce Excel taraması yapın.")
            return

        self.lbl_status.setText("🔄 Hafızadaki yükler canlı sorgulanıyor...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.scanner_thread = BackgroundScanner(
            self.router, mode="memory", existing_data=self.results_data
        )
        self.scanner_thread.progress_signal.connect(self._on_scan_progress)
        self.scanner_thread.completed_signal.connect(self._on_scan_completed)
        self.scanner_thread.start()

    def _scan_excel(self):
        def_path = self.config.get("default_excel_path", "")
        resolved = resolve_excel_path(def_path)
        if not resolved:
            f, _ = QFileDialog.getOpenFileName(self, "İş Takip Excel Dosyası Seç", "", "Excel (*.xlsx *.xls)")
            if not f:
                return
            resolved = f

        self.lbl_status.setText(f"🔄 Excel okunuyor: {os.path.basename(resolved)}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.scanner_thread = BackgroundScanner(
            self.router, mode="excel", target_path=resolved, existing_data=self.results_data
        )
        self.scanner_thread.progress_signal.connect(self._on_scan_progress)
        self.scanner_thread.completed_signal.connect(self._on_scan_completed)
        self.scanner_thread.start()

    def _on_scan_progress(self, msg, cur, tot):
        self.lbl_status.setText(msg)
        if tot > 0:
            self.progress_bar.setValue(int((cur / tot) * 100))

    def _on_scan_completed(self, data, success_cnt, tot):
        self.results_data = data
        self.progress_bar.setVisible(False)
        now_s = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.lbl_last_check.setText(f"Son Güncelleme: {now_s}")
        self.lbl_status.setText(f"✅ Tarama tamamlandı ({success_cnt}/{tot} canlı ETA güncellendi).")
        self._populate_table()
        QMessageBox.information(self, "SmartClearance Horizon", f"Canlı tarama başarıyla tamamlandı!\n\nCanlı güncellenen yük sayısı: {success_cnt}/{tot}")

    def _on_table_double_click(self, index):
        row = index.row()
        cntr = self.table.item(row, 2).text()
        bl = self.table.item(row, 3).text()
        q = cntr if cntr not in ("—", "") else bl
        if not q or q == "—":
            return

        carrier = self.table.item(row, 1).text()
        self.lbl_status.setText(f"⚡ {q} anlık canlı sorgulanıyor...")

        def _do_single():
            res = self.router.track(q, acenta_hint=carrier)
            if res and res.get("success") and res.get("items"):
                fresh = res["items"][0]
                for it in self.results_data:
                    if (it.get("container_no") == cntr) or (it.get("bl_no") == bl):
                        it.update(fresh)
                        break
                save_cache(self.results_data)
                QTimer.singleShot(0, self._populate_table)

        import threading
        threading.Thread(target=_do_single, daemon=True).start()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        cntr = self.table.item(row, 2).text()
        bl = self.table.item(row, 3).text()

        menu = QMenu(self)
        a_refresh = menu.addAction("⚡ Bu Yükü Anlık Canlı Sorgula")
        a_pdf = menu.addAction(f"📄 Bu Yük İçin Horizon Sefer Bülteni Çıkar ({cntr or bl})")
        a_copy_cntr = menu.addAction(f"📋 Konteyner No Kopyala ({cntr})")
        a_copy_bl = menu.addAction(f"📋 B/L No Kopyala ({bl})")

        act = menu.exec(self.table.mapToGlobal(pos))
        if act == a_refresh:
            self._on_table_double_click(self.table.currentIndex())
        elif act == a_pdf:
            self._export_single_pdf()
        elif act == a_copy_cntr and cntr != "—":
            QApplication.clipboard().setText(cntr)
        elif act == a_copy_bl and bl != "—":
            QApplication.clipboard().setText(bl)

    def _export_excel(self):
        if not self.results_data or not openpyxl:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak veri bulunamadı.")
            return

        def_name = f"SmartClearance_Horizon_Rapor_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        save_path, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet", def_name, "Excel (*.xlsx)")
        if not save_path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Horizon Canlı Takip"

        headers = ["Dosya No", "Armatör", "Konteyner No", "B/L No", "Excel ETA", "Canlı ETA", "Sapma", "Kalan Gün", "Gemi Adı", "Tahliye Limanı", "Kaynak"]
        ws.append(headers)

        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for it in self.results_data:
            ws.append([
                it.get("dosya", "—"),
                it.get("carrier", "—"),
                it.get("container_no", "—"),
                it.get("bl_no", "—"),
                it.get("excel_eta", "—"),
                it.get("live_eta", "—"),
                it.get("eta_diff", "—"),
                it.get("kalan_gun", "—"),
                it.get("vessel", "—"),
                it.get("pod", "—"),
                it.get("source", "—")
            ])

        for col in ws.columns:
            max_len = max(len(str(c.value or '')) for c in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(save_path)
        QMessageBox.information(self, "Başarılı", f"Rapor başarıyla kaydedildi:\n{save_path}")

    # --------------------------------------------------------------------------
    # HORIZON SEFER BÜLTENİ & YÖNETİCİ RAPORLARI
    # --------------------------------------------------------------------------

    def _show_pdf_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b111e;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 9px 20px;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11.5px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 8px;
            }
        """)
        a_single = menu.addAction("📄 Seçili Yükün Horizon Sefer Bülteni (Tek Yük PDF)")
        menu.addSeparator()
        a_carrier = menu.addAction("🚢 Armatör Bazlı Özel Sefer Bülteni (Filtreli PDF)...")
        a_fleet = menu.addAction("📊 Genel Filo Sefer & Operasyon Özeti (Tüm Yükler PDF)")

        btn = self.sender()
        pos = btn.mapToGlobal(btn.rect().bottomLeft()) if btn else QCursor.pos()
        act = menu.exec(pos)
        if act == a_single:
            self._export_single_pdf()
        elif act == a_carrier:
            self._export_carrier_pdf()
        elif act == a_fleet:
            self._export_fleet_pdf()

    def _export_carrier_pdf(self):
        if not self.results_data:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak yük verisi bulunamadı.")
            return

        dlg = CarrierPdfSelectionDialog(self, self.results_data)
        if not dlg.exec():
            return

        selected_carriers, only_active = dlg.get_selection()
        if not selected_carriers:
            return

        # Yükleri filtrele
        filtered_items = []
        for it in self.results_data:
            if only_active and not it.get("is_active", True):
                continue
            c = (it.get("carrier") or "DİĞER").strip().upper()
            if not c or c == "—":
                c = "DİĞER"
            if any(sel in c or c in sel for sel in selected_carriers):
                filtered_items.append(it)

        if not filtered_items:
            QMessageBox.warning(
                self, "Kayıt Bulunamadı",
                "Seçilen armatör(ler) için uygun yük kaydı bulunamadı."
            )
            return

        # Dosya adı ve başlık oluştur
        today_s = datetime.now().strftime('%Y%m%d')
        if len(selected_carriers) == 1:
            c_tag = re.sub(r'[^A-Za-z0-9]', '', selected_carriers[0])
            def_name = f"SmartClearance_Bulten_{c_tag}_{today_s}.pdf"
            title_text = f"SmartClearance Horizon — {selected_carriers[0]} Özel Sefer Bülteni"
            subtitle_text = f"Doğruer Gümrük Müşavirliği • {selected_carriers[0]} Özel Operasyon Raporu"
        else:
            c_tags = "_".join([re.sub(r'[^A-Za-z0-9]', '', c)[:6] for c in selected_carriers[:3]])
            def_name = f"SmartClearance_Bulten_CokluArmator_{c_tags}_{today_s}.pdf"
            c_names_str = ", ".join(selected_carriers)
            title_text = f"SmartClearance Horizon — Çoklu Armatör Sefer Bülteni"
            subtitle_text = f"Kapsam: {c_names_str} ({len(filtered_items)} Yük)"

        save_path, _ = QFileDialog.getSaveFileName(self, "Armatör Bazlı Horizon Bültenini Kaydet", def_name, "PDF (*.pdf)")
        if not save_path:
            return

        # Filtrelenen yüklerin KPI istatistiklerini anlık hesapla
        delayed_cnt = sum(1 for it in filtered_items if ("Rötar" in str(it.get("eta_diff", "")) or "+" in str(it.get("eta_diff", ""))))
        ontime_cnt = sum(1 for it in filtered_items if any(k in str(it.get("eta_diff", "")) for k in ["Zamanında", "Erken", "Aynı"]))
        live_cnt = sum(1 for it in filtered_items if it.get("live_eta") not in ("—", "", None))

        kpi_stats = {
            "total": str(len(filtered_items)),
            "delayed": str(delayed_cnt),
            "ontime": str(ontime_cnt),
            "live": str(live_cnt)
        }

        self.lbl_status.setText(f"📄 Armatör bülteni üretiliyor ({len(filtered_items)} yük)...")
        self.pdf_generator.generate_fleet_summary(
            filtered_items, kpi_stats, save_path,
            title=title_text, subtitle=subtitle_text
        )

    def _export_single_pdf(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Bilgi", "Lütfen önce tablodan bir yük seçin.")
            return
        row = sel[0].row()
        dosya = self.table.item(row, 0).text()
        cntr = self.table.item(row, 2).text()
        bl = self.table.item(row, 3).text()

        selected_item = None
        for it in self.results_data:
            if it.get("dosya") == dosya and (it.get("container_no") == cntr or it.get("bl_no") == bl):
                selected_item = it
                break

        if not selected_item:
            QMessageBox.warning(self, "Hata", "Seçili yükün detay verisi bulunamadı.")
            return

        ref_name = cntr if (cntr and cntr != "—") else (bl if bl != "—" else "Yuk")
        def_name = f"SmartClearance_Bulten_{ref_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Horizon Sefer Bültenini Kaydet", def_name, "PDF (*.pdf)")
        if not save_path:
            return

        self.lbl_status.setText(f"📄 Horizon Sefer Bülteni üretiliyor: {ref_name}...")
        self.pdf_generator.generate_single_brief(selected_item, save_path)

    def _export_fleet_pdf(self):
        if not self.results_data:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak veri bulunamadı.")
            return

        def_name = f"SmartClearance_Horizon_Filo_Ozeti_{datetime.now().strftime('%Y%m%d')}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Horizon Filo Bültenini Kaydet", def_name, "PDF (*.pdf)")
        if not save_path:
            return

        kpi_stats = {
            "total": self.card_total["val"].text(),
            "delayed": self.card_delayed["val"].text(),
            "ontime": self.card_ontime["val"].text(),
            "live": self.card_live["val"].text()
        }
        self.lbl_status.setText("📄 Horizon filo raporu üretiliyor...")
        self.pdf_generator.generate_fleet_summary(self.results_data, kpi_stats, save_path)

    def _on_pdf_generation_finished(self, path, success):
        if success and os.path.exists(path):
            self.lbl_status.setText(f"✅ PDF bülteni oluşturuldu: {os.path.basename(path)}")
            try:
                os.startfile(path)
            except Exception:
                pass
            QMessageBox.information(
                self, "Horizon Sefer Bülteni Hazır",
                f"SmartClearance Horizon Sefer Bülteni başarıyla oluşturuldu ve açıldı:\n\n{path}"
            )
        else:
            self.lbl_status.setText("❌ PDF oluşturulurken hata oluştu.")
            QMessageBox.critical(self, "Hata", "PDF belgesi oluşturulamadı.")
            QMessageBox.critical(self, "Hata", "PDF belgesi oluşturulamadı.")

    def _open_settings(self):
        dlg = HorizonSettingsDialog(self, self.config)
        if dlg.exec():
            self.config = load_config()
            self.router = GlobalTrackingRouter(self.config)
            QMessageBox.information(self, "Kaydedildi", "Acenta ayarları ve yapılandırma başarıyla güncellendi.")


# ==============================================================================
# ARMATÖR BAZLI PDF BÜLTEN SEÇİM DİYALOĞU (APPLE / OBSIDIAN MODAL STİLİ)
# ==============================================================================

class CarrierPdfSelectionDialog(QDialog):
    """Kullanıcının bir veya birden fazla armatör seçerek özel PDF bülteni üretmesini sağlayan diyalog."""

    def __init__(self, parent, items):
        super().__init__(parent)
        self.setWindowTitle("SmartClearance Horizon — Armatör Bazlı PDF Bülteni")
        self.setFixedSize(500, 560)
        self.items = items or []
        self.checkboxes = {}
        self.chk_active_only = None
        self.selected_carriers = []
        self.only_active = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Başlık
        lbl_hdr = QLabel("🚢 ARMATÖR BAZLI ÖZEL SEFER BÜLTENİ")
        lbl_hdr.setStyleSheet("font-size: 14px; font-weight: 800; color: #38bdf8;")
        layout.addWidget(lbl_hdr)

        lbl_desc = QLabel(
            "Raporlamak istediğiniz bir veya birden fazla armatörü seçiniz.\n"
            "Seçtiğiniz armatörlere ait yükler filtrelenerek özel filo bülteni oluşturulacaktır."
        )
        lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.4;")
        layout.addWidget(lbl_desc)

        # Hızlı Seçim Butonları
        f_quick = QFrame()
        l_quick = QHBoxLayout(f_quick)
        l_quick.setContentsMargins(0, 4, 0, 4)
        l_quick.setSpacing(8)

        btn_all = QPushButton("☑️ Tümünü Seç")
        btn_all.setFixedHeight(28)
        btn_all.setStyleSheet("background-color: #1e293b; color: #f8fafc; font-size: 11px; font-weight: 600; border-radius: 4px;")
        btn_all.clicked.connect(self._select_all)
        l_quick.addWidget(btn_all)

        btn_none = QPushButton("⬜ Temizle")
        btn_none.setFixedHeight(28)
        btn_none.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-size: 11px; border-radius: 4px;")
        btn_none.clicked.connect(self._select_none)
        l_quick.addWidget(btn_none)

        btn_live = QPushButton("⚓ Canlı Armatörler")
        btn_live.setFixedHeight(28)
        btn_live.setStyleSheet("background-color: #0369a1; color: #ffffff; font-size: 11px; font-weight: 600; border-radius: 4px;")
        btn_live.clicked.connect(self._select_live_only)
        l_quick.addWidget(btn_live)

        layout.addWidget(f_quick)

        # Armatör Listesi Kartı (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: #0b111e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; }")

        container = QWidget()
        container.setStyleSheet("background-color: #0b111e;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(10)

        # Mevcut yüklerden armatör istatistiklerini derle
        carrier_stats = {}
        for it in self.items:
            c = (it.get("carrier") or "DİĞER").strip().upper()
            if not c or c == "—":
                c = "DİĞER"
            if c not in carrier_stats:
                carrier_stats[c] = {"total": 0, "active": 0, "live": 0}
            carrier_stats[c]["total"] += 1
            if it.get("is_active", True):
                carrier_stats[c]["active"] += 1
            if it.get("live_eta") not in ("—", "", None):
                carrier_stats[c]["live"] += 1

        def _sort_key(c_name):
            priority = 0
            if "HAPAG" in c_name: priority = 3
            elif "MSC" in c_name: priority = 2
            elif "CMA" in c_name: priority = 2
            elif "ONE" in c_name: priority = 1
            return (-priority, -carrier_stats[c_name]["total"])

        sorted_carriers = sorted(carrier_stats.keys(), key=_sort_key)

        for c_name in sorted_carriers:
            st = carrier_stats[c_name]
            tag = f"{c_name}  ({st['active']} Aktif Yük"
            if st["live"] > 0:
                tag += f" • ⚡ {st['live']} Canlı"
            tag += f" / {st['total']} Toplam)"

            chk = QCheckBox(tag)
            chk.setStyleSheet("""
                QCheckBox {
                    color: #f1f5f9;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 0;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 1px solid #475569;
                    background-color: #1e293b;
                }
                QCheckBox::indicator:checked {
                    background-color: #0284c7;
                    border: 1px solid #38bdf8;
                }
            """)
            if any(k in c_name for k in ["HAPAG", "MSC", "CMA"]):
                chk.setChecked(True)
            self.checkboxes[c_name] = chk
            c_layout.addWidget(chk)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # Aktif Yük Filtresi Seçeneği
        self.chk_active_only = QCheckBox("Yalnızca Sahadaki Aktif Yükleri Dahil Et (Kapanmış Arşiv Hariç)")
        self.chk_active_only.setChecked(True)
        self.chk_active_only.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 600; margin-top: 4px;")
        layout.addWidget(self.chk_active_only)

        # Aksiyon Butonları
        f_actions = QFrame()
        l_actions = QHBoxLayout(f_actions)
        l_actions.setContentsMargins(0, 8, 0, 0)
        l_actions.setSpacing(10)

        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-weight: 600; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        l_actions.addWidget(btn_cancel)

        btn_generate = QPushButton("📄 Özel PDF Bülteni Oluştur  ➔")
        btn_generate.setFixedHeight(36)
        btn_generate.setStyleSheet("""
            background-color: #0284c7;
            color: #ffffff;
            font-size: 12px;
            font-weight: 800;
            border-radius: 6px;
            padding: 0 16px;
        """)
        btn_generate.clicked.connect(self._on_generate_clicked)
        l_actions.addWidget(btn_generate, 1)

        layout.addWidget(f_actions)

    def _select_all(self):
        for chk in self.checkboxes.values():
            chk.setChecked(True)

    def _select_none(self):
        for chk in self.checkboxes.values():
            chk.setChecked(False)

    def _select_live_only(self):
        for c_name, chk in self.checkboxes.items():
            chk.setChecked(any(k in c_name for k in ["HAPAG", "MSC", "CMA"]))

    def _on_generate_clicked(self):
        selected = [c for c, chk in self.checkboxes.items() if chk.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen bülten oluşturmak için en az bir armatör seçin.")
            return
        self.selected_carriers = selected
        self.only_active = self.chk_active_only.isChecked()
        self.accept()

    def get_selection(self):
        return self.selected_carriers, self.only_active


# ==============================================================================
# AYARLAR DİYALOĞU (APPLE MODAL STİLİ)
# ==============================================================================

class HorizonSettingsDialog(QDialog):

    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("SmartClearance Horizon — Sistem & Acenta Ayarları")
        self.setFixedSize(560, 520)
        self.config = dict(config)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl_hdr = QLabel("⚙️ ACENTA API & OTURUM ÇEREZİ AYARLARI")
        lbl_hdr.setStyleSheet("font-size: 14px; font-weight: 800; color: #38bdf8;")
        layout.addWidget(lbl_hdr)

        lbl_sub = QLabel("MSC motoru doğrudan ve ücretsiz çalışır. Hapag ve CMA CGM anahtarlarını aşağıdan yönetebilirsiniz.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)

        # Hapag
        layout.addWidget(QLabel("Hapag-Lloyd DCSA Client ID:"))
        self.e_hapag_id = QLineEdit(self.config.get("hapag_client_id", ""))
        layout.addWidget(self.e_hapag_id)

        layout.addWidget(QLabel("Hapag-Lloyd DCSA Client Secret:"))
        self.e_hapag_sec = QLineEdit(self.config.get("hapag_client_secret", ""))
        self.e_hapag_sec.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.e_hapag_sec)

        # CMA CGM
        layout.addWidget(QLabel("CMA CGM Canlı Oturum Çerezi (Session Cookie):"))
        self.e_cma_cookie = QLineEdit(self.config.get("cma_session_cookie", ""))
        layout.addWidget(self.e_cma_cookie)

        layout.addWidget(QLabel("CMA CGM Doğrulama Tokeni (__RequestVerificationToken):"))
        self.e_cma_token = QLineEdit(self.config.get("cma_token", ""))
        layout.addWidget(self.e_cma_token)

        # Excel Yolu
        layout.addWidget(QLabel("İş Takip Excel Dosyası / Klasörü:"))
        excel_box = QHBoxLayout()
        self.e_excel = QLineEdit(self.config.get("default_excel_path", ""))
        btn_pick = QPushButton("Seç...")
        btn_pick.clicked.connect(self._pick_excel)
        excel_box.addWidget(self.e_excel, 1)
        excel_box.addWidget(btn_pick)
        layout.addLayout(excel_box)

        layout.addStretch(1)

        # Alt Butonlar
        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Değişiklikleri Kaydet")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def _pick_excel(self):
        f, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel (*.xlsx *.xls)")
        if f:
            self.e_excel.setText(f)

    def _save(self):
        self.config["hapag_client_id"] = self.e_hapag_id.text().strip()
        self.config["hapag_client_secret"] = self.e_hapag_sec.text().strip()
        self.config["cma_session_cookie"] = self.e_cma_cookie.text().strip()
        self.config["cma_token"] = self.e_cma_token.text().strip()
        self.config["default_excel_path"] = self.e_excel.text().strip()
        save_config(self.config)
        self.accept()


# ==============================================================================
# GİRİŞ NOKTASI (MAIN)
# ==============================================================================

def main():
    import ctypes
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyleSheet(HORIZON_STYLESHEET)
    win = SmartClearanceHorizonWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
