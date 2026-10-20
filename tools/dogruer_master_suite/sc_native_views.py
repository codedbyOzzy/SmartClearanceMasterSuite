# -*- coding: utf-8 -*-
"""
sc_native_views.py — Doğruer MasterSuite Yerel (Native Tkinter) Arayüzleri
1. Excel Aktarım (Evrim Beyanname Hazırlayıcı)
2. Master Data Kontrol (Ürün Kataloğu & GTİP Denetimi)
"""
import os
import sys
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from tools.dogruer_master_suite.views.base_view import BaseView

from tools.smart_clearance_engine.storage import (
    new_run_dir, ensure_template, template_exists, save_template,
    master_katalog_exists, save_master_katalog, ensure_eklenecek_template
)
from tools.smart_clearance_engine.config import (
    TEMPLATE_XLSX, MASTER_KATALOG_XLSX, RUNS_DIR
)
from tools.smart_clearance_engine.services.pipeline import run_pipeline
from tools.smart_clearance_engine.services.master_pipeline import run_master_pipeline
from tools.smart_clearance_engine.parsers.master_katalog import load_master_katalog


# ══════════════════════════════════════════════════════════════════════════════
# MODÜL 1: EXCEL AKTARIM (YEREL TKINTER ARAYÜZÜ)
# ══════════════════════════════════════════════════════════════════════════════
class NativeExcelAktarimView(BaseView):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.selected_files = []
        self.latest_outputs = []
        self.latest_outputs_dir = None
        self.invoices_data = []
        self.setup_ui()

    def on_activate(self):
        """Sekme açıldığında çağrılır."""
        pass

    def setup_ui(self):
        # ── 1. ÜST KART: DOSYA SEÇİM & İŞLEM KONTROLLERİ ──
        card_upload = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID, padx=16, pady=14)
        card_upload.pack(fill=tk.X, pady=(0, 12))

        # Başlık ve Bilgi
        lbl_card_title = tk.Label(
            card_upload,
            text="📑 Fatura / Packing List / Konşimento Evraklarını Seçin",
            font=("Segoe UI", 11, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_card_title.pack(anchor="w")

        lbl_card_desc = tk.Label(
            card_upload,
            text="Şablon hazır gelir. Bir faturanın belgeleri tek PDF'te veya ayrı PDF'lerde olabilir — sistem fatura numarasına göre otomatik birleştirir.",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#ffffff"
        )
        lbl_card_desc.pack(anchor="w", pady=(2, 10))

        # Butonlar Satırı
        btn_bar = tk.Frame(card_upload, bg="#ffffff")
        btn_bar.pack(fill=tk.X)

        self.btn_select_pdf = tk.Button(
            btn_bar,
            text="📂 PDF Dosyalarını Seç",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.select_pdf_files
        )
        self.btn_select_pdf.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear = tk.Button(
            btn_bar,
            text="🗑️ Listeyi Temizle",
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#475569",
            activebackground="#e2e8f0",
            relief=tk.FLAT,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.clear_files
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 12))

        self.btn_process = tk.Button(
            btn_bar,
            text="⚡ Evrakları Çözümle & Evrim Exceli Üret",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.start_processing
        )
        self.btn_process.pack(side=tk.LEFT, padx=(0, 8))

        # Şablon İndir / Değiştir Butonları
        btn_sablon_dl = tk.Button(
            btn_bar,
            text="📥 Şablon İndir",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#475569",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.download_template
        )
        btn_sablon_dl.pack(side=tk.RIGHT, padx=(4, 0))

        btn_sablon_ul = tk.Button(
            btn_bar,
            text="📤 Şablon Güncelle",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#475569",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.upload_template
        )
        btn_sablon_ul.pack(side=tk.RIGHT)

        # Seçilen Dosyalar Durum Etiketi
        self.lbl_selected_status = tk.Label(
            card_upload,
            text="Henüz dosya seçilmedi. (İşlemek istediğiniz PDF'leri seçin)",
            font=("Segoe UI", 9, "italic"),
            fg="#94a3b8",
            bg="#ffffff"
        )
        self.lbl_selected_status.pack(anchor="w", pady=(8, 0))

        # ── 2. METRİK VE DURUM BİLGİSİ ──
        f_metrics = tk.Frame(self, bg="#f8fafc")
        f_metrics.pack(fill=tk.X, pady=(0, 8))

        self.card_inv_count = self.create_metric_widget(f_metrics, "FATURA SAYISI", "0", "Ayrıştırılan Fatura", "#0f172a", None)
        self.card_item_count = self.create_metric_widget(f_metrics, "TOPLAM KALEM", "0", "Ürün Satırı", "#2563eb", None)
        self.card_warn_count = self.create_metric_widget(f_metrics, "UYARILAR", "0", "Fatura / PL Uyumsuzluk", "#d97706", None)
        self.card_file_count = self.create_metric_widget(f_metrics, "EXCEL ÇIKTILARI", "0", "Hazır Dosya", "#16a34a", None)

        # ── 3. ÇIKTI VE SONUÇ TABLOSU ──
        card_table = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID, padx=12, pady=10)
        card_table.pack(fill=tk.BOTH, expand=True)

        table_header = tk.Frame(card_table, bg="#ffffff")
        table_header.pack(fill=tk.X, pady=(0, 8))

        lbl_tbl_title = tk.Label(
            table_header,
            text="📊 Üretilen Evrim Beyanname Excel Çıktıları & Kalem Özetleri",
            font=("Segoe UI", 10, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_tbl_title.pack(side=tk.LEFT)

        btn_open_folder = tk.Button(
            table_header,
            text="📁 Çıktı Klasörünü Aç",
            font=("Segoe UI", 8, "bold"),
            bg="#f1f5f9",
            fg="#334155",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.open_outputs_folder
        )
        btn_open_folder.pack(side=tk.RIGHT, padx=4)

        btn_open_selected = tk.Button(
            table_header,
            text="📂 Seçili Excel'i Aç",
            font=("Segoe UI", 8, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.open_selected_excel
        )
        btn_open_selected.pack(side=tk.RIGHT, padx=4)

        btn_show_warn = tk.Button(
            table_header,
            text="⚠️ Uyarı Detayını Gör",
            font=("Segoe UI", 8, "bold"),
            bg="#f59e0b",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.show_selected_warning_details
        )
        btn_show_warn.pack(side=tk.RIGHT, padx=4)

        # Tablo Kapsayıcısı
        tbl_container = tk.Frame(card_table, bg="#ffffff")
        tbl_container.pack(fill=tk.BOTH, expand=True)

        cols = ("fatura_no", "kalem_sayisi", "uyarilar", "cikti_dosyasi", "kaynak_evrak")
        self.tree_results = ttk.Treeview(tbl_container, columns=cols, show="headings", height=11)

        self.tree_results.heading("fatura_no", text="Fatura No")
        self.tree_results.heading("kalem_sayisi", text="Kalem Sayısı")
        self.tree_results.heading("uyarilar", text="Kontrol & Uyarılar")
        self.tree_results.heading("cikti_dosyasi", text="Üretilen Excel Dosyası")
        self.tree_results.heading("kaynak_evrak", text="Kaynak Evraklar")

        self.tree_results.column("fatura_no", width=130, anchor="w")
        self.tree_results.column("kalem_sayisi", width=95, anchor="center")
        self.tree_results.column("uyarilar", width=290, anchor="w")
        self.tree_results.column("cikti_dosyasi", width=200, anchor="w")
        self.tree_results.column("kaynak_evrak", width=260, anchor="w")

        scrollbar = ttk.Scrollbar(tbl_container, orient=tk.VERTICAL, command=self.tree_results.yview)
        self.tree_results.configure(yscrollcommand=scrollbar.set)

        self.tree_results.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_results.bind("<Double-1>", lambda e: self.open_selected_excel())
        self.tree_results.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Alt Bilgi / Canlı Uyarı Detay Çubuğu
        self.frame_warn_banner = tk.Frame(card_table, bg="#f8fafc", bd=1, relief=tk.SOLID, padx=12, pady=8)
        self.frame_warn_banner.pack(fill=tk.X, pady=(8, 0))

        self.lbl_warn_banner = tk.Label(
            self.frame_warn_banner,
            text="ℹ️ Tablodan bir fatura seçerek evrak kontrol özetini ve varsa uyarı detaylarını buradan anlık görebilirsiniz.",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#f8fafc",
            anchor="w",
            justify=tk.LEFT
        )
        self.lbl_warn_banner.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Sağ tık menüsü
        self.context_menu = tk.Menu(self.tree_results, tearoff=0)
        self.context_menu.add_command(label="⚠️ Uyarı Detaylarını Gör", command=self.show_selected_warning_details)
        self.context_menu.add_command(label="📂 Excel Dosyasını Aç", command=self.open_selected_excel)
        self.context_menu.add_command(label="📁 Dosya Konumunu Aç", command=self.open_outputs_folder)
        self.tree_results.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        row_id = self.tree_results.identify_row(event.y)
        if row_id:
            self.tree_results.selection_set(row_id)
            self.context_menu.post(event.x_root, event.y_root)

    def select_pdf_files(self):
        files = filedialog.askopenfilenames(
            title="İşlenecek PDF Dosyalarını Seçin",
            filetypes=[("PDF Dosyaları", "*.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        if files:
            self.selected_files = list(files)
            names = [os.path.basename(f) for f in files]
            if len(names) <= 3:
                txt = " ✅ " + ", ".join(names)
            else:
                txt = f" ✅ Toplam {len(names)} Adet PDF Seçildi: " + ", ".join(names[:2]) + f" ve {len(names)-2} dosya daha..."
            self.lbl_selected_status.config(text=txt, fg="#15803d", font=("Segoe UI", 9, "bold"))

    def clear_files(self):
        self.selected_files = []
        self.lbl_selected_status.config(text="Henüz dosya seçilmedi.", fg="#94a3b8", font=("Segoe UI", 9, "italic"))

    def start_processing(self):
        if not self.selected_files:
            messagebox.showwarning("Uyarı", "Lütfen önce en az 1 adet PDF dosyası seçin!")
            return

        self.btn_process.config(state=tk.DISABLED, text="⏳ Evraklar İşleniyor...")
        threading.Thread(target=self._run_pipeline_worker, daemon=True).start()

    def _run_pipeline_worker(self):
        try:
            ensure_template()
            run_id, run_dir = new_run_dir()
            pdf_paths = [Path(f) for f in self.selected_files]

            report = run_pipeline(pdf_paths, run_dir)
            self.latest_outputs_dir = run_dir / "outputs"

            # UI Güncelleme (Ana Thread)
            self.root.after(0, self._render_results, report)
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{err}"))
        finally:
            self.root.after(0, lambda: self.btn_process.config(state=tk.NORMAL, text="⚡ Evrakları Çözümle & Evrim Exceli Üret"))

    def _render_results(self, report):
        for item in self.tree_results.get_children():
            self.tree_results.delete(item)

        invoices = report.get("invoices", [])
        self.invoices_data = invoices
        total_kalem = 0
        total_warn = 0

        self.latest_outputs.clear()

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
            else:
                warn_str = "✅ Temiz / Sorunsuz"

            if inv.get("parse_failed") or not inv.get("kalemler"):
                warn_str = "❌ PDF tanınmadı / kalem yok"

            out_file = inv.get("output_filename") or "—"
            if self.latest_outputs_dir and inv.get("output_filename"):
                out_path = self.latest_outputs_dir / inv.get("output_filename")
                self.latest_outputs.append(str(out_path))

            src_files = ", ".join([os.path.basename(f) for f in inv.get("source_files", [])])

            self.tree_results.insert("", "end", iid=str(idx), values=(
                inv_no,
                f"{k_count} Kalem",
                warn_str,
                out_file,
                src_files
            ))

            # Activity Hub Günlüğüne Otomatik Kayıt
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

        # Metrik Kartları
        if hasattr(self, "card_inv_count") and "val_lbl" in self.card_inv_count:
            self.card_inv_count["val_lbl"].config(text=str(len(invoices)))
        if hasattr(self, "card_item_count") and "val_lbl" in self.card_item_count:
            self.card_item_count["val_lbl"].config(text=str(total_kalem))
        if hasattr(self, "card_warn_count") and "val_lbl" in self.card_warn_count:
            self.card_warn_count["val_lbl"].config(text=str(total_warn))
        if hasattr(self, "card_file_count") and "val_lbl" in self.card_file_count:
            self.card_file_count["val_lbl"].config(text=str(len(invoices)))

        # Varsa uyarı içeren ilk satırı otomatik seç ve canlı bilgi çubuğuna bas
        warn_idx = next((i for i, inv in enumerate(invoices) if inv.get("warnings")), 0 if invoices else None)
        if warn_idx is not None and str(warn_idx) in self.tree_results.get_children():
            self.tree_results.selection_set(str(warn_idx))
            self.tree_results.focus(str(warn_idx))
            self.on_tree_select()

        messagebox.showinfo(
            "İşlem Tamamlandı",
            f"✅ Başarılı!\nToplam {len(invoices)} adet fatura için Evrim Excel çıktıları hazırlandı."
        )

    def on_tree_select(self, event=None):
        sel = self.tree_results.selection()
        if not sel:
            return
        try:
            idx = int(sel[0])
            inv = self.invoices_data[idx] if hasattr(self, "invoices_data") and 0 <= idx < len(self.invoices_data) else None
        except Exception:
            inv = None

        if not inv:
            return

        inv_no = inv.get("invoice_no", "")
        warns = inv.get("warnings", [])
        if warns:
            self.frame_warn_banner.config(bg="#fffbeb")
            lines = [f"⚠️ [Fatura No: {inv_no}] {len(warns)} Adet Uyumsuzluk / Uyarı Tespit Edildi:"]
            for i, w in enumerate(warns, 1):
                lines.append(f"   {i}) {w}")
            lines.append("   👉 Tüm detayları ayrı pencerede görmek için '⚠️ Uyarı Detayını Gör' butonuna basabilirsiniz.")
            self.lbl_warn_banner.config(
                text="\n".join(lines),
                fg="#9a3412",
                bg="#fffbeb"
            )
        else:
            self.frame_warn_banner.config(bg="#f0fdf4")
            self.lbl_warn_banner.config(
                text=f"✅ [Fatura No: {inv_no}] Fatura, Packing List ve kalemler arasında herhangi bir uyumsuzluk bulunmuyor (Temiz/Sorunsuz).",
                fg="#166534",
                bg="#f0fdf4"
            )

    def show_selected_warning_details(self):
        sel = self.tree_results.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen detayını görmek istediğiniz fatura satırını seçin.")
            return

        try:
            idx = int(sel[0])
            inv = self.invoices_data[idx] if hasattr(self, "invoices_data") and 0 <= idx < len(self.invoices_data) else None
        except Exception:
            inv = None

        if not inv:
            messagebox.showwarning("Uyarı", "Seçili fatura bilgisi bulunamadı.")
            return

        warns = inv.get("warnings", [])
        infos = inv.get("infos", [])
        inv_no = inv.get("invoice_no", "Bilinmeyen")
        k_count = len(inv.get("kalemler", []))
        src_files = ", ".join([os.path.basename(f) for f in inv.get("source_files", [])])
        out_file = inv.get("output_filename", "")

        top = tk.Toplevel(self)
        top.title(f"Fatura {inv_no} - Evrak Uyarı ve Çapraz Kontrol Detayları")
        top.geometry("780x560")
        top.configure(bg="#f8fafc")
        top.transient(self.winfo_toplevel())
        top.grab_set()

        # Üst Başlık
        hdr = tk.Frame(top, bg="#0f172a", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text=f"📋 Fatura Kontrol & Uyarı Raporu: {inv_no}",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        ).pack(side=tk.LEFT)

        content = tk.Frame(top, bg="#f8fafc", padx=16, pady=12)
        content.pack(fill=tk.BOTH, expand=True)

        # Bilgi Kartı
        info_card = tk.Frame(content, bg="#ffffff", bd=1, relief=tk.SOLID, padx=14, pady=10)
        info_card.pack(fill=tk.X, pady=(0, 12))

        lbl_info_txt = (
            f"📄 Fatura No: {inv_no}   |   📦 Kalem Sayısı: {k_count} Kalem\n"
            f"📁 Kaynak Evraklar: {src_files}\n"
            f"📊 Üretilen Excel: {out_file}"
        )
        tk.Label(
            info_card,
            text=lbl_info_txt,
            font=("Segoe UI", 9),
            fg="#1e293b",
            bg="#ffffff",
            justify=tk.LEFT
        ).pack(anchor="w")

        # Uyarılar Kutusu
        if warns:
            warn_card = tk.LabelFrame(
                content,
                text=f" ⚠️ Tespit Edilen Evrak Uyumsuzlukları ({len(warns)} Adet) ",
                font=("Segoe UI", 10, "bold"),
                fg="#b45309",
                bg="#ffffff",
                padx=12,
                pady=10
            )
            warn_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            txt_warns = tk.Text(
                warn_card,
                font=("Consolas", 9),
                bg="#fffbeb",
                fg="#9a3412",
                wrap=tk.WORD,
                bd=1,
                relief=tk.SOLID,
                padx=10,
                pady=8
            )
            txt_warns.pack(fill=tk.BOTH, expand=True)

            txt_warns.insert(tk.END, "AŞAĞIDAKİ EVRAK UYUMSUZLUKLARI TESPİT EDİLDİ:\n" + "="*60 + "\n\n")
            for i, w in enumerate(warns, 1):
                txt_warns.insert(tk.END, f"[{i}] {w}\n\n")

            if infos:
                txt_warns.insert(tk.END, "\nEK BİLGİ & DOĞRULAMA NOTLARI:\n" + "-"*60 + "\n")
                for inf in infos:
                    txt_warns.insert(tk.END, f"• {inf}\n")

            txt_warns.insert(tk.END, "\n" + "="*60 + "\n")
            txt_warns.insert(tk.END, "💡 NOT: Evrak setindeki tüm kalemler eksiksiz ayrıştırılmış ve Excel'e yazılmıştır.\nAncak evrak başlığındaki alt toplam değerleri ile okunan kalem satırlarının toplamı tutmadığı için yukarıdaki uyarılar verilmiştir.")
            txt_warns.config(state=tk.DISABLED)
        else:
            clean_card = tk.Frame(content, bg="#f0fdf4", bd=1, relief=tk.SOLID, padx=16, pady=20)
            clean_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            tk.Label(
                clean_card,
                text="✅ Temiz / Sorunsuz Evrak Seti\n\nBu faturanın Fatura, Packing List ve Konşimento evrakları arasında miktar, ağırlık veya numara bazında herhangi bir uyumsuzluk bulunmamaktadır.",
                font=("Segoe UI", 10),
                fg="#166534",
                bg="#f0fdf4",
                justify=tk.LEFT
            ).pack(anchor="w")

        # Butonlar
        btn_frame = tk.Frame(top, bg="#f8fafc", padx=16, pady=10)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame,
            text="📂 Excel Dosyasını Aç",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.open_selected_excel
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_frame,
            text="Kapat",
            font=("Segoe UI", 9, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=18,
            pady=5,
            cursor="hand2",
            command=top.destroy
        ).pack(side=tk.RIGHT)

    def open_selected_excel(self):
        sel = self.tree_results.selection()
        if sel:
            try:
                idx = int(sel[0])
                if 0 <= idx < len(self.latest_outputs):
                    file_path = self.latest_outputs[idx]
                    if os.path.exists(file_path):
                        os.startfile(file_path)
                        return
                    else:
                        messagebox.showerror("Hata", f"Dosya bulunamadı:\n{file_path}")
                        return
            except Exception:
                pass
            messagebox.showerror("Hata", "Dosya açılamadı.")
        else:
            messagebox.showwarning("Uyarı", "Lütfen açmak için listeden bir fatura satırı seçin.")

    def open_outputs_folder(self):
        if hasattr(self, "latest_outputs_dir") and self.latest_outputs_dir and os.path.exists(self.latest_outputs_dir):
            try:
                os.startfile(self.latest_outputs_dir)
            except Exception as e:
                messagebox.showerror("Hata", f"Klasör açılamadı: {e}")
        elif os.path.exists(RUNS_DIR):
            try:
                os.startfile(RUNS_DIR)
            except Exception as e:
                messagebox.showerror("Hata", f"Klasör açılamadı: {e}")
        else:
            messagebox.showinfo("Bilgi", "Henüz bir çıktı klasörü oluşturulmadı.")

    def download_template(self):
        try:
            ensure_template()
            dest = filedialog.asksaveasfilename(
                title="Evrim Şablonunu Kaydet",
                initialfile="Evrim_sablon.xlsx",
                filetypes=[("Excel Dosyası", "*.xlsx")]
            )
            if dest:
                shutil.copy2(TEMPLATE_XLSX, dest)
                messagebox.showinfo("Başarılı", f"Şablon başarıyla kaydedildi:\n{dest}")
        except Exception as e:
            messagebox.showerror("Hata", f"Şablon indirilemedi: {e}")

    def upload_template(self):
        file = filedialog.askopenfilename(
            title="Yeni Evrim Şablonunu Seçin",
            filetypes=[("Excel Dosyası", "*.xlsx"), ("Tüm Dosyalar", "*.*")]
        )
        if file:
            try:
                save_template(Path(file))
                messagebox.showinfo("Başarılı", "Evrim şablonu başarıyla güncellendi!")
            except Exception as e:
                messagebox.showerror("Hata", f"Şablon güncellenemedi: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MODÜL 2: MASTER DATA KONTROL (YEREL TKINTER ARAYÜZÜ)
# ══════════════════════════════════════════════════════════════════════════════
class NativeMasterKontrolView(BaseView):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.selected_files = []
        self.current_report = None
        self.missing_excel_path = None
        self.mismatch_excel_path = None
        self.setup_ui()

    def on_activate(self):
        """Sekme açıldığında katalog durumunu tazeler."""
        self.refresh_katalog_status()

    def setup_ui(self):
        # ── 1. ÜST KART: MASTER KATALOG BİLGİSİ & YÜKLEME ──
        card_katalog = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID, padx=16, pady=12)
        card_katalog.pack(fill=tk.X, pady=(0, 10))

        top_katalog_row = tk.Frame(card_katalog, bg="#ffffff")
        top_katalog_row.pack(fill=tk.X)

        self.lbl_katalog_title = tk.Label(
            top_katalog_row,
            text="1. Master Ürün Kataloğu Referans Listesi",
            font=("Segoe UI", 11, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        self.lbl_katalog_title.pack(side=tk.LEFT)

        btn_upload_katalog = tk.Button(
            top_katalog_row,
            text="📤 Yeni Katalog Yükle / Güncelle",
            font=("Segoe UI", 8, "bold"),
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.upload_katalog
        )
        btn_upload_katalog.pack(side=tk.RIGHT, padx=4)

        btn_open_katalog = tk.Button(
            top_katalog_row,
            text="📥 Kataloğu Aç",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#475569",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.open_katalog
        )
        btn_open_katalog.pack(side=tk.RIGHT, padx=4)

        self.lbl_katalog_status = tk.Label(
            card_katalog,
            text="Katalog durumu kontrol ediliyor...",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#ffffff"
        )
        self.lbl_katalog_status.pack(anchor="w", pady=(4, 0))
        self.refresh_katalog_status()

        # ── 2. ORTA KART: FATURA PDF YÜKLEME & KONTROL BUTONU ──
        card_pdf = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID, padx=16, pady=12)
        card_pdf.pack(fill=tk.X, pady=(0, 10))

        lbl_pdf_title = tk.Label(
            card_pdf,
            text="2. Kontrol Edilecek Fatura / Packing List PDF'lerini Seçin",
            font=("Segoe UI", 11, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_pdf_title.pack(anchor="w")

        lbl_pdf_desc = tk.Label(
            card_pdf,
            text="Fatura kalemlerindeki her ürün kodu master katalogda aranır: Eşleşti / Tanım Uyuşmuyor / Kod Master'da Yok. Eksik ürünler Excel'e toplanır.",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#ffffff"
        )
        lbl_pdf_desc.pack(anchor="w", pady=(2, 8))

        pdf_btn_row = tk.Frame(card_pdf, bg="#ffffff")
        pdf_btn_row.pack(fill=tk.X)

        self.btn_select_pdf = tk.Button(
            pdf_btn_row,
            text="📂 Fatura PDF'lerini Seç",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.select_pdf_files
        )
        self.btn_select_pdf.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_run_check = tk.Button(
            pdf_btn_row,
            text="🔎 Master Data Kontrolünü Başlat",
            font=("Segoe UI", 9, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            activebackground="#1e293b",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.start_master_check
        )
        self.btn_run_check.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_pdf_status = tk.Label(
            card_pdf,
            text="Henüz PDF seçilmedi.",
            font=("Segoe UI", 9, "italic"),
            fg="#94a3b8",
            bg="#ffffff"
        )
        self.lbl_pdf_status.pack(anchor="w", pady=(6, 0))

        # ── 3. METRİK KARTLARI ──
        f_metrics = tk.Frame(self, bg="#f8fafc")
        f_metrics.pack(fill=tk.X, pady=(0, 8))

        self.card_total = self.create_metric_widget(f_metrics, "TOPLAM KALEM", "0", "Taranan Kalemler", "#0f172a", None)
        self.card_matched = self.create_metric_widget(f_metrics, "EŞLEŞTİ", "0", "Katalogda Doğrulandı", "#16a34a", None)
        self.card_mismatch = self.create_metric_widget(f_metrics, "TANIM UYUŞMUYOR", "0", "Açıklama Farklı", "#d97706", None)
        self.card_missing = self.create_metric_widget(f_metrics, "MASTER'DA YOK", "0", "Eksik / Yeni Ürün", "#dc2626", None)

        # ── 4. DETAYLI KALEM TABLOSU & AKSİYONLAR ──
        card_results = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID, padx=12, pady=10)
        card_results.pack(fill=tk.BOTH, expand=True)

        res_head = tk.Frame(card_results, bg="#ffffff")
        res_head.pack(fill=tk.X, pady=(0, 8))

        lbl_res_title = tk.Label(
            res_head,
            text="📋 Ürün Eşleştirme & GTİP Denetim Sonuçları",
            font=("Segoe UI", 10, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_res_title.pack(side=tk.LEFT)

        self.btn_dl_missing = tk.Button(
            res_head,
            text="📥 Eksik Ürünleri İndir (mastera_eklenecek.xlsx)",
            font=("Segoe UI", 8, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.open_missing_excel
        )
        self.btn_dl_missing.pack(side=tk.RIGHT, padx=4)

        self.btn_dl_mismatch = tk.Button(
            res_head,
            text="📥 Tanımı Uyuşmayanları İndir",
            font=("Segoe UI", 8, "bold"),
            bg="#d97706",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.open_mismatch_excel
        )
        self.btn_dl_mismatch.pack(side=tk.RIGHT, padx=4)

        # Tablo
        cols = ("durum", "urun_kodu", "fatura_tanimi", "master_tanimi", "gtip", "mense", "miktar")
        self.tree_master = ttk.Treeview(card_results, columns=cols, show="headings", height=10)

        self.tree_master.heading("durum", text="Durum")
        self.tree_master.heading("urun_kodu", text="Ürün Kodu")
        self.tree_master.heading("fatura_tanimi", text="Fatura Tanımı")
        self.tree_master.heading("master_tanimi", text="Master Tanımı")
        self.tree_master.heading("gtip", text="GTİP")
        self.tree_master.heading("mense", text="Menşe")
        self.tree_master.heading("miktar", text="Miktar")

        self.tree_master.column("durum", width=120, anchor="center")
        self.tree_master.column("urun_kodu", width=130, anchor="w")
        self.tree_master.column("fatura_tanimi", width=220, anchor="w")
        self.tree_master.column("master_tanimi", width=220, anchor="w")
        self.tree_master.column("gtip", width=110, anchor="center")
        self.tree_master.column("mense", width=80, anchor="center")
        self.tree_master.column("miktar", width=70, anchor="center")

        self.tree_master.tag_configure("matched", background="#f0fdf4")
        self.tree_master.tag_configure("description_mismatch", background="#fffbeb")
        self.tree_master.tag_configure("missing_code", background="#fef2f2")

        scr = ttk.Scrollbar(card_results, orient=tk.VERTICAL, command=self.tree_master.yview)
        self.tree_master.configure(yscrollcommand=scr.set)

        self.tree_master.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_master.bind("<Double-1>", self.on_master_row_double_click)

    def on_master_row_double_click(self, event=None):
        sel = self.tree_master.selection()
        if sel:
            vals = self.tree_master.item(sel[0], "values")
            if vals and len(vals) > 1:
                p_code = vals[1]
                self.copy_to_clipboard(p_code, show_msg=True)

    def refresh_katalog_status(self):
        if master_katalog_exists():
            try:
                katalog = load_master_katalog(MASTER_KATALOG_XLSX)
                self.lbl_katalog_status.config(
                    text=f"✅ Master Katalog Yüklü: Toplam {katalog.row_count} kayıtlı ürün referansı mevcut.",
                    fg="#15803d",
                    font=("Segoe UI", 9, "bold")
                )
            except Exception as e:
                self.lbl_katalog_status.config(
                    text=f"⚠️ Master katalog dosyası mevcut fakat okunamadı: {e}",
                    fg="#b91c1c"
                )
        else:
            self.lbl_katalog_status.config(
                text="⚠️ Henüz Master Katalog yüklenmedi. Lütfen sağdaki butondan Excel kataloğunuzu yükleyin.",
                fg="#dc2626",
                font=("Segoe UI", 9, "bold")
            )

    def upload_katalog(self):
        file = filedialog.askopenfilename(
            title="Master Katalog Excel Dosyasını Seçin",
            filetypes=[("Excel Dosyaları", "*.xlsx;*.xls"), ("Tüm Dosyalar", "*.*")]
        )
        if file:
            try:
                save_master_katalog(Path(file))
                self.refresh_katalog_status()
                messagebox.showinfo("Başarılı", "Master Katalog başarıyla güncellendi!")
            except Exception as e:
                messagebox.showerror("Hata", f"Katalog kaydedilemedi: {e}")

    def open_katalog(self):
        if master_katalog_exists():
            try:
                os.startfile(MASTER_KATALOG_XLSX)
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya açılamadı: {e}")
        else:
            messagebox.showwarning("Uyarı", "Henüz bir master katalog dosyası yüklenmemiş.")

    def select_pdf_files(self):
        files = filedialog.askopenfilenames(
            title="Kontrol Edilecek Fatura/PL PDF'lerini Seçin",
            filetypes=[("PDF Dosyaları", "*.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        if files:
            self.selected_files = list(files)
            names = [os.path.basename(f) for f in files]
            self.lbl_pdf_status.config(
                text=f" ✅ {len(names)} Adet PDF Seçildi: " + ", ".join(names[:3]) + ("..." if len(names)>3 else ""),
                fg="#15803d",
                font=("Segoe UI", 9, "bold")
            )

    def start_master_check(self):
        if not master_katalog_exists():
            messagebox.showwarning("Uyarı", "Önce Master Katalog Excel dosyasını yüklemelisiniz!")
            return
        if not self.selected_files:
            messagebox.showwarning("Uyarı", "Lütfen kontrol edilecek en az 1 adet PDF seçin!")
            return

        self.btn_run_check.config(state=tk.DISABLED, text="⏳ Kontrol Ediliyor...")
        threading.Thread(target=self._run_check_worker, daemon=True).start()

    def _run_check_worker(self):
        try:
            ensure_eklenecek_template()
            run_id, run_dir = new_run_dir()
            pdf_paths = [Path(f) for f in self.selected_files]

            report = run_master_pipeline(pdf_paths, run_dir)
            report["run_dir"] = run_dir

            self.root.after(0, self._render_results, report)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("Hata", f"Kontrol sırasında hata oluştu:\n{err}"))
        finally:
            self.root.after(0, lambda: self.btn_run_check.config(state=tk.NORMAL, text="🔎 Master Data Kontrolünü Başlat"))

    def _render_results(self, report):
        self.current_report = report
        for item in self.tree_master.get_children():
            self.tree_master.delete(item)

        rows = report.get("rows", [])
        for r in rows:
            st = r.get("status", "")
            if st == "matched":
                st_label = "✅ Eşleşti"
                tag = "matched"
            elif st == "description_mismatch":
                st_label = "⚠️ Tanım Farklı"
                tag = "description_mismatch"
            else:
                st_label = "❌ Master'da Yok"
                tag = "missing_code"

            mense_display = r.get("master_origin") or r.get("origin") or "—"
            if mense_display == "CHINA":
                mense_display = "Çin"
            elif mense_display == "KOREA":
                mense_display = "Kore"

            self.tree_master.insert("", "end", values=(
                st_label,
                r.get("product_code", ""),
                r.get("invoice_description", ""),
                r.get("master_turkish_description") or r.get("master_description") or "—",
                r.get("master_gtip") or "—",
                mense_display,
                r.get("quantity") or "1"
            ), tags=(tag,))

        # Metrik Kartları Güncelle
        tot = report.get("total", 0)
        mat = report.get("matched_count", 0)
        mis = report.get("mismatch_count", 0)
        missing = report.get("missing_count", 0)

        if hasattr(self, "card_total") and "val_lbl" in self.card_total:
            self.card_total["val_lbl"].config(text=str(tot))
        if hasattr(self, "card_matched") and "val_lbl" in self.card_matched:
            self.card_matched["val_lbl"].config(text=str(mat))
        if hasattr(self, "card_mismatch") and "val_lbl" in self.card_mismatch:
            self.card_mismatch["val_lbl"].config(text=str(mis))
        if hasattr(self, "card_missing") and "val_lbl" in self.card_missing:
            self.card_missing["val_lbl"].config(text=str(missing))

        # İndirme Butonları Durumu
        run_dir = report.get("run_dir")
        if report.get("eklenecek_filename") and run_dir:
            self.missing_excel_path = run_dir / "outputs" / report["eklenecek_filename"]
            self.btn_dl_missing.config(state=tk.NORMAL)
        else:
            self.btn_dl_missing.config(state=tk.DISABLED)

        if report.get("tanim_uyusmuyor_filename") and run_dir:
            self.mismatch_excel_path = run_dir / "outputs" / report["tanim_uyusmuyor_filename"]
            self.btn_dl_mismatch.config(state=tk.NORMAL)
        else:
            self.btn_dl_mismatch.config(state=tk.DISABLED)

        # Aktivite Günlüğü Kaydı
        try:
            from tools.supabase_sync_manager import get_supabase_manager
            sm = get_supabase_manager()
            if sm:
                sm.add_activity_log(
                    dosya_no="",
                    ref_no="",
                    islem_tipi="NOT",
                    baslik=f"Master Data Kontrol Tamamlandı ({tot} Ürün)",
                    icerik=f"Toplam: {tot} ürün | Eşleşen: {mat} | Tanım Farklı: {mis} | Eksik/Yeni Ürün: {missing}",
                    etiket="Bilgi" if missing == 0 else "Acil"
                )
        except Exception:
            pass

        messagebox.showinfo(
            "Kontrol Tamamlandı",
            f"✅ Master Data Kontrolü Tamamlandı!\n\nToplam Ürün: {tot}\nEşleşen: {mat}\nTanım Farklı: {mis}\nMaster'da Olmayan: {missing}"
        )

    def open_missing_excel(self):
        if hasattr(self, "missing_excel_path") and self.missing_excel_path and os.path.exists(self.missing_excel_path):
            try:
                os.startfile(self.missing_excel_path)
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya açılamadı: {e}")
        else:
            messagebox.showwarning("Uyarı", "Eksik ürünler Excel dosyası bulunamadı.")

    def open_mismatch_excel(self):
        if hasattr(self, "mismatch_excel_path") and self.mismatch_excel_path and os.path.exists(self.mismatch_excel_path):
            try:
                os.startfile(self.mismatch_excel_path)
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya açılamadı: {e}")
        else:
            messagebox.showwarning("Uyarı", "Tanımı uyuşmayanlar Excel dosyası bulunamadı.")
