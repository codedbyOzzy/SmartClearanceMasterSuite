# -*- coding: utf-8 -*-
"""
tools/dogruer_master_suite/views/activity_hub_view.py
=====================================================
Doğruer MasterSuite - Dosya Notları & Operasyonel İşlem Günlüğü (Activity Hub & Timeline View)
"""
import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta

from .base_view import BaseView

try:
    from tools.supabase_sync_manager import get_supabase_manager
except ImportError:
    try:
        from supabase_sync_manager import get_supabase_manager
    except ImportError:
        get_supabase_manager = None


class ActivityHubView(BaseView):
    """
    Dosya Notları & Operasyonel İşlem Günlüğü (Timeline) Görünümü
    """
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.current_activity_logs = []
        self.act_show_trash = False
        self.undo_banner = None
        self._undo_timer_id = None
        self.setup_activity_hub_view()

    def on_activate(self):
        """Sekme aktif olduğunda verileri otomatik olarak tazeler."""
        self.refresh_activity_hub()

    def create_metric_widget(self, parent, title, val, subtitle, accent_color, command=None):
        card = tk.Frame(parent, bg="#ffffff", padx=12, pady=8, relief=tk.FLAT, bd=0, cursor="hand2" if command else "arrow")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

        top_strip = tk.Frame(card, bg=accent_color, height=3)
        top_strip.pack(fill=tk.X, pady=(0, 4))

        lbl_t = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff", cursor="hand2" if command else "arrow")
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(card, text=val, font=("Segoe UI", 15, "bold"), fg=accent_color, bg="#ffffff", cursor="hand2" if command else "arrow")
        lbl_v.pack(anchor="w")

        lbl_sub = tk.Label(card, text=subtitle, font=("Segoe UI", 8), fg="#94a3b8", bg="#ffffff", cursor="hand2" if command else "arrow")
        lbl_sub.pack(anchor="w")

        if command:
            for w in (card, top_strip, lbl_t, lbl_v, lbl_sub):
                w.bind("<Button-1>", lambda e, cmd=command: cmd())

        return {"card": card, "val_lbl": lbl_v, "title": title}

    def setup_activity_hub_view(self):
        # 1. Metrik Barı (Aktivite Notları, Vergi Mailleri, GTB & Gümrük, Fatura & Eşleme)
        metric_bar = tk.Frame(self, bg="#f8fafc")
        metric_bar.pack(fill=tk.X, pady=(0, 10))

        self.card_act_notes = self.create_metric_widget(
            metric_bar, "AKTİVİTE NOTLARI", "0", "Kullanıcı Notları", "#7c3aed", lambda: self._act_filter_type("NOT")
        )
        self.card_act_mail = self.create_metric_widget(
            metric_bar, "VERGİ MAİLLERİ", "0", "Vergi & Bilgilendirme", "#2563eb", lambda: self._act_filter_type("MAIL")
        )
        self.card_act_tescil = self.create_metric_widget(
            metric_bar, "GTB & GÜMRÜK", "0", "Bakanlık Hareketleri", "#16a34a", lambda: self._act_filter_type("TESCIL")
        )
        self.card_act_fatura = self.create_metric_widget(
            metric_bar, "FATURA & EŞLEME", "0", "Fatura & Eşleme", "#d97706", lambda: self._act_filter_type("FATURA")
        )

        # Geriye dönük uyumluluk takma adları (Aliases)
        self.card_act_gtb = self.card_act_tescil
        self.card_act_total = self.card_act_notes

        # 2. Kontrol & Filtre Çubuğu
        ctrl_bar = tk.Frame(self, bg="#ffffff", padx=14, pady=10, relief=tk.FLAT, bd=0)
        ctrl_bar.pack(fill=tk.X, pady=(0, 10))

        # Satır 1: Filtreleme Elemanları
        f_filter_row = tk.Frame(ctrl_bar, bg="#ffffff")
        f_filter_row.pack(fill=tk.X)

        lbl_s = tk.Label(f_filter_row, text="🔍 Ara:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_s.pack(side=tk.LEFT, padx=(0, 4))

        self.txt_act_search = tk.Entry(f_filter_row, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, width=22)
        self.txt_act_search.pack(side=tk.LEFT, padx=(0, 12), ipady=3)
        self.txt_act_search.bind("<KeyRelease>", lambda e: self.refresh_activity_hub())

        lbl_d = tk.Label(f_filter_row, text="📅 Tarih:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_d.pack(side=tk.LEFT, padx=(0, 4))

        self.combo_act_date = ttk.Combobox(
            f_filter_row,
            values=["Tümü", "Bugün", "Dün", "Son 3 Gün", "Bu Hafta", "Bu Ay"],
            state="readonly",
            width=11,
            font=("Segoe UI", 9)
        )
        self.combo_act_date.set("Tümü")
        self.combo_act_date.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_act_date.bind("<<ComboboxSelected>>", lambda e: self.refresh_activity_hub())

        lbl_t = tk.Label(f_filter_row, text="🏷️ Tip:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_t.pack(side=tk.LEFT, padx=(0, 4))

        self.combo_act_type = ttk.Combobox(
            f_filter_row,
            values=["TÜMÜ", "NOT", "TESCIL", "MAIL", "FATURA", "ETA", "KANTAR"],
            state="readonly",
            width=10,
            font=("Segoe UI", 9)
        )
        self.combo_act_type.set("TÜMÜ")
        self.combo_act_type.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_act_type.bind("<<ComboboxSelected>>", lambda e: self.refresh_activity_hub())

        lbl_tag = tk.Label(f_filter_row, text="Etiket:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_tag.pack(side=tk.LEFT, padx=(0, 4))

        self.combo_act_tag = ttk.Combobox(
            f_filter_row,
            values=["TÜMÜ", "Normal", "Acil", "Beklemede", "Tamamlandı", "Bilgi"],
            state="readonly",
            width=11,
            font=("Segoe UI", 9)
        )
        self.combo_act_tag.set("TÜMÜ")
        self.combo_act_tag.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_act_tag.bind("<<ComboboxSelected>>", lambda e: self.refresh_activity_hub())

        # Aksiyon Butonları (Sağ Taraf)
        btn_box = tk.Frame(f_filter_row, bg="#ffffff")
        btn_box.pack(side=tk.RIGHT)

        btn_add_note = tk.Button(
            btn_box,
            text="➕ Yeni Not Ekle",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.show_add_note_dialog
        )
        btn_add_note.pack(side=tk.LEFT, padx=3)

        btn_sync = tk.Button(
            btn_box,
            text="🔄 Bulut Senkronize Et",
            font=("Segoe UI", 9, "bold"),
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.sync_activity_with_supabase
        )
        btn_sync.pack(side=tk.LEFT, padx=3)

        btn_export = tk.Button(
            btn_box,
            text="📊 Excel İndir",
            font=("Segoe UI", 9),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.export_activity_to_excel
        )
        btn_export.pack(side=tk.LEFT, padx=3)

        self.btn_act_trash = tk.Button(
            btn_box,
            text="🗑️ Çöp Kutusu",
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#475569",
            activebackground="#e2e8f0",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.toggle_activity_trash
        )
        self.btn_act_trash.pack(side=tk.LEFT, padx=3)

        self.btn_act_empty_trash = tk.Button(
            btn_box,
            text="🔥 Çöpü Boşalt",
            font=("Segoe UI", 9, "bold"),
            bg="#b91c1c",
            fg="#ffffff",
            activebackground="#991b1b",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.empty_activity_trash
        )

        # 3. Ana Tablo & Timeline (Treeview)
        t_card = tk.Frame(self, bg="#ffffff", relief=tk.FLAT, bd=0)
        t_card.pack(fill=tk.BOTH, expand=True)

        cols = ("created_at", "dosya_no", "ref_no", "islem_tipi", "etiket", "baslik", "icerik", "kullanici", "synced")
        self.tree_activity = ttk.Treeview(t_card, columns=cols, show="headings", selectmode="extended")

        self.tree_activity.heading("created_at", text="Tarih & Saat", anchor="center")
        self.tree_activity.heading("dosya_no", text="Dosya No", anchor="w")
        self.tree_activity.heading("ref_no", text="Ref / Konşimento", anchor="w")
        self.tree_activity.heading("islem_tipi", text="İşlem Tipi", anchor="center")
        self.tree_activity.heading("etiket", text="Etiket", anchor="center")
        self.tree_activity.heading("baslik", text="Başlık", anchor="w")
        self.tree_activity.heading("icerik", text="İçerik & Not Detayı", anchor="w")
        self.tree_activity.heading("kullanici", text="Kullanıcı", anchor="center")
        self.tree_activity.heading("synced", text="Bulut", anchor="center")

        self.tree_activity.column("created_at", width=125, minwidth=110, anchor="center")
        self.tree_activity.column("dosya_no", width=110, minwidth=90, anchor="w")
        self.tree_activity.column("ref_no", width=125, minwidth=100, anchor="w")
        self.tree_activity.column("islem_tipi", width=95, minwidth=80, anchor="center")
        self.tree_activity.column("etiket", width=85, minwidth=70, anchor="center")
        self.tree_activity.column("baslik", width=220, minwidth=160, anchor="w")
        self.tree_activity.column("icerik", width=380, minwidth=220, anchor="w")
        self.tree_activity.column("kullanici", width=95, minwidth=80, anchor="center")
        self.tree_activity.column("synced", width=70, minwidth=60, anchor="center")

        # Renk Etiketleri (Tags)
        self.tree_activity.tag_configure("tag_NOT", background="#fdf4ff")
        self.tree_activity.tag_configure("tag_TESCIL", background="#f0fdf4")
        self.tree_activity.tag_configure("tag_GTB", background="#f0fdf4")
        self.tree_activity.tag_configure("tag_MAIL", background="#eff6ff")
        self.tree_activity.tag_configure("tag_FATURA", background="#fffbeb")
        self.tree_activity.tag_configure("tag_ESLEME", background="#fffbeb")
        self.tree_activity.tag_configure("tag_ETA", background="#f0fdfa")
        self.tree_activity.tag_configure("tag_KANTAR", background="#fdf2f8")
        self.tree_activity.tag_configure("tag_Acil", foreground="#b91c1c")

        # Scrollbarlar
        sb_y = ttk.Scrollbar(t_card, orient="vertical", command=self.tree_activity.yview)
        self.tree_activity.configure(yscrollcommand=sb_y.set)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)

        sb_x = ttk.Scrollbar(t_card, orient="horizontal", command=self.tree_activity.xview)
        self.tree_activity.configure(xscrollcommand=sb_x.set)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree_activity.pack(fill=tk.BOTH, expand=True)

        # Tablo Tıklama, Klavye Kısayolları & Çoklu Seçim Olayları
        self.tree_activity.bind("<Double-1>", self.on_activity_row_double_click)
        self.tree_activity.bind("<Return>", self.on_activity_row_double_click)
        self.tree_activity.bind("<Button-3>", self.show_activity_context_menu)
        self.tree_activity.bind("<Control-a>", self._select_all_activity)
        self.tree_activity.bind("<Control-A>", self._select_all_activity)
        self.tree_activity.bind("<Delete>", self._on_delete_key_pressed)
        self.tree_activity.bind("<BackSpace>", self._on_delete_key_pressed)

    def _select_all_activity(self, event=None):
        for item in self.tree_activity.get_children():
            self.tree_activity.selection_add(item)
        return "break"

    def _on_delete_key_pressed(self, event=None):
        sel = self.tree_activity.selection()
        if not sel:
            return "break"

        # Çöp kutusu modunda isek geri yükleme sor
        if getattr(self, "act_show_trash", False):
            trash_ids = [int(iid) for iid in sel if str(iid).isdigit()]
            if trash_ids:
                if self.ask_yes_no("Geri Yükle", f"Seçili {len(trash_ids)} adet notu geri yüklemek istiyor musunuz?"):
                    self.undo_delete_activity_notes(trash_ids)
        else:
            # Sadece NOT tipindeki kayıtlar silinebilir
            sel_logs = [l for l in self.current_activity_logs if str(l["id"]) in sel]
            deletable_ids = [l["id"] for l in sel_logs if l.get("islem_tipi") == "NOT" and not l.get("is_deleted")]
            if deletable_ids:
                if len(deletable_ids) == 1:
                    prompt = "Seçili notu çöp kutusuna taşımak istiyor musunuz?"
                else:
                    prompt = f"Seçili {len(deletable_ids)} adet notu çöp kutusuna taşımak istiyor musunuz?"
                if self.ask_yes_no("Notu Sil", prompt):
                    self.delete_activity_notes(deletable_ids)
            else:
                self.show_warning("Uyarı", "Sadece kullanıcı tarafından eklenen 'NOT' tipindeki kayıtlar silinebilir.")
        return "break"

    def _act_filter_type(self, t_code):
        if hasattr(self, "combo_act_type"):
            current = self.combo_act_type.get()
            if current == t_code:
                self.combo_act_type.set("TÜMÜ")
            else:
                self.combo_act_type.set(t_code)
            self.refresh_activity_hub()

    def sync_activity_with_supabase(self):
        """Supabase ile canlı aktivite senkronizasyonunu tetikler."""
        try:
            sm = get_supabase_manager() if get_supabase_manager else None
            if sm:
                sm.sync_activity_logs()
                self.after(1200, self.refresh_activity_hub)
                self.show_info("Senkronizasyon", "Aktivite ve notlar Supabase bulutu ile senkronize edildi!")
            else:
                self.show_warning("Uyarı", "Supabase senkronizasyon yöneticisi yüklenemedi.")
        except Exception as e:
            self.show_error("Hata", f"Senkronizasyon başlatılamadı: {e}")

    def trigger_activity_sync(self):
        """sync_activity_with_supabase takma adı."""
        self.sync_activity_with_supabase()

    def refresh_activity_hub(self):
        """Aktivite & Not tablosunu filtrelere göre doldurur."""
        if not hasattr(self, "tree_activity"):
            return

        search_txt = self.txt_act_search.get().strip() if hasattr(self, "txt_act_search") else ""
        date_sel = self.combo_act_date.get() if hasattr(self, "combo_act_date") else "Tümü"
        type_sel = self.combo_act_type.get() if hasattr(self, "combo_act_type") else "TÜMÜ"
        tag_sel = self.combo_act_tag.get() if hasattr(self, "combo_act_tag") else "TÜMÜ"

        # Tarih filtre hesaplama
        now = datetime.now()
        date_from = None
        date_to = None

        if date_sel == "Bugün":
            date_from = now.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
        elif date_sel == "Dün":
            yst = now - timedelta(days=1)
            date_from = yst.strftime("%Y-%m-%d")
            date_to = yst.strftime("%Y-%m-%d")
        elif date_sel == "Son 3 Gün":
            d3 = now - timedelta(days=2)
            date_from = d3.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
        elif date_sel == "Bu Hafta":
            start_week = now - timedelta(days=now.weekday())
            date_from = start_week.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
        elif date_sel == "Bu Ay":
            date_from = now.strftime("%Y-%m-01")
            date_to = now.strftime("%Y-%m-%d")

        logs = []
        try:
            sm = get_supabase_manager() if get_supabase_manager else None
            if sm:
                # Metrik sayaçlarının doğru kalabilmesi için DB sorgusunda islem_tipi filtrelemiyoruz
                logs = sm.fetch_activity_logs(
                    search_term=search_txt if search_txt else None,
                    islem_tipi=None,
                    date_from=date_from,
                    date_to=date_to,
                    limit=500,
                    only_deleted=getattr(self, "act_show_trash", False)
                )
        except Exception as e:
            print("[ACT-FETCH-ERROR]", e)
            logs = []

        # Metrik Sayaçlarını Hesapla (Tüm tipler üzerinden)
        cnt_notes = 0
        cnt_mail = 0
        cnt_tescil = 0
        cnt_fatura = 0

        for row in logs:
            tip = (row.get("islem_tipi") or "NOT").upper()
            if tip == "NOT":
                cnt_notes += 1
            elif tip == "MAIL":
                cnt_mail += 1
            elif tip in ("TESCIL", "GTB", "GÜMRÜK"):
                cnt_tescil += 1
            elif tip in ("FATURA", "ESLEME", "EŞLEME"):
                cnt_fatura += 1

        # Metrik Kartlarını Güncelle
        cards_and_vals = [
            (getattr(self, "card_act_notes", None), cnt_notes),
            (getattr(self, "card_act_mail", None), cnt_mail),
            (getattr(self, "card_act_tescil", None), cnt_tescil),
            (getattr(self, "card_act_fatura", None), cnt_fatura),
        ]
        for c, val in cards_and_vals:
            if isinstance(c, dict) and "val_lbl" in c:
                c["val_lbl"].config(text=str(val))

        # Tip ve Etiket filtrelemesini uygulayarak görüntülenecek listeyi oluştur
        display_logs = logs
        if type_sel != "TÜMÜ":
            if type_sel == "NOT":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "NOT").upper() == "NOT"]
            elif type_sel == "TESCIL":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() in ("TESCIL", "GTB", "GÜMRÜK")]
            elif type_sel == "MAIL":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() == "MAIL"]
            elif type_sel == "FATURA":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() in ("FATURA", "ESLEME", "EŞLEME")]
            elif type_sel == "ETA":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() == "ETA"]
            elif type_sel == "KANTAR":
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() == "KANTAR"]
            else:
                display_logs = [l for l in display_logs if (l.get("islem_tipi") or "").upper() == type_sel.upper()]

        # Etiket filtresi
        if tag_sel != "TÜMÜ":
            display_logs = [l for l in display_logs if str(l.get("etiket", "")).lower() == tag_sel.lower()]

        self.current_activity_logs = display_logs

        # Tabloyu temizle
        for item in self.tree_activity.get_children():
            try:
                self.tree_activity.delete(item)
            except Exception:
                pass

        type_icons = {
            "NOT": "📝 NOT",
            "TESCIL": "🏛️ TESCİL",
            "GTB": "🏛️ GTB",
            "MAIL": "📧 MAİL",
            "FATURA": "💸 FATURA",
            "ESLEME": "💸 EŞLEME",
            "EŞLEME": "💸 EŞLEME",
            "ETA": "⏳ ETA",
            "KANTAR": "⚖️ KANTAR"
        }

        tag_icons = {
            "Normal": "Normal",
            "Acil": "🚨 Acil",
            "Beklemede": "⏳ Bekliyor",
            "Tamamlandı": "✅ Bitti",
            "Bilgi": "ℹ️ Bilgi"
        }

        for row in display_logs:
            tip = (row.get("islem_tipi") or "NOT").upper()
            t_str = row.get("created_at", "")
            if len(t_str) >= 16:
                try:
                    dt = datetime.strptime(t_str[:19], "%Y-%m-%d %H:%M:%S")
                    t_display = dt.strftime("%d.%m %H:%M")
                except Exception:
                    t_display = t_str[:16]
            else:
                t_display = t_str

            tip_display = type_icons.get(tip, tip)
            raw_tag = row.get("etiket", "Normal")
            tag_display = tag_icons.get(raw_tag, raw_tag)
            sync_icon = "☁️ Senkron" if row.get("synced") else "💾 Yerel"

            row_tag = f"tag_{tip}"
            tags = (row_tag,)
            if raw_tag == "Acil":
                tags = (row_tag, "tag_Acil")

            # İçeriği tek satıra indirgeyerek tabloda göster
            c_preview = (row.get("icerik") or "").replace("\n", " ").replace("\r", "")
            if len(c_preview) > 90:
                c_preview = c_preview[:90] + "..."

            self.tree_activity.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    t_display,
                    row.get("dosya_no", ""),
                    row.get("ref_no", ""),
                    tip_display,
                    tag_display,
                    row.get("baslik", ""),
                    c_preview,
                    row.get("kullanici", ""),
                    sync_icon
                ),
                tags=tags
            )

    def on_activity_row_double_click(self, event=None):
        sel = self.tree_activity.selection()
        if not sel:
            return
        log_id = sel[0]
        log_data = next((l for l in self.current_activity_logs if str(l["id"]) == str(log_id)), None)
        if log_data:
            self.show_activity_detail_dialog(log_data)

    def show_activity_context_menu(self, event):
        item_id = self.tree_activity.identify_row(event.y)
        if not item_id:
            return

        selected_items = list(self.tree_activity.selection())
        # Tıklanan satır mevcut çoklu seçimin içinde değilse sadece o satırı seç
        if item_id not in selected_items:
            self.tree_activity.selection_set(item_id)
            selected_items = [item_id]

        sel_logs = [l for l in self.current_activity_logs if str(l["id"]) in selected_items]
        if not sel_logs:
            return

        root_win = self.winfo_toplevel()
        menu = tk.Menu(root_win, tearoff=0)

        if len(sel_logs) == 1:
            log_data = sel_logs[0]
            menu.add_command(label="🔍 Detaylı İncele", command=lambda: self.show_activity_detail_dialog(log_data))

            d_no = log_data.get("dosya_no")
            if d_no:
                menu.add_command(
                    label=f"➕ '{d_no}' Dosyasına Yeni Not Ekle",
                    command=lambda: self.show_add_note_dialog(default_dosya=d_no, default_ref=log_data.get("ref_no", ""), default_beyan=log_data.get("beyanname_no", ""))
                )
                menu.add_command(
                    label=f"📋 Dosya Numarasını Kopyala ({d_no})",
                    command=lambda: self._copy_to_clipboard(d_no)
                )

            r_no = log_data.get("ref_no")
            if r_no:
                menu.add_command(
                    label=f"📋 Referans No Kopyala ({r_no})",
                    command=lambda: self._copy_to_clipboard(r_no)
                )

            # Silinmiş ise geri yükleme seçeneği göster
            if log_data.get("is_deleted") == 1:
                menu.add_separator()
                menu.add_command(label="♻️ Bu Notu Geri Yükle", command=lambda: self.undo_delete_activity_notes([log_data["id"]]))
            elif log_data.get("islem_tipi") == "NOT":
                menu.add_separator()
                menu.add_command(label="🗑️ Bu Notu Sil", command=lambda: self.delete_activity_notes([log_data["id"]]))
        else:
            # Çoklu Seçim Menüsü
            dosyalar = list(dict.fromkeys(l.get("dosya_no") for l in sel_logs if l.get("dosya_no")))
            if dosyalar:
                menu.add_command(
                    label=f"📋 Seçili {len(dosyalar)} Dosya Numarasını Kopyala",
                    command=lambda: self._copy_to_clipboard("\n".join(dosyalar))
                )

            # Çöp kutusu modunda mıyız?
            if getattr(self, "act_show_trash", False):
                trash_ids = [l["id"] for l in sel_logs if l.get("is_deleted") == 1]
                if trash_ids:
                    menu.add_separator()
                    menu.add_command(
                        label=f"♻️ Seçilenleri Geri Yükle ({len(trash_ids)} Not)",
                        command=lambda: self.undo_delete_activity_notes(trash_ids)
                    )
            else:
                # Sadece NOT tipindeki kayıtlar silinebilir
                deletable_ids = [l["id"] for l in sel_logs if l.get("islem_tipi") == "NOT" and not l.get("is_deleted")]
                if deletable_ids:
                    menu.add_separator()
                    menu.add_command(
                        label=f"🗑️ Seçilenleri Sil ({len(deletable_ids)} Not)",
                        command=lambda: self.delete_activity_notes(deletable_ids)
                    )

        menu.tk_popup(event.x_root, event.y_root)

    def toggle_activity_trash(self):
        self.act_show_trash = not getattr(self, "act_show_trash", False)
        if self.act_show_trash:
            self.btn_act_trash.config(text="📂 Aktif Notlara Dön", bg="#dc2626", fg="#ffffff")
            if hasattr(self, "btn_act_empty_trash"):
                self.btn_act_empty_trash.pack(side=tk.LEFT, padx=3)
            if hasattr(self.app, "lbl_head_subtitle"):
                self.app.lbl_head_subtitle.config(
                    text="🗑️ Çöp Kutusu: Silinen notlar listeleniyor. Geri yüklemek için sağ tıklayıp 'Geri Yükle' seçin veya 'Çöpü Boşalt' ile kalıcı temizleyin."
                )
        else:
            self.btn_act_trash.config(text="🗑️ Çöp Kutusu", bg="#f1f5f9", fg="#475569")
            if hasattr(self, "btn_act_empty_trash"):
                self.btn_act_empty_trash.pack_forget()
            if hasattr(self.app, "lbl_head_subtitle"):
                self.app.lbl_head_subtitle.config(
                    text="Dosyalara ait özel notlar, GTB tescil, mail ve fatura hareketlerinin canlı tarihçesi (Supabase Eşitlemeli)"
                )
        self.refresh_activity_hub()

    def empty_activity_trash(self):
        if not self.ask_yes_no(
            "Çöp Kutusunu Boşalt",
            "⚠️ DİKKAT: Çöp kutusundaki tüm silinmiş notlar hem yerelden hem de Supabase bulutundan kalıcı olarak temizlenecektir.\n"
            "Bu işlem geri alınamaz!\n\nDevam etmek istiyor musunuz?"
        ):
            return
        try:
            sm = get_supabase_manager() if get_supabase_manager else None
            if sm:
                count = sm.empty_trash()
                self.refresh_activity_hub()
                self.show_info("Çöp Kutusu Temizlendi", f"🗑️ Çöp kutusundaki {count} adet silinmiş kayıt kalıcı olarak temizlendi.")
            else:
                self.show_warning("Uyarı", "Supabase yöneticisi bulunamadı.")
        except Exception as e:
            self.show_error("Hata", f"Çöp kutusu boşaltılamadı: {e}")

    def _copy_to_clipboard(self, text):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.show_info("Kopyalandı", f"'{text[:120]}' panoya kopyalandı!")
        except Exception:
            pass

    def delete_activity_notes(self, log_ids):
        if not log_ids:
            return
        if not isinstance(log_ids, list):
            log_ids = [log_ids]
        try:
            sm = get_supabase_manager() if get_supabase_manager else None
            if not sm:
                self.show_error("Hata", "Supabase yöneticisi bulunamadı.")
                return
            count = 0
            for lid in log_ids:
                if sm.soft_delete_activity_log(lid):
                    count += 1
            if count > 0:
                self.refresh_activity_hub()
                msg = f"🗑️ {count} not silindi (Çöp kutusuna taşındı)." if count > 1 else "🗑️ Not silindi (Çöp kutusuna taşındı)."
                self.show_undo_banner(msg, log_ids)
            else:
                self.show_warning("Uyarı", "Seçili notlar silinemedi.")
        except Exception as e:
            self.show_error("Hata", f"Notlar silinemedi: {e}")

    def delete_activity_note(self, log_id):
        self.delete_activity_notes([log_id])

    def show_undo_banner(self, text, log_ids):
        """Activity Hub üzerinde 10 saniye süreyle kaybolan Geri Al (Undo) çubuğu gösterir."""
        if not isinstance(log_ids, list):
            log_ids = [log_ids]

        if hasattr(self, "_undo_timer_id") and self._undo_timer_id:
            try:
                self.after_cancel(self._undo_timer_id)
                self._undo_timer_id = None
            except Exception:
                pass

        if hasattr(self, "undo_banner") and self.undo_banner:
            try:
                self.undo_banner.destroy()
            except Exception:
                pass

        self.undo_banner = tk.Frame(self, bg="#1e293b", padx=14, pady=8, relief=tk.RAISED, bd=2)
        self.undo_banner.place(relx=0.5, rely=0.08, anchor=tk.CENTER)
        self.undo_banner.lift()

        lbl = tk.Label(self.undo_banner, text=text, font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b")
        lbl.pack(side=tk.LEFT, padx=(0, 12))

        btn_undo = tk.Button(
            self.undo_banner,
            text="↩️ Geri Al (Undo)",
            font=("Segoe UI", 9, "bold"),
            bg="#38bdf8",
            fg="#0f172a",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda: self.undo_delete_activity_notes(log_ids)
        )
        btn_undo.pack(side=tk.LEFT, padx=4)

        btn_close = tk.Button(
            self.undo_banner,
            text="✕",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._dismiss_undo_banner
        )
        btn_close.pack(side=tk.LEFT, padx=(4, 0))

        self._undo_timer_id = self.after(10000, self._dismiss_undo_banner)

    def _dismiss_undo_banner(self):
        if hasattr(self, "undo_banner") and self.undo_banner:
            try:
                self.undo_banner.destroy()
                self.undo_banner = None
            except Exception:
                pass
        self._undo_timer_id = None

    def undo_delete_activity_notes(self, log_ids):
        if not log_ids:
            return
        if not isinstance(log_ids, list):
            log_ids = [log_ids]
        try:
            sm = get_supabase_manager() if get_supabase_manager else None
            if not sm:
                self.show_error("Hata", "Supabase yöneticisi bulunamadı.")
                return
            count = 0
            for lid in log_ids:
                if sm.restore_activity_log(lid):
                    count += 1
            if count > 0:
                self._dismiss_undo_banner()
                self.refresh_activity_hub()
                msg = f"✅ {count} adet not başarıyla geri yüklendi!" if count > 1 else "✅ Not başarıyla geri yüklendi!"
                self.show_info("Geri Alındı", msg)
            else:
                self.show_warning("Uyarı", "Notlar geri yüklenemedi.")
        except Exception as e:
            self.show_error("Hata", f"Geri alma hatası: {e}")

    def undo_delete_activity_note(self, log_id):
        self.undo_delete_activity_notes([log_id])

    def show_add_note_dialog(self, default_dosya="", default_ref="", default_beyan=""):
        """Hızlı not ekleme penceresini açar."""
        root_win = self.winfo_toplevel()
        dlg = tk.Toplevel(root_win)
        dlg.title("➕ Yeni Operasyon Notu Ekle")
        dlg.geometry("540x580")
        dlg.resizable(False, False)
        dlg.configure(bg="#ffffff", padx=22, pady=18)
        dlg.transient(root_win)
        dlg.grab_set()

        # Pencereyi ana ekrana ortala
        try:
            dlg.update_idletasks()
            w = 540
            h = 580
            x = root_win.winfo_x() + (root_win.winfo_width() - w) // 2
            y = root_win.winfo_y() + (root_win.winfo_height() - h) // 2
            dlg.geometry(f"{w}x{h}+{max(x, 50)}+{max(y, 50)}")
        except Exception:
            pass

        tk.Label(dlg, text="📝 Operasyon Notu Girişi", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w", pady=(0, 10))

        # Form Alanları
        f_grid = tk.Frame(dlg, bg="#ffffff")
        f_grid.pack(fill=tk.X, pady=(0, 8))

        # Dosya No
        tk.Label(f_grid, text="Dosya No:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=0, column=0, sticky="w", pady=4)
        ent_dosya = tk.Entry(f_grid, font=("Segoe UI", 10), width=18)
        ent_dosya.insert(0, default_dosya)
        ent_dosya.grid(row=0, column=1, sticky="w", padx=(6, 16), pady=4)

        # Ref No
        tk.Label(f_grid, text="Ref / BL No:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=0, column=2, sticky="w", pady=4)
        ent_ref = tk.Entry(f_grid, font=("Segoe UI", 10), width=18)
        ent_ref.insert(0, default_ref)
        ent_ref.grid(row=0, column=3, sticky="w", padx=(6, 0), pady=4)

        # Beyanname No
        tk.Label(f_grid, text="Beyanname No:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=1, column=0, sticky="w", pady=4)
        ent_beyan = tk.Entry(f_grid, font=("Segoe UI", 10), width=18)
        ent_beyan.insert(0, default_beyan)
        ent_beyan.grid(row=1, column=1, sticky="w", padx=(6, 16), pady=4)

        # Etiket
        tk.Label(f_grid, text="Etiket / Durum:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=1, column=2, sticky="w", pady=4)
        combo_tag = ttk.Combobox(f_grid, values=["Normal", "Acil", "Beklemede", "Tamamlandı", "Bilgi"], state="readonly", width=16)
        combo_tag.set("Normal")
        combo_tag.grid(row=1, column=3, sticky="w", padx=(6, 0), pady=4)

        # Başlık
        tk.Label(dlg, text="Not Başlığı (Kısa Konu):", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w", pady=(6, 2))
        ent_baslik = tk.Entry(dlg, font=("Segoe UI", 10))
        ent_baslik.pack(fill=tk.X, pady=(0, 8))

        # Hızlı Şablon Butonları
        f_templates = tk.Frame(dlg, bg="#ffffff")
        f_templates.pack(fill=tk.X, pady=(0, 6))
        tk.Label(f_templates, text="Hızlı Ekle:", font=("Segoe UI", 8), bg="#ffffff", fg="#64748b").pack(side=tk.LEFT, padx=(0, 4))

        txt_icerik = scrolledtext.ScrolledText(dlg, font=("Segoe UI", 9), height=7)

        def _append_template(txt):
            cur = txt_icerik.get("1.0", tk.END).strip()
            if cur:
                txt_icerik.delete("1.0", tk.END)
                txt_icerik.insert("1.0", cur + " | " + txt)
            else:
                txt_icerik.insert("1.0", txt)
            if not ent_baslik.get():
                ent_baslik.insert(0, txt)

        for tmpl in ["Ordino Alındı", "Evrak Bekleniyor", "Müşteriye Bilgi Verildi", "Muayenede", "Kantar Yapıldı", "Vergi Ödendi"]:
            btn_t = tk.Button(
                f_templates,
                text=tmpl,
                font=("Segoe UI", 8),
                bg="#f1f5f9",
                fg="#334155",
                relief=tk.FLAT,
                padx=5,
                pady=1,
                cursor="hand2",
                command=lambda t=tmpl: _append_template(t)
            )
            btn_t.pack(side=tk.LEFT, padx=2)

        # Not İçeriği
        tk.Label(dlg, text="Not Açıklaması / Detay:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w", pady=(4, 2))
        txt_icerik.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        # Alt Butonlar
        f_btns = tk.Frame(dlg, bg="#ffffff")
        f_btns.pack(fill=tk.X)

        def _on_save():
            d_val = ent_dosya.get().strip()
            r_val = ent_ref.get().strip()
            b_val = ent_beyan.get().strip()
            t_val = combo_tag.get()
            head_val = ent_baslik.get().strip()
            body_val = txt_icerik.get("1.0", tk.END).strip()

            if not head_val and not body_val:
                messagebox.showwarning("Eksik Bilgi", "Lütfen en azından bir başlık veya not içeriği yazın.", parent=dlg)
                return

            if not head_val:
                head_val = body_val[:40]

            try:
                sm = get_supabase_manager() if get_supabase_manager else None
                if not sm:
                    messagebox.showerror("Hata", "Supabase yöneticisi bulunamadı.", parent=dlg)
                    return

                u_name = self.current_user.get("full_name") or self.current_user.get("username") or os.environ.get("USERNAME", "Operatör")
                sm.add_activity_log(
                    dosya_no=d_val,
                    ref_no=r_val,
                    beyanname_no=b_val,
                    islem_tipi="NOT",
                    baslik=head_val,
                    icerik=body_val,
                    etiket=t_val,
                    kullanici=u_name
                )
                dlg.destroy()
                self.refresh_activity_hub()
                messagebox.showinfo("Kaydedildi", "Not başarıyla kaydedildi ve buluta iletildi!")
            except Exception as e:
                messagebox.showerror("Hata", f"Not kaydedilemedi: {e}", parent=dlg)

        btn_save = tk.Button(
            f_btns,
            text="💾 Notu Kaydet & Eşitle",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            command=_on_save
        )
        btn_save.pack(side=tk.RIGHT)

        btn_cancel = tk.Button(
            f_btns,
            text="İptal",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#334155",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=dlg.destroy
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(0, 8))

    def show_activity_detail_dialog(self, log):
        """Tekil kayıt detay görüntüleyici modal."""
        root_win = self.winfo_toplevel()
        dlg = tk.Toplevel(root_win)
        dlg.title(f"Aktivite Detayı: {log.get('baslik', 'Detay')}")
        dlg.geometry("560x500")
        dlg.configure(bg="#ffffff", padx=20, pady=16)
        dlg.transient(root_win)

        try:
            dlg.update_idletasks()
            w = 560
            h = 500
            x = root_win.winfo_x() + (root_win.winfo_width() - w) // 2
            y = root_win.winfo_y() + (root_win.winfo_height() - h) // 2
            dlg.geometry(f"{w}x{h}+{max(x, 50)}+{max(y, 50)}")
        except Exception:
            pass

        # Üst Başlık & Rozetler
        f_top = tk.Frame(dlg, bg="#ffffff")
        f_top.pack(fill=tk.X, pady=(0, 10))

        tip = log.get("islem_tipi", "NOT")
        tk.Label(f_top, text=f"İşlem Tipi: {tip}", font=("Segoe UI", 11, "bold"), fg="#2563eb", bg="#ffffff").pack(side=tk.LEFT)

        tag = log.get("etiket", "Normal")
        lbl_tag = tk.Label(f_top, text=f"[{tag}]", font=("Segoe UI", 10, "bold"), fg="#b91c1c" if tag == "Acil" else "#16a34a", bg="#ffffff")
        lbl_tag.pack(side=tk.LEFT, padx=8)

        sync_st = "☁️ Supabase Bulutunda Kayıtlı" if log.get("synced") else "💾 Henüz Sadece Yerelde (Offline)"
        tk.Label(f_top, text=sync_st, font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(side=tk.RIGHT)

        # Bilgi Satırları
        f_info = tk.Frame(dlg, bg="#f8fafc", padx=12, pady=10, relief=tk.SOLID, bd=1)
        f_info.pack(fill=tk.X, pady=(0, 12))

        lines = [
            ("📁 Dosya No:", log.get("dosya_no") or "—"),
            ("📦 Ref / Konşimento:", log.get("ref_no") or "—"),
            ("📑 Beyanname No:", log.get("beyanname_no") or "—"),
            ("👤 Kullanıcı:", log.get("kullanici") or "—"),
            ("🕒 Kayıt Tarihi:", log.get("created_at") or "—")
        ]
        for idx, (k, v) in enumerate(lines):
            r = idx // 2
            c = (idx % 2) * 2
            tk.Label(f_info, text=k, font=("Segoe UI", 8, "bold"), bg="#f8fafc", fg="#475569").grid(row=r, column=c, sticky="w", pady=2, padx=(0, 4))
            tk.Label(f_info, text=v, font=("Segoe UI", 8), bg="#f8fafc", fg="#0f172a").grid(row=r, column=c+1, sticky="w", pady=2, padx=(0, 16))

        # Başlık & İçerik
        tk.Label(dlg, text="Başlık:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w")
        lbl_b = tk.Label(dlg, text=log.get("baslik", "—"), font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#1e293b", wraplength=510, justify="left")
        lbl_b.pack(anchor="w", pady=(2, 8))

        tk.Label(dlg, text="Açıklama & Not Detayı:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w")
        txt_body = scrolledtext.ScrolledText(dlg, font=("Segoe UI", 9), height=8, relief=tk.SOLID, bd=1)
        txt_body.pack(fill=tk.BOTH, expand=True, pady=(2, 12))
        txt_body.insert("1.0", log.get("icerik") or "—")
        txt_body.config(state="disabled")

        # Alt Butonlar
        f_actions = tk.Frame(dlg, bg="#ffffff")
        f_actions.pack(fill=tk.X)

        def _copy_all():
            full_txt = f"Dosya: {log.get('dosya_no')}\nRef: {log.get('ref_no')}\nBeyanname: {log.get('beyanname_no')}\nTarih: {log.get('created_at')}\nBaşlık: {log.get('baslik')}\nİçerik:\n{log.get('icerik')}"
            self._copy_to_clipboard(full_txt)

        btn_cp = tk.Button(f_actions, text="📋 Tüm Detayı Kopyala", font=("Segoe UI", 9), bg="#f1f5f9", fg="#334155", relief=tk.FLAT, padx=12, pady=5, cursor="hand2", command=_copy_all)
        btn_cp.pack(side=tk.LEFT)

        if log.get("is_deleted") == 1:
            def _restore_and_close():
                self.undo_delete_activity_notes([log["id"]])
                dlg.destroy()
            btn_res = tk.Button(f_actions, text="♻️ Geri Yükle", font=("Segoe UI", 9, "bold"), bg="#16a34a", fg="#ffffff", relief=tk.FLAT, padx=12, pady=5, cursor="hand2", command=_restore_and_close)
            btn_res.pack(side=tk.LEFT, padx=6)
        elif log.get("islem_tipi") == "NOT":
            def _delete_and_close():
                self.delete_activity_notes([log["id"]])
                dlg.destroy()
            btn_del = tk.Button(f_actions, text="🗑️ Sil", font=("Segoe UI", 9), bg="#fee2e2", fg="#b91c1c", relief=tk.FLAT, padx=12, pady=5, cursor="hand2", command=_delete_and_close)
            btn_del.pack(side=tk.LEFT, padx=6)

        btn_close = tk.Button(f_actions, text="Kapat", font=("Segoe UI", 9), bg="#e2e8f0", fg="#334155", relief=tk.FLAT, padx=14, pady=5, cursor="hand2", command=dlg.destroy)
        btn_close.pack(side=tk.RIGHT)

    def export_activity_to_excel(self):
        """Görüntülenen aktivite loglarını Excel (.xlsx) dosyası olarak dışa aktarır."""
        if not self.current_activity_logs:
            self.show_info("Kayıt Yok", "Dışa aktarılacak aktivite kaydı bulunmuyor.")
            return

        try:
            save_path = filedialog.asksaveasfilename(
                title="Aktivite Günlüğü Excel Olarak Kaydet",
                defaultextension=".xlsx",
                filetypes=[("Excel Dosyası", "*.xlsx"), ("CSV Dosyası", "*.csv")],
                initialfile=f"Operasyon_Gunlugu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )
            if not save_path:
                return

            rows = []
            for r in self.current_activity_logs:
                rows.append({
                    "Tarih": r.get("created_at"),
                    "Dosya No": r.get("dosya_no"),
                    "Referans No": r.get("ref_no"),
                    "Beyanname No": r.get("beyanname_no"),
                    "İşlem Tipi": r.get("islem_tipi"),
                    "Etiket": r.get("etiket"),
                    "Başlık": r.get("baslik"),
                    "Açıklama / Not": r.get("icerik"),
                    "Kullanıcı": r.get("kullanici"),
                    "Bulut Senkron": "Evet" if r.get("synced") else "Hayır"
                })

            if save_path.endswith(".csv"):
                import csv
                with open(save_path, "w", newline="", encoding="utf-8-sig") as cf:
                    writer = csv.DictWriter(cf, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                try:
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    df.to_excel(save_path, index=False)
                except ImportError:
                    import openpyxl
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Aktivite Günlüğü"
                    headers = list(rows[0].keys())
                    ws.append(headers)
                    for r_data in rows:
                        ws.append([r_data.get(h, "") for h in headers])
                    wb.save(save_path)

            self.show_info("Başarılı", f"Excel dosyası başarıyla oluşturuldu:\n{save_path}")
            try:
                os.startfile(save_path)
            except Exception:
                pass
        except Exception as e:
            self.show_error("Hata", f"Excel'e aktarım hatası: {e}")
