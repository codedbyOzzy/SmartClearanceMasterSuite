# -*- coding: utf-8 -*-
"""
ai_assistant_view.py — Doğruer MasterSuite Gemini Yapay Zeka Danışmanı
Gümrük Mevzuatı, GTİP Danışmanlığı ve Operasyonel Soru-Cevap Ekranı
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser

from .base_view import BaseView
from tools.dogruer_master_suite.gemini_assistant_service import get_assistant_service


class AIAssistantView(BaseView):
    """Doğruer SmartClearance Yapay Zeka Operasyon & Mevzuat Asistanı Görünümü."""

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.assistant_service = get_assistant_service()
        self.is_processing = False
        self._build_ui()

    def on_activate(self):
        """Sekmeye geçildiğinde başlık ve API durumunu tazele."""
        self.set_header_subtitle("🧠 Doğruer Akıllı Gümrük & Mevzuat Danışmanı (Google Gemini AI)")
        self._check_api_status()

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. ÜST PANEL: Bilgi Kartı ve API Key Yönetimi
        self.card_top = tk.Frame(self, bg="#ffffff", padx=16, pady=12, relief=tk.FLAT, bd=0)
        self.card_top.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 6))

        # Üst şerit rengi
        strip = tk.Frame(self.card_top, bg="#0284c7", height=3)
        strip.pack(fill=tk.X, pady=(0, 8))

        top_header_row = tk.Frame(self.card_top, bg="#ffffff")
        top_header_row.pack(fill=tk.X)

        lbl_icon = tk.Label(top_header_row, text="🧠", font=("Segoe UI", 18), bg="#ffffff")
        lbl_icon.pack(side=tk.LEFT, padx=(0, 8))

        f_titles = tk.Frame(top_header_row, bg="#ffffff")
        f_titles.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lbl_main = tk.Label(
            f_titles, text="SmartClearance AI Danışmanı (Google Gemini)",
            font=("Segoe UI", 12, "bold"), fg="#0f172a", bg="#ffffff"
        )
        lbl_main.pack(anchor="w")

        lbl_sub = tk.Label(
            f_titles,
            text="Gümrük mevzuatı, 12 haneli GTİP tespiti, ithalat/ihracat kuralları ve operasyonel işler için yapay zeka asistanı.",
            font=("Segoe UI", 8), fg="#64748b", bg="#ffffff"
        )
        lbl_sub.pack(anchor="w")

        self.lbl_status_badge = tk.Label(
            top_header_row, text="● API Kontrol Ediliyor...",
            font=("Segoe UI", 8, "bold"), fg="#d97706", bg="#fef3c7", padx=10, pady=4
        )
        self.lbl_status_badge.pack(side=tk.RIGHT)

        # API Key Çubuğu
        f_key_row = tk.Frame(self.card_top, bg="#f8fafc", padx=10, pady=8, highlightthickness=1, highlightbackground="#e2e8f0")
        f_key_row.pack(fill=tk.X, pady=(10, 0))

        lbl_key_t = tk.Label(f_key_row, text="Gemini API Key:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#f8fafc")
        lbl_key_t.pack(side=tk.LEFT, padx=(0, 8))

        self.ent_key = tk.Entry(f_key_row, font=("Segoe UI", 9), show="●", bg="#ffffff", fg="#0f172a", relief=tk.SOLID, bd=1)
        self.ent_key.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        cur_key = self.assistant_service.get_api_key()
        if cur_key:
            self.ent_key.insert(0, cur_key)

        btn_save_key = tk.Button(
            f_key_row, text="💾 Key Kaydet", font=("Segoe UI", 8, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief=tk.FLAT, bd=0, padx=10, pady=4, cursor="hand2", command=self._save_api_key
        )
        btn_save_key.pack(side=tk.LEFT, padx=(0, 6))

        btn_get_key = tk.Button(
            f_key_row, text="🔑 Ücretsiz Key Al", font=("Segoe UI", 8),
            bg="#f1f5f9", fg="#475569", activebackground="#e2e8f0", activeforeground="#0f172a",
            relief=tk.FLAT, bd=0, padx=8, pady=4, cursor="hand2",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey")
        )
        btn_get_key.pack(side=tk.LEFT)

        # 2. HIZLI SORU ŞABLONLARI (Kısayollar)
        f_quick = tk.Frame(self, bg="#f8fafc")
        f_quick.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        lbl_q_icon = tk.Label(f_quick, text="Hızlı Şablonlar:", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#f8fafc")
        lbl_q_icon.pack(side=tk.LEFT, padx=(4, 8))

        quick_prompts = [
            ("🔍 Lastik GTİP ve Vergi", "Otomobil dış lastikleri için olası 12 haneli GTİP kodları, gümrük vergisi ve TAREKS denetim şartları nelerdir?"),
            ("📋 Ordino vs Konşimento", "Dış ticarette konşimento ile ordino arasındaki hukuki ve operasyonel fark nedir?"),
            ("🏛️ Antrepo Süresi & Teminat", "Gümrük Kanununa göre antrepo rejiminde bekleme süresi sınırı var mıdır, teminat oranları nedir?"),
            ("⚠️ Damping Vergisi", "İthalatta dampinge karşı kesin önlem (vergi) nedir ve nasıl hesaplanır?")
        ]

        for title, prompt_text in quick_prompts:
            btn_q = tk.Button(
                f_quick, text=title, font=("Segoe UI", 8),
                bg="#ffffff", fg="#0284c7", activebackground="#e0f2fe", activeforeground="#0369a1",
                relief=tk.FLAT, bd=1, padx=8, pady=2, cursor="hand2",
                command=lambda p=prompt_text: self._send_quick_prompt(p)
            )
            btn_q.pack(side=tk.LEFT, padx=3)

        btn_clear = tk.Button(
            f_quick, text="🧹 Temizle", font=("Segoe UI", 8),
            bg="#ffffff", fg="#ef4444", activebackground="#fee2e2", activeforeground="#b91c1c",
            relief=tk.FLAT, bd=1, padx=8, pady=2, cursor="hand2",
            command=self._clear_chat
        )
        btn_clear.pack(side=tk.RIGHT, padx=4)

        # 3. SOHBET GEÇMİŞİ (Ana Mesaj Alanı)
        f_chat_wrap = tk.Frame(self, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0")
        f_chat_wrap.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 6))
        f_chat_wrap.grid_rowconfigure(0, weight=1)
        f_chat_wrap.grid_columnconfigure(0, weight=1)

        self.txt_chat = scrolledtext.ScrolledText(
            f_chat_wrap, font=("Segoe UI", 10), wrap=tk.WORD,
            bg="#ffffff", fg="#0f172a", relief=tk.FLAT, bd=0, padx=14, pady=12
        )
        self.txt_chat.grid(row=0, column=0, sticky="nsew")

        # Metin stilleri / Tag yapılandırması
        self.txt_chat.tag_configure("user_hdr", font=("Segoe UI", 9, "bold"), foreground="#0284c7")
        self.txt_chat.tag_configure("user_msg", font=("Segoe UI", 10), foreground="#0f172a", lmargin1=12, lmargin2=12)
        self.txt_chat.tag_configure("ai_hdr", font=("Segoe UI", 9, "bold"), foreground="#059669")
        self.txt_chat.tag_configure("ai_msg", font=("Segoe UI", 10), foreground="#1e293b", lmargin1=12, lmargin2=12)
        self.txt_chat.tag_configure("system_msg", font=("Segoe UI", 8, "italic"), foreground="#94a3b8")
        self.txt_chat.tag_configure("sep", font=("Segoe UI", 6), foreground="#cbd5e1")
        self.txt_chat.config(state=tk.DISABLED)

        # 4. GİRİŞ ÇUBUĞU
        f_input_card = tk.Frame(self, bg="#ffffff", padx=12, pady=10, highlightthickness=1, highlightbackground="#e2e8f0")
        f_input_card.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

        self.ent_msg = tk.Entry(
            f_input_card, font=("Segoe UI", 10),
            bg="#f8fafc", fg="#0f172a", relief=tk.SOLID, bd=1
        )
        self.ent_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self.ent_msg.bind("<Return>", lambda e: self._on_send_click())
        self.ent_msg.focus_set()

        self.btn_send = tk.Button(
            f_input_card, text="🚀 Gönder", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief=tk.FLAT, bd=0, padx=16, pady=6, cursor="hand2", command=self._on_send_click
        )
        self.btn_send.pack(side=tk.LEFT)

        # Karşılama mesajını ekle
        self._append_system_msg("Doğruer SmartClearance Yapay Zeka Danışmanına hoş geldiniz.")
        self._append_ai_msg(
            "Merhaba! Ben SmartClearance bünyesindeki Gümrük ve Dış Ticaret Yapay Zeka Danışmanınızım. 🤖\n\n"
            "Bana GTİP tespiti, ithalat/ihracat prosedürleri, vergi oranları veya operasyonel süreçlerle ilgili dilediğiniz soruyu sorabilirsiniz.\n"
            "Eğer henüz Gemini API anahtarınızı girmediyseniz yukarıdaki hızlı şablonlara tıklayarak sistemin nasıl yanıt verdiğini hemen test edebilirsiniz!"
        )

        self._check_api_status()

    def _check_api_status(self):
        key = self.assistant_service.get_api_key()
        if key:
            self.lbl_status_badge.config(
                text="🟢 Canlı Gemini API Aktif",
                fg="#166534", bg="#dcfce7"
            )
        else:
            self.lbl_status_badge.config(
                text="🟠 Test Modu (Key Girilmedi)",
                fg="#9a3412", bg="#ffedd5"
            )

    def _save_api_key(self):
        new_key = self.ent_key.get().strip()
        if not new_key:
            messagebox.showwarning("Eksik Anahtar", "Lütfen geçerli bir Gemini API anahtarı giriniz.")
            return
        ok = self.assistant_service.set_api_key(new_key)
        if ok:
            messagebox.showinfo("Başarılı", "Gemini API anahtarı güvenli şekilde kaydedildi!")
            self._check_api_status()
        else:
            messagebox.showerror("Hata", "API anahtarı kaydedilemedi.")

    def _send_quick_prompt(self, prompt_text: str):
        if self.is_processing:
            return
        self.ent_msg.delete(0, tk.END)
        self.ent_msg.insert(0, prompt_text)
        self._on_send_click()

    def _on_send_click(self):
        if self.is_processing:
            return
        query = self.ent_msg.get().strip()
        if not query:
            return

        self.ent_msg.delete(0, tk.END)
        self._append_user_msg(query)

        # Thread içinde Gemini'ye sor
        self.is_processing = True
        self.btn_send.config(text="⏳ Aranıyor...", state=tk.DISABLED)
        self.ent_msg.config(state=tk.DISABLED)

        t = threading.Thread(target=self._ask_worker, args=(query,), daemon=True)
        t.start()

    def _ask_worker(self, query: str):
        success, reply = self.assistant_service.ask(query)
        # Tkinter ana thread'ine geri aktar
        if self.is_alive():
            self.after(0, lambda: self._handle_response(success, reply))

    def _handle_response(self, success: bool, reply: str):
        self.is_processing = False
        self.btn_send.config(text="🚀 Gönder", state=tk.NORMAL)
        self.ent_msg.config(state=tk.NORMAL)
        self.ent_msg.focus_set()

        if success:
            self._append_ai_msg(reply)
        else:
            self._append_ai_msg(f"⚠️ Bir sorun oluştu:\n{reply}")

    def _append_user_msg(self, text: str):
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.insert(tk.END, "\n👤 SİZ:\n", "user_hdr")
        self.txt_chat.insert(tk.END, f"{text}\n\n", "user_msg")
        self.txt_chat.insert(tk.END, "—" * 60 + "\n", "sep")
        self.txt_chat.config(state=tk.DISABLED)
        self.txt_chat.see(tk.END)

    def _append_ai_msg(self, text: str):
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.insert(tk.END, "\n🤖 SMARTCLEARANCE AI:\n", "ai_hdr")
        self.txt_chat.insert(tk.END, f"{text}\n\n", "ai_msg")
        self.txt_chat.insert(tk.END, "—" * 60 + "\n", "sep")
        self.txt_chat.config(state=tk.DISABLED)
        self.txt_chat.see(tk.END)

    def _append_system_msg(self, text: str):
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.insert(tk.END, f"ℹ️ {text}\n", "system_msg")
        self.txt_chat.config(state=tk.DISABLED)
        self.txt_chat.see(tk.END)

    def _clear_chat(self):
        self.assistant_service.clear_history()
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.delete("1.0", tk.END)
        self.txt_chat.config(state=tk.DISABLED)
        self._append_system_msg("Sohbet geçmişi temizlendi.")
