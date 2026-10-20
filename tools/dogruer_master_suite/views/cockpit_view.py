# -*- coding: utf-8 -*-
"""
==============================================================================
🏛️ DOĞRUER SMARTCLEARANCE MASTER SUITE - MODÜL 1: CANLI OPERASYON KOKPİTİ
==============================================================================
Excel Canlı Senkronizasyon, 5 Aşamalı Operasyonel Süreç Takibi, Outlook Vergi Maili
Entegrasyonu, Canlı Mail Zaman Tüneli (Timeline) ve GTB Bakanlık Durum Paneli.
"""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

try:
    import openpyxl
    import openpyxl.styles
    import openpyxl.utils
except ImportError:
    openpyxl = None

from .base_view import BaseView


class CockpitView(BaseView):
    """
    Modül 1: Canlı Operasyon Kokpiti Görünümü
    """
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.current_stage_filter = "ALL_ACTIVE"
        self.selected_cockpit_rec = None
        self.current_timeline_items = []
        self.filtered_records = []

        self._build_ui()

    def on_activate(self):
        """Kokpit sekmesi aktif hale geldiğinde tabloyu ve detayları günceller."""
        self.refresh_cockpit_table()
        if hasattr(self, "selected_cockpit_rec") and self.selected_cockpit_rec:
            self._update_gtb_status_for_rec(self.selected_cockpit_rec)

    def _build_ui(self):
        # 1. Üst Metrik Kartları
        metric_bar = tk.Frame(self, bg="#f8fafc")
        metric_bar.pack(fill=tk.X, pady=(0, 10))

        self.card_c_active = self.create_metric_widget(
            metric_bar, "AÇIK DOSYALAR", "0", "Toplam Aktif", "#1e3a8a",
            lambda: self.set_stage_filter("ALL_ACTIVE")
        )
        self.card_c_mail_wait = self.create_metric_widget(
            metric_bar, "VERGİ MAİLİ BEKLEYEN", "0", "Acil Gönderim", "#dc2626",
            lambda: self.set_stage_filter("MAIL_WAITING")
        )
        self.card_c_tescil = self.create_metric_widget(
            metric_bar, "TESCİL / MUAYENE", "0", "Sarı / Kırmızı Hat", "#2563eb",
            lambda: self.set_stage_filter("3_TESCILDE")
        )
        self.card_c_ordino = self.create_metric_widget(
            metric_bar, "ORDİNO / TAREKS", "0", "İşlem Aşamasında", "#7c3aed",
            lambda: self.set_stage_filter("2_ORDINO_TAREKS")
        )
        self.card_c_closed = self.create_metric_widget(
            metric_bar, "KAPANDI / ARŞİV", "0", "Tamamlananlar", "#16a34a",
            lambda: self.set_stage_filter("5_KAPANDI")
        )

        # 2. Arama ve Filtreleme Barı
        search_bar = tk.Frame(self, bg="#ffffff", padx=12, pady=8, relief=tk.FLAT, bd=0)
        search_bar.pack(fill=tk.X, pady=(0, 10))

        lbl_s = tk.Label(
            search_bar, text="🔍 Hızlı Filtrele / Ara:",
            font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a"
        )
        lbl_s.pack(side=tk.LEFT, padx=(0, 8))

        self.txt_cockpit_search = tk.Entry(search_bar, font=("Segoe UI", 9), bd=1, relief=tk.SOLID)
        self.txt_cockpit_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=3)
        self.txt_cockpit_search.bind("<KeyRelease>", self._on_cockpit_search_change)

        # Hızlı Aşama Sekme Butonları (Stage Filter Tabs)
        f_stage_tabs = tk.Frame(search_bar, bg="#ffffff")
        f_stage_tabs.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_f_active = tk.Button(
            f_stage_tabs, text="⚡ Aktif", font=("Segoe UI", 8, "bold"),
            bg="#1e3a8a", fg="#ffffff", relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
            command=lambda: self.set_stage_filter("ALL_ACTIVE")
        )
        self.btn_f_active.pack(side=tk.LEFT, padx=2)

        self.btn_f_mail = tk.Button(
            f_stage_tabs, text="✉️ Vergi Bekleyen", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#dc2626", relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
            command=lambda: self.set_stage_filter("MAIL_WAITING")
        )
        self.btn_f_mail.pack(side=tk.LEFT, padx=2)

        self.btn_f_tescil = tk.Button(
            f_stage_tabs, text="🟢 Tescilde", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#2563eb", relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
            command=lambda: self.set_stage_filter("3_TESCILDE")
        )
        self.btn_f_tescil.pack(side=tk.LEFT, padx=2)

        self.btn_f_ordino = tk.Button(
            f_stage_tabs, text="📦 Ordino/Tareks", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#7c3aed", relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
            command=lambda: self.set_stage_filter("2_ORDINO_TAREKS")
        )
        self.btn_f_ordino.pack(side=tk.LEFT, padx=2)

        self.btn_f_closed = tk.Button(
            f_stage_tabs, text="📁 Kapandı", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#64748b", relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
            command=lambda: self.set_stage_filter("5_KAPANDI")
        )
        self.btn_f_closed.pack(side=tk.LEFT, padx=2)

        self.btn_f_all = tk.Button(
            f_stage_tabs, text="Tümü", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#0f172a", relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
            command=lambda: self.set_stage_filter("ALL")
        )
        self.btn_f_all.pack(side=tk.LEFT, padx=2)

        # Excel Aktarım Butonu
        self.btn_export_excel = tk.Button(
            search_bar,
            text="📥 Excel'e Aktar",
            font=("Segoe UI", 8, "bold"),
            bg="#107c41",
            fg="#ffffff",
            activebackground="#0b5e31",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.export_cockpit_to_excel
        )
        self.btn_export_excel.pack(side=tk.RIGHT, padx=(6, 0))

        self.lbl_cockpit_count = tk.Label(
            search_bar, text="0 Kayıt Gösteriliyor",
            font=("Segoe UI", 8, "bold"), fg="#1e40af", bg="#eff6ff", padx=8, pady=2
        )
        self.lbl_cockpit_count.pack(side=tk.RIGHT)

        # 3. İki Bölümlü Ana Alan (Sol: Tablo, Sağ: Detay Paneli)
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#f8fafc", sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        table_frame = tk.Frame(paned, bg="#ffffff", relief=tk.FLAT, bd=0)
        paned.add(table_frame, minsize=680, stretch="always")

        columns = ("dosya", "ref", "bl", "asama", "hat", "mail", "bayi", "liman")
        self.tree_cockpit = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)

        self.tree_cockpit.heading("dosya", text="Dosya No")
        self.tree_cockpit.heading("ref", text="Referans No")
        self.tree_cockpit.heading("bl", text="Konşimento (B/L)")
        self.tree_cockpit.heading("asama", text="Operasyonel Aşama")
        self.tree_cockpit.heading("hat", text="Hat")
        self.tree_cockpit.heading("mail", text="Vergi Maili Durumu")
        self.tree_cockpit.heading("bayi", text="Bayi / Alıcı")
        self.tree_cockpit.heading("liman", text="Liman")

        self.tree_cockpit.column("dosya", width=90, anchor="center")
        self.tree_cockpit.column("ref", width=105, anchor="center")
        self.tree_cockpit.column("bl", width=145, anchor="center")
        self.tree_cockpit.column("asama", width=175, anchor="w")
        self.tree_cockpit.column("hat", width=70, anchor="center")
        self.tree_cockpit.column("mail", width=180, anchor="w")
        self.tree_cockpit.column("bayi", width=130, anchor="w")
        self.tree_cockpit.column("liman", width=95, anchor="center")

        self.tree_cockpit.tag_configure("kirmizi_hat", background="#fef2f2", foreground="#991b1b")
        self.tree_cockpit.tag_configure("tescil_ok", background="#f4fffa", foreground="#166534")
        self.tree_cockpit.tag_configure("mail_ok", background="#f4fffa", foreground="#047857")
        self.tree_cockpit.tag_configure("mail_warning", background="#fff7ed", foreground="#c2410c")
        self.tree_cockpit.tag_configure("closed", background="#f8fafc", foreground="#64748b")

        self.tree_cockpit.bind("<<TreeviewSelect>>", self.on_cockpit_select)
        self.tree_cockpit.bind("<Double-1>", self._on_cockpit_double_click)
        self.tree_cockpit.bind("<Button-3>", self.show_cockpit_context_menu)

        # Sağ Tık Menüsü (Hızlı Aksiyonlar)
        self._setup_context_menu()

        sc_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree_cockpit.yview)
        self.tree_cockpit.configure(yscroll=sc_y.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_cockpit.pack(fill=tk.BOTH, expand=True)

        self.detail_frame = tk.Frame(paned, bg="#ffffff", padx=14, pady=12, relief=tk.FLAT, bd=0)
        paned.add(self.detail_frame, minsize=350, stretch="never")

        self.setup_cockpit_detail_panel()

    def _setup_context_menu(self):
        self.cockpit_menu = tk.Menu(self.tree_cockpit, tearoff=0)
        self.cockpit_menu.add_command(
            label="🔍 GTB Canlı Sorgula",
            command=self.query_selected_cockpit_gtb
        )
        self.cockpit_menu.add_command(
            label="📧 Vergi Talebi Maili Oluştur",
            command=self.open_mail_draft_dialog
        )
        self.cockpit_menu.add_command(
            label="📑 Evrim Detayına Git",
            command=self.navigate_to_evrim_detail
        )
        self.cockpit_menu.add_command(
            label="📜 Mail Zaman Tüneline Git",
            command=lambda: self.detail_nb.select(1) if hasattr(self, "detail_nb") else None
        )
        self.cockpit_menu.add_command(
            label="🛡️ Mail Güvenlik Kalkanında Sorgula",
            command=self.cross_inspect_selected_file
        )
        self.cockpit_menu.add_separator()
        self.cockpit_menu.add_command(
            label="💸 Bu Dosya İçin Para Talebi Aç",
            command=self.send_selected_cockpit_to_talep
        )
        self.cockpit_menu.add_separator()
        self.cockpit_menu.add_command(
            label="📋 Konşimento (B/L) Kopyala",
            command=self.copy_selected_bl
        )
        self.cockpit_menu.add_command(
            label="📋 Dosya Numarasını Kopyala",
            command=self.copy_selected_dosya
        )
        self.cockpit_menu.add_command(
            label="📋 Referans Numarasını Kopyala",
            command=self.copy_selected_ref
        )
        self.cockpit_menu.add_separator()
        self.cockpit_menu.add_command(
            label="📊 Excel'e Aktar",
            command=self.export_cockpit_to_excel
        )

    def create_metric_widget(self, parent, title, val, subtitle, accent_color, command):
        card = tk.Frame(parent, bg="#ffffff", padx=12, pady=8, relief=tk.FLAT, bd=0, cursor="hand2")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

        top_strip = tk.Frame(card, bg=accent_color, height=3)
        top_strip.pack(fill=tk.X, pady=(0, 4))

        lbl_t = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff", cursor="hand2")
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(card, text=val, font=("Segoe UI", 15, "bold"), fg=accent_color, bg="#ffffff", cursor="hand2")
        lbl_v.pack(anchor="w")

        lbl_sub = tk.Label(card, text=subtitle, font=("Segoe UI", 8), fg="#94a3b8", bg="#ffffff", cursor="hand2")
        lbl_sub.pack(anchor="w")

        if command:
            for w in (card, top_strip, lbl_t, lbl_v, lbl_sub):
                w.bind("<Button-1>", lambda e, cmd=command: cmd())

        return {"card": card, "val_lbl": lbl_v, "title": title}

    def setup_cockpit_detail_panel(self):
        head_box = tk.Frame(self.detail_frame, bg="#ffffff")
        head_box.pack(fill=tk.X, pady=(0, 6))

        lbl_head = tk.Label(
            head_box, text="📋 SEÇİLİ DOSYA DETAYI",
            font=("Segoe UI", 10, "bold"), fg="#0f172a", bg="#ffffff"
        )
        lbl_head.pack(side=tk.LEFT)

        self.lbl_c_dosya_badge = tk.Label(
            head_box, text="—",
            font=("Segoe UI", 9, "bold"), fg="#2563eb", bg="#eff6ff",
            padx=6, pady=2, relief=tk.GROOVE
        )
        self.lbl_c_dosya_badge.pack(side=tk.RIGHT)

        # Sekmeli Sağ Panel (Dosya Bilgileri + Mail Zaman Tüneli)
        self.detail_nb = ttk.Notebook(self.detail_frame)
        self.detail_nb.pack(fill=tk.BOTH, expand=True)

        tab_info = ttk.Frame(self.detail_nb)
        self.detail_nb.add(tab_info, text="  📋 Dosya Özeti  ")

        tab_timeline = ttk.Frame(self.detail_nb)
        self.tab_timeline_ref = tab_timeline
        self.detail_nb.add(tab_timeline, text="  📜 Mail Zaman Tüneli  ")

        # 1. SEKME: DOSYA BİLGİLERİ
        info_scroll = tk.Frame(tab_info, bg="#f8fafc", padx=10, pady=8, relief=tk.FLAT, bd=0)
        info_scroll.pack(fill=tk.BOTH, expand=True)

        self.lbl_c_ref = self.add_card_row(info_scroll, "🔖 Referans No:", "—")
        self.lbl_c_bl = self.add_card_row(info_scroll, "🚢 Konşimento (B/L):", "—")
        self.lbl_c_bayi = self.add_card_row(info_scroll, "🏢 Bayi / Alıcı:", "—")
        self.lbl_c_liman = self.add_card_row(info_scroll, "📍 Gümrük & Liman:", "—")

        sep1 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep1.pack(fill=tk.X, pady=4)

        self.lbl_c_stage = self.add_card_row(info_scroll, "⚡ Operasyonel Aşama:", "—")
        self.lbl_c_hat = self.add_card_row(info_scroll, "🚦 Hat Durumu:", "—")
        self.lbl_c_tescil = self.add_card_row(info_scroll, "📅 Tescil Tarihi:", "—")
        self.lbl_c_ordino = self.add_card_row(info_scroll, "📦 Ordino Teslim:", "—")
        self.lbl_c_tareks = self.add_card_row(info_scroll, "📋 Tareks Başvuru:", "—")

        sep2 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep2.pack(fill=tk.X, pady=4)

        lbl_m = tk.Label(
            info_scroll, text="📬 OUTLOOK VERGİ MAİL DURUMU",
            font=("Segoe UI", 8, "bold"), fg="#1e3a8a", bg="#f8fafc"
        )
        lbl_m.pack(anchor="w", pady=(2, 2))

        self.lbl_c_mail_status = self.add_card_row(info_scroll, "• Durum:", "—")
        self.lbl_c_mail_time = self.add_card_row(info_scroll, "• Gönderim Saati:", "—")
        self.lbl_c_mail_to = self.add_card_row(info_scroll, "• Alıcı:", "—")
        self.lbl_c_mail_atts = self.add_card_row(info_scroll, "• Ekler:", "—")

        sep3 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep3.pack(fill=tk.X, pady=4)

        self.lbl_c_aciklama = self.add_card_row(info_scroll, "📝 Açıklama:", "—")

        sep4 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep4.pack(fill=tk.X, pady=4)

        # ── GTB BAKANLIK CANLI DURUM BLOĞU ──────────────────────────────────
        self.frm_gtb_status_block = tk.Frame(info_scroll, bg="#f8fafc")
        self.frm_gtb_status_block.pack(fill=tk.X)

        lbl_gtb_head = tk.Label(
            self.frm_gtb_status_block,
            text="🏛️ GTB BAKANLIK CANLI DURUM",
            font=("Segoe UI", 8, "bold"), fg="#0369a1", bg="#f8fafc"
        )
        lbl_gtb_head.pack(anchor="w", pady=(0, 3))

        # Durum rozeti (renk dinamik değişir)
        self.lbl_c_gtb_badge = tk.Label(
            self.frm_gtb_status_block,
            text="🔍 Takip Havuzunda Bulunamadı",
            font=("Segoe UI", 8), fg="#64748b", bg="#f1f5f9",
            padx=6, pady=3, anchor="w", wraplength=240, justify="left"
        )
        self.lbl_c_gtb_badge.pack(fill=tk.X, pady=(0, 2))

        self.lbl_c_gtb_time = tk.Label(
            self.frm_gtb_status_block,
            text="", font=("Segoe UI", 7), fg="#94a3b8", bg="#f8fafc"
        )
        self.lbl_c_gtb_time.pack(anchor="w")

        # 2. SEKME: CANLI MAİL ZAMAN TÜNELİ (TIMELINE)
        f_tl = tk.Frame(tab_timeline, bg="#ffffff", padx=6, pady=6)
        f_tl.pack(fill=tk.BOTH, expand=True)

        self.lbl_tl_status = tk.Label(
            f_tl, text="Dosya seçildiğinde mail akışı taranır.",
            font=("Segoe UI", 8, "italic"), fg="#64748b", bg="#ffffff"
        )
        self.lbl_tl_status.pack(anchor="w", pady=(0, 4))

        tl_tree_box = tk.Frame(f_tl, bg="#ffffff", relief=tk.FLAT, bd=0)
        tl_tree_box.pack(fill=tk.BOTH, expand=True)

        tl_cols = ("yon", "tarih", "muhatap", "konu", "ekler")
        self.tree_timeline = ttk.Treeview(tl_tree_box, columns=tl_cols, show="headings", height=8)

        self.tree_timeline.heading("yon", text="Yön")
        self.tree_timeline.heading("tarih", text="Tarih/Saat")
        self.tree_timeline.heading("muhatap", text="Muhatap")
        self.tree_timeline.heading("konu", text="Konu")
        self.tree_timeline.heading("ekler", text="Ek")

        self.tree_timeline.column("yon", width=55, anchor="center")
        self.tree_timeline.column("tarih", width=95, anchor="center")
        self.tree_timeline.column("muhatap", width=110, anchor="w")
        self.tree_timeline.column("konu", width=140, anchor="w")
        self.tree_timeline.column("ekler", width=45, anchor="center")

        self.tree_timeline.tag_configure("giden_mail", background="#f0fdf4", foreground="#166534")
        self.tree_timeline.tag_configure("gelen_mail", background="#eff6ff", foreground="#1e40af")

        sc_tl = ttk.Scrollbar(tl_tree_box, orient=tk.VERTICAL, command=self.tree_timeline.yview)
        self.tree_timeline.configure(yscroll=sc_tl.set)
        sc_tl.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_timeline.pack(fill=tk.BOTH, expand=True)

        self.tree_timeline.bind("<Double-1>", self.on_timeline_double_click)

        btn_open_mail = tk.Button(
            f_tl,
            text="📬 Seçili Maili Outlook'ta Aç",
            font=("Segoe UI", 8, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            activebackground="#e2e8f0",
            relief=tk.SOLID,
            bd=1,
            pady=3,
            cursor="hand2",
            command=self.on_timeline_open_click
        )
        btn_open_mail.pack(fill=tk.X, pady=(4, 0))

        # ALT AKSİYON BUTONLARI
        btn_action_box = tk.Frame(self.detail_frame, bg="#ffffff")
        btn_action_box.pack(fill=tk.X, pady=(6, 0))

        btn_auto_draft = tk.Button(
            btn_action_box,
            text="✉️ Vergi Maili Taslağı Aç (Seçilen Dosyalar)",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=5,
            cursor="hand2",
            command=self.open_mail_draft_dialog
        )
        btn_auto_draft.pack(fill=tk.X, pady=(0, 3))

        btn_cockpit_gtb = tk.Button(
            btn_action_box,
            text="🏛️ GTB Bakanlık'tan Canlı Sorgula",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=4,
            cursor="hand2",
            command=self.query_selected_cockpit_gtb
        )
        btn_cockpit_gtb.pack(fill=tk.X, pady=(0, 3))

        btn_cockpit_evrim = tk.Button(
            btn_action_box,
            text="📑 Evrim Detayına Git & Sorgula",
            font=("Segoe UI", 8, "bold"),
            bg="#475569",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=4,
            cursor="hand2",
            command=self.navigate_to_evrim_detail
        )
        btn_cockpit_evrim.pack(fill=tk.X, pady=(0, 3))

        btn_cross_inspect = tk.Button(
            btn_action_box,
            text="🛡️ Mail Güvenlik Kalkanında İncele",
            font=("Segoe UI", 8, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=4,
            cursor="hand2",
            command=self.cross_inspect_selected_file
        )
        btn_cross_inspect.pack(fill=tk.X, pady=(0, 3))

        btn_cockpit_talep = tk.Button(
            btn_action_box,
            text="💸 Bu Dosya İçin Para Talebi Aç",
            font=("Segoe UI", 8, "bold"),
            bg="#107c41",
            fg="#ffffff",
            activebackground="#0b5e31",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=4,
            cursor="hand2",
            command=self.send_selected_cockpit_to_talep
        )
        btn_cockpit_talep.pack(fill=tk.X)

    def add_card_row(self, parent, label_text, default_val):
        row = tk.Frame(parent, bg="#f8fafc")
        row.pack(fill=tk.X, pady=1)

        lbl_k = tk.Label(row, text=label_text, font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc", width=17, anchor="w")
        lbl_k.pack(side=tk.LEFT)

        lbl_v = tk.Label(row, text=default_val, font=("Segoe UI", 8, "bold"), fg="#0f172a", bg="#f8fafc", anchor="w", wraplength=180, justify=tk.LEFT)
        lbl_v.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return lbl_v

    # -------------------------------------------------------------------------
    # Filtreleme ve Arama Metodları
    # -------------------------------------------------------------------------
    def set_stage_filter(self, stage_code):
        """Aşama filtresini ayarlar ve tabloyu günceller."""
        self.current_stage_filter = stage_code
        self._update_stage_button_styles()
        self.apply_cockpit_filter()

    def _update_stage_button_styles(self):
        """Aktif aşama filtresi butonunu belirginleştirir."""
        st = self.current_stage_filter
        btns = [
            ("ALL_ACTIVE", self.btn_f_active),
            ("MAIL_WAITING", self.btn_f_mail),
            ("3_TESCILDE", self.btn_f_tescil),
            ("2_ORDINO_TAREKS", self.btn_f_ordino),
            ("5_KAPANDI", self.btn_f_closed),
            ("ALL", self.btn_f_all)
        ]
        for code, btn in btns:
            if code == st:
                btn.config(bg="#1e3a8a", fg="#ffffff")
            else:
                btn.config(bg="#f1f5f9", fg="#475569")

    def _on_cockpit_search_change(self, event=None):
        """Arama kutusu tuş vuruşlarını işler."""
        self.apply_cockpit_filter()

    def refresh_cockpit_table(self):
        """Tabloyu ve metrikleri tamamen yeniler."""
        self.update_metrics()
        self.apply_cockpit_filter()

    def update_metrics(self):
        """Metrik kartlarındaki sayıları hesaplayıp günceller."""
        records = getattr(self.engine, "records", [])
        total_open = sum(1 for r in records if not r.get("kapanis"))
        tescil_count = sum(1 for r in records if not r.get("kapanis") and (r.get("stage") in ["3_TESCILDE", "3_MUAYENE"]))
        mail_waiting_count = sum(1 for r in records if not r.get("kapanis") and r.get("is_tax_pending") and r.get("mail_badge") == "red")
        ordino_count = sum(1 for r in records if not r.get("kapanis") and r.get("stage") == "2_ORDINO_TAREKS")
        closed_count = sum(1 for r in records if r.get("kapanis"))

        if hasattr(self, "card_c_active"):
            self.card_c_active["val_lbl"].config(text=str(total_open))
            self.card_c_mail_wait["val_lbl"].config(text=str(mail_waiting_count))
            self.card_c_tescil["val_lbl"].config(text=str(tescil_count))
            self.card_c_ordino["val_lbl"].config(text=str(ordino_count))
            self.card_c_closed["val_lbl"].config(text=str(closed_count))

    def apply_cockpit_filter(self):
        """Aktif filtre ve arama sorgusuna göre Treeview tablosunu doldurur."""
        st = self.current_stage_filter
        records = getattr(self.engine, "records", [])

        if st == "ALL_ACTIVE":
            subset = [r for r in records if not r.get("kapanis")]
        elif st == "MAIL_WAITING":
            subset = [r for r in records if not r.get("kapanis") and r.get("is_tax_pending") and r.get("mail_badge") == "red"]
        elif st == "3_TESCILDE":
            subset = [r for r in records if not r.get("kapanis") and r.get("stage") in ["3_TESCILDE", "3_MUAYENE"]]
        elif st == "2_ORDINO_TAREKS":
            subset = [r for r in records if not r.get("kapanis") and r.get("stage") == "2_ORDINO_TAREKS"]
        elif st == "5_KAPANDI":
            subset = [r for r in records if r.get("kapanis")]
        else:
            subset = records[:]

        query = self.txt_cockpit_search.get().strip().upper() if hasattr(self, "txt_cockpit_search") else ""
        final_list = []
        for r in subset:
            full_str = f"{r.get('dosya', '')} {r.get('ref', '')} {r.get('bl', '')} {r.get('bayi', '')} {r.get('acenta', '')} {r.get('liman', '')} {r.get('gumruk', '')} {r.get('hat', '')} {r.get('stage_title', '')} {r.get('aciklama', '')} {r.get('konteyner', '')} {r.get('gemi', '')} {r.get('beyanname_no', '')} {r.get('beyan_no', '')}".upper()
            if not query or query in full_str:
                final_list.append(r)

        self.filtered_records = final_list

        for item in self.tree_cockpit.get_children():
            self.tree_cockpit.delete(item)

        for idx, r in enumerate(final_list):
            tag = "normal"
            if r.get("kapanis"):
                tag = "closed"
            elif r.get("hat") == "KIRMIZI":
                tag = "kirmizi_hat"
            elif r.get("mail_badge") == "red":
                tag = "mail_warning"
            elif r.get("stage") in ["3_TESCILDE", "3_MUAYENE"]:
                tag = "tescil_ok"
            elif r.get("mail_badge") == "green":
                tag = "mail_ok"

            r_iid = str(r["row_idx"]) if r.get("row_idx") is not None and str(r.get("row_idx")) != "" else f"row_{idx}"

            self.tree_cockpit.insert("", tk.END, values=(
                r.get("dosya") or "—",
                r.get("ref") or "—",
                r.get("bl") or "—",
                r.get("stage_title", ""),
                r.get("hat") or "—",
                r.get("mail_status", ""),
                r.get("bayi") or "—",
                r.get("liman") or "—"
            ), tags=(tag,), iid=r_iid)

        self.lbl_cockpit_count.config(text=f"{len(final_list)} Kayıt Listeleniyor")

    # -------------------------------------------------------------------------
    # Seçim ve Detay Drawer / Panel Metodları
    # -------------------------------------------------------------------------
    def on_cockpit_select(self, event=None):
        """Kullanıcı tablodan bir satır seçtiğinde detay panelini günceller."""
        sel = self.tree_cockpit.selection()
        if not sel:
            return

        try:
            row_idx = sel[0]
            records = getattr(self.engine, "records", []) or self.filtered_records
            rec = next((r for r in records if str(r.get("row_idx")) == str(row_idx)), None)
            if not rec and hasattr(self, "filtered_records"):
                rec = next((r for r in self.filtered_records if str(r.get("row_idx")) == str(row_idx)), None)
            if rec:
                self.show_cockpit_detail_drawer(rec)
        except Exception as e:
            print(f"Cockpit select error: {e}")

    def show_cockpit_detail_drawer(self, rec):
        """Seçili kaydın bilgilerini detay paneline yükler."""
        if not rec:
            return

        self.selected_cockpit_rec = rec

        self.lbl_c_dosya_badge.config(text=rec.get("dosya") or "Dosya No Yok")
        self.lbl_c_ref.config(text=rec.get("ref") or "—")
        self.lbl_c_bl.config(text=rec.get("bl") or "—")
        self.lbl_c_bayi.config(text=rec.get("bayi") or "—")
        self.lbl_c_liman.config(text=f"{rec.get('gumruk') or '—'} / {rec.get('liman') or '—'}")

        self.lbl_c_stage.config(text=rec.get("stage_title", "—"))
        self.lbl_c_hat.config(text=rec.get("hat") or "—")
        self.lbl_c_tescil.config(text=rec.get("tescil") or "—")
        self.lbl_c_ordino.config(text=rec.get("ordino") or "—")
        self.lbl_c_tareks.config(text=rec.get("tareks") or "—")

        self.lbl_c_mail_status.config(text=rec.get("mail_status", "—"))
        self.lbl_c_mail_time.config(text=rec.get("mail_date") or "—")
        self.lbl_c_mail_to.config(text=rec.get("mail_to") or "—")
        atts = rec.get("mail_attachments", [])
        self.lbl_c_mail_atts.config(text=", ".join(atts) if atts else "—")
        self.lbl_c_aciklama.config(text=rec.get("aciklama") or "Yok")

        # GTB Takip Havuzuyla Eşleştir
        self._update_gtb_status_for_rec(rec)

        # Zaman Tüneli Yükleme
        self.load_selected_file_timeline(rec)

    def _on_cockpit_double_click(self, event=None):
        """Satıra çift tıklandığında detayları ve zaman tünelini öne çıkarır."""
        sel = self.tree_cockpit.selection()
        if sel:
            self.on_cockpit_select(event)
            if hasattr(self, "detail_nb"):
                self.detail_nb.select(0)

    def show_cockpit_context_menu(self, event):
        """Tabloda sağ tıklandığında dinamik ve zengin aksiyon menüsünü açar."""
        iid = self.tree_cockpit.identify_row(event.y)
        current_sel = list(self.tree_cockpit.selection())
        if iid and iid not in current_sel:
            self.tree_cockpit.selection_set(iid)
            current_sel = [iid]
            self.on_cockpit_select(None)

        if not current_sel:
            return

        sel_count = len(current_sel)
        menu = tk.Menu(self.tree_cockpit, tearoff=0)

        # 1. Temel Aksiyonlar
        if sel_count == 1:
            menu.add_command(label="🔍 GTB Canlı Sorgula", command=self.query_selected_cockpit_gtb)
            menu.add_command(label="📧 Vergi Talebi Maili Oluştur", command=self.open_mail_draft_dialog)
            menu.add_command(label="🤖 Otonom RPA İstasyonuna Gönder", command=self.send_selected_to_rpa)
            menu.add_command(label="📑 Evrim Detayına Git", command=self.navigate_to_evrim_detail)
            menu.add_command(label="📜 Mail Zaman Tüneline Git", command=lambda: self.detail_nb.select(1) if hasattr(self, "detail_nb") else None)
            menu.add_command(label="🛡️ Mail Güvenlik Kalkanında Sorgula", command=self.cross_inspect_selected_file)
            menu.add_command(label="💸 Bu Dosya İçin Para Talebi Aç", command=self.send_selected_cockpit_to_talep)
        else:
            menu.add_command(label=f"📧 Seçili ({sel_count}) Dosya İçin Vergi Talebi Maili Oluştur", command=self.open_mail_draft_dialog)
            menu.add_command(label=f"🤖 Seçili ({sel_count}) Dosyayı Otonom RPA İstasyonuna Gönder", command=self.send_selected_to_rpa)
            menu.add_command(label=f"🔍 Seçili ({sel_count}) Dosyayı GTB'de Canlı Sorgula", command=self.query_selected_cockpit_gtb)

        menu.add_separator()

        # 2. Seçili Sütun Kopyalama
        lbl_dosya = f"📋 Seçili ({sel_count}) Dosya No'ları Kopyala (Alt Alta)" if sel_count > 1 else "📋 Dosya Numarasını Kopyala"
        lbl_ref = f"📋 Seçili ({sel_count}) Referans No'ları Kopyala (Alt Alta)" if sel_count > 1 else "📋 Referans Numarasını Kopyala"
        lbl_bl = f"📋 Seçili ({sel_count}) Konşimento (B/L) Kopyala (Alt Alta)" if sel_count > 1 else "📋 Konşimento (B/L) Kopyala"

        menu.add_command(label=lbl_dosya, command=lambda: self.copy_column_values("dosya", "Dosya No", only_selected=True))
        menu.add_command(label=lbl_ref, command=lambda: self.copy_column_values("ref", "Referans No", only_selected=True))
        menu.add_command(label=lbl_bl, command=lambda: self.copy_column_values("bl", "Konşimento (B/L)", only_selected=True))
        if sel_count > 1:
            menu.add_command(label=f"📋 Seçili ({sel_count}) Satırı Excel Tablosu Olarak Kopyala", command=self.copy_selected_rows_as_table)

        menu.add_separator()

        # 3. Tablodaki TÜM Sütunları Kopyalama Alt Menüsü
        all_recs = self.filtered_records or getattr(self.engine, "records", []) or []
        all_count = len(all_recs)
        all_menu = tk.Menu(menu, tearoff=0)
        all_menu.add_command(label=f"📑 Tablodaki TÜM Dosya No'ları Kopyala ({all_count} Satır)", command=lambda: self.copy_column_values("dosya", "Dosya No", only_selected=False))
        all_menu.add_command(label=f"📑 Tablodaki TÜM Referans No'ları Kopyala ({all_count} Satır)", command=lambda: self.copy_column_values("ref", "Referans No", only_selected=False))
        all_menu.add_command(label=f"📑 Tablodaki TÜM Konşimentoları Kopyala ({all_count} Satır)", command=lambda: self.copy_column_values("bl", "Konşimento", only_selected=False))
        menu.add_cascade(label=f"📑 Tablodaki TÜM Sütunları Kopyala ({all_count} Satır)...", menu=all_menu)

        menu.add_separator()
        menu.add_command(label="📊 Excel'e Aktar (.xlsx)", command=self.export_cockpit_to_excel)

        menu.tk_popup(event.x_root, event.y_root)

    # -------------------------------------------------------------------------
    # GTB Bakanlık Durum ve Entegrasyon
    # -------------------------------------------------------------------------
    def _update_gtb_status_for_rec(self, rec):
        """GTB takip havuzundan bu dosyanın beyannamesini bulur ve Dosya Özeti'ne yansıtır."""
        if not hasattr(self, "lbl_c_gtb_badge"):
            return

        gtb_tracker = getattr(self.app, "gtb_tracker", None)
        if not gtb_tracker:
            self.lbl_c_gtb_badge.config(
                text="⚠️ GTB İzleme Servisi Başlatılmadı",
                fg="#92400e", bg="#fffbeb"
            )
            self.lbl_c_gtb_time.config(text="")
            return

        rec_beyan = (rec.get("beyanname_no") or rec.get("beyan_no") or "").strip().upper()
        rec_ref = (rec.get("ref") or "").strip().upper()
        rec_dosya = (rec.get("dosya") or "").strip().upper()

        # Evrim canlı verisinden beyanname eşleştirmesi
        if not rec_beyan:
            evrim_records = getattr(self.app, "evrim_records", []) or []
            for ev in evrim_records:
                ev_dosya = str(ev.get("dosya_no") or "").strip().upper()
                ev_ref = str(ev.get("hankook_ref") or ev.get("musteri_referans") or "").strip().upper()
                if (rec_dosya and rec_dosya in ev_dosya) or (rec_ref and rec_ref in ev_ref):
                    b = ev.get("beyanname_no") or ev.get("gumruk_beyanname_no")
                    if b and len(str(b)) >= 8:
                        rec_beyan = str(b).strip().upper()
                        break

        tracked_records = gtb_tracker.list_tracked(only_active=False)
        gtb_match = None

        for tr in tracked_records:
            tr_beyan = (tr.get("beyanname_no") or "").strip().upper()
            tr_ref = (tr.get("ref") or tr.get("ref_no") or "").strip().upper()
            tr_dosya = (tr.get("dosya_no") or "").strip().upper()

            if rec_beyan and tr_beyan and rec_beyan == tr_beyan:
                gtb_match = tr
                break
            if rec_ref and tr_ref and rec_ref == tr_ref:
                gtb_match = tr
                break
            if rec_dosya and tr_dosya and rec_dosya == tr_dosya:
                gtb_match = tr
                break

        if not gtb_match:
            self.lbl_c_gtb_badge.config(
                text="🔍 GTB Takip Havuzunda Yok",
                fg="#64748b", bg="#f1f5f9"
            )
            self.lbl_c_gtb_time.config(text="GTB beyanname takibine alınmamış.")
            return

        durum = (gtb_match.get("durum") or "İzleniyor").strip()
        kapandi = gtb_match.get("kapandi", False)
        son_chk = gtb_match.get("son_kontrol") or gtb_match.get("son_sorgu_zamani") or "—"

        if kapandi or "tamamland" in durum.lower() or "kapan" in durum.lower():
            badge_fg = "#166534"
            badge_bg = "#dcfce7"
            ikon = "✅"
        elif "işlemde" in durum.lower() or "muayene" in durum.lower() or "tescil" in durum.lower():
            badge_fg = "#92400e"
            badge_bg = "#fef3c7"
            ikon = "⚙️"
        elif "bekleniyor" in durum.lower() or "henüz" in durum.lower():
            badge_fg = "#1e40af"
            badge_bg = "#dbeafe"
            ikon = "⏳"
        else:
            badge_fg = "#1e3a8a"
            badge_bg = "#eff6ff"
            ikon = "🏛️"

        self.lbl_c_gtb_badge.config(
            text=f"{ikon} {durum}",
            fg=badge_fg, bg=badge_bg
        )
        self.lbl_c_gtb_time.config(
            text=f"Son GTB Kontrolü: {son_chk}   |   Beyan No: {gtb_match.get('beyanname_no', '—')}"
        )

    def _refresh_cockpit_gtb_badge(self):
        """Cockpit'te seçili dosyanın GTB rozetini yeniden hesaplar."""
        try:
            rec = getattr(self, "selected_cockpit_rec", None)
            if rec and hasattr(self, "lbl_c_gtb_badge"):
                self._update_gtb_status_for_rec(rec)
        except Exception:
            pass

    def query_selected_cockpit_gtb(self):
        """Seçili dosyayı GTB Bakanlık sisteminden canlı sorgular."""
        sel = self.tree_cockpit.selection()
        if not sel:
            self.show_warning("Uyarı", "Lütfen GTB'den sorgulamak istediğiniz bir dosya seçin.")
            return

        item_vals = self.tree_cockpit.item(sel[0], "values")
        dosya = item_vals[0] if len(item_vals) > 0 else ""
        ref = item_vals[1] if len(item_vals) > 1 else ""

        target_beyan = None
        evrim_records = getattr(self.app, "evrim_records", []) or []
        for ev in evrim_records:
            d_c = re.sub(r"[^A-Z0-9]", "", str(ev.get("dosya_no") or "").upper())
            r_c = re.sub(r"[^A-Z0-9]", "", str(ev.get("hankook_ref") or ev.get("musteri_referans") or "").upper())
            if (dosya and dosya.replace("-", "") in d_c) or (ref and ref in r_c):
                b = ev.get("beyanname_no") or ev.get("gumruk_beyanname_no")
                if b and len(str(b)) >= 8:
                    target_beyan = str(b).strip()
                    break

        if not target_beyan:
            target_beyan = ref if len(ref) >= 8 else dosya

        if not target_beyan:
            self.show_warning("Uyarı", "Seçili kayda ait geçerli bir beyanname veya referans numarası bulunamadı.")
            return

        if hasattr(self.app, "query_selected_gtb_row"):
            self.app.query_selected_gtb_row(target_beyan)
        else:
            gtb_v = self.app.views.get("GTB_TAKIP") if hasattr(self.app, "views") else getattr(self.app, "view_gtb_takip", None)
            if gtb_v and hasattr(gtb_v, "query_selected_gtb_row"):
                gtb_v.query_selected_gtb_row(target_beyan)
            elif getattr(self.app, "gtb_tracker", None):
                self.set_header_subtitle(f"⏳ GTB Canlı Sorgu yapılıyor: {target_beyan}...")
                def _worker():
                    res = self.app.gtb_tracker.query_single_now(target_beyan)
                    def _done():
                        if res.get("success"):
                            self.set_header_subtitle(f"✅ GTB Sorgusu Tamamlandı: {target_beyan}", fg="#166534")
                            self._refresh_cockpit_gtb_badge()
                            self.show_info("GTB Canlı Sonuç", f"📑 Beyanname / Ref: {target_beyan}\n\n🏛️ Bakanlık Durumu:\n{res.get('durum')}")
                        else:
                            self.set_header_subtitle(f"⚠️ GTB Sorgu Hatası: {target_beyan}", fg="#dc2626")
                            self.show_error("GTB Sorgu Hatası", f"Sorgulama başarısız:\n{res.get('error')}")
                    root = getattr(self.app, "root", None) or self.winfo_toplevel()
                    root.after(0, _done)
                threading.Thread(target=_worker, daemon=True).start()
            else:
                self.show_info("GTB Sorgu", f"Beyanname No: {target_beyan}")

    # -------------------------------------------------------------------------
    # Mail Zaman Tüneli (Timeline) Metodları
    # -------------------------------------------------------------------------
    def load_selected_file_timeline(self, rec):
        """Seçili dosyanın Outlook mail akışını asenkron olarak çeker ve listeler."""
        for item in self.tree_timeline.get_children():
            try:
                self.tree_timeline.delete(item)
            except Exception:
                pass

        self.current_timeline_items = []
        self.lbl_tl_status.config(text="⏳ Mail akışı Outlook'tan taranıyor...")
        target_row_idx = rec.get("row_idx")

        def _fetch():
            timeline = self.engine.fetch_file_mail_timeline(rec)

            def _render():
                if not hasattr(self, "selected_cockpit_rec") or self.selected_cockpit_rec.get("row_idx") != target_row_idx:
                    return

                for item in self.tree_timeline.get_children():
                    try:
                        self.tree_timeline.delete(item)
                    except Exception:
                        pass

                self.current_timeline_items = timeline
                for idx, m in enumerate(timeline):
                    tag = "giden_mail" if m.get("direction") == "OUT" else "gelen_mail"
                    atts = m.get("attachments", [])
                    att_icon = f"📎 ({len(atts)})" if atts else "—"
                    self.tree_timeline.insert("", tk.END, values=(
                        m.get("label", ""),
                        m.get("time_str", ""),
                        m.get("party", ""),
                        m.get("subject", ""),
                        att_icon
                    ), tags=(tag,), iid=str(idx))

                count = len(timeline)
                if count > 0:
                    self.lbl_tl_status.config(text=f"✅ {count} adet ilgili mail bulundu (Çift tıkla aç).")
                else:
                    self.lbl_tl_status.config(text="ℹ️ Bu dosyaya ait Outlook mail akışı bulunamadı.")

                if hasattr(self, "detail_nb"):
                    try:
                        self.detail_nb.tab(1, text=f"  📜 Mail Zaman Tüneli ({count})  ")
                    except Exception:
                        pass

            root = getattr(self.app, "root", None) or self.winfo_toplevel()
            root.after(0, _render)

        threading.Thread(target=_fetch, daemon=True).start()

    def on_timeline_double_click(self, event=None):
        self.on_timeline_open_click()

    def on_timeline_open_click(self):
        """Zaman tünelinde seçili maili Outlook'ta açar."""
        sel = self.tree_timeline.selection()
        if not sel or not hasattr(self, "current_timeline_items"):
            return
        try:
            idx = int(sel[0])
            if 0 <= idx < len(self.current_timeline_items):
                entry_id = self.current_timeline_items[idx].get("entry_id")
                if entry_id:
                    ok = self.engine.open_outlook_mail_by_id(entry_id)
                    if not ok:
                        self.show_warning("Uyarı", "Mail Outlook'ta açılamadı.")
        except Exception as e:
            print(f"Timeline open error: {e}")

    # -------------------------------------------------------------------------
    # Aksiyon Metodları: Vergi Maili, Kalkan, Evrim, Para Talebi, Excel, Kopyalama
    # -------------------------------------------------------------------------
    def trigger_auto_tax_draft(self):
        """Seçili dosyalar için otomatik vergi talebi mail taslağı hazırlar."""
        self.open_mail_draft_dialog()

    def open_mail_draft_dialog(self):
        """Seçili dosyalar için Outlook'ta Vergi Talebi taslağı açar."""
        sel = self.tree_cockpit.selection()
        if not sel:
            self.show_warning(
                "Uyarı",
                "Lütfen önce tablodan bir veya birden fazla dosya seçin!\n\n(Çoklu seçim için Ctrl veya Shift tuşunu basılı tutarak satırlara tıklayabilirsiniz)"
            )
            return

        records = getattr(self.engine, "records", []) or self.filtered_records
        selected_records = []
        for item_id in sel:
            try:
                rec = next((r for r in records if str(r.get("row_idx")) == str(item_id)), None)
                if not rec and hasattr(self, "filtered_records"):
                    rec = next((r for r in self.filtered_records if str(r.get("row_idx")) == str(item_id)), None)
                if rec:
                    selected_records.append(rec)
            except Exception:
                continue

        if not selected_records:
            self.show_warning("Uyarı", "Seçili dosya bilgisi alınamadı.")
            return

        self.set_header_subtitle(f"⏳ {len(selected_records)} dosya için vergi maili taslağı ve ekleri Outlook'ta hazırlanıyor, lütfen bekleyin...")

        def _worker():
            ok, msg = self.engine.create_tax_mail_draft(selected_records)

            def _done():
                if ok:
                    self.set_header_subtitle(f"✅ {len(selected_records)} dosya için Vergi Talebi taslağı Outlook'ta açıldı!", fg="#166534")
                else:
                    self.set_header_subtitle("⚠️ Vergi mail taslağı oluşturulamadı.", fg="#dc2626")
                    self.show_error("Hata", msg)

            root = getattr(self.app, "root", None) or self.winfo_toplevel()
            root.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def cross_inspect_selected_file(self):
        """Seçili dosyayı Mail Güvenlik Kalkanı sekmesinde sorgular."""
        if not hasattr(self, "selected_cockpit_rec") or not self.selected_cockpit_rec:
            sel = self.tree_cockpit.selection()
            if sel:
                self.on_cockpit_select(None)

        if hasattr(self, "selected_cockpit_rec") and self.selected_cockpit_rec:
            ref = self.selected_cockpit_rec.get("ref") or self.selected_cockpit_rec.get("dosya") or self.selected_cockpit_rec.get("bl") or ""
            if hasattr(self.app, "do_shield_quick_search"):
                self.app.do_shield_quick_search(ref)
            else:
                self.switch_tab("SHIELD")
                shield_v = self.app.views.get("SHIELD") if hasattr(self.app, "views") else getattr(self.app, "view_shield", None)
                if shield_v:
                    if hasattr(shield_v, "txt_shield_query"):
                        shield_v.txt_shield_query.delete(0, tk.END)
                        shield_v.txt_shield_query.insert(0, ref)
                    if hasattr(shield_v, "do_shield_quick_search"):
                        shield_v.do_shield_quick_search()

    def navigate_to_evrim_detail(self):
        """Seçili dosyayı Evrim Canlı Veri Gezgini sekmesinde açar ve filtreler."""
        if not hasattr(self, "selected_cockpit_rec") or not self.selected_cockpit_rec:
            sel = self.tree_cockpit.selection()
            if sel:
                self.on_cockpit_select(None)

        if hasattr(self, "selected_cockpit_rec") and self.selected_cockpit_rec:
            rec = self.selected_cockpit_rec
            target_key = (rec.get("ref") or rec.get("dosya") or rec.get("bl") or "").strip()
            if target_key:
                if hasattr(self.app, "navigate_to_evrim_detail"):
                    self.app.navigate_to_evrim_detail(target_key)
                else:
                    self.switch_tab("EVRIM_EXPLORER")
                    evrim_v = self.app.views.get("EVRIM_EXPLORER") if hasattr(self.app, "views") else getattr(self.app, "view_evrim", None)
                    if evrim_v:
                        if hasattr(evrim_v, "txt_ev_search"):
                            evrim_v.txt_ev_search.delete(0, tk.END)
                            evrim_v.txt_ev_search.insert(0, target_key)
                        if hasattr(evrim_v, "apply_evrim_filters"):
                            evrim_v.apply_evrim_filters()
            else:
                self.switch_tab("EVRIM_EXPLORER")
        else:
            self.switch_tab("EVRIM_EXPLORER")

    def send_selected_cockpit_to_talep(self):
        """Seçili dosya için Para Talebi modülüne aktarım yapar."""
        sel = self.tree_cockpit.selection()
        if not sel:
            self.show_warning("Uyarı", "Lütfen önce tablodan bir dosya seçin!")
            return

        row_idx = sel[0]
        records = getattr(self.engine, "records", []) or self.filtered_records
        rec = next((r for r in records if str(r.get("row_idx")) == str(row_idx)), None)
        if not rec and hasattr(self, "selected_cockpit_rec"):
            rec = self.selected_cockpit_rec
        if not rec:
            self.show_warning("Uyarı", "Seçili dosya bilgisi bulunamadı.")
            return

        dosya_no = rec.get("dosya", "").strip()
        ref_no = rec.get("ref", "").strip()
        liman = rec.get("liman", "").strip()

        target_ref = dosya_no or ref_no
        self.copy_to_clipboard(target_ref)

        payload = {
            "dosyaNo": dosya_no,
            "ref": ref_no,
            "liman": liman,
            "aciklama": "ARDİYE FATURASI"
        }
        if hasattr(self.app, "send_to_talep_form"):
            self.app.send_to_talep_form(payload)
        else:
            talep_v = self.app.views.get("TALEP") if hasattr(self.app, "views") else getattr(self.app, "view_talep", None)
            if talep_v and hasattr(talep_v, "send_to_talep_form"):
                talep_v.send_to_talep_form(payload)
            else:
                self.show_info("Para Talebi", f"Talep hazırlandı: {payload}")

    def send_selected_to_rpa(self):
        """Seçili dosyaları Otonom RPA İstasyonu kuyruğuna gönderir ve sekmeyi açar."""
        recs = self.get_selected_cockpit_records()
        if not recs:
            self.show_warning("Uyarı", "Lütfen önce tablodan dosya seçin.")
            return

        items = []
        for r in recs:
            items.append({
                "dosya_no": r.get("dosya", ""),
                "ref": r.get("ref", ""),
                "beyanname_no": r.get("beyanname_no") or r.get("beyan_no", ""),
                "gemi": r.get("gemi", "")
            })

        rpa_view = getattr(self.app, "view_rpa", None) or (self.app.views.get("RPA_STATION") if hasattr(self.app, "views") else None)
        if rpa_view and hasattr(rpa_view, "add_external_files_to_queue"):
            rpa_view.add_external_files_to_queue(items)
            self.switch_tab("RPA_STATION")
            self.show_info("RPA İstasyonu", f"✅ {len(items)} adet dosya Otonom RPA İstasyonu kuyruğuna aktarıldı!")
        else:
            self.switch_tab("RPA_STATION")

    def get_selected_cockpit_records(self):
        """Seçili satırların kayıt objelerini döndürür."""
        sel = self.tree_cockpit.selection()
        records = getattr(self.engine, "records", []) or self.filtered_records or []
        selected_recs = []
        for item_id in sel:
            rec = next((r for r in records if str(r.get("row_idx")) == str(item_id)), None)
            if not rec and hasattr(self, "filtered_records") and self.filtered_records:
                rec = next((r for r in self.filtered_records if str(r.get("row_idx")) == str(item_id)), None)
            if not rec:
                vals = self.tree_cockpit.item(item_id, "values")
                if vals and len(vals) >= 2:
                    rec = next((r for r in records if r.get("dosya") == vals[0] and r.get("ref") == vals[1]), None)
            if rec:
                selected_recs.append(rec)
        return selected_recs

    def copy_column_values(self, col_key, col_title, only_selected=True):
        """Belirtilen sütundaki verileri (seçili veya tüm tablodaki) alt alta panoya kopyalar."""
        if only_selected:
            recs = self.get_selected_cockpit_records()
            scope_name = f"Seçili {len(recs)} adet"
        else:
            recs = self.filtered_records or getattr(self.engine, "records", []) or []
            scope_name = f"Tablodaki tüm ({len(recs)})"

        if not recs:
            self.show_warning("Uyarı", "Kopyalanacak kayıt bulunamadı.")
            return

        vals = []
        for r in recs:
            v = str(r.get(col_key) or "").strip()
            if v and v != "—":
                vals.append(v)

        if not vals:
            self.show_warning("Uyarı", f"Bu sütunda geçerli {col_title} bulunamadı.")
            return

        text = "\n".join(vals)
        self.copy_to_clipboard(text)
        self.show_info(
            "Kopyalandı",
            f"📋 {scope_name} {col_title} alt alta panoya kopyalandı!\n\n(Excel'e veya arama alanına doğrudan yapıştırabilirsiniz)"
        )

    def copy_selected_rows_as_table(self):
        """Seçili satırları Excel uyumlu sekme ayrılmış (tab-delimited) tablo formatında panoya kopyalar."""
        recs = self.get_selected_cockpit_records()
        if not recs:
            self.show_warning("Uyarı", "Lütfen önce tablodan kopyalanacak satırları seçin.")
            return

        lines = ["Dosya No\tReferans No\tKonşimento (B/L)\tOperasyonel Aşama\tHat\tVergi Maili Durumu\tBayi / Alıcı\tLiman"]
        for r in recs:
            lines.append(
                f"{r.get('dosya','')}\t{r.get('ref','')}\t{r.get('bl','')}\t{r.get('stage_title','')}\t{r.get('hat','')}\t{r.get('mail_status','')}\t{r.get('bayi','')}\t{r.get('liman','')}"
            )
        text = "\n".join(lines)
        self.copy_to_clipboard(text)
        self.show_info(
            "Kopyalandı",
            f"📋 Seçili {len(recs)} satır Excel formatında panoya kopyalandı!\n\n(Excel'e doğrudan Ctrl+V ile yapıştırabilirsiniz)"
        )

    def copy_selected_bl(self):
        """Seçili konşimento numarasını panoya kopyalar."""
        self.copy_column_values("bl", "Konşimento (B/L)", only_selected=True)

    def copy_selected_dosya(self):
        """Seçili dosya numarasını panoya kopyalar."""
        self.copy_column_values("dosya", "Dosya No", only_selected=True)

    def copy_selected_ref(self):
        """Seçili referans numarasını panoya kopyalar."""
        self.copy_column_values("ref", "Referans No", only_selected=True)

    def export_cockpit_to_excel(self):
        """Filtrelenmiş kokpit kayıtlarını Excel dosyası olarak dışa aktarır."""
        target_records = self.filtered_records or getattr(self.engine, "records", [])
        if not target_records:
            self.show_warning("Uyarı", "Dışa aktarılacak kayıt bulunamadı.")
            return

        default_name = f"Canli_Operasyon_Kokpiti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        save_path = filedialog.asksaveasfilename(
            title="Kokpit Raporunu Excel Olarak Kaydet",
            initialfile=default_name,
            filetypes=[("Excel Dosyaları", "*.xlsx")]
        )
        if not save_path:
            return

        if not openpyxl:
            self.show_error("Hata", "openpyxl kütüphanesi bulunamadı.")
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Canlı Operasyon Kokpiti"

            headers = [
                "Dosya No", "Referans No", "Konşimento (B/L)", "Operasyonel Aşama",
                "Hat", "Vergi Mail Durumu", "Bayi / Alıcı", "Liman", "Gümrük",
                "Tescil Tarihi", "Ordino Tarihi", "Tareks", "Açıklama", "Mail Tarihi", "Mail Alıcı"
            ]
            ws.append(headers)

            for cell in ws[1]:
                cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
                cell.fill = openpyxl.styles.PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

            for r in target_records:
                ws.append([
                    r.get("dosya", ""),
                    r.get("ref", ""),
                    r.get("bl", ""),
                    r.get("stage_title", ""),
                    r.get("hat", ""),
                    r.get("mail_status", ""),
                    r.get("bayi", ""),
                    r.get("liman", ""),
                    r.get("gumruk", ""),
                    r.get("tescil", ""),
                    r.get("ordino", ""),
                    r.get("tareks", ""),
                    r.get("aciklama", ""),
                    r.get("mail_date", ""),
                    r.get("mail_to", "")
                ])

            # Otomatik sütun genişliği
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

            wb.save(save_path)
            if self.ask_yes_no("Başarılı", f"✅ {len(target_records)} adet kayıt başarıyla Excel'e aktarıldı!\n\nDosyayı şimdi açmak ister misiniz?"):
                os.startfile(save_path)
        except Exception as e:
            self.show_error("Hata", f"Excel oluşturulurken hata oluştu: {e}")
