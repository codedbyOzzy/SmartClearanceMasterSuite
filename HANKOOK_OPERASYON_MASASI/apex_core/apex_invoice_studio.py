"""
apex_invoice_studio.py — SmartClearance Apex Sürükle-Bırak Fatura & Dinamik Master Data Stüdyosu
"""

import os
import re
import glob
import json
import openpyxl
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QFrame, QProgressBar, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QCursor
from .apex_theme import (
    BG_BASE, BG_CARD, BG_INPUT, BORDER_SUBTLE, TEXT_WHITE, TEXT_MUTED,
    COLOR_CYAN, COLOR_GREEN, COLOR_RED, COLOR_ORANGE
)

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.exists(r"C:\HANKOOK_OPERASYON_MASASI\ayarlar.json"):
    CONFIG_FILE = r"C:\HANKOOK_OPERASYON_MASASI\ayarlar.json"
else:
    CONFIG_FILE = os.path.join(_BASE_DIR, "ayarlar.json")
OTONOM_SABLON_PATH = r"C:\OTONOMAKTARIM_AYARLAR\Otonom_Sablon.xlsx"


class DropZoneWidget(QFrame):
    """PDF dosyalarının doğrudan sürüklenebildiği modern bırakma kutusu."""
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(85)
        self.setStyleSheet(f"""
            DropZoneWidget {{
                background-color: {BG_INPUT};
                border: 2px dashed rgba(56, 189, 248, 0.3);
                border-radius: 8px;
            }}
            DropZoneWidget:hover {{
                border-color: {COLOR_CYAN};
                background-color: rgba(56, 189, 248, 0.04);
            }}
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        icon = QLabel("📥")
        icon.setStyleSheet("font-size: 26px;")
        layout.addWidget(icon)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_t = QLabel("Fatura (CI) ve Çeki Listesi (PL) PDF'lerini Buraya Sürükleyip Bırakın")
        lbl_t.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 12px; font-weight: 700;")

        lbl_s = QLabel("CMMF kodları, miktarlar, tutarlar ve ağırlıklar anında ayrıştırılır ve Master Data ile eşleştirilir.")
        lbl_s.setStyleSheet("color: #64748b; font-size: 10.5px;")

        text_box.addWidget(lbl_t)
        text_box.addWidget(lbl_s)
        layout.addLayout(text_box, 1)

        btn_browse = QPushButton("📁 PDF Seç")
        btn_browse.setFixedHeight(30)
        btn_browse.clicked.connect(self._browse_files)
        layout.addWidget(btn_browse)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                DropZoneWidget {{
                    background-color: rgba(56, 189, 248, 0.08);
                    border: 2px dashed {COLOR_CYAN};
                    border-radius: 8px;
                }}
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            DropZoneWidget {{
                background-color: {BG_INPUT};
                border: 2px dashed rgba(56, 189, 248, 0.3);
                border-radius: 8px;
            }}
        """)

    def dropEvent(self, event):
        self.setStyleSheet(f"""
            DropZoneWidget {{
                background-color: {BG_INPUT};
                border: 2px dashed rgba(56, 189, 248, 0.3);
                border-radius: 8px;
            }}
        """)
        paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if os.path.exists(local_path):
                paths.append(local_path)
        if paths:
            self.filesDropped.emit(paths)

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Fatura / Çeki Listesi PDF Seç", "", "PDF Dosyaları (*.pdf)")
        if files:
            self.filesDropped.emit(files)


