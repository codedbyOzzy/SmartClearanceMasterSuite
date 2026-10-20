# -*- coding: utf-8 -*-
"""
kantar_view.py — DP World & Körfez Kantar / DBA Takip Görünümü
MasterSuite için DP World & Körfez Kantar/DBA tablosu, tike PDF indirme, filtreler, manuel sorgu.
"""
import os
import sys
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .base_view import BaseView


class KantarView(BaseView):
    """DP World & Körfez Kantar / DBA Takip Sekmesi."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.current_kantar_filter = "ALL"
        self.setup_ui()

    @property
    def kantar_tracker(self):
        return getattr(self.app, "kantar_tracker", None)

    def setup_ui(self):
        # 1. Metrik Barı
        metric_bar = tk.Frame(self, bg="#f8fafc")
        metric_bar.pack(fill=tk.X, pady=(0, 10))

        self.card_k_total = self.create_metric_widget(
            metric_bar, "İZLENEN KONTEYNERLER", "0", "Otonom Havuzda", "#0f172a",
            lambda: self.filter_kantar_table("ALL")
        )
        self.card_k_ready = self.create_metric_widget(
            metric_bar, "TARTIM HAZIR (TİKE VAR)", "0", "PDF İndirilebilir", "#16a34a",
            lambda: self.filter_kantar_table("READY")
        )
        self.card_k_pending = self.create_metric_widget(
            metric_bar, "TARTIM BEKLİYOR", "0", "Liman / Sahada", "#d97706",
            lambda: self.filter_kantar_table("PENDING")
        )
        self.card_k_last_scan = self.create_metric_widget(
            metric_bar, "SON OTONOM TARAMA", "—", "10 Dk Döngü", "#2563eb", None
        )

        # 2. Kontrol Çubuğu & Butonlar
        ctrl_bar = tk.Frame(self, bg="#ffffff", padx=12, pady=10, relief=tk.FLAT, bd=0)
        ctrl_bar.pack(fill=tk.X, pady=(0, 10))

        # Sol Arama
        lbl_s = tk.Label(ctrl_bar, text="🔍 Ara / Filtrele:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_s.pack(side=tk.LEFT, padx=(0, 6))

        self.txt_kantar_search = tk.Entry(ctrl_bar, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, width=20)
        self.txt_kantar_search.pack(side=tk.LEFT, padx=(0, 8), ipady=3)
        self.txt_kantar_search.bind("<KeyRelease>", lambda e: self.refresh_kantar_takip_table())

        # Aksiyon Butonları
        self.btn_kantar_add = tk.Button(
            ctrl_bar, text="➕ Konteyner Ekle", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.show_kantar_add_dialog
        )
        self.btn_kantar_add.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_kantar_sync = tk.Button(
            ctrl_bar, text="⚡ Evrim/Excel'den Aktar", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.auto_sync_kantar_from_evrim
        )
        self.btn_kantar_sync.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_kantar_scan_now = tk.Button(
            ctrl_bar, text="🔄 Şimdi Tümünü Tara", font=("Segoe UI", 9, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.run_kantar_scan_now
        )
        self.btn_kantar_scan_now.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_yilport_login = tk.Button(
            ctrl_bar, text="🌐 Yılport Oturumu Aç", font=("Segoe UI", 9, "bold"),
            bg="#6b21a8", fg="#ffffff", activebackground="#581c87", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.launch_yilport_auth_helper
        )
        self.btn_yilport_login.pack(side=tk.LEFT, padx=(0, 6))

        btn_open_pdf = tk.Button(
            ctrl_bar, text="📥 Seçili Kantar PDF'ini Aç / İndir", font=("Segoe UI", 9, "bold"),
            bg="#7c3aed", fg="#ffffff", activebackground="#6d28d9", activeforeground="#ffffff",
            relief=tk.FLAT, padx=12, pady=4, cursor="hand2", command=self.download_and_open_selected_kantar_pdf
        )
        btn_open_pdf.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_kantar_clear = tk.Button(
            ctrl_bar, text="🗑️ Temizle", font=("Segoe UI", 9),
            bg="#f1f5f9", fg="#dc2626", activebackground="#fee2e2", activeforeground="#991b1b",
            relief=tk.FLAT, bd=0, padx=8, pady=3, cursor="hand2", command=self.clear_all_kantar_pool
        )
        self.btn_kantar_clear.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_kantar_merge_pdf = tk.Button(
            ctrl_bar, text="📦 Tike PDF'lerini Birleştir", font=("Segoe UI", 9, "bold"),
            bg="#0f766e", fg="#ffffff", activebackground="#0d6b63", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.merge_and_download_kantar_pdfs
        )
        self.btn_kantar_merge_pdf.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_kantar_status = tk.Label(
            ctrl_bar, text="🤖 10 Dk Otonom İzleme Aktif",
            font=("Segoe UI", 8, "bold"), fg="#16a34a", bg="#dcfce7", padx=8, pady=4
        )
        self.lbl_kantar_status.pack(side=tk.RIGHT)

        # 3. Tablo
        table_frame = tk.Frame(self, bg="#ffffff", relief=tk.FLAT, bd=0)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("cntr_no", "dosya_no", "kaynak", "tartim_no", "tarih", "plaka", "firma", "dba", "durum", "son_kontrol")
        self.tree_kantar = ttk.Treeview(table_frame, columns=cols, show="headings", height=16, selectmode="extended")

        self.tree_kantar.heading("cntr_no", text="Konteyner No")
        self.tree_kantar.heading("dosya_no", text="Dosya No")
        self.tree_kantar.heading("kaynak", text="Liman / Kaynak")
        self.tree_kantar.heading("tartim_no", text="Tartım No")
        self.tree_kantar.heading("tarih", text="Tartım Tarihi")
        self.tree_kantar.heading("plaka", text="Çekici Plaka")
        self.tree_kantar.heading("firma", text="Firma / Bayi")
        self.tree_kantar.heading("dba", text="DBA (VGM) / Dara")
        self.tree_kantar.heading("durum", text="Kantar Tikesi Durumu")
        self.tree_kantar.heading("son_kontrol", text="Son Kontrol")

        self.tree_kantar.column("cntr_no", width=130, anchor="w")
        self.tree_kantar.column("dosya_no", width=110, anchor="center")
        self.tree_kantar.column("kaynak", width=95, anchor="center")
        self.tree_kantar.column("tartim_no", width=100, anchor="center")
        self.tree_kantar.column("tarih", width=110, anchor="center")
        self.tree_kantar.column("plaka", width=100, anchor="center")
        self.tree_kantar.column("firma", width=130, anchor="w")
        self.tree_kantar.column("dba", width=100, anchor="center")
        self.tree_kantar.column("durum", width=140, anchor="w")
        self.tree_kantar.column("son_kontrol", width=110, anchor="center")

        sb_k = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree_kantar.yview)
        self.tree_kantar.configure(yscrollcommand=sb_k.set)
        sb_k.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_kantar.pack(fill=tk.BOTH, expand=True)

        self.tree_kantar.tag_configure("hazir", background="#f0fdf4", foreground="#166534")
        self.tree_kantar.tag_configure("bekliyor", background="#fffbeb", foreground="#92400e")

        self.tree_kantar.bind("<Control-a>", lambda e: self.select_all_kantar_rows())
        self.tree_kantar.bind("<Control-A>", lambda e: self.select_all_kantar_rows())
        self.tree_kantar.bind("<Double-1>", lambda e: self.download_and_open_selected_kantar_pdf())
        self.tree_kantar.bind("<Button-3>", lambda e: self.show_kantar_context_menu(e))

    def select_all_kantar_rows(self):
        all_i = self.tree_kantar.get_children()
        if all_i:
            self.tree_kantar.selection_set(all_i)
        return "break"

    def filter_kantar_table(self, filter_type):
        self.current_kantar_filter = filter_type
        self.refresh_kantar_takip_table()

    def refresh_kantar_takip_table(self):
        """Kantar Takip tablosunu tracker verileriyle günceller."""
        if not hasattr(self, "tree_kantar") or not self.kantar_tracker:
            return
        try:
            if not self.tree_kantar.winfo_exists():
                return
        except Exception:
            return

        for r in self.tree_kantar.get_children():
            self.tree_kantar.delete(r)

        tracked = self.kantar_tracker.list_tracked(only_active=True)
        search_q = self.txt_kantar_search.get().strip().upper() if hasattr(self, "txt_kantar_search") else ""

        ready_cnt = 0
        pending_cnt = 0
        displayed_cnt = 0

        for item in tracked:
            c_no = item.get("konteyner_no", "")
            dosya_no = item.get("dosya_no")
            if not dosya_no or str(dosya_no).strip() in ("—", "-", "None", ""):
                if hasattr(self.kantar_tracker, "_find_dosya_no_from_excel"):
                    found = self.kantar_tracker._find_dosya_no_from_excel(c_no)
                    if found:
                        dosya_no = found
                        item["dosya_no"] = found
                if (not dosya_no or str(dosya_no).strip() in ("—", "-", "None", "")) and hasattr(self.app, "engine") and hasattr(self.app.engine, "records"):
                    c_clean = c_no.strip().upper()
                    for rec in (self.app.engine.records or []):
                        raw = str(rec.get("konteyner") or "").upper()
                        parts = [p.strip() for p in raw.replace(",", " ").split()]
                        if c_clean in parts:
                            dosya_no = str(rec.get("dosya") or "").strip()
                            item["dosya_no"] = dosya_no
                            break
            if not dosya_no:
                dosya_no = "—"

            kaynak = item.get("kaynak", "Liman").capitalize()
            t_no = item.get("tartim_no", "—")
            t_dt = item.get("tarih", "—")
            plaka = item.get("plaka", "—")
            firma = item.get("firma", "—")
            dba = item.get("dba", "—")
            durum = item.get("durum", "⏳ Tartım Bekliyor")
            t_val = str(item.get("tartim_no") or "").strip()
            dba_val = str(item.get("dba") or "").strip()
            has_t = bool(t_val) and t_val not in ("—", "-", "None", "")
            has_dba = bool(dba_val) and dba_val not in ("—", "-", "None", "")
            hazir = bool(item.get("hazir")) or "hazır" in durum.lower() or has_t or has_dba
            son_chk = self.format_check_time(item.get("son_kontrol") or item.get("updated_at") or "—")

            if hazir:
                ready_cnt += 1
            else:
                pending_cnt += 1

            if self.current_kantar_filter == "READY" and not hazir:
                continue
            elif self.current_kantar_filter == "PENDING" and hazir:
                continue

            if search_q:
                haystack = f"{c_no} {dosya_no} {t_no} {plaka} {firma} {dba} {kaynak}".upper()
                if search_q not in haystack:
                    continue

            tag = "hazir" if hazir else "bekliyor"
            self.tree_kantar.insert("", tk.END, values=(c_no, dosya_no, kaynak, t_no, t_dt, plaka, firma, dba, durum, son_chk), tags=(tag,))
            displayed_cnt += 1

        if hasattr(self, "card_k_total"):
            self.card_k_total["val_lbl"].config(text=str(len(tracked)))
            self.card_k_ready["val_lbl"].config(text=str(ready_cnt))
            self.card_k_pending["val_lbl"].config(text=str(pending_cnt))
            last_scan = getattr(self.kantar_tracker, "last_scan_time", "—")
            scan_t = last_scan.split(" ")[-1] if " " in str(last_scan) else str(last_scan)
            self.card_k_last_scan["val_lbl"].config(text=scan_t)

            # Aktif Filtre Görsel Vurgusu
            self.card_k_total["card"].config(bg="#f1f5f9" if self.current_kantar_filter == "ALL" else "#ffffff")
            self.card_k_ready["card"].config(bg="#dcfce7" if self.current_kantar_filter == "READY" else "#ffffff")
            self.card_k_pending["card"].config(bg="#fef3c7" if self.current_kantar_filter == "PENDING" else "#ffffff")

        # Filtre durumu rozeti
        if hasattr(self, "lbl_kantar_status"):
            if self.current_kantar_filter == "READY":
                self.lbl_kantar_status.config(text=f"🟢 Filtre: Tartımı Hazır ({displayed_cnt}/{len(tracked)})", bg="#dcfce7", fg="#166534")
            elif self.current_kantar_filter == "PENDING":
                self.lbl_kantar_status.config(text=f"🟡 Filtre: Tartım Bekleyen ({displayed_cnt}/{len(tracked)})", bg="#fef3c7", fg="#92400e")
            else:
                self.lbl_kantar_status.config(text=f"🤖 10 Dk Otonom İzleme Aktif ({displayed_cnt} Konteyner)", bg="#dcfce7", fg="#16a34a")

    def refresh_table(self):
        self.refresh_kantar_takip_table()

    def on_kantar_status_changed(self):
        try:
            self.root.after(0, self.refresh_kantar_takip_table)
        except Exception:
            pass

    def show_kantar_context_menu(self, event):
        item_id = self.tree_kantar.identify_row(event.y)
        selected_ids = list(self.tree_kantar.selection())
        if item_id and item_id not in selected_ids:
            self.tree_kantar.selection_set(item_id)
            selected_ids = [item_id]

        if not selected_ids:
            return

        menu = tk.Menu(self.root, tearoff=0)
        sel_count = len(selected_ids)

        if sel_count == 1:
            vals = self.tree_kantar.item(selected_ids[0], "values")
            c_no = vals[0] if vals else ""
            d_no = vals[1] if (vals and len(vals) > 1) else ""
            menu.add_command(label=f"📄 Kantar Tikesi PDF'ini Aç / İndir: {c_no}", command=self.download_and_open_selected_kantar_pdf)
            menu.add_command(label=f"🔍 Şimdi Canlı Tartım Sorgula: {c_no}", command=lambda: self.query_selected_kantar_row(c_no))
            menu.add_command(label="📋 Konteyner No Kopyala", command=lambda: self.copy_to_clipboard(c_no, show_msg=True))
            if d_no and d_no not in ("—", "-", "None", ""):
                menu.add_command(label=f"📋 Dosya No Kopyala ({d_no})", command=lambda: self.copy_to_clipboard(d_no, show_msg=True))
            menu.add_separator()
            menu.add_command(label="❌ Takipten Çıkar", command=self.remove_kantar_selected_rows)
        else:
            menu.add_command(label=f"🔍 Seçili ({sel_count}) Konteyneri Canlı Sorgula", command=self.query_multiple_kantar_rows)
            menu.add_command(label=f"📦 Seçili ({sel_count}) Tike PDF'ini Birleştir & İndir", command=self.merge_and_download_kantar_pdfs)
            menu.add_command(label=f"📋 Seçili ({sel_count}) Konteyner Numaralarını Kopyala", command=self.copy_selected_kantar_numbers)
            menu.add_separator()
            menu.add_command(label=f"❌ Seçili ({sel_count}) Konteyneri Takipten Çıkar", command=self.remove_kantar_selected_rows)

        menu.add_separator()
        menu.add_command(label="🗑️ Tüm Kantar Havuzunu Temizle", command=self.clear_all_kantar_pool)
        menu.tk_popup(event.x_root, event.y_root)

    def download_and_open_selected_kantar_pdf(self):
        sel = self.tree_kantar.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen PDF tikesini açmak istediğiniz bir konteyner seçin.")
            return

        vals = self.tree_kantar.item(sel[0], "values")
        c_no = vals[0] if vals else ""
        if not c_no:
            return

        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return

        def _worker():
            fn = getattr(self.kantar_tracker, "download_and_get_pdf", None) or getattr(self.kantar_tracker, "download_pdf_tike", None)
            pdf_path = fn(c_no) if fn else None
            def _done():
                self.refresh_kantar_takip_table()
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.startfile(pdf_path)
                    except Exception as e:
                        messagebox.showinfo("PDF İndirildi", f"Kantar tikesi başarıyla indirildi:\n{pdf_path}")
                else:
                    messagebox.showwarning("Tike Bulunamadı", f"'{c_no}' konteyneri için henüz bir kantar tikesi veya PDF oluşturulmamış.\nLiman tartımının tamamlanması bekleniyor.")
            self.root.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def query_selected_kantar_row(self, cntr_no):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return

        def _worker():
            res = self.kantar_tracker.query_single_now(cntr_no)
            def _done():
                self.refresh_kantar_takip_table()
                if res.get("success"):
                    hazir = res.get("hazir")
                    msg = f"📦 Konteyner: {cntr_no}\n"
                    msg += f"📊 Durum: {'🟢 Tartım Hazır' if hazir else '⏳ Tartım Bekliyor'}\n"
                    msg += f"🧾 Tartım No: {res.get('tartim_no') or '—'}\n"
                    msg += f"📅 Tarih: {res.get('tarih') or '—'}\n"
                    msg += f"🚛 Plaka: {res.get('plaka') or '—'}\n"
                    msg += f"⚖️ DBA (VGM): {res.get('dba') or '—'}\n"
                    messagebox.showinfo("DP World & Körfez Kantar Sonucu", msg)
                else:
                    messagebox.showerror("Hata", f"Kantar sorgulanamadı:\n{res.get('error')}")
            self.root.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def query_multiple_kantar_rows(self):
        sel = self.tree_kantar.selection()
        if not sel or not self.kantar_tracker:
            return
        cntrs = [self.tree_kantar.item(s, "values")[0] for s in sel if self.tree_kantar.item(s, "values")]
        if not cntrs:
            return

        self.btn_kantar_scan_now.config(text=f"⏳ {len(cntrs)} Taranıyor...", state=tk.DISABLED)
        self.lbl_kantar_status.config(text=f"🔄 Seçili {len(cntrs)} Konteyner Taranıyor...", bg="#fef3c7", fg="#92400e")

        def _worker():
            for c in cntrs:
                self.kantar_tracker.query_single_now(c)
                time.sleep(0.8)
            def _done():
                self.btn_kantar_scan_now.config(text="🔄 Şimdi Tümünü Tara", state=tk.NORMAL)
                self.lbl_kantar_status.config(text="🤖 10 Dk Otonom İzleme Aktif", bg="#dcfce7", fg="#16a34a")
                self.refresh_kantar_takip_table()
                messagebox.showinfo("Tamamlandı", f"{len(cntrs)} adet konteyner kantar sistemlerinde sorgulandı ve güncellendi!")
            self.root.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def copy_selected_kantar_numbers(self):
        sel = self.tree_kantar.selection()
        cntrs = [self.tree_kantar.item(s, "values")[0] for s in sel if self.tree_kantar.item(s, "values")]
        if cntrs:
            self.copy_to_clipboard("\n".join(cntrs))
            messagebox.showinfo("Kopyalandı", f"{len(cntrs)} adet konteyner numarası panoya kopyalandı!")

    def remove_kantar_selected_rows(self):
        sel = self.tree_kantar.selection()
        if not sel or not self.kantar_tracker:
            return
        cntrs = [self.tree_kantar.item(s, "values")[0] for s in sel if self.tree_kantar.item(s, "values")]
        if not cntrs:
            return

        msg = f"Seçili {len(cntrs)} adet konteyner kantar takibinden çıkarılsın mı?" if len(cntrs) > 1 else f"'{cntrs[0]}' takipten çıkarılsın mı?"
        if messagebox.askyesno("Takipten Çıkar", msg):
            self.kantar_tracker.remove_multiple_from_tracking(cntrs)
            self.refresh_kantar_takip_table()

    def clear_all_kantar_pool(self):
        if not self.kantar_tracker:
            return
        tracked = self.kantar_tracker.list_tracked()
        if not tracked:
            messagebox.showinfo("Bilgi", "Kantar takip havuzu zaten boş.")
            return

        if messagebox.askyesno("Havuzu Temizle", f"Tüm kantar takip havuzundaki ({len(tracked)} konteyner) sıfırlamak istediğinize emin misiniz?"):
            self.kantar_tracker.clear_all_tracking()
            self.refresh_kantar_takip_table()
            messagebox.showinfo("Temizlendi", "Kantar takip havuzu tamamen temizlendi.")

    def show_kantar_add_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("➕ Kantar Takip Havuzuna Konteyner Ekle")
        dlg.geometry("520x420")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        lbl_info = tk.Label(
            dlg, text="İzlemek istediğiniz Konteyner numaralarını alt alta yapıştırın:",
            font=("Segoe UI", 9), padx=16, pady=12
        )
        lbl_info.pack(anchor="w")

        txt_input = tk.Text(dlg, font=("Consolas", 10), bd=1, relief=tk.SOLID, height=12, padx=8, pady=8)
        txt_input.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        btn_box = tk.Frame(dlg, padx=16, pady=12)
        btn_box.pack(fill=tk.X)

        # Evrim ve Excel Lookup
        cntr_lookup = {}
        try:
            pool = list(self.evrim_records) if self.evrim_records else []
            if self.engine and hasattr(self.engine, "records") and self.engine.records:
                for r in self.engine.records:
                    if not any(e.get("dosya_no") == r.get("dosya") for e in pool):
                        pool.append(r)
            for rec in pool:
                c_raw = rec.get("konteyner") or rec.get("konteyner_no") or rec.get("cntr") or ""
                if isinstance(c_raw, str):
                    for part in re.split(r"[\s,;+/]+", c_raw):
                        c_clean = re.sub(r"[^A-Z0-9]", "", part.upper())
                        if len(c_clean) >= 4:
                            cntr_lookup[c_clean] = rec
        except Exception:
            pass

        def _do_add():
            if not self.kantar_tracker:
                self.show_error("Hata", "Kantar takip servisi devrede değil.")
                return
            raw = txt_input.get("1.0", tk.END).strip()
            if not raw:
                messagebox.showwarning("Uyarı", "Lütfen en az bir konteyner numarası girin.")
                return

            lines = [l.strip() for l in re.split(r"[\n,;]+", raw) if l.strip()]
            added = 0
            updated = 0
            for line in lines:
                clean_no = re.sub(r"[^A-Z0-9]", "", line.upper())
                if len(clean_no) >= 4:
                    rec_match = cntr_lookup.get(clean_no, {})
                    dosya = rec_match.get("dosya_no") or rec_match.get("dosya") or "—"
                    ref = rec_match.get("hankook_ref") or rec_match.get("musteri_referans") or rec_match.get("ref") or "—"
                    firma = rec_match.get("yurt_disi_firma") or rec_match.get("bayi") or rec_match.get("firma") or "WH-HANKOOK"

                    res = self.kantar_tracker.add_to_tracking(clean_no, dosya_no=dosya, ref=ref, firma=firma, kaynak="otomatik")
                    if res.get("success"):
                        if res.get("created"):
                            added += 1
                        else:
                            updated += 1

            self.refresh_kantar_takip_table()
            dlg.destroy()
            if added > 0 or updated > 0:
                messagebox.showinfo("Başarılı", f"{added} yeni konteyner eklendi, {updated} mevcut kayıt güncellendi!")
            else:
                messagebox.showwarning("Uyarı", "Geçerli formatta (en az 4 haneli) konteyner numarası bulunamadı.")

        btn_save = tk.Button(
            btn_box, text="✅ Havuza Ekle ve Başlat", font=("Segoe UI", 9, "bold"),
            bg="#334155", fg="#ffffff", padx=14, pady=6, relief=tk.FLAT, cursor="hand2", command=_do_add
        )
        btn_save.pack(side=tk.RIGHT, padx=(6, 0))

        btn_cancel = tk.Button(
            btn_box, text="İptal", font=("Segoe UI", 9),
            bg="#e2e8f0", fg="#334155", padx=12, pady=6, relief=tk.FLAT, cursor="hand2", command=dlg.destroy
        )
        btn_cancel.pack(side=tk.RIGHT)

    def auto_sync_kantar_from_evrim(self):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return
        if self.engine and not getattr(self.engine, "records", None):
            if hasattr(self.engine, "fetch_excel_records"):
                self.engine.fetch_excel_records()

        evrim_recs = self.evrim_records
        engine_recs = getattr(self.engine, "records", []) if self.engine else []
        cnt = self.kantar_tracker.auto_sync_from_evrim_and_excel(evrim_recs, engine_recs)
        self.refresh_kantar_takip_table()
        messagebox.showinfo("Kantar Senkronizasyonu", f"Excel U Sütunu ve Evrim'den {cnt} yeni konteyner Kantar takip havuzuna aktarıldı!")

    def launch_yilport_auth_helper(self):
        """Yılport reCAPTCHA doğrulama penceresini açar ve çerezleri kaydeder."""
        helper_path = os.path.join(os.path.dirname(__file__), "..", "..", "kantar_engine", "yilport_session_helper.py")
        helper_path = os.path.abspath(helper_path)
        if not os.path.exists(helper_path):
            messagebox.showerror("Hata", "Yılport oturum yardımcısı bulunamadı.")
            return

        import subprocess
        def _run():
            try:
                proc = subprocess.run([sys.executable, helper_path], capture_output=True, text=True, timeout=180)
                if proc.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Yılport Oturumu", "✅ Yılport oturumu başarıyla doğrulandı! Tarama başlatılıyor..."))
                    self.after(500, self.run_kantar_scan_now)
                else:
                    self.after(0, lambda: messagebox.showwarning("Yılport Oturumu", "Doğrulama tamamlanamadı."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Yılport Hatası", str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def run_kantar_scan_now(self):
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return
        if getattr(self.kantar_tracker, "is_scanning", False):
            messagebox.showwarning("Tarama Sürüyor", "Kantar taraması şu anda devam ediyor, lütfen bekleyin.")
            return

        active_list = self.kantar_tracker.list_tracked(only_active=True)
        if not active_list:
            messagebox.showinfo("Bilgi", "Kantar takip havuzunda taranacak aktif konteyner bulunamadı.\nÖnce konteyner ekleyin veya Evrim'den aktarın.")
            return

        self.btn_kantar_scan_now.config(text="⏳ Taranıyor...", state=tk.DISABLED)
        self.lbl_kantar_status.config(text=f"🔄 Canlı Kantar Taraması Yapılıyor ({len(active_list)} Konteyner)...", bg="#fef3c7", fg="#92400e")

        def _worker():
            try:
                res = self.kantar_tracker.run_full_cycle()
                def _done():
                    self.btn_kantar_scan_now.config(text="🔄 Şimdi Tümünü Tara", state=tk.NORMAL)
                    self.lbl_kantar_status.config(text="🤖 10 Dk Otonom İzleme Aktif", bg="#dcfce7", fg="#16a34a")
                    self.refresh_kantar_takip_table()
                    tot = res.get("total_checked", 0) if isinstance(res, dict) else 0
                    chg = res.get("changed_count", 0) if isinstance(res, dict) else 0
                    messagebox.showinfo("Tarama Tamamlandı", f"{tot} konteyner kantar portallarında sorgulandı.\nHazır olan yeni tike: {chg} adet.")
                self.root.after(0, _done)
            except Exception as e:
                def _err():
                    self.btn_kantar_scan_now.config(text="🔄 Şimdi Tümünü Tara", state=tk.NORMAL)
                    self.lbl_kantar_status.config(text="⚠️ Tarama Hatası", bg="#fee2e2", fg="#991b1b")
                    messagebox.showerror("Tarama Hatası", f"Kantar tarama hatası:\n{e}")
                self.root.after(0, _err)

        threading.Thread(target=_worker, daemon=True).start()

    def merge_and_download_kantar_pdfs(self):
        """Hazır tike PDF'lerini birleştirerek tek dosya olarak kaydeder.

        Tabloda seçili satırlar varsa sadece onları; seçim yoksa tüm hazır
        konteynerleri (tabloda göründüğü sırayla) birleştirir.
        """
        if not self.kantar_tracker:
            self.show_warning("Kantar Servisi", "Kantar takip servisi aktif değil.")
            return

        # Seçili konteynerler var mı?
        sel = self.tree_kantar.selection()
        if sel:
            cntr_list = [
                self.tree_kantar.item(s, "values")[0]
                for s in sel
                if self.tree_kantar.item(s, "values")
            ]
            baslik_ek = f" ({len(cntr_list)} Seçili)"
        else:
            cntr_list = None  # Tümü (sadece hazır olanlar)
            baslik_ek = " (Tüm Hazır)"

        # Hazır PDF sayısını hızlıca kontrol et
        tracked = self.kantar_tracker.list_tracked(only_active=True)
        if cntr_list is not None:
            c_set = set(cntr_list)
            ready_recs = [r for r in tracked if r.get("konteyner_no") in c_set and (r.get("hazir") or r.get("pdf_url"))]
        else:
            ready_recs = [r for r in tracked if r.get("hazir") or r.get("pdf_url")]

        if not ready_recs:
            messagebox.showwarning(
                "Hazır Tike Yok",
                "Birleştirilecek hazır kantar tikesi (PDF) bulunamadı.\n"
                "Lütfen önce tarama yapın veya hazır konteynerleri seçin."
            )
            return

        # Kayıt yeri diyalogu
        import datetime as _dt
        tarih_str = _dt.datetime.now().strftime("%Y%m%d_%H%M")
        oneri_ad = f"Kantar_Tikeler_{tarih_str}.pdf"
        output_path = filedialog.asksaveasfilename(
            title="Birleşik Kantar Tike PDF'ini Kaydet",
            defaultextension=".pdf",
            initialfile=oneri_ad,
            filetypes=[("PDF Dosyası", "*.pdf"), ("Tüm Dosyalar", "*.*")],
        )
        if not output_path:
            return  # Kullanıcı iptal etti

        # UI'yi kilitle, ilerleme etiketini göster
        self.btn_kantar_merge_pdf.config(
            text=f"⏳ Birleştiriliyor {baslik_ek.strip()}...", state=tk.DISABLED
        )
        self.lbl_kantar_status.config(
            text=f"📦 Tike PDF'leri birleştiriliyor ({len(ready_recs)} adet)...",
            bg="#e0f2fe", fg="#0369a1"
        )

        def _on_progress(done: int, total: int, cntr: str):
            """Arkaplan thread'inden UI güncellemesi (after ile ana thread'e taşı)."""
            try:
                msg = (
                    f"📦 Birleştiriliyor: {cntr} ({done}/{total})"
                    if cntr
                    else f"📦 Birleştirme tamamlandı ({total} tike)"
                )
                self.root.after(0, lambda m=msg: self.lbl_kantar_status.config(text=m, bg="#e0f2fe", fg="#0369a1"))
            except Exception:
                pass

        def _worker():
            try:
                res = self.kantar_tracker.merge_all_pdfs(
                    output_path=output_path,
                    konteyner_list=cntr_list,
                    on_progress=_on_progress,
                )
            except Exception as exc:
                res = {"success": False, "error": str(exc), "total": 0, "skipped": 0, "merged_path": None}

            def _done():
                # Butonu ve etiketi geri al
                self.btn_kantar_merge_pdf.config(
                    text="📦 Tike PDF'lerini Birleştir", state=tk.NORMAL
                )
                self.lbl_kantar_status.config(
                    text="🤖 10 Dk Otonom İzleme Aktif", bg="#dcfce7", fg="#16a34a"
                )
                self.refresh_kantar_takip_table()

                if res.get("success"):
                    merged = res.get("total", 0)
                    skipped = res.get("skipped", 0)
                    merged_path = res.get("merged_path", "")
                    atla_satiri = f"\n⚠️ PDF'i henüz hazır olmayan konteyner: {skipped} adet (atlandı)" if skipped else ""
                    msg = (
                        f"✅ {merged} adet kantar tikesi başarıyla birleştirildi!{atla_satiri}\n\n"
                        f"📁 Kaydedilen dosya:\n{merged_path}\n\n"
                        f"PDF şimdi açılsın mı?"
                    )
                    if messagebox.askyesno("Birleştirme Tamamlandı", msg):
                        try:
                            os.startfile(merged_path)
                        except Exception:
                            messagebox.showinfo("Dosya Konumu", f"Dosya kaydedildi:\n{merged_path}")
                else:
                    messagebox.showerror(
                        "Birleştirme Başarısız",
                        f"PDF birleştirme işlemi tamamlanamadı:\n{res.get('error', 'Bilinmeyen hata')}"
                    )

            self.root.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()
