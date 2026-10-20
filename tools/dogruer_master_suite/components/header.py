# -*- coding: utf-8 -*-
import tkinter as tk

class MasterSuiteHeader(tk.Frame):
    """Pencerenin ust baslik ve hizli aksiyon alani."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, bg="#ffffff", height=65, relief=tk.FLAT, bd=0, *args, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        h_title_box = tk.Frame(self, bg="#ffffff")
        h_title_box.pack(side=tk.LEFT, padx=20, pady=12)

        self.lbl_head_title = tk.Label(
            h_title_box,
            text="📊 MERKEZİ OPERASYON KONTROL PANELİ",
            font=("Segoe UI", 13, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        self.lbl_head_title.pack(anchor="w")

        self.lbl_head_subtitle = tk.Label(
            h_title_box,
            text="Tüm aktif dosyaların gümrük tescil ve Outlook vergi mail durumları",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#ffffff"
        )
        self.lbl_head_subtitle.pack(anchor="w")

        btn_box = tk.Frame(self, bg="#ffffff")
        btn_box.pack(side=tk.RIGHT, padx=12, pady=10)

        self.bind("<Configure>", self._on_header_resize)

        btn_open_excel = tk.Button(
            btn_box,
            text="📊 Excel Aç",
            font=("Segoe UI", 9, "bold"),
            bg="#107c41",
            fg="#ffffff",
            activebackground="#0b5e31",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.app.open_excel_file
        )
        btn_open_excel.pack(side=tk.LEFT, padx=(0, 8))

        btn_sync_now = tk.Button(
            btn_box,
            text="🔄 Şimdi Yenile",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.app.trigger_sync_async
        )
        btn_sync_now.pack(side=tk.LEFT)

    def set_title(self, title, subtitle):
        self.lbl_head_title.config(text=title)
        self.lbl_head_subtitle.config(text=subtitle)
        self._on_header_resize()

    def _on_header_resize(self, event=None):
        try:
            w = max(180, self.winfo_width() - 280)
            self.lbl_head_title.config(wraplength=w)
            self.lbl_head_subtitle.config(wraplength=w)
        except Exception:
            pass
