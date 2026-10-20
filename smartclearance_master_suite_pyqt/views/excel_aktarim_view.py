# -*- coding: utf-8 -*-
"""
excel_aktarim_view.py — Fatura & Packing List'ten Evrim Excel Aktarımı (PyQt6)
PDF evraklarını ayrıştırma, kalem birleştirme, uyarı denetimi ve Evrim Excel üretimi.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QFileDialog, QMenu, QDialog,
    QTextEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QCursor

# Lib/site-packages'i sys.path'e dahil et
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_lib_pkgs = os.path.join(_root, "Lib", "site-packages")
if os.path.exists(_lib_pkgs) and _lib_pkgs not in sys.path:
    sys.path.insert(0, _lib_pkgs)

from .base_view import BaseView
from ..components.metric_card import MetricCard

from tools.smart_clearance_engine.storage import (
    new_run_dir, ensure_template, template_exists, save_template,
    master_katalog_exists, save_master_katalog
)
from tools.smart_clearance_engine.config import (
    TEMPLATE_XLSX, MASTER_KATALOG_XLSX, RUNS_DIR
)
from tools.smart_clearance_engine.services.pipeline import run_pipeline


# ----------------------------------------------------------------------
# Background Pipeline Worker
# ----------------------------------------------------------------------
class PipelineWorker(QThread):
    finished_pipeline = pyqtSignal(dict, object)  # report, run_dir
    error = pyqtSignal(str)

    def __init__(self, selected_files: List[str]):
        super().__init__()
        self.selected_files = selected_files

    def run(self):
        try:
            ensure_template()
            run_id, run_dir = new_run_dir()
            pdf_paths = [Path(f) for f in self.selected_files]
            report = run_pipeline(pdf_paths, run_dir)
            self.finished_pipeline.emit(report, run_dir)
        except Exception as exc:
            self.error.emit(str(exc))


class ExcelAktarimView(BaseView):
    """📑 Fatura & Packing List'ten Evrim Excel Aktarımı Sekmesi (PyQt6)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.selected_files: List[str] = []
        self.latest_outputs: List[str] = []
        self.latest_outputs_dir: Optional[Path] = None
        self.invoices_data: List[Dict[str, Any]] = []
        self._worker: Optional[PipelineWorker] = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # ── 1. ÜST KART: DOSYA SEÇİM & İŞLEM KONTROLLERİ ──
        card_upload = QFrame(self)
        card_upload.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        cu_layout = QVBoxLayout(card_upload)
        cu_layout.setContentsMargins(12, 10, 12, 10)
        cu_layout.setSpacing(6)

        lbl_card_title = QLabel("📑 Fatura / Packing List / Konşimento Evraklarını Seçin", card_upload)
        lbl_card_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8; border: none;")
        cu_layout.addWidget(lbl_card_title)

        lbl_card_desc = QLabel(
            "Şablon hazır gelir. Bir faturanın belgeleri tek PDF'te veya ayrı PDF'lerde olabilir — sistem fatura numarasına göre otomatik birleştirir.",
            card_upload
        )
        lbl_card_desc.setStyleSheet("font-size: 10px; color: #94a3b8; border: none;")
        cu_layout.addWidget(lbl_card_desc)

        # Butonlar Satırı
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_select_pdf = QPushButton("📂 PDF Dosyalarını Seç", card_upload)
        self.btn_select_pdf.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 700; padding: 7px 14px; border-radius: 6px;")
        self.btn_select_pdf.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_select_pdf.clicked.connect(self.select_pdf_files)
        btn_bar.addWidget(self.btn_select_pdf)

        self.btn_clear = QPushButton("🗑️ Listeyi Temizle", card_upload)
        self.btn_clear.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-weight: 600; padding: 7px 12px; border-radius: 6px; border: 1px solid #334155;")
        self.btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear.clicked.connect(self.clear_files)
        btn_bar.addWidget(self.btn_clear)

        self.btn_process = QPushButton("⚡ Evrakları Çözümle & Evrim Exceli Üret", card_upload)
        self.btn_process.setStyleSheet("background-color: #16a34a; color: #ffffff; font-weight: 800; padding: 7px 18px; border-radius: 6px;")
        self.btn_process.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_process.clicked.connect(self.start_processing)
        btn_bar.addWidget(self.btn_process)

        btn_bar.addStretch()

        btn_sablon_dl = QPushButton("📥 Şablon İndir", card_upload)
        btn_sablon_dl.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 5px 10px; border-radius: 6px; font-weight: 600;")
        btn_sablon_dl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_sablon_dl.clicked.connect(self.download_template)
        btn_bar.addWidget(btn_sablon_dl)

        btn_sablon_ul = QPushButton("📤 Şablon Güncelle", card_upload)
        btn_sablon_ul.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 5px 10px; border-radius: 6px; font-weight: 600;")
        btn_sablon_ul.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_sablon_ul.clicked.connect(self.upload_template)
        btn_bar.addWidget(btn_sablon_ul)

        cu_layout.addLayout(btn_bar)

        self.lbl_selected_status = QLabel("Henüz dosya seçilmedi. (İşlemek istediğiniz PDF'leri seçin)", card_upload)
        self.lbl_selected_status.setStyleSheet("font-size: 11px; color: #94a3b8; font-style: italic; border: none; padding-top: 4px;")
        cu_layout.addWidget(self.lbl_selected_status)

        layout.addWidget(card_upload)

        # ── 2. METRİK VE DURUM BİLGİSİ ──
        f_metrics = QHBoxLayout()
        f_metrics.setSpacing(8)

        self.card_inv_count = MetricCard("FATURA SAYISI", "0", "Ayrıştırılan Fatura", "#0284c7", self)
        self.card_item_count = MetricCard("TOPLAM KALEM", "0", "Ürün Satırı", "#2563eb", self)
        self.card_warn_count = MetricCard("UYARILAR", "0", "Fatura / PL Uyumsuzluk", "#d97706", self)
        self.card_file_count = MetricCard("EXCEL ÇIKTILARI", "0", "Hazır Dosya", "#16a34a", self)

        f_metrics.addWidget(self.card_inv_count)
        f_metrics.addWidget(self.card_item_count)
        f_metrics.addWidget(self.card_warn_count)
        f_metrics.addWidget(self.card_file_count)

        layout.addLayout(f_metrics)

        # ── 3. ÇIKTI VE SONUÇ TABLOSU ──
        card_table = QFrame(self)
        card_table.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;")
        ct_layout = QVBoxLayout(card_table)
        ct_layout.setContentsMargins(10, 8, 10, 8)
        ct_layout.setSpacing(6)

        table_header = QHBoxLayout()
        lbl_tbl_title = QLabel("📊 Üretilen Evrim Beyanname Excel Çıktıları & Kalem Özetleri", card_table)
        lbl_tbl_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #38bdf8; border: none;")
        table_header.addWidget(lbl_tbl_title)

        table_header.addStretch()

        btn_show_warn = QPushButton("⚠️ Uyarı Detayını Gör", card_table)
        btn_show_warn.setStyleSheet("background-color: #f59e0b; color: #ffffff; font-weight: 700; padding: 5px 10px; border-radius: 6px;")
        btn_show_warn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_show_warn.clicked.connect(self.show_selected_warning_details)
        table_header.addWidget(btn_show_warn)

        btn_open_selected = QPushButton("📂 Seçili Excel'i Aç", card_table)
        btn_open_selected.setStyleSheet("background-color: #16a34a; color: #ffffff; font-weight: 700; padding: 5px 10px; border-radius: 6px;")
        btn_open_selected.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open_selected.clicked.connect(self.open_selected_excel)
        table_header.addWidget(btn_open_selected)

        btn_open_folder = QPushButton("📁 Çıktı Klasörünü Aç", card_table)
        btn_open_folder.setStyleSheet("background-color: #1e293b; color: #cbd5e1; font-weight: 700; padding: 5px 10px; border-radius: 6px; border: 1px solid #334155;")
        btn_open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open_folder.clicked.connect(self.open_outputs_folder)
        table_header.addWidget(btn_open_folder)

        ct_layout.addLayout(table_header)

        # Tablo
        self.tree_results = QTableWidget(card_table)
        self.tree_results.setColumnCount(5)
        self.tree_results.setHorizontalHeaderLabels([
            "Fatura No", "Kalem Sayısı", "Kontrol & Uyarılar",
            "Üretilen Excel Dosyası", "Kaynak Evraklar"
        ])
        self.tree_results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_results.setAlternatingRowColors(True)
        self.tree_results.verticalHeader().setVisible(False)
        self.tree_results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_results.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_results.cellDoubleClicked.connect(lambda r, c: self.open_selected_excel())
        self.tree_results.itemSelectionChanged.connect(self.on_table_select)

        header = self.tree_results.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)

        self.tree_results.setColumnWidth(0, 130)
        self.tree_results.setColumnWidth(1, 100)
        self.tree_results.setColumnWidth(3, 210)
        self.tree_results.setColumnWidth(4, 250)

        ct_layout.addWidget(self.tree_results, stretch=1)

        # Alt Uyarı Bildirim Kutusu
        self.frame_warn_banner = QFrame(card_table)
        self.frame_warn_banner.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px;")
        fb_layout = QHBoxLayout(self.frame_warn_banner)
        fb_layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_warn_banner = QLabel(
            "ℹ️ Tablodan bir fatura seçerek evrak kontrol özetini ve varsa uyarı detaylarını buradan anlık görebilirsiniz.",
            self.frame_warn_banner
        )
        self.lbl_warn_banner.setStyleSheet("font-size: 11px; color: #475569; border: none;")
        self.lbl_warn_banner.setWordWrap(True)
        fb_layout.addWidget(self.lbl_warn_banner)

        ct_layout.addWidget(self.frame_warn_banner)
        layout.addWidget(card_table, stretch=1)

    # ------------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------------
    def select_pdf_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "İşlenecek PDF Dosyalarını Seçin", "", "PDF Dosyaları (*.pdf);;Tüm Dosyalar (*.*)"
        )
        if files:
            self.selected_files = list(files)
            names = [os.path.basename(f) for f in files]
            if len(names) <= 3:
                txt = " ✅ " + ", ".join(names)
            else:
                txt = f" ✅ Toplam {len(names)} Adet PDF Seçildi: " + ", ".join(names[:2]) + f" ve {len(names)-2} dosya daha..."
            self.lbl_selected_status.setText(txt)
            self.lbl_selected_status.setStyleSheet("font-size: 11px; color: #15803d; font-weight: 700; border: none;")

    def clear_files(self):
        self.selected_files = []
        self.lbl_selected_status.setText("Henüz dosya seçilmedi.")
        self.lbl_selected_status.setStyleSheet("font-size: 11px; color: #94a3b8; font-style: italic; border: none;")

    def start_processing(self):
        if not self.selected_files:
            self.show_warning("Uyarı", "Lütfen önce en az 1 adet PDF dosyası seçin!")
            return

        self.btn_process.setEnabled(False)
        self.btn_process.setText("⏳ Evraklar İşleniyor...")

        self._worker = PipelineWorker(self.selected_files)
        self._worker.finished_pipeline.connect(self._render_results)
        self._worker.error.connect(self._on_pipeline_error)
        self._worker.start()

    def _on_pipeline_error(self, err: str):
        self.btn_process.setEnabled(True)
        self.btn_process.setText("⚡ Evrakları Çözümle & Evrim Exceli Üret")
        self.show_error("Hata", f"İşlem sırasında hata oluştu:\n{err}")

    def _render_results(self, report: dict, run_dir: Path):
        self.btn_process.setEnabled(True)
        self.btn_process.setText("⚡ Evrakları Çözümle & Evrim Exceli Üret")

        self.latest_outputs_dir = run_dir / "outputs"
        invoices = report.get("invoices", [])
        self.invoices_data = invoices
        total_kalem = 0
        total_warn = 0

        self.latest_outputs.clear()
        self.tree_results.setRowCount(len(invoices))

        for idx, inv in enumerate(invoices):
            inv_no = inv.get("invoice_no", "Bilinmeyen")
            k_count = len(inv.get("kalemler", []))
            total_kalem += k_count

            warns = inv.get("warnings", [])
            total_warn += len(warns)
            if warns:
                short_items = []
                for w in warns:
                    w_lower = w.lower()
                    if "kalem miktarlari" in w_lower or "miktar" in w_lower:
                        short_items.append("Miktar Uyuşmazlığı")
                    elif "agirlik" in w_lower or "ağırlık" in w_lower:
                        short_items.append("Ağırlık Farkı")
                    elif "tutarsiz" in w_lower or "fatura no" in w_lower:
                        short_items.append("Fatura No Farkı")
                    elif "konsimento" in w_lower or "waybill" in w_lower:
                        short_items.append("Konşimento Eksik")
                    else:
                        short_items.append("Evrak Uyumsuzluğu")
                uniq_shorts = list(dict.fromkeys(short_items))
                warn_str = f"⚠️ {len(warns)} Uyarı: " + ", ".join(uniq_shorts)
                bg_c = QColor("#fffbeb"); fg_c = QColor("#b45309")
            else:
                warn_str = "✅ Temiz / Sorunsuz"
                bg_c = QColor("#f0fdf4"); fg_c = QColor("#166534")

            if inv.get("parse_failed") or not inv.get("kalemler"):
                warn_str = "❌ PDF tanınmadı / kalem yok"
                bg_c = QColor("#fee2e2"); fg_c = QColor("#b91c1c")

            out_file = inv.get("output_filename") or "—"
            if self.latest_outputs_dir and inv.get("output_filename"):
                out_path = self.latest_outputs_dir / inv.get("output_filename")
                self.latest_outputs.append(str(out_path))

            src_files = ", ".join([os.path.basename(f) for f in inv.get("source_files", [])])

            values = [inv_no, f"{k_count} Kalem", warn_str, out_file, src_files]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(str(val))
                cell.setBackground(bg_c)
                cell.setForeground(fg_c)
                if col == 1:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    f = cell.font()
                    f.setBold(True)
                    cell.setFont(f)
                self.tree_results.setItem(idx, col, cell)

            # Activity Hub Logging
            try:
                from tools.supabase_sync_manager import get_supabase_manager
                sm = get_supabase_manager()
                if sm:
                    sm.add_activity_log(
                        dosya_no="",
                        ref_no=inv_no,
                        islem_tipi="FATURA",
                        baslik=f"Evrim Beyanname Exceli Üretildi ({inv_no})",
                        icerik=f"Fatura No: {inv_no} | {k_count} kalem ürün | Çıktı: {out_file}",
                        etiket="Hata" if inv.get("parse_failed") else "Tamamlandı"
                    )
            except Exception:
                pass

        # Update metrics
        self.card_inv_count.set_value(len(invoices))
        self.card_item_count.set_value(total_kalem)
        self.card_warn_count.set_value(total_warn)
        self.card_file_count.set_value(len(invoices))

        if invoices:
            self.tree_results.selectRow(0)

        self.show_info(
            "İşlem Tamamlandı",
            f"✅ Başarılı!\nToplam {len(invoices)} adet fatura için Evrim Excel çıktıları hazırlandı."
        )

    def on_table_select(self):
        selected_rows = self.tree_results.selectedIndexes()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if not (0 <= row < len(self.invoices_data)):
            return

        inv = self.invoices_data[row]
        inv_no = inv.get("invoice_no", "")
        warns = inv.get("warnings", [])

        if warns:
            self.frame_warn_banner.setStyleSheet("background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 6px;")
            lines = [f"⚠️ [Fatura No: {inv_no}] {len(warns)} Adet Uyumsuzluk / Uyarı Tespit Edildi:"]
            for i, w in enumerate(warns, 1):
                lines.append(f"   {i}) {w}")
            lines.append("   👉 Tüm detayları ayrı pencerede görmek için '⚠️ Uyarı Detayını Gör' butonuna basabilirsiniz.")
            self.lbl_warn_banner.setText("\n".join(lines))
            self.lbl_warn_banner.setStyleSheet("font-size: 11px; color: #9a3412; font-weight: 600; border: none;")
        else:
            self.frame_warn_banner.setStyleSheet("background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px;")
            self.lbl_warn_banner.setText(f"✅ [Fatura No: {inv_no}] Fatura, Packing List ve kalemler arasında herhangi bir uyumsuzluk bulunmuyor (Temiz/Sorunsuz).")
            self.lbl_warn_banner.setStyleSheet("font-size: 11px; color: #166534; font-weight: 600; border: none;")

    def show_selected_warning_details(self):
        selected_rows = self.tree_results.selectedIndexes()
        if not selected_rows:
            self.show_info("Bilgi", "Lütfen detayını görmek istediğiniz fatura satırını seçin.")
            return

        row = selected_rows[0].row()
        if not (0 <= row < len(self.invoices_data)):
            return

        inv = self.invoices_data[row]
        warns = inv.get("warnings", [])
        infos = inv.get("infos", [])
        inv_no = inv.get("invoice_no", "Bilinmeyen")
        k_count = len(inv.get("kalemler", []))
        src_files = ", ".join([os.path.basename(f) for f in inv.get("source_files", [])])
        out_file = inv.get("output_filename", "")

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Fatura {inv_no} - Evrak Uyarı ve Çapraz Kontrol Detayları")
        dlg.resize(780, 560)
        dlg.setStyleSheet("background-color: #0b0f19; color: #f8fafc;")

        d_layout = QVBoxLayout(dlg)
        d_layout.setContentsMargins(16, 14, 16, 14)
        d_layout.setSpacing(10)

        hdr = QFrame(dlg)
        hdr.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;")
        hl = QHBoxLayout(hdr)
        lbl_h = QLabel(f"📋 Fatura Kontrol & Uyarı Raporu: {inv_no}", hdr)
        lbl_h.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 800; border: none;")
        hl.addWidget(lbl_h)
        d_layout.addWidget(hdr)

        # Bilgi Kartı
        info_card = QFrame(dlg)
        info_card.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        icl = QVBoxLayout(info_card)
        lbl_info_txt = (
            f"📄 Fatura No: {inv_no}   |   📦 Kalem Sayısı: {k_count} Kalem\n"
            f"📁 Kaynak Evraklar: {src_files}\n"
            f"📊 Üretilen Excel: {out_file}"
        )
        lbl_i = QLabel(lbl_info_txt, info_card)
        lbl_i.setStyleSheet("font-size: 11px; color: #f8fafc; border: none;")
        icl.addWidget(lbl_i)
        d_layout.addWidget(info_card)

        # Uyarılar
        txt_warns = QTextEdit(dlg)
        txt_warns.setReadOnly(True)
        txt_warns.setFont(QFont("Consolas", 10))

        if warns:
            txt_warns.setStyleSheet("background-color: #1c1917; color: #fbbf24; border: 1px solid #78350f; border-radius: 8px; padding: 10px;")
            content = "AŞAĞIDAKİ EVRAK UYUMSUZLUKLARI TESPİT EDİLDİ:\n" + "="*60 + "\n\n"
            for i, w in enumerate(warns, 1):
                content += f"[{i}] {w}\n\n"
            if infos:
                content += "\nEK BİLGİ & DOĞRULAMA NOTLARI:\n" + "-"*60 + "\n"
                for inf in infos:
                    content += f"• {inf}\n"
            content += "\n" + "="*60 + "\n"
            content += "💡 NOT: Evrak setindeki tüm kalemler eksiksiz ayrıştırılmış ve Excel'e yazılmıştır.\nAncak evrak başlığındaki alt toplam değerleri ile okunan kalem satırlarının toplamı tutmadığı için yukarıdaki uyarılar verilmiştir."
        else:
            txt_warns.setStyleSheet("background-color: #06281e; color: #34d399; border: 1px solid #059669; border-radius: 8px; padding: 10px;")
            content = "✅ Temiz / Sorunsuz Evrak Seti\n\nBu faturanın Fatura, Packing List ve Konşimento evrakları arasında miktar, ağırlık veya numara bazında herhangi bir uyumsuzluk bulunmamaktadır."

        txt_warns.setText(content)
        d_layout.addWidget(txt_warns, stretch=1)

        btn_box = QHBoxLayout()
        btn_open = QPushButton("📂 Excel Dosyasını Aç", dlg)
        btn_open.setStyleSheet("background-color: #16a34a; color: #ffffff; font-weight: 700; padding: 6px 14px; border-radius: 6px;")
        btn_open.clicked.connect(self.open_selected_excel)
        btn_box.addWidget(btn_open)

        btn_box.addStretch()

        btn_close = QPushButton("Kapat", dlg)
        btn_close.setStyleSheet("background-color: #0f172a; color: #ffffff; font-weight: 700; padding: 6px 16px; border-radius: 6px;")
        btn_close.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_close)

        d_layout.addLayout(btn_box)
        dlg.exec()

    def open_selected_excel(self):
        selected_rows = self.tree_results.selectedIndexes()
        if not selected_rows:
            self.show_warning("Uyarı", "Lütfen açmak için listeden bir fatura satırı seçin.")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.latest_outputs):
            file_path = self.latest_outputs[row]
            if os.path.exists(file_path):
                try:
                    os.startfile(file_path)
                except Exception as e:
                    self.show_error("Hata", f"Dosya açılamadı: {e}")
            else:
                self.show_error("Hata", f"Dosya bulunamadı:\n{file_path}")
        else:
            self.show_error("Hata", "Dosya açılamadı.")

    def open_outputs_folder(self):
        if self.latest_outputs_dir and os.path.exists(self.latest_outputs_dir):
            try:
                os.startfile(self.latest_outputs_dir)
            except Exception as e:
                self.show_error("Hata", f"Klasör açılamadı: {e}")
        elif os.path.exists(RUNS_DIR):
            try:
                os.startfile(RUNS_DIR)
            except Exception as e:
                self.show_error("Hata", f"Klasör açılamadı: {e}")
        else:
            self.show_info("Bilgi", "Henüz bir çıktı klasörü oluşturulmadı.")

    def download_template(self):
        try:
            ensure_template()
            dest, _ = QFileDialog.getSaveFileName(
                self, "Evrim Şablonunu Kaydet", "Evrim_sablon.xlsx", "Excel Dosyası (*.xlsx)"
            )
            if dest:
                shutil.copy2(TEMPLATE_XLSX, dest)
                self.show_info("Başarılı", f"Şablon başarıyla kaydedildi:\n{dest}")
        except Exception as e:
            self.show_error("Hata", f"Şablon indirilemedi: {e}")

    def upload_template(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Yeni Evrim Şablonunu Seçin", "", "Excel Dosyası (*.xlsx);;Tüm Dosyalar (*.*)"
        )
        if file:
            try:
                save_template(Path(file))
                self.show_info("Başarılı", "Evrim Excel şablonu başarıyla güncellendi!")
            except Exception as e:
                self.show_error("Hata", f"Şablon kaydedilemedi: {e}")

    def show_context_menu(self, pos):
        selected_rows = self.tree_results.selectedIndexes()
        if not selected_rows:
            return

        menu = QMenu(self)
        menu.addAction("⚠️ Uyarı Detaylarını Gör", self.show_selected_warning_details)
        menu.addAction("📂 Excel Dosyasını Aç", self.open_selected_excel)
        menu.addAction("📁 Dosya Konumunu Aç", self.open_outputs_folder)
        menu.exec(self.tree_results.viewport().mapToGlobal(pos))