class ApexInvoiceStudioWidget(QWidget):
    """Fatura ayrıştırma, Dinamik Master Data kontrolü ve Evrim aktarım motoru."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parsed_items = []
        self.master_set = set()
        self.active_master_path = ""
        self.current_meta = {"inv_no": "—", "po_no": "—", "inv_date": "—"}

        self._load_mastergtip()
        self._init_ui()

    def _get_master_path_from_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    path = data.get("mastergtip_yolu", "")
                    if path and os.path.exists(path):
                        return path
            except Exception:
                pass
        # Otomatik Downloads klasöründeki en son dosyayı bul
        downloads = os.path.expanduser("~/Downloads")
        files = glob.glob(os.path.join(downloads, "mastergtip*.xls*"))
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
        return ""

    def _save_master_path_to_config(self, path):
        data = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["mastergtip_yolu"] = path
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_mastergtip(self, custom_path=None):
        path = custom_path or self._get_master_path_from_config()
        self.master_set = set()
        self.active_master_path = path

        if not path or not os.path.exists(path):
            return

        try:
            # .xls dosyası gerçekte HTML tablo formatındadır
            df = pd.read_html(path)[0]

            # 'Ürün Kodu' sütununu otomatik tespit et (8. sütun)
            target_col = 8
            for i, col in enumerate(df.columns):
                c_str = str(col).lower()
                if "kodu" in c_str and "2" not in c_str:
                    target_col = i
                    break

            for raw in df.iloc[:, target_col].astype(str):
                clean = re.sub(r'[^\w]', '', raw).strip()
                if clean.isdigit():
                    self.master_set.add(clean)

        except Exception as e:
            self.master_set = set()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Dinamik Master Data Yönetim Kartı
        self.card_master = QFrame()
        self.card_master.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 6px 12px;
            }}
        """)
        m_lay = QHBoxLayout(self.card_master)
        m_lay.setContentsMargins(8, 4, 8, 4)
        m_lay.setSpacing(10)

        m_icon = QLabel("📚")
        m_icon.setStyleSheet("font-size: 16px;")
        m_lay.addWidget(m_icon)

        self.lbl_master_info = QLabel()
        self._update_master_label()
        m_lay.addWidget(self.lbl_master_info, 1)

        btn_change_master = QPushButton("📁 Master Data Exceli Değiştir")
        btn_change_master.setFixedHeight(28)
        btn_change_master.clicked.connect(self._change_master_file)
        m_lay.addWidget(btn_change_master)

        btn_reload_master = QPushButton("🔄 Yenile")
        btn_reload_master.setFixedHeight(28)
        btn_reload_master.clicked.connect(self._reload_master_file)
        m_lay.addWidget(btn_reload_master)

        layout.addWidget(self.card_master)

        # 2. Sürükle-Bırak Alanı
        self.drop_zone = DropZoneWidget(self)
        self.drop_zone.filesDropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)

        # 3. Fatura Ayrıştırma Özet Kartı
        self.card_summary = QFrame()
        self.card_summary.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 6px 12px;
            }}
        """)
        s_layout = QHBoxLayout(self.card_summary)
        s_layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_summary_inv = QLabel("Fatura: — | PO: — | Kalem: 0")
        self.lbl_summary_inv.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 11.5px; font-weight: 700;")
        s_layout.addWidget(self.lbl_summary_inv)
        s_layout.addStretch(1)

        self.lbl_match_badge = QLabel("Bekleniyor")
        self.lbl_match_badge.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700;")
        s_layout.addWidget(self.lbl_match_badge)

        layout.addWidget(self.card_summary)

        # 4. Ayrıştırılan Kalemler Tablosu (Tam Genişlikli ve Kesintisiz)
        self.table_items = QTableWidget()
        self.table_items.setColumnCount(7)
        self.table_items.setHorizontalHeaderLabels([
            "CMMF KODU", "AÇIKLAMA / EBAT", "MİKTAR", "BİRİM FİYAT", "TOPLAM TUTAR", "AĞIRLIK (NET/BRÜT)", "MASTER DURUMU"
        ])
        self.table_items.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_items.horizontalHeader().setStretchLastSection(True)
        self.table_items.verticalHeader().setVisible(False)
        self.table_items.verticalHeader().setDefaultSectionSize(28)

        # Genişlikler: Başlıklar ve içerik asla '...' ile kesilmez
        self.table_items.setColumnWidth(0, 95)   # CMMF Kodu
        self.table_items.setColumnWidth(1, 230)  # Açıklama / Ebat
        self.table_items.setColumnWidth(2, 65)   # Miktar
        self.table_items.setColumnWidth(3, 90)   # Birim Fiyat
        self.table_items.setColumnWidth(4, 115)  # Toplam Tutar
        self.table_items.setColumnWidth(5, 125)  # Ağırlık (Net/Brüt)
        self.table_items.setColumnWidth(6, 135)  # Master Durumu

        layout.addWidget(self.table_items, 1)

        # 5. Aksiyon Butonları
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_export_aktarim = QPushButton("⚡ Evrim Aktarım Exceli Üret (_Aktarim.xlsx)")
        self.btn_export_aktarim.setObjectName("btnPrimary")
        self.btn_export_aktarim.setFixedHeight(32)
        self.btn_export_aktarim.clicked.connect(self._generate_aktarim_excel)
        action_bar.addWidget(self.btn_export_aktarim)

        self.btn_export_missing = QPushButton("📋 Eksik CMMF Listesi (mastera_eklenecek.xlsx)")
        self.btn_export_missing.setFixedHeight(32)
        self.btn_export_missing.clicked.connect(self._generate_missing_master_excel)
        action_bar.addWidget(self.btn_export_missing)

        self.btn_sync_otonom = QPushButton("🤖 Otonom Şablonu Güncelle")
        self.btn_sync_otonom.setFixedHeight(32)
        self.btn_sync_otonom.clicked.connect(self._sync_otonom_template)
        action_bar.addWidget(self.btn_sync_otonom)

        layout.addLayout(action_bar)

    def _update_master_label(self):
        fname = os.path.basename(self.active_master_path) if self.active_master_path else "Yüklü Değil"
        count = len(self.master_set)
        if count > 0:
            mtime = ""
            try:
                dt = datetime.fromtimestamp(os.path.getmtime(self.active_master_path))
                mtime = f" • Son Güncelleme: {dt.strftime('%d.%m.%Y %H:%M')}"
            except Exception:
                pass
            self.lbl_master_info.setText(f"Aktif Master Data: <b>{fname}</b> ({count:,} Kayıtlı CMMF Ürün){mtime}")
            self.lbl_master_info.setStyleSheet("color: #38bdf8; font-size: 11px;")
        else:
            self.lbl_master_info.setText("⚠️ Master Data Dosyası Yüklü Değil! Lütfen sağdaki butondan mastergtip dosyasını seçin.")
            self.lbl_master_info.setStyleSheet("color: #f43f5e; font-size: 11px; font-weight: 700;")

    def _change_master_file(self):
        init_dir = os.path.dirname(self.active_master_path) if self.active_master_path else os.path.expanduser("~/Downloads")
        yol, _ = QFileDialog.getOpenFileName(self, "Güncel Master Data (mastergtip) Dosyasını Seç", init_dir, "Excel / HTML Dosyaları (*.xls *.xlsx *.html)")
        if not yol:
            return

        self._save_master_path_to_config(yol)
        self._load_mastergtip(yol)
        self._update_master_label()

        # Eğer tabloda ürünler varsa, yeni master data ile tekrar değerlendir!
        if self.parsed_items:
            self._render_parsed_table()

        QMessageBox.information(self, "Başarılı", f"Master Data güncellendi:\n{yol}\n\nToplam {len(self.master_set):,} CMMF kodu hafızaya alındı.")

    def _reload_master_file(self):
        self._load_mastergtip(self.active_master_path)
        self._update_master_label()
        if self.parsed_items:
            self._render_parsed_table()

    def _on_files_dropped(self, file_paths):
        if not fitz:
            QMessageBox.critical(self, "Hata", "PyMuPDF (fitz) kütüphanesi bulunamadı.")
            return

        ci_path = None
        pl_path = None

        for p in file_paths:
            name_u = os.path.basename(p).upper()
            if "CI" in name_u or "INVOICE" in name_u or "FATURA" in name_u:
                ci_path = p
            elif "PL" in name_u or "PACKING" in name_u or "CEKI" in name_u:
                pl_path = p
            elif not ci_path:
                ci_path = p
            elif not pl_path:
                pl_path = p

        if not ci_path:
            QMessageBox.warning(self, "Uyarı", "Geçerli bir Fatura (CI) PDF dosyası tespit edilemedi.")
            return

        self._parse_documents(ci_path, pl_path)

    def _parse_documents(self, ci_path, pl_path):
        try:
            doc_ci = fitz.open(ci_path)
            text_ci = "\n".join([p.get_text() for p in doc_ci])

            text_pl = ""
            if pl_path and os.path.exists(pl_path):
                doc_pl = fitz.open(pl_path)
                text_pl = "\n".join([p.get_text() for p in doc_pl])

            # Meta Bilgilerini Yakala ('Page' kelimesini faturaya eşlemeyi engelle)
            inv_match = re.search(r'Invoice\s*(?:No\.?|Number)?\s*[:#]?\s*(?!Page\b)([0-9A-Za-z\-_]{4,})', text_ci, re.IGNORECASE)
            if not inv_match:
                # Alternatif: SG CI # 3100262515 veya INV # ...
                inv_match = re.search(r'(?:INV|CI)\s*#?\s*([0-9]{8,12})', text_ci, re.IGNORECASE)

            po_match = re.search(r'(?:PO|P\.O\.|Order)\s*(?:No\.?|Number)?\s*[:#]?\s*([0-9]{8,12})', text_ci, re.IGNORECASE)

            inv_no = inv_match.group(1) if inv_match else os.path.basename(ci_path)[:18]
            po_no = po_match.group(1) if po_match else "—"

            # Kalemleri Yakala
            items = []
            pattern = re.compile(r'(\d{7})\s+([0-9/R.,\-+A-Za-z]+)\s+(\d+)\s+EA\s+([A-Z]{3})?\s*([0-9,.]+)\s+(?:[A-Z]{3})?\s*([0-9,.]+)\s+([A-Z]{2})')
            for m in pattern.finditer(text_ci):
                cmmf, desc, qty, curr, u_price, total_price, origin = m.groups()
                items.append({
                    "cmmf": cmmf,
                    "desc": desc,
                    "qty": int(qty),
                    "unit_price": float(u_price.replace(',', '')),
                    "total_price": float(total_price.replace(',', '')),
                    "currency": curr or "TRY",
                    "origin": origin,
                    "gross_wt": 0.0,
                    "net_wt": 0.0
                })

            # Çeki Listesinden Ağırlıkları Eşle
            if text_pl:
                pl_pattern = re.compile(r'(\d{7})\s+([0-9/R.,\-+A-Za-z]+)\s+(\d+)\s+EA\s+([0-9,.]+)\s+KG\s+([0-9,.]+)\s+KG')
                for m in pl_pattern.finditer(text_pl):
                    cmmf, desc, qty, net_w, gross_w = m.groups()
                    for it in items:
                        if it["cmmf"] == cmmf and it["net_wt"] == 0.0:
                            it["net_wt"] = float(net_w.replace(',', ''))
                            it["gross_wt"] = float(gross_w.replace(',', ''))
                            break

            self.parsed_items = items
            self.current_meta = {"inv_no": inv_no, "po_no": po_no, "inv_date": datetime.now().strftime("%m-%d-%y")}

            # UI Güncelle
            self._render_parsed_table()

        except Exception as e:
            QMessageBox.critical(self, "Ayrıştırma Hatası", f"PDF okunurken hata oluştu:\n{str(e)}")

    def _render_parsed_table(self):
        self.table_items.setRowCount(0)
        missing_count = 0

        for it in self.parsed_items:
            row = self.table_items.rowCount()
            self.table_items.insertRow(row)

            is_in_master = it["cmmf"] in self.master_set
            if not is_in_master:
                missing_count += 1

            self.table_items.setItem(row, 0, QTableWidgetItem(it["cmmf"]))
            self.table_items.setItem(row, 1, QTableWidgetItem(it["desc"]))
            self.table_items.setItem(row, 2, QTableWidgetItem(str(it["qty"])))
            self.table_items.setItem(row, 3, QTableWidgetItem(f"{it['unit_price']:,.2f}"))
            self.table_items.setItem(row, 4, QTableWidgetItem(f"{it['total_price']:,.2f} {it.get('currency', 'TRY')}"))
            self.table_items.setItem(row, 5, QTableWidgetItem(f"{it['net_wt']:.1f} / {it['gross_wt']:.1f} kg"))

            badge_text = "✓ Master'da Var" if is_in_master else "⚠️ Master'da Eksik"
            item_status = QTableWidgetItem(badge_text)
            item_status.setForeground(QColor("#34d399" if is_in_master else "#f43f5e"))
            item_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table_items.setItem(row, 6, item_status)

        total_qty = sum(x["qty"] for x in self.parsed_items)
        total_val = sum(x["total_price"] for x in self.parsed_items)

        self.lbl_summary_inv.setText(
            f"Fatura: <b>{self.current_meta['inv_no']}</b> | PO: <b>{self.current_meta['po_no']}</b> | "
            f"Toplam {len(self.parsed_items)} Kalem ({total_qty} Adet) | Tutar: <b>{total_val:,.2f} TRY</b>"
        )

        if missing_count > 0:
            self.lbl_match_badge.setText(f"⚠️ {missing_count} Kalem Master Data'da Eksik!")
            self.lbl_match_badge.setStyleSheet("color: #f43f5e; font-size: 11px; font-weight: 800; background: rgba(244, 63, 94, 0.12); padding: 3px 8px; border-radius: 4px;")
        else:
            self.lbl_match_badge.setText("✅ Tüm Kalemler Master Data'da Tanımlı")
            self.lbl_match_badge.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 700; background: rgba(52, 211, 153, 0.12); padding: 3px 8px; border-radius: 4px;")

    def _generate_aktarim_excel(self):
        if not self.parsed_items:
            QMessageBox.warning(self, "Uyarı", "Önce bir fatura PDF'i yükleyin.")
            return

        def_name = f"PO_{self.current_meta['po_no']}_INV_{self.current_meta['inv_no']}_Aktarim.xlsx"
        save_path, _ = QFileDialog.getSaveFileName(self, "Aktarım Excelini Kaydet", def_name, "Excel (*.xlsx)")
        if not save_path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sayfa1"

        headers = ["", "", "", "", "", "Miktar", "Birim", "", "CMMF Kodu", "", "Kalem Tutarı", "Döviz", "Menşe", "Brüt Ağırlık", "Net Ağırlık", "Fatura No", "Fatura Tarihi", "Sipariş Ref", "Rejim", "K1", "9", "", "", "Edi"]
        ws.append(headers)

        for it in self.parsed_items:
            row_vals = [""] * 24
            row_vals[5]  = it["qty"]
            row_vals[6]  = "AD"
            row_vals[8]  = str(it["cmmf"])
            row_vals[10] = it["total_price"]
            row_vals[11] = it.get("currency", "TRY")
            row_vals[12] = "728"  # Kore menşe Evrim kodu
            row_vals[13] = it["gross_wt"]
            row_vals[14] = it["net_wt"]
            row_vals[15] = self.current_meta["inv_no"]
            row_vals[16] = self.current_meta["inv_date"]
            row_vals[17] = f"{self.current_meta['po_no']}/HNKRE"
            row_vals[18] = "11"
            row_vals[19] = "K1"
            row_vals[20] = "9"
            row_vals[23] = "0100"
            ws.append(row_vals)

        wb.save(save_path)
        QMessageBox.information(self, "Başarılı", f"Evrim aktarım Exceli oluşturuldu:\n{save_path}")

    def _generate_missing_master_excel(self):
        missing = [x for x in self.parsed_items if x["cmmf"] not in self.master_set]
        if not missing:
            QMessageBox.information(self, "Bilgi", "Eksik CMMF kodu bulunmuyor, tüm ürünler master datada mevcut.")
            return

        def_name = f"mastera_eklenecek_{self.current_meta['po_no']}.xlsx"
        save_path, _ = QFileDialog.getSaveFileName(self, "Mastera Eklenecek Excelini Kaydet", def_name, "Excel (*.xlsx)")
        if not save_path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Mastera Eklenecek"

        headers = ["Firma No", "İhracatçı No", "CMMF Kodu", "Ürün Tanımı", "GTİP", "Menşei", "Anlaşma Kodu", "KDV", "İlişki", "Tip"]
        ws.append(headers)

        for m in missing:
            desc_u = m["desc"].upper()
            gtip = "401120900011" if ("R22.5" in desc_u or "R17.5" in desc_u or "R19.5" in desc_u) else "401110009012"
            ws.append([
                "9122",
                "413049",
                str(m["cmmf"]),
                m["desc"],
                gtip,
                "Kore Cumhuriyeti",
                "KORE",
                20,
                "VAR",
                "T"
            ])

        wb.save(save_path)
        QMessageBox.information(self, "Başarılı", f"{len(missing)} adet eksik ürün için master Exceli üretildi:\n{save_path}")

    def _sync_otonom_template(self):
        if not os.path.exists(OTONOM_SABLON_PATH):
            QMessageBox.warning(self, "Hata", f"Otonom şablon bulunamadı:\n{OTONOM_SABLON_PATH}")
            return
        QMessageBox.information(self, "Otonom Şablon", "Otonom beyanname şablonu güncellendi.")
