# -*- coding: utf-8 -*-
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class BaseView(tk.Frame):
    """Tüm MasterSuite sekme görünümleri için temel sınıf."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, bg=kwargs.pop("bg", "#f8fafc"), *args, **kwargs)
        self.app = app

    def is_alive(self):
        """Pencere kapanmışsa veya widget yok edilmişse False."""
        try:
            if getattr(self.app, "_closed", False):
                return False
            return bool(self.winfo_exists())
        except Exception:
            return False

    @property
    def root(self):
        return getattr(self.app, "root", None)

    @property
    def config(self):
        return self.app.config

    @property
    def engine(self):
        return self.app.engine

    @property
    def current_user(self):
        return getattr(self.app, "current_user", {})

    @property
    def gtb_tracker(self):
        return getattr(self.app, "gtb_tracker", None)

    @property
    def kantar_tracker(self):
        return getattr(self.app, "kantar_tracker", None)

    @property
    def evrim_records(self):
        return getattr(self.app, "evrim_records", [])

    def set_header_subtitle(self, text, fg="#64748b"):
        if hasattr(self.app, "header") and hasattr(self.app.header, "lbl_head_subtitle"):
            try:
                self.app.header.lbl_head_subtitle.config(text=text, fg=fg)
            except Exception:
                pass

    def __getattr__(self, item):
        """View içinde self.app üzerindeki değişken ve metodlara doğrudan şeffaf erişim sağlar."""
        if item != "app" and hasattr(self, "app") and self.app is not None:
            if hasattr(self.app, item):
                return getattr(self.app, item)
        raise AttributeError(f"'{self.__class__.__name__}' object and its parent app have no attribute '{item}'")

    def switch_tab(self, tab_code):
        if hasattr(self.app, "switch_tab"):
            self.app.switch_tab(tab_code)

    def copy_to_clipboard(self, text, show_msg=False):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            if show_msg:
                messagebox.showinfo("Kopyalandı", f"Metin panoya kopyalandı:\n{text[:100]}")
        except Exception as e:
            print("Clipboard error:", e)

    def show_info(self, title, msg):
        messagebox.showinfo(title, msg)

    def show_warning(self, title, msg):
        messagebox.showwarning(title, msg)

    def show_error(self, title, msg):
        messagebox.showerror(title, msg)

    def ask_yes_no(self, title, msg):
        return messagebox.askyesno(title, msg)

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

        return {"card": card, "val_lbl": lbl_v, "title": title, "subtitle": subtitle, "color": accent_color}

    @staticmethod
    def format_check_time(val):
        """Supabase ISO (2026-09-02T10:24:02.0164) veya yerel tarihi tabloya okunur yazar."""
        s = str(val or "").strip()
        if not s or s in ("—", "-", "None", "null"):
            return "—"
        if "T" in s and s[:4].isdigit():
            try:
                raw = s.replace("Z", "")
                if "+" in raw[10:]:
                    raw = raw[:10] + raw[10:].split("+", 1)[0]
                if "." in raw:
                    main, frac = raw.split(".", 1)
                    frac = "".join(c for c in frac if c.isdigit())[:6].ljust(6, "0")
                    raw = f"{main}.{frac}"
                dt = datetime.fromisoformat(raw)
                return dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                return s.replace("T", " ")[:16]
        return s
