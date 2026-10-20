# -*- coding: utf-8 -*-
"""
gtb_view.py — GTB Otonom Beyanname Takip Görünümü
MasterSuite için GTB canlı takip tablosu, manuel sorgu diyaloğu, filtreler, export, auto-refresh.
"""
import os
import sys
import re
import time
import datetime
from datetime import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .base_view import BaseView


class GTBView(BaseView):
    """GTB Otonom Beyanname Takip Sekmesi."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.current_gtb_filter = "ALL"
        self.setup_ui()

    @property
    def gtb_tracker(self):
        return getattr(self.app, "gtb_tracker", None)

    def setup_ui(self):
        # 1. Metrik Barı
        metric_bar = tk.Frame(self, bg="#f8fafc")
        metric_bar.pack(fill=tk.X, pady=(0, 10))

        self.card_gtb_total = self.create_metric_widget(
            metric_bar, "İZLENEN BEYANNAMELER", "0", "Otonom Havuzda", "#0f172a",
            lambda: self.filter_gtb_table("ALL")
        )
        self.card_gtb_closed = self.create_metric_widget(
            metric_bar, "KAPANAN / TAMAMLANAN", "0", "Gümrük Bitti", "#16a34a",
            lambda: self.filter_gtb_table("CLOSED")
        )
        self.card_gtb_in_proc = self.create_metric_widget(
            metric_bar, "İŞLEMDE OLANLAR", "0", "Tescil / Muayene", "#d97706",
            lambda: self.filter_gtb_table("IN_PROC")
        )
        self.card_gtb_last_scan = self.create_metric_widget(
            metric_bar, "SON OTONOM TARAMA", "—", "10 Dk Döngü", "#2563eb", None
        )

        # 2. Kontrol Çubuğu & Butonlar
        ctrl_bar = tk.Frame(self, bg="#ffffff", padx=12, pady=10, relief=tk.FLAT, bd=0)
        ctrl_bar.pack(fill=tk.X, pady=(0, 10))

        # Sol Arama
        lbl_s = tk.Label(ctrl_bar, text="🔍 Ara / Filtrele:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_s.pack(side=tk.LEFT, padx=(0, 6))

        self.txt_gtb_search = tk.Entry(ctrl_bar, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, width=22)
        self.txt_gtb_search.pack(side=tk.LEFT, padx=(0, 10), ipady=3)
        self.txt_gtb_search.bind("<KeyRelease>", lambda e: self.refresh_gtb_takip_table())

        # Aksiyon Butonları
        self.btn_gtb_add = tk.Button(
            ctrl_bar, text="➕ Manuel Beyanname Ekle", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.show_gtb_add_dialog
        )
        self.btn_gtb_add.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_gtb_sync = tk.Button(
            ctrl_bar, text="⚡ Tescil Tarihine Göre İçe Aktar", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.show_gtb_smart_import_dialog
        )
        self.btn_gtb_sync.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_gtb_scan_now = tk.Button(
            ctrl_bar, text="🔄 Şimdi Tümünü Tara", font=("Segoe UI", 9, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.run_gtb_scan_now
        )
        self.btn_gtb_scan_now.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_gtb_clear_all = tk.Button(
            ctrl_bar, text="🗑️ Havuzu Temizle", font=("Segoe UI", 9),
            bg="#f1f5f9", fg="#dc2626", activebackground="#fee2e2", activeforeground="#991b1b",
            relief=tk.FLAT, bd=0, padx=8, pady=3, cursor="hand2", command=self.clear_all_gtb_pool
        )
        self.btn_gtb_clear_all.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_gtb_mail = tk.Button(
            ctrl_bar, text="📧 Vergi Talebi Maili Oluştur", font=("Segoe UI", 9, "bold"),
            bg="#7c3aed", fg="#ffffff", activebackground="#6d28d9", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=self.create_tax_mail_from_gtb
        )
        self.btn_gtb_mail.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_gtb_status = tk.Label(
            ctrl_bar, text="🤖 10 Dk Otonom İzleme Aktif",
            font=("Segoe UI", 8, "bold"), fg="#16a34a", bg="#dcfce7", padx=8, pady=4
        )
        self.lbl_gtb_status.pack(side=tk.RIGHT)

        # 3. Tablo (Çoklu Seçim / Extended Selection & Ctrl+A Destekli)
        table_frame = tk.Frame(self, bg="#ffffff", relief=tk.FLAT, bd=0)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("beyan_no", "dosya_no", "ref", "firma", "statu", "son_kontrol", "degisim_tarihi")
        self.tree_gtb = ttk.Treeview(table_frame, columns=cols, show="headings", height=16, selectmode="extended")

        self.tree_gtb.heading("beyan_no", text="16 Haneli Beyanname No")
        self.tree_gtb.heading("dosya_no", text="Dosya No")
        self.tree_gtb.heading("ref", text="Referans No")
        self.tree_gtb.heading("firma", text="Firma / Bayi")
        self.tree_gtb.heading("statu", text="GTB Bakanlık Canlı Durumu")
        self.tree_gtb.heading("son_kontrol", text="Son Kontrol")
        self.tree_gtb.heading("degisim_tarihi", text="Değişim Zamanı")

        self.tree_gtb.column("beyan_no", width=180, anchor="w")
        self.tree_gtb.column("dosya_no", width=100, anchor="center")
        self.tree_gtb.column("ref", width=140, anchor="center")
        self.tree_gtb.column("firma", width=140, anchor="w")
        self.tree_gtb.column("statu", width=420, anchor="w")
        self.tree_gtb.column("son_kontrol", width=120, anchor="center")
        self.tree_gtb.column("degisim_tarihi", width=120, anchor="center")

        # Scrollbar
        sb_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree_gtb.yview)
        self.tree_gtb.configure(yscrollcommand=sb_y.set)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_gtb.pack(fill=tk.BOTH, expand=True)

        # Renk Etiketleri
        self.tree_gtb.tag_configure("kapandi", background="#f0fdf4", foreground="#166534")
        self.tree_gtb.tag_configure("islemde", background="#fffbeb", foreground="#92400e")
        self.tree_gtb.tag_configure("bekliyor", background="#f8fafc", foreground="#334155")

        # Klavye Kısayolları (Ctrl+A ile Tümünü Seç)
        self.tree_gtb.bind("<Control-a>", self.select_all_gtb_rows)
        self.tree_gtb.bind("<Control-A>", self.select_all_gtb_rows)
        self.tree_gtb.bind("<Delete>", lambda e: self.remove_gtb_selected_rows())

        # Çift Tıklama & Sağ Tık Menüsü
        self.tree_gtb.bind("<Double-1>", lambda e: self.on_gtb_row_double_click())
        self.tree_gtb.bind("<Button-3>", lambda e: self.show_gtb_context_menu(e))

    def select_all_gtb_rows(self, event=None):
        """Ctrl+A ile tablodaki tüm satırları seçer."""
        all_items = self.tree_gtb.get_children()
        if all_items:
            self.tree_gtb.selection_set(all_items)
        return "break"

    def filter_gtb_table(self, filter_type):
        self.current_gtb_filter = filter_type
        self.refresh_gtb_takip_table()

    def refresh_gtb_takip_table(self):
        """GTB Takip tablosunu tracker verileriyle günceller."""
        if not hasattr(self, "tree_gtb") or not self.gtb_tracker:
            return

        for r in self.tree_gtb.get_children():
            self.tree_gtb.delete(r)

        raw_tracked = self.gtb_tracker.list_tracked(only_active=True)
        tracked = [
            item for item in raw_tracked
            if item.get("beyanname_no") and not str(item.get("beyanname_no")).startswith("BEYAN")
        ]
        search_q = self.txt_gtb_search.get().strip().upper() if hasattr(self, "txt_gtb_search") else ""

        kapanan_cnt = 0
        islemde_cnt = 0
        displayed_cnt = 0

        for item in tracked:
            b_no = item.get("beyanname_no", "")
            d_no = item.get("dosya_no", "—")
            ref_no = item.get("ref", "—")
            firma = item.get("firma", "—")
            statu = item.get("durum", "—")
            is_kapandi = bool(item.get("kapandi")) or "kapan" in statu.lower() or "tamamlan" in statu.lower()
            son_chk = self.format_check_time(item.get("son_kontrol") or item.get("son_sorgu_zamani") or "—")
            deg_dt = self.format_check_time(item.get("degisim_tarihi") or "—")

            if is_kapandi:
                kapanan_cnt += 1
            else:
                islemde_cnt += 1

            if self.current_gtb_filter == "CLOSED" and not is_kapandi:
                continue
            elif self.current_gtb_filter == "IN_PROC" and is_kapandi:
                continue

            if search_q:
                haystack = f"{b_no} {d_no} {ref_no} {firma} {statu}".upper()
                if search_q not in haystack:
                    continue

            tag = "kapandi" if is_kapandi else ("islemde" if "işlemde" in statu.lower() or "süresi" in statu.lower() or "tescil" in statu.lower() else "bekliyor")
            self.tree_gtb.insert("", tk.END, values=(b_no, d_no, ref_no, firma, statu, son_chk, deg_dt), tags=(tag,))
            displayed_cnt += 1

        # KPI Kartlarını Güncelle
        if hasattr(self, "card_gtb_total"):
            self.card_gtb_total["val_lbl"].config(text=str(len(tracked)))
            self.card_gtb_closed["val_lbl"].config(text=str(kapanan_cnt))
            self.card_gtb_in_proc["val_lbl"].config(text=str(islemde_cnt))
            last_scan = getattr(self.gtb_tracker, "last_scan_time", "—")
            scan_t = last_scan.split(" ")[-1] if " " in str(last_scan) else str(last_scan)
            self.card_gtb_last_scan["val_lbl"].config(text=scan_t)

            # Aktif Filtre Görsel Vurgusu
            self.card_gtb_total["card"].config(bg="#f1f5f9" if self.current_gtb_filter == "ALL" else "#ffffff")
            self.card_gtb_closed["card"].config(bg="#dcfce7" if self.current_gtb_filter == "CLOSED" else "#ffffff")
            self.card_gtb_in_proc["card"].config(bg="#fef3c7" if self.current_gtb_filter == "IN_PROC" else "#ffffff")

        # Filtre durumu rozeti
        if hasattr(self, "lbl_gtb_status"):
            if self.current_gtb_filter == "CLOSED":
                self.lbl_gtb_status.config(text=f"🟢 Filtre: Kapananlar ({displayed_cnt}/{len(tracked)})", bg="#dcfce7", fg="#166534")
            elif self.current_gtb_filter == "IN_PROC":
                self.lbl_gtb_status.config(text=f"🟡 Filtre: İşlemde Olanlar ({displayed_cnt}/{len(tracked)})", bg="#fef3c7", fg="#92400e")
            else:
                self.lbl_gtb_status.config(text=f"🤖 10 Dk Otonom İzleme Aktif ({displayed_cnt} Beyanname)", bg="#dcfce7", fg="#16a34a")

    def refresh_table(self):
        self.refresh_gtb_takip_table()

    def on_gtb_status_changed(self):
        try:
            self.root.after(0, self.refresh_gtb_takip_table)
            self.root.after(100, self._refresh_cockpit_gtb_badge)
        except Exception:
            pass

    def _refresh_cockpit_gtb_badge(self):
        """Cockpit'te seçili dosyanın GTB rozetini yeniden hesaplar."""
        try:
            cockpit_v = self.app.views.get("COCKPIT") if hasattr(self.app, "views") else None
            if cockpit_v and hasattr(cockpit_v, "_refresh_cockpit_gtb_badge"):
                cockpit_v._refresh_cockpit_gtb_badge()
        except Exception:
            pass

    def show_gtb_context_menu(self, event):
        item_id = self.tree_gtb.identify_row(event.y)
        selected_ids = list(self.tree_gtb.selection())

        if item_id and item_id not in selected_ids:
            self.tree_gtb.selection_set(item_id)
            selected_ids = [item_id]

        if not selected_ids:
            return

        menu = tk.Menu(self.root, tearoff=0)
        sel_count = len(selected_ids)

        if sel_count == 1:
            vals = self.tree_gtb.item(selected_ids[0], "values")
            b_no = vals[0]
            menu.add_command(label=f"🔍 Şimdi Canlı Sorgula (GTB): {b_no}", command=lambda: self.query_selected_gtb_row(b_no))
            menu.add_command(label="📧 Vergi Talebi Maili Oluştur", command=self.create_tax_mail_from_gtb)
            menu.add_separator()
            menu.add_command(label="📋 Beyanname No Kopyala", command=lambda: self.copy_gtb_column(0, "Beyanname No", only_selected=True))
            menu.add_command(label="📋 Dosya No Kopyala", command=lambda: self.copy_gtb_column(1, "Dosya No", only_selected=True))
            menu.add_command(label="📋 Referans No Kopyala", command=lambda: self.copy_gtb_column(2, "Referans No", only_selected=True))
            menu.add_separator()
            menu.add_command(label="❌ Takipten Çıkar", command=lambda: self.remove_gtb_selected_rows())
        else:
            menu.add_command(label=f"🔍 Seçili ({sel_count}) Beyannameyi Canlı Sorgula (GTB)", command=self.query_multiple_gtb_rows)
            menu.add_command(label=f"📧 Seçili ({sel_count}) Beyanname İçin Vergi Talebi Maili Oluştur", command=self.create_tax_mail_from_gtb)
            menu.add_separator()
            menu.add_command(label=f"📋 Seçili ({sel_count}) Beyanname No'ları Kopyala (Alt Alta)", command=lambda: self.copy_gtb_column(0, "Beyanname No", only_selected=True))
            menu.add_command(label=f"📋 Seçili ({sel_count}) Dosya No'ları Kopyala (Alt Alta)", command=lambda: self.copy_gtb_column(1, "Dosya No", only_selected=True))
            menu.add_command(label=f"📋 Seçili ({sel_count}) Referans No'ları Kopyala (Alt Alta)", command=lambda: self.copy_gtb_column(2, "Referans No", only_selected=True))
            menu.add_command(label=f"📋 Seçili ({sel_count}) Satırı Excel Tablosu Olarak Kopyala", command=self.copy_selected_gtb_rows_as_table)
            menu.add_separator()
            menu.add_command(label=f"❌ Seçili ({sel_count}) Beyannameyi Takipten Çıkar", command=self.remove_gtb_selected_rows)

        # Tablodaki Tüm Sütunu Kopyalama Alt Menüsü
        all_ids = self.tree_gtb.get_children()
        all_count = len(all_ids)
        all_menu = tk.Menu(menu, tearoff=0)
        all_menu.add_command(label=f"📑 Tablodaki TÜM Beyanname No'ları Kopyala ({all_count} Satır)", command=lambda: self.copy_gtb_column(0, "Beyanname No", only_selected=False))
        all_menu.add_command(label=f"📑 Tablodaki TÜM Dosya No'ları Kopyala ({all_count} Satır)", command=lambda: self.copy_gtb_column(1, "Dosya No", only_selected=False))
        all_menu.add_command(label=f"📑 Tablodaki TÜM Referans No'ları Kopyala ({all_count} Satır)", command=lambda: self.copy_gtb_column(2, "Referans No", only_selected=False))
        menu.add_separator()
        menu.add_cascade(label=f"📑 Tablodaki TÜM Sütunu Kopyala ({all_count} Satır)...", menu=all_menu)

        menu.add_separator()
        menu.add_command(label="🗑️ Havuzdaki TÜMÜNÜ Takipten Çıkar (Temizle)", command=self.clear_all_gtb_pool)
        menu.tk_popup(event.x_root, event.y_root)

    def on_gtb_row_double_click(self):
        sel = self.tree_gtb.selection()
        if sel:
            vals = self.tree_gtb.item(sel[0], "values")
            if vals:
                self.query_selected_gtb_row(vals[0])

    def query_selected_gtb_row(self, beyanname_no):
        if not self.gtb_tracker:
            self.show_warning("GTB Servisi", "GTB takip servisi aktif değil.")
            return

        def _worker():
            res = self.gtb_tracker.query_single_now(beyanname_no)
            def _done():
                self.refresh_gtb_takip_table()
                if res.get("success"):
                    messagebox.showinfo("GTB Canlı Sonuç", f"📑 Beyanname: {beyanname_no}\n\n🏛️ Bakanlık Durumu:\n{res.get('durum')}")
                else:
                    messagebox.showerror("GTB Sorgu Hatası", f"Sorgulama başarısız:\n{res.get('error')}")
            self.root.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def query_multiple_gtb_rows(self):
        selected_ids = self.tree_gtb.selection()
        if not selected_ids or not self.gtb_tracker:
            return

        beyan_list = [self.tree_gtb.item(s, "values")[0] for s in selected_ids if self.tree_gtb.item(s, "values")]
        if not beyan_list:
            return

        self.btn_gtb_scan_now.config(text=f"⏳ {len(beyan_list)} Taranıyor...", state=tk.DISABLED)
        self.lbl_gtb_status.config(text=f"🔄 Seçili {len(beyan_list)} Beyanname Taranıyor...", bg="#fef3c7", fg="#92400e")

        t_start = time.time()
        count = 0
        tot = len(beyan_list)
        progress_lock = threading.Lock()

        def _task(b):
            nonlocal count
            res = self.gtb_tracker.query_single_now(b)
            with progress_lock:
                count += 1
                cur = count
            st = res.get("durum", "")[:30] if res.get("success") else res.get("error", "")[:30]
            def _ui_update():
                self.lbl_gtb_status.config(text=f"🔄 Taranıyor [{cur}/{tot}]: {b} ({st})", bg="#fef3c7", fg="#92400e")
                self.refresh_gtb_takip_table()
            try:
                self.root.after(0, _ui_update)
            except Exception:
                pass
            return res

        def _worker():
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=3) as ex:
                list(ex.map(_task, beyan_list))
            elapsed = time.time() - t_start
            def _done():
                self.btn_gtb_scan_now.config(text="🔄 Şimdi Tümünü Tara", state=tk.NORMAL)
                self.lbl_gtb_status.config(text="🤖 10 Dk Otonom İzleme Aktif", bg="#dcfce7", fg="#16a34a")
                self.refresh_gtb_takip_table()
                messagebox.showinfo("Tamamlandı", f"⚡ {len(beyan_list)} adet beyanname {elapsed:.1f} saniyede GTB üzerinden sorgulandı ve güncellendi!")
            self.root.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def copy_gtb_column(self, col_idx, col_title, only_selected=True):
        """GTB tablosunda belirtilen sütundaki değerleri alt alta kopyalar."""
        if only_selected:
            target_ids = list(self.tree_gtb.selection())
            scope_name = f"Seçili {len(target_ids)} adet"
        else:
            target_ids = list(self.tree_gtb.get_children())
            scope_name = f"Havuzdaki tüm ({len(target_ids)})"

        if not target_ids:
            self.show_warning("Uyarı", "Kopyalanacak satır bulunamadı.")
            return

        vals = []
        for s in target_ids:
            item_vals = self.tree_gtb.item(s, "values")
            if item_vals and len(item_vals) > col_idx:
                v = str(item_vals[col_idx] or "").strip()
                if v and v != "—":
                    vals.append(v)

        if not vals:
            self.show_warning("Uyarı", f"Bu sütunda geçerli {col_title} bulunamadı.")
            return

        text = "\n".join(vals)
        self.copy_to_clipboard(text)
        messagebox.showinfo(
            "Kopyalandı",
            f"📋 {scope_name} {col_title} alt alta panoya kopyalandı!\n\n(Excel'e veya arama alanına doğrudan yapıştırabilirsiniz)"
        )

    def copy_selected_gtb_rows_as_table(self):
        """Seçili GTB satırlarını Excel uyumlu tablo formatında panoya kopyalar."""
        selected_ids = list(self.tree_gtb.selection())
        if not selected_ids:
            self.show_warning("Uyarı", "Lütfen önce tablodan kopyalanacak satırları seçin.")
            return

        lines = ["Beyanname No\tDosya No\tReferans No\tFirma / Bayi\tGTB Bakanlık Canlı Durumu\tSon Kontrol\tDeğişim Zamanı"]
        for s in selected_ids:
            v = self.tree_gtb.item(s, "values")
            if v:
                lines.append("\t".join(str(x) for x in v))

        text = "\n".join(lines)
        self.copy_to_clipboard(text)
        messagebox.showinfo(
            "Kopyalandı",
            f"📋 Seçili {len(selected_ids)} satır Excel formatında panoya kopyalandı!\n\n(Excel'e doğrudan Ctrl+V ile yapıştırabilirsiniz)"
        )

    def copy_selected_gtb_numbers(self):
        self.copy_gtb_column(0, "Beyanname No", only_selected=True)

    def create_tax_mail_from_gtb(self):
        """
        GTB Takip tablosunda Ctrl/Shift+Tık ile seçili beyannameler için
        Vergi Talebi maili taslağını Outlook'ta açar.
        Seçili yoksa: Tüm havuzdaki aktif beyannameleri kullanır.
        """
        selected_ids = list(self.tree_gtb.selection())

        use_all = not selected_ids
        if use_all:
            all_items = self.tree_gtb.get_children()
            if not all_items:
                messagebox.showwarning("Uyarı", "GTB Takip havuzunda beyanname bulunamadı.\nÖnce beyanname ekleyin.")
                return
            selected_ids = list(all_items)

        gtb_rows = []
        for s in selected_ids:
            vals = self.tree_gtb.item(s, "values")
            if vals:
                gtb_rows.append({
                    "beyan_no": vals[0] if len(vals) > 0 else "",
                    "dosya_no": vals[1] if len(vals) > 1 else "",
                    "ref":      vals[2] if len(vals) > 2 else "",
                    "firma":    vals[3] if len(vals) > 3 else "",
                    "statu":    vals[4] if len(vals) > 4 else "",
                })

        if not gtb_rows:
            messagebox.showwarning("Uyarı", "Seçili satırlardan veri alınamadı.")
            return

        # Evrim kayıtlarından ref_no eşleşmesiyle dosya bilgisini zenginleştir
        evrim_lookup = {}
        try:
            all_evrim = getattr(self.app, "filtered_evrim_records", None) or getattr(self.app, "evrim_records", []) or []
            for er in all_evrim:
                ref_key = (er.get("hankook_ref") or "").strip().upper()
                dosya_key = (er.get("dosya_no") or "").strip().upper()
                if ref_key:   evrim_lookup[ref_key]   = er
                if dosya_key: evrim_lookup[dosya_key] = er
        except Exception:
            pass

        formatted_records = []
        for row in gtb_rows:
            ref   = row["ref"].strip()
            dosya = row["dosya_no"].strip()
            beyan = row["beyan_no"].strip()
            clean_b = re.sub(r"[^A-Z0-9]", "", beyan.upper())

            # Evrim'den zenginleştir
            ev = evrim_lookup.get(ref.upper()) or evrim_lookup.get(dosya.upper()) or evrim_lookup.get(clean_b) or {}
            if ev:
                ref   = (ev.get("hankook_ref") or ref).strip() or ref
                dosya = (ev.get("dosya_no") or dosya).strip() or dosya
                beyan = (ev.get("beyanname_no") or beyan).strip() or beyan

            formatted_records.append({
                "ref":       ref   or beyan,
                "dosya":     dosya or "—",
                "beyan_no":  beyan,
                "beyanname": beyan
            })

        sel_label = f"{len(formatted_records)} adet" if not use_all else f"tüm {len(formatted_records)} adet"
        self.set_header_subtitle(f"⏳ {sel_label} beyanname için Vergi Talebi taslağı Outlook'ta hazırlanıyor...")

        def _worker():
            if not self.engine or not hasattr(self.engine, "create_tax_mail_draft"):
                self.show_error("Hata", "Motor veya vergi maili oluşturucu bulunamadı.")
                return
            ok, msg = self.engine.create_tax_mail_draft(formatted_records)
            def _done():
                if ok:
                    self.set_header_subtitle(
                        f"✅ {sel_label} beyanname için Vergi Talebi taslağı Outlook'ta açıldı!",
                        fg="#16a34a"
                    )
                else:
                    self.set_header_subtitle("⚠️ Vergi maili taslağı oluşturulamadı.")
                    messagebox.showerror("Outlook Hatası", msg)
            self.root.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def remove_gtb_selected_rows(self):
        selected_ids = self.tree_gtb.selection()
        if not selected_ids or not self.gtb_tracker:
            return

        beyan_list = [self.tree_gtb.item(s, "values")[0] for s in selected_ids if self.tree_gtb.item(s, "values")]
        if not beyan_list:
            return

        msg = f"Seçili {len(beyan_list)} adet beyannameyi takip havuzundan çıkarmak istediğinize emin misiniz?" if len(beyan_list) > 1 else f"'{beyan_list[0]}' takip havuzundan çıkarılsın mı?"
        if messagebox.askyesno("Takipten Çıkar", msg):
            if hasattr(self.gtb_tracker, "remove_multiple_from_tracking"):
                self.gtb_tracker.remove_multiple_from_tracking(beyan_list)
            else:
                for b in beyan_list:
                    self.gtb_tracker.remove_from_tracking(b)
            self.refresh_gtb_takip_table()

    def clear_all_gtb_pool(self):
        tracked = self.gtb_tracker.list_tracked() if self.gtb_tracker else []
        if not tracked:
            messagebox.showinfo("Bilgi", "Takip havuzu zaten boş.")
            return

        if messagebox.askyesno("Tüm Havuzu Temizle", f"Takip havuzundaki TÜM {len(tracked)} beyannameyi silmek istediğinize emin misiniz?"):
            if hasattr(self.gtb_tracker, "clear_all_tracking"):
                self.gtb_tracker.clear_all_tracking()
            else:
                for r in tracked:
                    self.gtb_tracker.remove_from_tracking(r.get("beyanname_no"))
            self.refresh_gtb_takip_table()
            messagebox.showinfo("Temizlendi", "GTB takip havuzu tamamen temizlendi.")

    def show_gtb_add_dialog(self):
        """Kullanıcının tekli veya toplu alt alta beyanname ekleyebileceği modern modal pencere."""
        dlg = tk.Toplevel(self.root)
        dlg.title("➕ GTB Takip Havuzuna Beyanname Ekle")
        dlg.geometry("520x420")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        lbl_info = tk.Label(
            dlg, text="İzlemek istediğiniz 16 haneli Beyanname numaralarını veya\nreferansları alt alta yapıştırın:",
            font=("Segoe UI", 9), justify=tk.LEFT, padx=16, pady=12
        )
        lbl_info.pack(anchor="w")

        txt_input = tk.Text(dlg, font=("Consolas", 10), bd=1, relief=tk.SOLID, height=12, padx=8, pady=8)
        txt_input.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        btn_box = tk.Frame(dlg, padx=16, pady=12)
        btn_box.pack(fill=tk.X)

        # Evrim ve Excel Lookup Haritası
        lookup_map = {}
        try:
            pool = list(self.evrim_records) if self.evrim_records else []
            if self.engine and hasattr(self.engine, "records") and self.engine.records:
                for r in self.engine.records:
                    if not any(e.get("dosya_no") == r.get("dosya") for e in pool):
                        pool.append(r)
            for rec in pool:
                b_raw = rec.get("beyanname_no") or rec.get("gumruk_beyanname_no") or rec.get("beyan") or rec.get("beyanname")
                clean_b = re.sub(r"[^A-Z0-9]", "", str(b_raw or "").upper())
                if clean_b:
                    lookup_map[clean_b] = rec
        except Exception:
            pass

        def _do_add():
            if not self.gtb_tracker:
                self.show_error("Hata", "GTB takip servisi devrede değil.")
                return
            raw = txt_input.get("1.0", tk.END).strip()
            if not raw:
                messagebox.showwarning("Uyarı", "Lütfen en az bir beyanname numarası girin.")
                return

            lines = [l.strip() for l in re.split(r"[\n,;]+", raw) if l.strip()]
            added = 0
            updated = 0
            for line in lines:
                clean_no = re.sub(r"[^A-Z0-9]", "", line.upper())
                if len(clean_no) >= 10:
                    rec_match = lookup_map.get(clean_no, {})
                    dosya_no = rec_match.get("dosya_no") or rec_match.get("dosya") or "—"
                    ref_no = rec_match.get("hankook_ref") or rec_match.get("musteri_referans") or rec_match.get("ref") or "—"
                    firma = rec_match.get("yurt_disi_firma") or rec_match.get("bayi") or rec_match.get("firma") or "WH-HANKOOK"

                    res = self.gtb_tracker.add_to_tracking(clean_no, dosya_no=dosya_no, firma=firma, ref=ref_no)
                    if res.get("success"):
                        if res.get("created"):
                            added += 1
                        else:
                            updated += 1

            self.refresh_gtb_takip_table()
            dlg.destroy()
            if added > 0 or updated > 0:
                messagebox.showinfo("Başarılı", f"{added} yeni beyanname eklendi, {updated} mevcut kayıt güncellendi!")
            else:
                messagebox.showwarning("Uyarı", "Geçerli formatta (en az 10 haneli) beyanname numarası bulunamadı.")

        btn_save = tk.Button(
            btn_box, text="✅ Havuza Ekle ve Başlat", font=("Segoe UI", 9, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff",
            padx=14, pady=6, relief=tk.FLAT, cursor="hand2", command=_do_add
        )
        btn_save.pack(side=tk.RIGHT, padx=(6, 0))

        btn_cancel = tk.Button(
            btn_box, text="İptal", font=("Segoe UI", 9),
            bg="#e2e8f0", fg="#334155", padx=12, pady=6, relief=tk.FLAT, cursor="hand2", command=dlg.destroy
        )
        btn_cancel.pack(side=tk.RIGHT)

    def show_gtb_smart_import_dialog(self):
        """Tescil Tarihine Göre Akıllı İçe Aktarma Modalı."""
        dlg = tk.Toplevel(self.root)
        dlg.title("⚡ GTB Takip İçin Dosyaları İçe Aktar (Tescil Tarihine Göre)")
        dlg.geometry("740x640")
        dlg.minsize(680, 560)
        dlg.transient(self.root)
        dlg.grab_set()

        # 1. Tescil Tarihlerini Topla ve Grupla
        date_counts = {}
        all_candidates = []
        seen_beyan = set()

        pool_records = list(self.evrim_records) if self.evrim_records else []
        if self.engine and hasattr(self.engine, "records") and self.engine.records:
            for r in self.engine.records:
                if not any(e.get("dosya_no") == r.get("dosya") for e in pool_records):
                    pool_records.append(r)

        for rec in pool_records:
            b_no = rec.get("beyanname_no") or rec.get("gumruk_beyanname_no") or rec.get("beyan") or rec.get("beyanname")
            clean_b = re.sub(r"[^A-Z0-9]", "", str(b_no or "").upper())
            if clean_b and len(clean_b) >= 10:
                if clean_b in seen_beyan:
                    continue
                seen_beyan.add(clean_b)

                t_dt = (rec.get("beyanname_tarihi") or rec.get("tescil") or rec.get("tescil_tarihi") or "").strip()
                d_no = rec.get("dosya_no") or rec.get("dosya") or "—"
                ref_no = rec.get("hankook_ref") or rec.get("musteri_referans") or rec.get("ref") or "—"
                firma = rec.get("yurt_disi_firma") or rec.get("bayi") or rec.get("firma") or "WH-HANKOOK"
                statu = rec.get("statu") or rec.get("stage_title") or rec.get("stage") or ""
                is_closed = "kapan" in str(statu).lower() or "teslim" in str(statu).lower() or bool(rec.get("kapanis"))

                cand = {
                    "beyanname_no": clean_b,
                    "dosya_no": d_no,
                    "ref": ref_no,
                    "firma": firma,
                    "tescil": t_dt or "Tarih Yok",
                    "is_closed": is_closed
                }
                all_candidates.append(cand)
                k_date = t_dt or "Tarih Yok"
                date_counts[k_date] = date_counts.get(k_date, 0) + 1

        def _parse_date_sort_key(d_str: str):
            s = str(d_str or "").strip()
            if not s or s == "Tarih Yok":
                return (0, 0, 0)
            m_dmy = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", s)
            if m_dmy:
                return (int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))
            m_ymd = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", s)
            if m_ymd:
                return (int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3)))
            return (0, 0, 0)

        sorted_dates = sorted(date_counts.keys(), key=_parse_date_sort_key, reverse=True)
        all_candidates.sort(key=lambda c: _parse_date_sort_key(c.get("tescil", "")), reverse=True)

        # Başlık Paneli
        header_f = tk.Frame(dlg, bg="#0284c7", padx=16, pady=12)
        header_f.pack(fill=tk.X)
        tk.Label(
            header_f, text="⚡ Tescil Tarihine Göre Toplu İçe Aktarma",
            font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0284c7"
        ).pack(anchor="w")
        tk.Label(
            header_f,
            text="Evrim veya Excel'deki tescil almış beyannameleri tek tıkla GTB Takip havuzuna aktarın.",
            font=("Segoe UI", 8), fg="#e0f2fe", bg="#0284c7"
        ).pack(anchor="w")

        # Filtre Seçenekleri
        opt_frame = tk.LabelFrame(dlg, text=" Aktarma Kriteri Seçin ", font=("Segoe UI", 9, "bold"), padx=14, pady=10)
        opt_frame.pack(fill=tk.X, padx=16, pady=10)

        import_mode_var = tk.StringVar(value="BY_DATE" if sorted_dates else "ONLY_OPEN")

        # Radyo 1: Belirli Tarih
        r1_box = tk.Frame(opt_frame)
        r1_box.pack(fill=tk.X, pady=2)
        rb1 = ttk.Radiobutton(r1_box, text="📅 Belirli Bir Tescil Tarihindekiler:", variable=import_mode_var, value="BY_DATE")
        rb1.pack(side=tk.LEFT)

        date_options = [f"{d} ({date_counts[d]} Dosya)" for d in sorted_dates]
        cb_dates = ttk.Combobox(r1_box, values=date_options, state="readonly", width=28)
        if date_options:
            cb_dates.current(0)
        cb_dates.pack(side=tk.LEFT, padx=(10, 0))

        # Radyo 2: Sadece Açık Dosyalar
        r2_box = tk.Frame(opt_frame)
        r2_box.pack(fill=tk.X, pady=2)
        rb2 = ttk.Radiobutton(r2_box, text="🟡 Sadece Açık / Kapanmamış Olan Tüm Dosyalar", variable=import_mode_var, value="ONLY_OPEN")
        rb2.pack(side=tk.LEFT)

        # Radyo 3: Tüm Tescilliler
        r3_box = tk.Frame(opt_frame)
        r3_box.pack(fill=tk.X, pady=2)
        rb3 = ttk.Radiobutton(r3_box, text="🌐 Sistemdeki Tüm Tescilli Beyannameler", variable=import_mode_var, value="ALL")
        rb3.pack(side=tk.LEFT)

        # Alt Buton Paneli
        btn_bottom = tk.Frame(dlg, bg="#f1f5f9", padx=16, pady=12, relief=tk.FLAT, bd=0)
        btn_bottom.pack(side=tk.BOTTOM, fill=tk.X)

        lbl_summary_count = tk.Label(btn_bottom, text="0 Beyanname Seçildi", font=("Segoe UI", 10, "bold"), fg="#1e40af", bg="#f1f5f9")
        lbl_summary_count.pack(side=tk.LEFT)

        # Orta Önizleme Tablosu Üst Başlık & Hızlı Seçim Barı
        prev_head_bar = tk.Frame(dlg, padx=16)
        prev_head_bar.pack(fill=tk.X, pady=(8, 4))

        lbl_prev = tk.Label(prev_head_bar, text="📋 İçe Aktarılacak Eşleşen Beyanname Önizlemesi:", font=("Segoe UI", 9, "bold"))
        lbl_prev.pack(side=tk.LEFT)

        lbl_hint = tk.Label(prev_head_bar, text="(Ctrl veya Shift ile çoklu seçebilirsiniz)", font=("Segoe UI", 8), fg="#64748b")
        lbl_hint.pack(side=tk.LEFT, padx=(8, 0))

        btn_deselect_all = tk.Button(
            prev_head_bar, text="⚪ Seçimi Temizle", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#475569", relief=tk.GROOVE, padx=6, pady=1, cursor="hand2"
        )
        btn_deselect_all.pack(side=tk.RIGHT, padx=(4, 0))

        btn_select_all = tk.Button(
            prev_head_bar, text="🔘 Tümünü Seç (Ctrl+A)", font=("Segoe UI", 8, "bold"),
            bg="#e0f2fe", fg="#0369a1", relief=tk.GROOVE, padx=6, pady=1, cursor="hand2"
        )
        btn_select_all.pack(side=tk.RIGHT)

        prev_frame = tk.Frame(dlg, padx=16)
        prev_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        prev_cols = ("beyan", "dosya", "ref", "tescil", "firma")
        tree_prev = ttk.Treeview(prev_frame, columns=prev_cols, show="headings", height=9, selectmode="extended")

        tree_prev.heading("beyan", text="Beyanname No")
        tree_prev.heading("dosya", text="Dosya No")
        tree_prev.heading("ref", text="Referans")
        tree_prev.heading("tescil", text="Tescil Tarihi")
        tree_prev.heading("firma", text="Firma")

        tree_prev.column("beyan", width=180)
        tree_prev.column("dosya", width=100, anchor="center")
        tree_prev.column("ref", width=130, anchor="center")
        tree_prev.column("tescil", width=110, anchor="center")
        tree_prev.column("firma", width=140)

        sb_pv = ttk.Scrollbar(prev_frame, orient=tk.VERTICAL, command=tree_prev.yview)
        tree_prev.configure(yscrollcommand=sb_pv.set)
        sb_pv.pack(side=tk.RIGHT, fill=tk.Y)
        tree_prev.pack(fill=tk.BOTH, expand=True)

        current_filtered = []
        current_item_map = {}

        def _on_selection_changed(event=None):
            sel = tree_prev.selection()
            total = len(current_filtered)
            if sel:
                count_sel = len(sel)
                lbl_summary_count.config(text=f"🎯 {count_sel} / {total} Beyanname Seçildi (Seçilenler Aktarılacak)", fg="#15803d")
                btn_import_submit.config(
                    text=f"🚀 Seçilen {count_sel} Beyannameyi GTB Havuzuna Aktar",
                    bg="#0284c7"
                )
            else:
                lbl_summary_count.config(text=f"✅ Toplam {total} Adet Beyanname Aktarılacak (Tümü)", fg="#1e40af")
                btn_import_submit.config(
                    text=f"🚀 Listedeki Tüm ({total}) Beyannameleri Aktar",
                    bg="#334155"
                )

        def _do_execute_import():
            sel_iids = tree_prev.selection()
            if sel_iids:
                to_import = [current_item_map[iid] for iid in sel_iids if iid in current_item_map]
                import_type_msg = f"{len(to_import)} adet seçili beyanname"
            else:
                to_import = list(current_filtered)
                import_type_msg = f"Listedeki tüm {len(to_import)} adet beyanname"

            if not to_import:
                messagebox.showwarning("Uyarı", "Aktarılacak beyanname bulunamadı.")
                return

            if not self.gtb_tracker:
                self.show_error("Hata", "GTB takip servisi aktif değil.")
                return

            added = 0
            updated = 0
            for item in to_import:
                res = self.gtb_tracker.add_to_tracking(
                    item["beyanname_no"],
                    dosya_no=item["dosya_no"],
                    firma=item["firma"],
                    ref=item["ref"]
                )
                if res.get("success"):
                    if res.get("created"):
                        added += 1
                    else:
                        updated += 1

            self.refresh_gtb_takip_table()
            dlg.destroy()
            messagebox.showinfo("Başarılı", f"{import_type_msg} incelendi:\n• {added} yeni beyanname eklendi\n• {updated} mevcut kayıt güncellendi!")

        btn_import_submit = tk.Button(
            btn_bottom, text="🚀 Seçilen Beyannameleri GTB Havuzuna Aktar", font=("Segoe UI", 10, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff",
            padx=18, pady=8, relief=tk.FLAT, cursor="hand2", command=_do_execute_import
        )
        btn_import_submit.pack(side=tk.RIGHT, padx=(8, 0))

        btn_close = tk.Button(
            btn_bottom, text="Vazgeç", font=("Segoe UI", 9),
            bg="#e2e8f0", fg="#334155", padx=14, pady=8, relief=tk.FLAT, cursor="hand2", command=dlg.destroy
        )
        btn_close.pack(side=tk.RIGHT)

        def _select_all(event=None):
            tree_prev.selection_set(tree_prev.get_children())
            _on_selection_changed()
            return "break"

        def _deselect_all(event=None):
            tree_prev.selection_remove(tree_prev.selection())
            _on_selection_changed()
            return "break"

        btn_select_all.config(command=_select_all)
        btn_deselect_all.config(command=_deselect_all)
        tree_prev.bind("<<TreeviewSelect>>", _on_selection_changed)
        dlg.bind("<Control-a>", _select_all)
        dlg.bind("<Control-A>", _select_all)
        dlg.bind("<Escape>", _deselect_all)

        def _update_preview(*args):
            nonlocal current_filtered, current_item_map
            mode = import_mode_var.get()
            selected_date_str = cb_dates.get().split(" (")[0] if cb_dates.get() else ""

            filtered = []
            for item in all_candidates:
                if mode == "BY_DATE":
                    if item["tescil"] == selected_date_str:
                        filtered.append(item)
                elif mode == "ONLY_OPEN":
                    if not item["is_closed"]:
                        filtered.append(item)
                elif mode == "ALL":
                    filtered.append(item)

            current_filtered = filtered
            current_item_map = {}

            for r in tree_prev.get_children():
                tree_prev.delete(r)

            for idx, f in enumerate(filtered):
                iid = f"cand_{idx}_{f['beyanname_no']}"
                current_item_map[iid] = f
                tree_prev.insert("", tk.END, iid=iid, values=(f["beyanname_no"], f["dosya_no"], f["ref"], f["tescil"], f["firma"]))

            _on_selection_changed()
            return filtered

        rb1.config(command=_update_preview)
        rb2.config(command=_update_preview)
        rb3.config(command=_update_preview)
        cb_dates.bind("<<ComboboxSelected>>", _update_preview)

        _update_preview()

    def run_gtb_scan_now(self):
        """Kullanıcı butona bastığında arka planda anlık tüm listeyi yüksek hızla (paralel) tarar ve canlı ilerleme gösterir."""
        if not self.gtb_tracker:
            self.show_warning("GTB Servisi", "GTB takip servisi aktif değil.")
            return

        if getattr(self.gtb_tracker, "is_scanning", False):
            messagebox.showwarning("Tarama Sürüyor", "GTB taraması şu anda devam ediyor, lütfen bekleyin.")
            return

        active_list = self.gtb_tracker.list_tracked(only_active=True)
        if not active_list:
            messagebox.showinfo("Bilgi", "GTB takip havuzunda taranacak aktif beyanname bulunamadı.\nÖnce beyanname ekleyin.")
            return

        self.btn_gtb_scan_now.config(text="⏳ Taranıyor (Paralel)...", state=tk.DISABLED)
        self.lbl_gtb_status.config(text=f"🔄 GTB Canlı Taraması Başlatıldı ({len(active_list)} Beyanname)...", bg="#fef3c7", fg="#92400e")

        t_start = time.time()

        def _on_progress(cur, tot, b_no, res):
            st = res.get("durum", "")[:30] if res.get("success") else res.get("error", "")[:30]
            def _ui_update():
                self.lbl_gtb_status.config(text=f"🔄 Taranıyor [{cur}/{tot}]: {b_no} ({st})", bg="#fef3c7", fg="#92400e")
                self.refresh_gtb_takip_table()
            try:
                self.root.after(0, _ui_update)
            except Exception:
                pass

        def _worker():
            try:
                res = self.gtb_tracker.run_full_cycle(on_progress_callback=_on_progress)
                elapsed = time.time() - t_start
                def _done():
                    self.btn_gtb_scan_now.config(text="🔄 Şimdi Tümünü Tara", state=tk.NORMAL)
                    now_str = datetime.now().strftime("%H:%M:%S")
                    self.lbl_gtb_status.config(
                        text=f"✅ Son Tarama: {now_str} ({elapsed:.1f} sn - 10 Dk Otonom Aktif)",
                        bg="#dcfce7", fg="#16a34a"
                    )
                    self.refresh_gtb_takip_table()
                    tot = res.get("total_checked", 0) if isinstance(res, dict) else 0
                    chg = res.get("changed_count", 0) if isinstance(res, dict) else 0
                    messagebox.showinfo("Tarama Tamamlandı", f"⚡ {tot} beyanname {elapsed:.1f} saniyede GTB üzerinden sorgulandı.\nDeğişen statü: {chg} adet.")
                self.root.after(0, _done)
            except Exception as e:
                def _err():
                    self.btn_gtb_scan_now.config(text="🔄 Şimdi Tümünü Tara", state=tk.NORMAL)
                    self.lbl_gtb_status.config(text="⚠️ Tarama Hatası", bg="#fee2e2", fg="#991b1b")
                    messagebox.showerror("Tarama Hatası", f"GTB tarama sırasında bir hata oluştu:\n{e}")
                self.root.after(0, _err)

        threading.Thread(target=_worker, daemon=True).start()

