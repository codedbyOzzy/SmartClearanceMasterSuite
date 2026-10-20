# -*- coding: utf-8 -*-
"""
tools/dogruer_master_suite/views/shield_view.py
===============================================
Doğruer MasterSuite - Akıllı Güvenlik Kalkanı & Konuşma Gezgini Görünümü (Shield & Timeline View)
- Akıllı Konuşma Gezgini (Adım Adım Sohbet Akışı)
- Hızlı Mail Sorgulama ("Buna Mail Attım mı?")
- Göndermeden Önce Güvenlik Denetimi
"""
import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .base_view import BaseView

try:
    from tools.dogruer_master_suite.outlook_memory_guard import safe_open_mail_by_entry_id
except Exception:
    try:
        from outlook_memory_guard import safe_open_mail_by_entry_id
    except Exception:
        safe_open_mail_by_entry_id = None


class ShieldView(BaseView):
    """
    Akıllı Güvenlik Kalkanı & Konuşma Gezgini Görünümü
    """

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.selected_inspector_files = []
        self.all_raw_conv_results = []
        self.current_conv_results = []
        self.conv_sort_state = {"col": "date", "reverse": True}
        self.current_selected_conv_idx = -1
        self._shield_tree_items_map = {}
        self._build_ui()

    def on_activate(self):
        """Sekme açıldığında arka planda Outlook önbelleğini hazırlar."""
        if hasattr(self.engine, "outlook_cache") and not self.engine.outlook_cache:
            def _preload():
                try:
                    recs = self.engine.fetch_outlook_sent_items(limit=350)
                    self.engine.outlook_cache = recs
                except Exception:
                    pass
            threading.Thread(target=_preload, daemon=True).start()

    def _build_ui(self):
        shield_nb = ttk.Notebook(self)
        shield_nb.pack(fill=tk.BOTH, expand=True)

        tab_s_conv = ttk.Frame(shield_nb)
        shield_nb.add(tab_s_conv, text="  🧵 Akıllı Konuşma Gezgini (Adım Adım Sohbet Akışı)  ")

        tab_s_query = ttk.Frame(shield_nb)
        shield_nb.add(tab_s_query, text="  🔍 'Buna Mail Attım mı?' Sorgula  ")

        tab_s_inspect = ttk.Frame(shield_nb)
        shield_nb.add(tab_s_inspect, text="  🛡️ Göndermeden Önce Denetle  ")

        # 0. ANA SEKME: AKILLI KONUŞMA GEZGİNİ
        self.setup_conv_explorer_tab(tab_s_conv)

        # 1. ALT SEKME: HIZLI MAİL SORGULA
        self.setup_quick_search_tab(tab_s_query)

        # 2. ALT SEKME: GÖNDERMEDEN ÖNCE DENETLE
        self.setup_inspector_tab(tab_s_inspect)

    def setup_quick_search_tab(self, parent_frame):
        f_q = tk.Frame(parent_frame, bg="#ffffff", padx=14, pady=12)
        f_q.pack(fill=tk.BOTH, expand=True)

        top_s_box = tk.Frame(f_q, bg="#f8fafc", padx=12, pady=10, relief=tk.FLAT, bd=0)
        top_s_box.pack(fill=tk.X, pady=(0, 10))

        lbl = tk.Label(
            top_s_box,
            text="🔎 Sorgulanacak Referans / Dosya / Konşimento No:",
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            fg="#0f172a"
        )
        lbl.pack(anchor="w", pady=(0, 4))

        i_row = tk.Frame(top_s_box, bg="#f8fafc")
        i_row.pack(fill=tk.X)

        self.txt_shield_query = tk.Entry(i_row, font=("Consolas", 11), bd=1, relief=tk.SOLID)
        self.txt_shield_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=3)
        self.txt_shield_query.bind("<Return>", lambda e: self.do_shield_quick_search())

        btn_sq = tk.Button(
            i_row,
            text="🔍 Geçmişi Tara",
            font=("Segoe UI", 9, "bold"),
            bg="#1e3a8a",
            fg="#ffffff",
            activebackground="#1e40af",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            cursor="hand2",
            command=self.do_shield_quick_search
        )
        btn_sq.pack(side=tk.RIGHT)

        self.card_s_res = tk.Frame(f_q, bg="#ffffff", padx=12, pady=10, relief=tk.FLAT, bd=0)
        self.card_s_res.pack(fill=tk.X, pady=(0, 10))

        self.lbl_s_res_banner = tk.Label(
            self.card_s_res,
            text="Lütfen yukarıdan aratmak istediğiniz numarayı girin.",
            font=("Segoe UI", 10, "bold"),
            fg="#64748b",
            bg="#ffffff"
        )
        self.lbl_s_res_banner.pack(anchor="w")

        self.lbl_s_res_details = tk.Label(
            self.card_s_res,
            text="",
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#ffffff",
            justify=tk.LEFT
        )
        self.lbl_s_res_details.pack(anchor="w", pady=(2, 0))

        cols = ("durum", "tarih", "kime", "ek_sayisi", "ek_listesi", "konu")
        self.tree_shield = ttk.Treeview(f_q, columns=cols, show="headings", height=8, selectmode="browse")

        self.tree_shield.heading("durum", text="Durum")
        self.tree_shield.heading("tarih", text="Tarih / Saat")
        self.tree_shield.heading("kime", text="Alıcı")
        self.tree_shield.heading("ek_sayisi", text="Ek")
        self.tree_shield.heading("ek_listesi", text="Gönderilen Ekler")
        self.tree_shield.heading("konu", text="Mail Konusu")

        self.tree_shield.column("durum", width=120, anchor="center")
        self.tree_shield.column("tarih", width=110, anchor="center")
        self.tree_shield.column("kime", width=150, anchor="w")
        self.tree_shield.column("ek_sayisi", width=65, anchor="center")
        self.tree_shield.column("ek_listesi", width=220, anchor="w")
        self.tree_shield.column("konu", width=240, anchor="w")

        self.tree_shield.tag_configure("has_pdf", background="#dcfce7", foreground="#166534")
        self.tree_shield.tag_configure("is_reply", background="#fef9c3", foreground="#854d0e")
        self.tree_shield.tag_configure("no_att", background="#fee2e2", foreground="#991b1b")

        self.tree_shield.pack(fill=tk.BOTH, expand=True)

        # Tablo çift tıklama ve sağ tık menüsü
        self.tree_shield.bind("<Double-1>", self._on_shield_tree_double_click)
        self.tree_shield.bind("<Return>", self._on_shield_tree_double_click)
        self.tree_shield.bind("<Button-3>", self._show_shield_tree_context_menu)

    def setup_inspector_tab(self, parent_frame):
        f_i = tk.Frame(parent_frame, bg="#ffffff", padx=14, pady=12)
        f_i.pack(fill=tk.BOTH, expand=True)

        lbl_i1 = tk.Label(
            f_i,
            text="1. Hazırladığınız Mail Konusu veya Referanslar:",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a"
        )
        lbl_i1.pack(anchor="w", pady=(0, 2))

        self.txt_inspect_subj = tk.Entry(f_i, font=("Segoe UI", 9), bd=1, relief=tk.SOLID)
        self.txt_inspect_subj.pack(fill=tk.X, pady=(0, 8), ipady=3)
        self.txt_inspect_subj.insert(0, "Vergi Talebi / 4200788458 + 4200788463 + 4200789554")

        lbl_i2 = tk.Label(
            f_i,
            text="2. Eke Koyacağınız PDF Dosyaları:",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a"
        )
        lbl_i2.pack(anchor="w", pady=(0, 2))

        f_att_row = tk.Frame(f_i, bg="#ffffff")
        f_att_row.pack(fill=tk.X, pady=(0, 8))

        self.lbl_inspect_att_count = tk.Label(
            f_att_row,
            text="Henüz PDF seçilmedi (0 Dosya)",
            font=("Segoe UI", 8, "bold"),
            fg="#64748b",
            bg="#ffffff"
        )
        self.lbl_inspect_att_count.pack(side=tk.LEFT)

        btn_clear_pdf = tk.Button(
            f_att_row,
            text="🗑️ Ekleri Temizle",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            cursor="hand2",
            command=self.clear_inspect_pdfs
        )
        btn_clear_pdf.pack(side=tk.RIGHT, padx=(4, 0))

        btn_sel_pdf = tk.Button(
            f_att_row,
            text="📁 PDF Seç...",
            font=("Segoe UI", 8, "bold"),
            bg="#e0f2fe",
            fg="#0369a1",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            cursor="hand2",
            command=self.select_inspect_pdfs
        )
        btn_sel_pdf.pack(side=tk.RIGHT)

        btn_do_inspect = tk.Button(
            f_i,
            text="🛡️ GÜVENLİK DENETİMİNİ BAŞLAT",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=8,
            cursor="hand2",
            command=self.run_shield_inspection
        )
        btn_do_inspect.pack(fill=tk.X, pady=(0, 8))

        self.txt_shield_report = tk.Text(
            f_i,
            font=("Consolas", 9),
            bg="#f8fafc",
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=8
        )
        self.txt_shield_report.pack(fill=tk.BOTH, expand=True)

    def setup_conv_explorer_tab(self, parent_frame):
        f_main = tk.Frame(parent_frame, bg="#ffffff", padx=10, pady=10)
        f_main.pack(fill=tk.BOTH, expand=True)

        # 1. ÜST ARAMA VE FİLTRE ÇUBUĞU
        top_bar = tk.Frame(f_main, bg="#f8fafc", padx=12, pady=10, relief=tk.FLAT, bd=0)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        lbl_s = tk.Label(
            top_bar,
            text="🔍 Konuşma & Mail Arama (Konu, Acente, Müşteri, Dosya No, Konşimento, Gönderen, Alıcı):",
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            fg="#0f172a"
        )
        lbl_s.pack(anchor="w", pady=(0, 4))

        search_row = tk.Frame(top_bar, bg="#f8fafc")
        search_row.pack(fill=tk.X)

        self.txt_conv_search = tk.Entry(search_row, font=("Segoe UI", 10), bd=1, relief=tk.SOLID)
        self.txt_conv_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        self.txt_conv_search.bind("<Return>", lambda e: self.do_conv_search())

        btn_search = tk.Button(
            search_row,
            text="🔍 Konuşmaları Ara",
            font=("Segoe UI", 9, "bold"),
            bg="#1e3a8a",
            fg="#ffffff",
            activebackground="#1e40af",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.do_conv_search
        )
        btn_search.pack(side=tk.LEFT, padx=(0, 6))

        btn_recent = tk.Button(
            search_row,
            text="⚡ Son Konuşmalar",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: self.do_conv_search(query="")
        )
        btn_recent.pack(side=tk.LEFT)

        # Hızlı Filtre Çipleri
        filter_row = tk.Frame(top_bar, bg="#f8fafc")
        filter_row.pack(fill=tk.X, pady=(6, 0))

        self.lbl_conv_status = tk.Label(
            filter_row,
            text="Hazır. Arama yapmak için bir kelime yazıp Enter'a veya butona basın.",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#f8fafc"
        )
        self.lbl_conv_status.pack(side=tk.LEFT)

        f_chips = tk.Frame(filter_row, bg="#f8fafc")
        f_chips.pack(side=tk.RIGHT)

        btn_f_all = tk.Button(
            f_chips, text="Tümü", font=("Segoe UI", 8), bg="#ffffff",
            relief=tk.FLAT, bd=0, padx=6, pady=1, cursor="hand2",
            command=lambda: self.filter_conv_results("ALL")
        )
        btn_f_all.pack(side=tk.LEFT, padx=2)

        btn_f_att = tk.Button(
            f_chips, text="📎 Sadece Ekli", font=("Segoe UI", 8), bg="#ffffff",
            relief=tk.FLAT, bd=0, padx=6, pady=1, cursor="hand2",
            command=lambda: self.filter_conv_results("ATTACHMENTS")
        )
        btn_f_att.pack(side=tk.LEFT, padx=2)

        btn_f_multi = tk.Button(
            f_chips, text="🧵 Çok Aşamalı (2+ Adım)", font=("Segoe UI", 8), bg="#ffffff",
            relief=tk.FLAT, bd=0, padx=6, pady=1, cursor="hand2",
            command=lambda: self.filter_conv_results("MULTI_STEP")
        )
        btn_f_multi.pack(side=tk.LEFT, padx=2)

        # 2. İKİYE BÖLÜNMÜŞ PANEL (SOL: KONULAR, SAĞ: ADIM ADIM SOHBET AKIŞI)
        paned = tk.PanedWindow(f_main, orient=tk.HORIZONTAL, bg="#cbd5e1", bd=0, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        # SOL: KONU LİSTESİ
        f_left = tk.Frame(paned, bg="#ffffff", relief=tk.FLAT, bd=0)
        paned.add(f_left, width=460)

        lbl_l_title = tk.Label(
            f_left,
            text="📋 Bulunan Konuşma Konuları (Başlığa basarak sıralayabilirsiniz)",
            font=("Segoe UI", 8, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            padx=8,
            pady=6,
            anchor="w"
        )
        lbl_l_title.pack(fill=tk.X)

        cols = ("topic", "steps", "date", "sender")
        self.tree_conv_list = ttk.Treeview(f_left, columns=cols, show="headings", height=15, selectmode="browse")

        # Tıklanabilir Başlıklar (Windows Tarzı Sıralama)
        self.tree_conv_list.heading("topic", text="Konuşma Konusu", command=lambda: self.sort_conv_tree("topic"))
        self.tree_conv_list.heading("steps", text="Adım", command=lambda: self.sort_conv_tree("steps"))
        self.tree_conv_list.heading("date", text="Son Tarih ▼", command=lambda: self.sort_conv_tree("date"))
        self.tree_conv_list.heading("sender", text="Son Gönderen", command=lambda: self.sort_conv_tree("sender"))

        self.tree_conv_list.column("topic", width=210, anchor="w")
        self.tree_conv_list.column("steps", width=60, anchor="center")
        self.tree_conv_list.column("date", width=125, anchor="center")
        self.tree_conv_list.column("sender", width=130, anchor="w")

        sc_y = ttk.Scrollbar(f_left, orient=tk.VERTICAL, command=self.tree_conv_list.yview)
        self.tree_conv_list.configure(yscroll=sc_y.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_conv_list.pack(fill=tk.BOTH, expand=True)

        self.tree_conv_list.bind("<<TreeviewSelect>>", self.on_conv_tree_select)

        # SAĞ: ADIM ADIM SOHBET AKIŞI KARTLARI
        f_right = tk.Frame(paned, bg="#ffffff", relief=tk.FLAT, bd=0)
        paned.add(f_right)

        # Üst Başlık & Navigasyon Kartı
        self.f_conv_head = tk.Frame(f_right, bg="#f8fafc", padx=12, pady=10, relief=tk.FLAT, bd=0)
        self.f_conv_head.pack(fill=tk.X)

        # Başlık ve Konuşma Gezinme Butonları Satırı
        h_row1 = tk.Frame(self.f_conv_head, bg="#f8fafc")
        h_row1.pack(fill=tk.X)

        self.lbl_conv_detail_title = tk.Label(
            h_row1,
            text="Lütfen soldaki listeden bir konuşma seçin.",
            font=("Segoe UI", 11, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
            wraplength=480,
            justify=tk.LEFT
        )
        self.lbl_conv_detail_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Konuşma Navigasyon Butonları
        f_conv_nav = tk.Frame(h_row1, bg="#f8fafc")
        f_conv_nav.pack(side=tk.RIGHT)

        btn_prev_conv = tk.Button(
            f_conv_nav,
            text="◀ Önceki Konuşma",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#334155",
            relief=tk.SOLID,
            bd=1,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._nav_prev_conversation
        )
        btn_prev_conv.pack(side=tk.LEFT, padx=2)

        btn_next_conv = tk.Button(
            f_conv_nav,
            text="Sonraki Konuşma ▶",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#334155",
            relief=tk.SOLID,
            bd=1,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._nav_next_conversation
        )
        btn_next_conv.pack(side=tk.LEFT, padx=2)

        # Meta Satırı ve Adım Atlama Butonları
        h_row2 = tk.Frame(self.f_conv_head, bg="#f8fafc")
        h_row2.pack(fill=tk.X, pady=(2, 4))

        self.lbl_conv_detail_meta = tk.Label(
            h_row2,
            text="",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#f8fafc"
        )
        self.lbl_conv_detail_meta.pack(side=tk.LEFT)

        f_step_nav = tk.Frame(h_row2, bg="#f8fafc")
        f_step_nav.pack(side=tk.RIGHT)

        btn_jump_first = tk.Button(
            f_step_nav,
            text="⏮️ İlk Adım",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.FLAT,
            bd=0,
            padx=6,
            cursor="hand2",
            command=lambda: self.canvas_conv.yview_moveto(0.0) if hasattr(self, "canvas_conv") else None
        )
        btn_jump_first.pack(side=tk.LEFT, padx=2)

        btn_jump_last = tk.Button(
            f_step_nav,
            text="⏭️ Son Adım",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.FLAT,
            bd=0,
            padx=6,
            cursor="hand2",
            command=lambda: self.canvas_conv.yview_moveto(1.0) if hasattr(self, "canvas_conv") else None
        )
        btn_jump_last.pack(side=tk.LEFT, padx=2)

        self.f_conv_att_vault = tk.Frame(self.f_conv_head, bg="#f8fafc")
        self.f_conv_att_vault.pack(fill=tk.X, pady=(2, 0))

        # Kaydırılabilir Adım Kartları Alanı
        canvas_frame = tk.Frame(f_right, bg="#ffffff")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas_conv = tk.Canvas(canvas_frame, bg="#ffffff", highlightthickness=0)
        self.scroll_conv_y = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas_conv.yview)
        self.f_conv_cards = tk.Frame(self.canvas_conv, bg="#ffffff", padx=8, pady=8)

        self.f_conv_cards.bind(
            "<Configure>",
            lambda e: self.canvas_conv.configure(scrollregion=self.canvas_conv.bbox("all"))
        )
        self.canvas_window = self.canvas_conv.create_window((0, 0), window=self.f_conv_cards, anchor="nw")
        self.canvas_conv.bind(
            "<Configure>",
            lambda e: self.canvas_conv.itemconfig(self.canvas_window, width=e.width)
        )

        self.canvas_conv.configure(yscrollcommand=self.scroll_conv_y.set)
        self.scroll_conv_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_conv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _nav_prev_conversation(self):
        children = self.tree_conv_list.get_children()
        if not children:
            return
        sel = self.tree_conv_list.selection()
        cur_idx = children.index(sel[0]) if sel else 0
        prev_idx = max(0, cur_idx - 1)
        self.tree_conv_list.selection_set(children[prev_idx])
        self.tree_conv_list.see(children[prev_idx])
        if 0 <= prev_idx < len(self.current_conv_results):
            self.render_conversation_thread(self.current_conv_results[prev_idx])

    def _nav_next_conversation(self):
        children = self.tree_conv_list.get_children()
        if not children:
            return
        sel = self.tree_conv_list.selection()
        cur_idx = children.index(sel[0]) if sel else 0
        next_idx = min(len(children) - 1, cur_idx + 1)
        self.tree_conv_list.selection_set(children[next_idx])
        self.tree_conv_list.see(children[next_idx])
        if 0 <= next_idx < len(self.current_conv_results):
            self.render_conversation_thread(self.current_conv_results[next_idx])

    def do_conv_search(self, query=None, async_mode=True):
        if query is None:
            query = self.txt_conv_search.get().strip()

        for item in self.tree_conv_list.get_children():
            try:
                self.tree_conv_list.delete(item)
            except Exception:
                pass

        self.lbl_conv_status.config(
            text=f"⏳ Outlook'ta '{query or 'Son Konuşmalar'}' taranıyor, lütfen bekleyin...",
            fg="#f59e0b"
        )

        def _fetch():
            convs = []
            if hasattr(self.engine, "search_outlook_conversations"):
                convs = self.engine.search_outlook_conversations(query=query, limit=150)

            def _render():
                self.all_raw_conv_results = convs
                self.current_conv_results = list(convs)
                if not convs:
                    self.lbl_conv_status.config(
                        text=f"❌ '{query}' ile eşleşen konuşma bulunamadı.",
                        fg="#dc2626"
                    )
                    return

                self.lbl_conv_status.config(
                    text=f"✅ Toplam {len(convs)} adet konuşma konusu bulundu.",
                    fg="#16a34a"
                )
                self.conv_sort_state = {"col": "date", "reverse": True}
                self.refresh_conv_tree_ui()

                children = self.tree_conv_list.get_children()
                if children and self.current_conv_results:
                    self.tree_conv_list.selection_set(children[0])
                    self.render_conversation_thread(self.current_conv_results[0])

            if async_mode:
                root_widget = getattr(self.app, "root", None) or self.winfo_toplevel()
                try:
                    if root_widget and root_widget.winfo_exists():
                        root_widget.after(0, _render)
                    else:
                        _render()
                except Exception:
                    try:
                        _render()
                    except Exception:
                        pass
            else:
                _render()

        if async_mode:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            _fetch()

    def filter_conv_results(self, filter_type):
        if not hasattr(self, "all_raw_conv_results"):
            return
        if filter_type == "ALL":
            self.current_conv_results = list(self.all_raw_conv_results)
        elif filter_type == "ATTACHMENTS":
            self.current_conv_results = [
                c for c in self.all_raw_conv_results if len(c.get("all_attachments", [])) > 0
            ]
        elif filter_type == "MULTI_STEP":
            self.current_conv_results = [
                c for c in self.all_raw_conv_results if c.get("total_steps", 0) >= 2
            ]

        self.refresh_conv_tree_ui()
        children = self.tree_conv_list.get_children()
        if children and self.current_conv_results:
            self.tree_conv_list.selection_set(children[0])
            self.render_conversation_thread(self.current_conv_results[0])

    def sort_conv_tree(self, col):
        if not hasattr(self, "current_conv_results") or not self.current_conv_results:
            return

        if self.conv_sort_state["col"] == col:
            new_reverse = not self.conv_sort_state["reverse"]
        else:
            new_reverse = True if col in ("date", "steps") else False

        self.conv_sort_state = {"col": col, "reverse": new_reverse}

        if col == "date":
            self.current_conv_results.sort(key=lambda x: x.get("latest_timestamp") or 0, reverse=new_reverse)
        elif col == "steps":
            self.current_conv_results.sort(key=lambda x: x.get("total_steps") or 0, reverse=new_reverse)
        elif col == "topic":
            self.current_conv_results.sort(key=lambda x: (x.get("topic") or "").lower(), reverse=new_reverse)
        elif col == "sender":
            self.current_conv_results.sort(key=lambda x: (x.get("latest_sender") or "").lower(), reverse=new_reverse)

        self.refresh_conv_tree_ui()
        children = self.tree_conv_list.get_children()
        if children and self.current_conv_results:
            self.tree_conv_list.selection_set(children[0])
            self.render_conversation_thread(self.current_conv_results[0])

    def refresh_conv_tree_ui(self):
        for item in self.tree_conv_list.get_children():
            try:
                self.tree_conv_list.delete(item)
            except Exception:
                pass

        col_titles = {
            "topic": "Konuşma Konusu",
            "steps": "Adım",
            "date": "Son Tarih",
            "sender": "Son Gönderen"
        }
        for c_key, c_text in col_titles.items():
            if self.conv_sort_state["col"] == c_key:
                arrow = " ▼" if self.conv_sort_state["reverse"] else " ▲"
                self.tree_conv_list.heading(c_key, text=f"{c_text}{arrow}")
            else:
                self.tree_conv_list.heading(c_key, text=c_text)

        for c in self.current_conv_results:
            self.tree_conv_list.insert("", tk.END, values=(
                c.get("topic", "Konuşma"),
                f"{c.get('total_steps', 1)} Adım",
                c.get("latest_date", "—"),
                c.get("latest_sender", "—")
            ))

    def on_conv_tree_select(self, event):
        sel = self.tree_conv_list.selection()
        if not sel or not hasattr(self, "current_conv_results"):
            return
        try:
            item_id = sel[0]
            idx = self.tree_conv_list.index(item_id)
            if 0 <= idx < len(self.current_conv_results):
                self.current_selected_conv_idx = idx
                self.render_conversation_thread(self.current_conv_results[idx])
        except Exception as e:
            print(f"Selection error: {e}")

    def render_conversation_thread(self, conv):
        # 1. Başlık ve Üst Bilgi
        self.lbl_conv_detail_title.config(text=f"💬 {conv.get('topic', 'Konuşma')}")
        all_senders = list(set([m.get('sender', '—') for m in conv.get('messages', []) if m.get('sender')]))
        senders_str = ", ".join(all_senders[:3]) + (f" (+{len(all_senders)-3} kişi)" if len(all_senders) > 3 else "")
        self.lbl_conv_detail_meta.config(
            text=f"📊 Toplam {conv.get('total_steps', 0)} Adım / Mesaj  |  👥 Katılımcılar: {senders_str}  |  📅 Son Tarih: {conv.get('latest_date', '—')}"
        )

        # 2. Ekler Havuzu
        for child in self.f_conv_att_vault.winfo_children():
            child.destroy()

        all_atts = conv.get("all_attachments", [])
        if all_atts:
            lbl_att_title = tk.Label(
                self.f_conv_att_vault,
                text=f"📎 Konuşmadaki Ekler ({len(all_atts)}):",
                font=("Segoe UI", 8, "bold"),
                fg="#1e293b",
                bg="#f8fafc"
            )
            lbl_att_title.pack(side=tk.LEFT, padx=(0, 6))

            for att_name in all_atts[:5]:
                lbl_badge = tk.Label(
                    self.f_conv_att_vault,
                    text=f"📄 {att_name[:25]}",
                    font=("Segoe UI", 8),
                    bg="#e0f2fe",
                    fg="#0369a1",
                    padx=6,
                    pady=2,
                    relief=tk.FLAT,
                    bd=0,
                    cursor="hand2"
                )
                lbl_badge.pack(side=tk.LEFT, padx=2)
                lbl_badge.bind("<Button-1>", lambda e, a=att_name: self.copy_to_clipboard(a, show_msg=True))

        # 3. Adım Adım Kartları Çiz
        for child in self.f_conv_cards.winfo_children():
            child.destroy()

        messages = conv.get("messages", [])
        for m in messages:
            step_num = m.get("step", 1)
            is_out = m.get("direction") == "OUT"

            bg_color = "#f0fdf4" if is_out else "#f8fafc"
            header_bg = "#dcfce7" if is_out else "#f1f5f9"
            dir_icon = "📤 [GİDEN - BİZ]" if is_out else "📥 [GELEN - YANIT]"

            card = tk.Frame(self.f_conv_cards, bg=bg_color, relief=tk.FLAT, bd=0, padx=10, pady=8)
            card.pack(fill=tk.X, pady=6)

            head_row = tk.Frame(card, bg=header_bg, padx=8, pady=5)
            head_row.pack(fill=tk.X, pady=(0, 6))

            lbl_step = tk.Label(
                head_row,
                text=f"Adım {step_num}: {dir_icon}  {m.get('sender', '—')} ➡️ {m.get('to', '—')[:30]}",
                font=("Segoe UI", 9, "bold"),
                bg=header_bg,
                fg="#166534" if is_out else "#1e3a8a"
            )
            lbl_step.pack(side=tk.LEFT)

            eid = m.get("entry_id")
            btn_open = tk.Button(
                head_row,
                text="✉️ Outlook'ta Aç",
                font=("Segoe UI", 8, "bold"),
                bg="#ffffff",
                fg="#0f172a",
                relief=tk.SOLID,
                bd=1,
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda eid_val=eid: self.open_selected_mail_in_outlook(eid_val)
            )
            btn_open.pack(side=tk.RIGHT)

            lbl_time = tk.Label(head_row, text=f"📅 {m.get('time_str', '—')}", font=("Segoe UI", 8), bg=header_bg, fg="#475569")
            lbl_time.pack(side=tk.RIGHT, padx=8)

            lbl_subj = tk.Label(card, text=f"Konu: {m.get('subject', '—')}", font=("Segoe UI", 8, "bold"), bg=bg_color, fg="#334155", anchor="w")
            lbl_subj.pack(fill=tk.X, pady=(0, 4))

            txt_preview = tk.Label(
                card,
                text=m.get("snippet", "—") or "(Metin gövdesi yok)",
                font=("Segoe UI", 8),
                bg="#ffffff",
                fg="#1e293b",
                relief=tk.SOLID,
                bd=1,
                padx=8,
                pady=6,
                justify=tk.LEFT,
                wraplength=600,
                anchor="w"
            )
            txt_preview.pack(fill=tk.X, pady=(0, 4))

            m_atts = m.get("attachments", [])
            if m_atts:
                f_m_atts = tk.Frame(card, bg=bg_color)
                f_m_atts.pack(fill=tk.X, pady=(2, 0))

                lbl_a_title = tk.Label(f_m_atts, text="📎 Ekler:", font=("Segoe UI", 8, "bold"), bg=bg_color, fg="#64748b")
                lbl_a_title.pack(side=tk.LEFT, padx=(0, 4))

                for a_name in m_atts:
                    lbl_a_badge = tk.Label(f_m_atts, text=f"📄 {a_name}", font=("Segoe UI", 8), bg="#ffffff", fg="#0369a1", padx=6, pady=1, relief=tk.FLAT, bd=0, cursor="hand2")
                    lbl_a_badge.pack(side=tk.LEFT, padx=2)
                    lbl_a_badge.bind("<Button-1>", lambda e, a=a_name: self.copy_to_clipboard(a, show_msg=True))

    def open_selected_mail_in_outlook(self, entry_id=None):
        """Belirtilen veya seçili maili Outlook'ta güvenli bir şekilde açar."""
        if not entry_id:
            # Shield quick search tablosundan veya conversation seçili öğesinden al
            sel_shield = self.tree_shield.selection() if hasattr(self, "tree_shield") else None
            if sel_shield:
                entry_id = self._shield_tree_items_map.get(sel_shield[0])

        if not entry_id:
            self.show_warning("Uyarı", "Açılacak mail için geçerli bir kimlik (EntryID) bulunamadı.")
            return False

        try:
            ok = False
            if safe_open_mail_by_entry_id:
                ok = safe_open_mail_by_entry_id(entry_id)
            elif hasattr(self.engine, "open_outlook_mail_by_id"):
                ok = self.engine.open_outlook_mail_by_id(entry_id)

            if not ok:
                self.show_warning("Outlook Uyarısı", "Mail Outlook'ta açılamadı. Lütfen Outlook uygulamasının açık olduğunu kontrol edin.")
            return ok
        except Exception as e:
            self.show_error("Hata", f"Mail açılırken hata oluştu: {e}")
            return False

    def do_shield_quick_search(self):
        raw_q = self.txt_shield_query.get().strip()
        if not raw_q:
            return

        for item in self.tree_shield.get_children():
            try:
                self.tree_shield.delete(item)
            except Exception:
                pass
        self._shield_tree_items_map = {}

        refs = re.findall(r"\b(\d{10}|\d{2}-\d{6}|[A-Z0-9]{3}202\d{10}|[A-Z]{4}\d{7})\b", raw_q.upper())
        if not refs:
            refs = [raw_q.upper()]

        cache = getattr(self.engine, "outlook_cache", [])
        if not cache and hasattr(self.engine, "fetch_outlook_sent_items"):
            try:
                cache = self.engine.fetch_outlook_sent_items(limit=350)
                self.engine.outlook_cache = cache
            except Exception:
                cache = []

        all_matches = []
        for ref in refs:
            clean_r = re.sub(r"[^A-Z0-9]", "", ref)
            for mail in cache:
                subj_c = re.sub(r"[^A-Z0-9]", "", mail.get("subject", "").upper())
                att_c = re.sub(r"[^A-Z0-9]", "", " ".join(mail.get("attachments", [])).upper())

                if (clean_r in subj_c) or (clean_r in att_c):
                    if mail not in all_matches:
                        all_matches.append(mail)

        if all_matches:
            self.lbl_s_res_banner.config(
                text=f"✅ BU REFERANS İÇİN MAİL ATILMIŞ! ({len(all_matches)} Gönderim Bulundu)",
                fg="#15803d"
            )
            self.lbl_s_res_details.config(
                text=f"Son Gönderim: {all_matches[0].get('sent_on', '—')} | Kime: {all_matches[0].get('to', '—')} (Açmak için satıra çift tıklayın)"
            )

            for idx, m in enumerate(all_matches):
                atts = m.get("attachments", [])
                att_cnt = len(atts)
                att_str = ", ".join(atts) if att_cnt > 0 else "—"

                if att_cnt > 0:
                    badge = "🟢 PDF Gönderildi"
                    tag = "has_pdf"
                elif m.get("is_reply"):
                    badge = "🟡 Yanıt (RE:)"
                    tag = "is_reply"
                else:
                    badge = "⚠️ Ek Yok (Metin)"
                    tag = "no_att"

                row_iid = f"shield_row_{idx}"
                eid = m.get("entry_id", "")
                self._shield_tree_items_map[row_iid] = eid

                self.tree_shield.insert("", tk.END, iid=row_iid, values=(
                    badge,
                    m.get("sent_on", "—"),
                    m.get("to", "—"),
                    f"{att_cnt} Adet" if att_cnt > 0 else "0",
                    att_str,
                    m.get("subject", "—")
                ), tags=(tag,))
        else:
            self.lbl_s_res_banner.config(
                text="⏳ BU REFERANS İÇİN GÖNDERİLMİŞ MAİL BULUNAMADI.",
                fg="#b91c1c"
            )
            self.lbl_s_res_details.config(
                text="Son 350 mailde rastlanmadı. Güvenle mail atabilirsiniz."
            )

    def _on_shield_tree_double_click(self, event=None):
        sel = self.tree_shield.selection()
        if not sel:
            return
        eid = self._shield_tree_items_map.get(sel[0])
        if eid:
            self.open_selected_mail_in_outlook(eid)

    def _show_shield_tree_context_menu(self, event):
        item_id = self.tree_shield.identify_row(event.y)
        if not item_id:
            return
        self.tree_shield.selection_set(item_id)
        eid = self._shield_tree_items_map.get(item_id)
        vals = self.tree_shield.item(item_id, "values")

        menu = tk.Menu(self.winfo_toplevel(), tearoff=0)
        if eid:
            menu.add_command(label="✉️ Bu Maili Outlook'ta Aç", command=lambda: self.open_selected_mail_in_outlook(eid))
            menu.add_separator()

        if vals and len(vals) >= 6:
            menu.add_command(label=f"📋 Mail Konusunu Kopyala ({vals[5][:30]}...)", command=lambda: self.copy_to_clipboard(vals[5], show_msg=True))
            menu.add_command(label=f"📋 Alıcı Adresini Kopyala ({vals[2]})", command=lambda: self.copy_to_clipboard(vals[2], show_msg=True))
            menu.add_command(label=f"📋 Gönderilen Ekleri Kopyala", command=lambda: self.copy_to_clipboard(vals[4], show_msg=True))

        menu.tk_popup(event.x_root, event.y_root)

    def select_inspect_pdfs(self):
        files = filedialog.askopenfilenames(
            title="Eklenecek PDF Dosyalarını Seçin",
            filetypes=[("PDF Dosyaları", "*.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        if files:
            self.selected_inspector_files = list(files)
            names = [os.path.basename(f) for f in files]
            self.lbl_inspect_att_count.config(
                text=f"✅ {len(files)} Adet PDF Seçildi: {', '.join(names[:2])}{'...' if len(names)>2 else ''}",
                fg="#15803d"
            )

    def clear_inspect_pdfs(self):
        self.selected_inspector_files = []
        self.lbl_inspect_att_count.config(
            text="Henüz PDF seçilmedi (0 Dosya)",
            fg="#64748b"
        )

    def run_shield_inspection(self):
        subj = self.txt_inspect_subj.get().strip()
        att_names = [os.path.basename(f) for f in self.selected_inspector_files]

        self.txt_shield_report.delete("1.0", tk.END)
        lines = []
        has_error = False

        detected_refs = re.findall(r"\b(\d{10}|\d{2}-\d{6}|[A-Z0-9]{3}202\d{10}|[A-Z]{4}\d{7})\b", subj.upper())
        lines.append(f"📌 Konuda Tespit Edilen Referanslar ({len(detected_refs)} Adet): {', '.join(detected_refs) if detected_refs else 'Yok'}")

        is_talep = any(k in subj.upper() for k in ["VERGİ", "VERGI", "FATURA", "TALEP", "TALEBİ", "DEKONT", "ORDİNO"])
        if is_talep and len(att_names) == 0:
            lines.append("\n❌ [KRİTİK UYARI] BOŞ EK RİSKİ: Konuda 'Vergi/Fatura Talebi' var ama HİÇBİR PDF EKLENMEMİŞ!")
            has_error = True
        else:
            lines.append(f"\n✅ [EK DURUMU] Toplam {len(att_names)} adet ek dosya mevcut.")

        dup_warns = []
        cache = getattr(self.engine, "outlook_cache", [])
        if not cache and hasattr(self.engine, "fetch_outlook_sent_items"):
            try:
                cache = self.engine.fetch_outlook_sent_items(limit=350)
                self.engine.outlook_cache = cache
            except Exception:
                cache = []

        for ref in detected_refs:
            clean_r = re.sub(r"[^A-Z0-9]", "", ref)
            for m in cache:
                s_c = re.sub(r"[^A-Z0-9]", "", m.get("subject", "").upper())
                a_c = re.sub(r"[^A-Z0-9]", "", " ".join(m.get("attachments", [])).upper())
                if clean_r in s_c or clean_r in a_c:
                    dup_warns.append(f"   ⚠️ Referans [{ref}] için {m.get('sent_on', '—')} tarihinde [{m.get('to', '—')}] adresine mail atılmış!")
                    break

        if dup_warns:
            lines.append("\n⚠️ [MÜKERRERLİK UYARISI]:")
            lines.extend(dup_warns)
        else:
            lines.append("\n✅ [MÜKERRERLİK TEMİZ] Bu referanslar için yakın zamanda mail atılmamış.")

        if detected_refs and att_names:
            missings = []
            for ref in detected_refs:
                clean_r = re.sub(r"[^A-Z0-9]", "", ref)
                if not any(clean_r in re.sub(r"[^A-Z0-9]", "", a.upper()) for a in att_names):
                    missings.append(ref)
            if missings:
                lines.append(f"\n⚠️ [EKSİK PDF UYARISI]: Konudaki şu referansların PDF eki yok: {', '.join(missings)}")
            else:
                lines.append("\n✅ [TAM UYUM] Konudaki tüm referansların PDF ekleri mevcut.")

        lines.append("\n" + "=" * 55)
        if has_error:
            lines.append("🛑 SONUÇ: MAİLİ GÖNDERMEDEN ÖNCE EKLERİ MUTLAKA KONTROL EDİN!")
        elif dup_warns:
            lines.append("⚠️ SONUÇ: DİKKAT GEREKTİREN UYARILAR VAR (Yukarıyı İnceleyin).")
        else:
            lines.append("🎉 SONUÇ: %100 GÜVENLİ! Mail ve ekler kusursuz uyumlu.")

        self.txt_shield_report.insert("1.0", "\n".join(lines))
