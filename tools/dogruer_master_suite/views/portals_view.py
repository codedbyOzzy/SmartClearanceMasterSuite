# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import re
import threading
import webbrowser
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

from .base_view import BaseView

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
TALEP_QUEUE_PATH = os.path.join(CONFIG_DIR, "talep_queue.json")
EVRIM_DATA_PATH = os.path.join(CONFIG_DIR, "evrim_live_data.json")
DOGRUER_ONLINE_URL = "https://dogruer.online"


def load_talep_queue():
    if os.path.exists(TALEP_QUEUE_PATH):
        try:
            with open(TALEP_QUEUE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def load_evrim_cached_data():
    try:
        if os.path.exists(EVRIM_DATA_PATH):
            with open(EVRIM_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception as e:
        print(f"Evrim Verisi Okuma Hatası: {e}")
    return []


def refresh_embedded_hwnd(hwnd, container):
    """Gömülü Win32 penceresinin boyutlarını eşitler ve arka plan siyah kalmasını önler."""
    if hwnd and win32gui:
        try:
            w = container.winfo_width()
            h = container.winfo_height()
            if w > 10 and h > 10:
                win32gui.MoveWindow(hwnd, 0, 0, w, h, True)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.InvalidateRect(hwnd, None, True)
            win32gui.UpdateWindow(hwnd)
        except Exception:
            pass


class QNBPortalView(BaseView):
    """Gömülü QNB eSolutions Portalı & Fatura Eşleştirici Görünümü."""

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.qnb_process = None
        self.qnb_hwnd = 0
        self._build_ui()

    def _build_ui(self):
        f_box = tk.Frame(self, bg="#ffffff", padx=8, pady=8, relief=tk.FLAT, bd=0)
        f_box.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(f_box, bg="#ffffff")
        top_row.pack(fill=tk.X, pady=(0, 4))

        lbl_title = tk.Label(
            top_row,
            text="🌐 QNB eSolutions Portal & Otomatik Fatura Eşleştirici (Doğrudan Gömülü)",
            font=("Segoe UI", 11, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_title.pack(side=tk.LEFT)

        btn_inject_script = tk.Button(
            top_row,
            text="🚀 Eşleştiriciyi Manuel Aç",
            font=("Segoe UI", 8, "bold"),
            bg="#6b21a8",
            fg="#ffffff",
            activebackground="#581c87",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.trigger_manual_inject
        )
        btn_inject_script.pack(side=tk.RIGHT, padx=4)

        btn_refresh_page = tk.Button(
            top_row,
            text="🔄 Yenile (F5)",
            font=("Segoe UI", 8, "bold"),
            bg="#0369a1",
            fg="#ffffff",
            activebackground="#075985",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.trigger_refresh
        )
        btn_refresh_page.pack(side=tk.RIGHT, padx=4)

        btn_copy_bm = tk.Button(
            top_row,
            text="⭐ Kodu Kopyala",
            font=("Segoe UI", 8, "bold"),
            bg="#f59e0b",
            fg="#ffffff",
            activebackground="#d97706",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.copy_qnb_bookmarklet_code
        )
        btn_copy_bm.pack(side=tk.RIGHT, padx=4)

        btn_copy_all_bl = tk.Button(
            top_row,
            text="📋 Açık BL Kopyala",
            font=("Segoe UI", 8, "bold"),
            bg="#107c41",
            fg="#ffffff",
            activebackground="#0b5e31",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.copy_active_bl_list
        )
        btn_copy_all_bl.pack(side=tk.RIGHT, padx=4)

        self.qnb_container = tk.Frame(f_box, bg="#e2e8f0", bd=2, relief=tk.SUNKEN)
        self.qnb_container.pack(fill=tk.BOTH, expand=True)
        self.qnb_container.bind("<Configure>", self.on_qnb_container_resize)

        # F5 klavye kısayolu ile sayfa yenileme
        self.bind_all("<F5>", lambda e: self.trigger_refresh())

    def trigger_manual_inject(self):
        if self.qnb_process and self.qnb_process.poll() is None:
            try:
                self.qnb_process.stdin.write(b"INJECT\n")
                self.qnb_process.stdin.flush()
            except Exception as e:
                messagebox.showerror("Hata", f"İletişim hatası: {e}")
        else:
            messagebox.showwarning("Uyarı", "Tarayıcı henüz yüklenmedi veya kapandı.")

    def trigger_refresh(self):
        """QNB eSolutions sayfasını yeniler (F5 veya Yenile butonu)."""
        if self.qnb_process and self.qnb_process.poll() is None:
            try:
                self.qnb_process.stdin.write(b"REFRESH\n")
                self.qnb_process.stdin.flush()
            except Exception as e:
                messagebox.showerror("Hata", f"Yenileme hatası: {e}")
        else:
            messagebox.showwarning("Uyarı", "Tarayıcı henüz yüklenmedi veya kapandı.")

    def on_activate(self):
        self.ensure_qnb_embedded()
        self.after(50, lambda: refresh_embedded_hwnd(self.qnb_hwnd, self.qnb_container))
        self.after(200, lambda: refresh_embedded_hwnd(self.qnb_hwnd, self.qnb_container))

    def launch_pyqt_browser(self):
        if self.qnb_process or self.qnb_hwnd:
            return

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        script_path = os.path.join(root_dir, "tools", "qnb_fatura_eslestirici", "qnb_pyqt_embed.py")
        if not os.path.exists(script_path):
            script_path = os.path.join(os.getcwd(), "tools", "qnb_fatura_eslestirici", "qnb_pyqt_embed.py")

        if not os.path.exists(script_path):
            messagebox.showerror("Hata", f"qnb_pyqt_embed.py bulunamadı:\n{script_path}")
            return

        env = os.environ.copy()
        env["QT_OPENGL"] = "software"
        site_pkgs = os.path.join(root_dir, "Lib", "site-packages")
        env["PYTHONPATH"] = f"{site_pkgs};{root_dir};{env.get('PYTHONPATH', '')}"

        self.qnb_process = subprocess.Popen(
            [sys.executable, script_path],
            env=env,
            stdin=subprocess.PIPE
        )

        def find_hwnd():
            hwnds = []

            def enum_cb(h, _):
                if win32gui and win32gui.IsWindowVisible(h):
                    if "QNB_PYQT_EMBED_WINDOW" in win32gui.GetWindowText(h):
                        hwnds.append(h)
                return True

            for _ in range(20):
                time.sleep(0.5)
                hwnds.clear()
                if win32gui:
                    win32gui.EnumWindows(enum_cb, None)
                if hwnds:
                    self.qnb_hwnd = hwnds[0]
                    break

            if self.qnb_hwnd and win32gui:
                win32gui.SetParent(self.qnb_hwnd, self.qnb_container.winfo_id())

                style = win32gui.GetWindowLong(self.qnb_hwnd, win32con.GWL_STYLE)
                style = style | win32con.WS_CHILD
                style = style & ~win32con.WS_POPUP
                style = style & ~win32con.WS_CAPTION
                style = style & ~win32con.WS_THICKFRAME
                win32gui.SetWindowLong(self.qnb_hwnd, win32con.GWL_STYLE, style)

                w = self.qnb_container.winfo_width()
                h = self.qnb_container.winfo_height()
                win32gui.MoveWindow(self.qnb_hwnd, 0, 0, w, h, True)
                win32gui.ShowWindow(self.qnb_hwnd, win32con.SW_SHOW)

        threading.Thread(target=find_hwnd, daemon=True).start()

    def on_qnb_container_resize(self, event):
        if self.qnb_hwnd and win32gui:
            win32gui.MoveWindow(self.qnb_hwnd, 0, 0, event.width, event.height, True)

    def ensure_qnb_embedded(self):
        if not self.qnb_process:
            lbl = tk.Label(
                self.qnb_container,
                text="Tarayıcı yükleniyor, lütfen bekleyin...",
                font=("Segoe UI", 12),
                bg="#e2e8f0",
                fg="#64748b"
            )
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.launch_pyqt_browser()
            self.after(4000, lbl.destroy)

    def copy_active_bl_list(self):
        rows = []
        seen = set()
        records = getattr(self.engine, "records", [])
        for r in records:
            bl = str(r.get("bl") or "").strip()
            if not r.get("kapanis") and bl and len(bl) >= 5:
                if bl not in seen:
                    seen.add(bl)
                    d_no = str(r.get("dosya_no") or r.get("dosya") or "").strip()
                    ref_no = str(r.get("hankook_ref") or r.get("ref") or "").strip()
                    if d_no or ref_no:
                        rows.append(f"{d_no}\t{ref_no}\t{bl}")
                    else:
                        rows.append(bl)

        if rows:
            text_to_copy = "\n".join(rows)
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            messagebox.showinfo(
                "Panoya Kopyalandı",
                f"✅ Toplam {len(rows)} adet açık iş (Dosya No, Referans, Konşimento) panoya kopyalandı!\n\nŞimdi gömülü QNB ekranındaki kutucuğa yapıştırıp (Ctrl+V) tek seferde taratabilirsiniz."
            )
        else:
            messagebox.showwarning("Uyarı", "Açık konşimento bulunamadı.")

    def copy_qnb_bookmarklet_code(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        candidates = [
            os.path.join(root_dir, "tools", "qnb_fatura_eslestirici", "fatura_eslestirici.js"),
            os.path.join(os.getcwd(), "tools", "qnb_fatura_eslestirici", "fatura_eslestirici.js"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "qnb_fatura_eslestirici", "fatura_eslestirici.js"))
        ]
        p = next((x for x in candidates if os.path.exists(x)), candidates[0])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            bookmarklet = "javascript:" + code.replace("\n", " ")
            self.clipboard_clear()
            self.clipboard_append(bookmarklet)
            messagebox.showinfo("Kopyalandı", "⭐ QNB Fatura Eşleştirici bookmarklet kodu panoya kopyalandı!")
        else:
            messagebox.showwarning("Bulunamadı", f"fatura_eslestirici.js dosyası bulunamadı:\n{p}")


class GLPPortalView(BaseView):
    """Gömülü Hankook GLP Global Lojistik Portalı Görünümü."""

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.glp_process = None
        self.glp_hwnd = 0
        self._build_ui()

    def _build_ui(self):
        f_box = tk.Frame(self, bg="#ffffff", padx=8, pady=8, relief=tk.FLAT, bd=0)
        f_box.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(f_box, bg="#ffffff")
        top_row.pack(fill=tk.X, pady=(0, 6))

        lbl_info = tk.Label(
            top_row,
            text="🚛 Hankook GLP Lojistik Portalı (glp.hankooktech.com)",
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_info.pack(side=tk.LEFT)

        btn_open_ext = tk.Button(
            top_row,
            text="🌐 Harici Tarayıcıda Aç",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: webbrowser.open("https://glp.hankooktech.com/login.html?redirectUrl=%2FMAIN%2Fmain.html%3Flang%3Dko")
        )
        btn_open_ext.pack(side=tk.RIGHT, padx=4)

        btn_copy_all_bl = tk.Button(
            top_row,
            text="📋 Açık BL Kopyala",
            font=("Segoe UI", 8, "bold"),
            bg="#107c41",
            fg="#ffffff",
            activebackground="#0b5e31",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.copy_active_bl_list
        )
        btn_copy_all_bl.pack(side=tk.RIGHT, padx=4)

        self.glp_container = tk.Frame(f_box, bg="#e2e8f0", bd=2, relief=tk.SUNKEN)
        self.glp_container.pack(fill=tk.BOTH, expand=True)
        self.glp_container.bind("<Configure>", self.on_glp_container_resize)

    def on_activate(self):
        self.ensure_glp_embedded()
        self.after(50, lambda: refresh_embedded_hwnd(self.glp_hwnd, self.glp_container))
        self.after(200, lambda: refresh_embedded_hwnd(self.glp_hwnd, self.glp_container))

    def launch_glp_browser(self):
        if self.glp_process or self.glp_hwnd:
            return

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        script_candidates = [
            os.path.join(root_dir, "tools", "glp_portal", "glp_pyqt_embed.py"),
            os.path.join(os.getcwd(), "tools", "glp_portal", "glp_pyqt_embed.py"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "glp_portal", "glp_pyqt_embed.py"))
        ]
        script_path = next((p for p in script_candidates if os.path.exists(p)), script_candidates[0])

        if not os.path.exists(script_path):
            messagebox.showerror("Hata", f"glp_pyqt_embed.py bulunamadı:\n{script_path}")
            return

        env = os.environ.copy()
        env["QT_OPENGL"] = "software"
        site_pkgs = os.path.join(root_dir, "Lib", "site-packages")
        env["PYTHONPATH"] = f"{site_pkgs};{root_dir};{env.get('PYTHONPATH', '')}"

        self.glp_process = subprocess.Popen(
            [sys.executable, script_path],
            env=env,
            stdin=subprocess.PIPE
        )

        def find_hwnd():
            hwnds = []

            def enum_cb(h, _):
                if win32gui and win32gui.IsWindowVisible(h):
                    if "GLP_PYQT_EMBED_WINDOW" in win32gui.GetWindowText(h):
                        hwnds.append(h)
                return True

            for _ in range(25):
                time.sleep(0.4)
                hwnds.clear()
                if win32gui:
                    win32gui.EnumWindows(enum_cb, None)
                if hwnds:
                    self.glp_hwnd = hwnds[0]
                    break

            if self.glp_hwnd and win32gui:
                win32gui.SetParent(self.glp_hwnd, self.glp_container.winfo_id())

                style = win32gui.GetWindowLong(self.glp_hwnd, win32con.GWL_STYLE)
                style = style | win32con.WS_CHILD
                style = style & ~win32con.WS_POPUP
                style = style & ~win32con.WS_CAPTION
                style = style & ~win32con.WS_THICKFRAME
                win32gui.SetWindowLong(self.glp_hwnd, win32con.GWL_STYLE, style)

                w = self.glp_container.winfo_width()
                h = self.glp_container.winfo_height()
                win32gui.MoveWindow(self.glp_hwnd, 0, 0, w if w > 10 else 1000, h if h > 10 else 700, True)
                win32gui.ShowWindow(self.glp_hwnd, win32con.SW_SHOW)

        threading.Thread(target=find_hwnd, daemon=True).start()

    def on_glp_container_resize(self, event):
        if self.glp_hwnd and win32gui:
            win32gui.MoveWindow(self.glp_hwnd, 0, 0, event.width, event.height, True)

    def ensure_glp_embedded(self):
        if not self.glp_process:
            lbl = tk.Label(
                self.glp_container,
                text="Hankook GLP Portalı yükleniyor, lütfen bekleyin...",
                font=("Segoe UI", 12),
                bg="#e2e8f0",
                fg="#64748b"
            )
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.launch_glp_browser()
            self.after(4000, lbl.destroy)

    def copy_active_bl_list(self):
        bl_list = []
        records = getattr(self.engine, "records", [])
        for r in records:
            if not r.get("kapanis") and r.get("bl") and len(str(r.get("bl"))) >= 5:
                if r["bl"] not in bl_list:
                    bl_list.append(str(r["bl"]))

        if bl_list:
            text_to_copy = "\n".join(bl_list)
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            messagebox.showinfo(
                "Panoya Kopyalandı",
                f"✅ Toplam {len(bl_list)} adet açık Konşimento (B/L) numarası kopyalandı!"
            )
        else:
            messagebox.showwarning("Uyarı", "Açık konşimento bulunamadı.")


class DogruerPortalView(BaseView):
    """Gömülü Doğruer Online & Canlı Evrim Portalı Görünümü."""

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.dogruer_process = None
        self.dogruer_hwnd = 0
        self._build_ui()

    def _build_ui(self):
        f_box = tk.Frame(self, bg="#ffffff", padx=8, pady=8, relief=tk.FLAT, bd=0)
        f_box.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(f_box, bg="#ffffff")
        top_row.pack(fill=tk.X, pady=(0, 2))

        lbl_info = tk.Label(
            top_row,
            text="🌐 Doğruer Online Portalı (dogruer.online) - Evrim Canlı Entegrasyon",
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_info.pack(side=tk.LEFT, padx=6)

        # ── YENİ: ⚡ Otomatik Giriş & Çek butonu ──────────────────────────
        self.btn_auto_login = tk.Button(
            top_row,
            text="⚡ Otomatik Giriş & Çek",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.trigger_auto_login
        )
        self.btn_auto_login.pack(side=tk.LEFT, padx=4)
        # ──────────────────────────────────────────────────────────────────

        btn_sync_all = tk.Button(
            top_row,
            text="🔄 Tüm Sayfaları Tara & Evrim Verilerini Çek",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.trigger_dogruer_embed_sync
        )
        btn_sync_all.pack(side=tk.LEFT, padx=4)

        btn_copy_open = tk.Button(
            top_row,
            text="📋 Açık Dosya Numaralarını Kopyala",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#0f172a",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.copy_all_open_dosya_nos
        )
        btn_copy_open.pack(side=tk.LEFT, padx=4)

        btn_copy_bm = tk.Button(
            top_row,
            text="⭐ Kodu Kopyala",
            font=("Segoe UI", 8, "bold"),
            bg="#f59e0b",
            fg="#ffffff",
            activebackground="#d97706",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.copy_dogruer_bookmarklet_code
        )
        btn_copy_bm.pack(side=tk.LEFT, padx=4)

        btn_ext = tk.Button(
            top_row,
            text="🌐 Harici Tarayıcıda Aç",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=4,
            cursor="hand2",
            command=lambda: webbrowser.open(DOGRUER_ONLINE_URL)
        )
        btn_ext.pack(side=tk.RIGHT, padx=4)

        # ── YENİ: Durum bilgisi satırı ────────────────────────────────────
        status_row = tk.Frame(f_box, bg="#ffffff")
        status_row.pack(fill=tk.X, pady=(0, 4))

        self.lbl_auto_status = tk.Label(
            status_row,
            text="",
            font=("Segoe UI", 8),
            fg="#475569",
            bg="#ffffff",
            anchor="w"
        )
        self.lbl_auto_status.pack(side=tk.LEFT, padx=8)
        # ──────────────────────────────────────────────────────────────────

        self.dogruer_container = tk.Frame(f_box, bg="#e2e8f0", relief=tk.SUNKEN, bd=1)
        self.dogruer_container.pack(fill=tk.BOTH, expand=True)
        self.dogruer_container.bind("<Configure>", self.on_dogruer_container_resize)

    def on_activate(self):
        self.ensure_dogruer_embedded()
        self.after(50, lambda: refresh_embedded_hwnd(self.dogruer_hwnd, self.dogruer_container))
        self.after(200, lambda: refresh_embedded_hwnd(self.dogruer_hwnd, self.dogruer_container))

    def launch_dogruer_browser(self):
        if self.dogruer_process or self.dogruer_hwnd:
            return

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        script_candidates = [
            os.path.join(root_dir, "tools", "dogruer_online_bridge", "dogruer_pyqt_embed.py"),
            os.path.join(os.getcwd(), "tools", "dogruer_online_bridge", "dogruer_pyqt_embed.py"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dogruer_online_bridge", "dogruer_pyqt_embed.py"))
        ]
        script_path = next((p for p in script_candidates if os.path.exists(p)), script_candidates[0])

        if not os.path.exists(script_path):
            messagebox.showerror("Hata", f"dogruer_pyqt_embed.py bulunamadı:\n{script_path}")
            return

        env = os.environ.copy()
        env["QT_OPENGL"] = "software"
        site_pkgs = os.path.join(root_dir, "Lib", "site-packages")
        env["PYTHONPATH"] = f"{site_pkgs};{root_dir};{env.get('PYTHONPATH', '')}"

        self.dogruer_process = subprocess.Popen(
            [sys.executable, script_path],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        def listen_stdout():
            if not self.dogruer_process or not self.dogruer_process.stdout:
                return
            for line in self.dogruer_process.stdout:
                if "SYNC_SUCCESS" in line:
                    def _on_synced():
                        records = load_evrim_cached_data()
                        if hasattr(self.app, "evrim_records"):
                            self.app.evrim_records = records
                        if hasattr(self.app, "apply_evrim_filters"):
                            self.app.apply_evrim_filters()
                        messagebox.showinfo("Başarılı", f"🎉 {len(records)} adet dosya Evrim'den başarıyla çekildi ve Evrim Veri Merkezi güncellendi!")
                        if hasattr(self.app, "switch_tab"):
                            self.app.switch_tab("EVRIM_EXPLORER")
                    self.after(0, _on_synced)

        threading.Thread(target=listen_stdout, daemon=True).start()

        def find_hwnd():
            hwnds = []

            def enum_cb(h, _):
                if win32gui and win32gui.IsWindowVisible(h):
                    if "DOGRUER_PYQT_EMBED_WINDOW" in win32gui.GetWindowText(h):
                        hwnds.append(h)
                return True

            for _ in range(25):
                time.sleep(0.4)
                hwnds.clear()
                if win32gui:
                    win32gui.EnumWindows(enum_cb, None)
                if hwnds:
                    self.dogruer_hwnd = hwnds[0]
                    break

            if self.dogruer_hwnd and win32gui:
                win32gui.SetParent(self.dogruer_hwnd, self.dogruer_container.winfo_id())

                style = win32gui.GetWindowLong(self.dogruer_hwnd, win32con.GWL_STYLE)
                style = style | win32con.WS_CHILD
                style = style & ~win32con.WS_POPUP
                style = style & ~win32con.WS_CAPTION
                style = style & ~win32con.WS_THICKFRAME
                win32gui.SetWindowLong(self.dogruer_hwnd, win32con.GWL_STYLE, style)

                w = self.dogruer_container.winfo_width()
                h = self.dogruer_container.winfo_height()
                win32gui.MoveWindow(self.dogruer_hwnd, 0, 0, w if w > 10 else 1000, h if h > 10 else 700, True)
                win32gui.ShowWindow(self.dogruer_hwnd, win32con.SW_SHOW)

        threading.Thread(target=find_hwnd, daemon=True).start()

    def _set_auto_status(self, msg: str):
        """Durum etiketini güvenli şekilde günceller."""
        try:
            if hasattr(self, "lbl_auto_status"):
                self.lbl_auto_status.config(text=msg)
            if hasattr(self.app, "lbl_head_subtitle") and msg:
                self.app.lbl_head_subtitle.config(text=msg)
        except Exception:
            pass

    def _set_auto_btn_state(self, enabled: bool):
        """Otomatik giriş butonunu aktif/pasif yapar."""
        try:
            if hasattr(self, "btn_auto_login"):
                if enabled:
                    self.btn_auto_login.config(
                        state=tk.NORMAL,
                        text="⚡ Otomatik Giriş & Çek",
                        bg="#16a34a"
                    )
                else:
                    self.btn_auto_login.config(
                        state=tk.DISABLED,
                        text="⏳ Giriş yapılıyor...",
                        bg="#64748b"
                    )
        except Exception:
            pass

    def on_dogruer_container_resize(self, event):
        if self.dogruer_hwnd and win32gui:
            win32gui.MoveWindow(self.dogruer_hwnd, 0, 0, event.width, event.height, True)

    def ensure_dogruer_embedded(self):
        if not self.dogruer_process:
            lbl = tk.Label(
                self.dogruer_container,
                text="Doğruer Online Portalı yükleniyor, lütfen bekleyin...",
                font=("Segoe UI", 12),
                bg="#e2e8f0",
                fg="#64748b"
            )
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.launch_dogruer_browser()
            self.after(4000, lbl.destroy)

    def trigger_auto_login(self):
        """⚡ Otomatik Giriş & Çek butonuna basıldığında çağrılır."""
        # Portal henüz başlatılmadıysa başlat
        if not self.dogruer_process:
            self.ensure_dogruer_embedded()
            # Process başlaması için bekle, sonra komutu gönder
            self.after(4500, self._send_auto_login_cmd)
        else:
            self._send_auto_login_cmd()

    def _send_auto_login_cmd(self):
        """AUTO_LOGIN stdin komutunu PyQt6 embed'e gönderir."""
        if self.dogruer_process and self.dogruer_process.stdin:
            try:
                self._set_auto_btn_state(False)
                self._set_auto_status("🔐 Otomatik giriş başlatılıyor...")
                self.dogruer_process.stdin.write("AUTO_LOGIN\n")
                self.dogruer_process.stdin.flush()
            except Exception as e:
                messagebox.showerror("Hata", f"Otomatik giriş komutu gönderilemedi: {e}")
                self._set_auto_btn_state(True)
        else:
            messagebox.showwarning("Uyarı", "Doğruer Online Portalı henüz hazır değil. Lütfen birkaç saniye bekleyin.")

    def trigger_dogruer_embed_sync(self):
        if self.dogruer_process and self.dogruer_process.stdin:
            try:
                self.dogruer_process.stdin.write("SYNC\n")
                self.dogruer_process.stdin.flush()
                if hasattr(self.app, "lbl_head_subtitle"):
                    self.app.lbl_head_subtitle.config(text="⏳ Evrim'den tüm sayfalar taranıyor, lütfen bekleyin...")
            except Exception as e:
                messagebox.showerror("Hata", f"Senkronizasyon sinyali gönderilemedi: {e}")
        else:
            messagebox.showwarning("Uyarı", "Doğruer Online Portalı henüz başlatılmadı. Lütfen portalın açılmasını bekleyin.")

    def copy_all_open_dosya_nos(self):
        evrim_records = getattr(self.app, "evrim_records", [])
        dosyalar = [r.get("dosya_no") for r in evrim_records if r.get("dosya_no")]
        if not dosyalar:
            records = getattr(self.engine, "records", [])
            dosyalar = [r.get("dosya") for r in records if r.get("dosya")]
        if dosyalar:
            txt = "\n".join(str(d) for d in dosyalar[:50])
            self.clipboard_clear()
            self.clipboard_append(txt)
            messagebox.showinfo("Kopyalandı", f"📋 {min(len(dosyalar), 50)} adet dosya numarası panoya kopyalandı!")

    def copy_dogruer_bookmarklet_code(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        candidates = [
            os.path.join(root_dir, "tools", "dogruer_online_bridge", "dogruer_sync.js"),
            os.path.join(os.getcwd(), "tools", "dogruer_online_bridge", "dogruer_sync.js"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dogruer_online_bridge", "dogruer_sync.js"))
        ]
        p = next((x for x in candidates if os.path.exists(x)), candidates[0])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            bookmarklet = "javascript:" + code.replace("\n", " ")
            self.clipboard_clear()
            self.clipboard_append(bookmarklet)
            messagebox.showinfo("Kopyalandı", "⭐ Doğruer Online Senkronizasyon bookmarklet kodu panoya kopyalandı!")
        else:
            messagebox.showwarning("Bulunamadı", f"dogruer_sync.js dosyası bulunamadı:\n{p}")


class TalepPortalView(BaseView):
    """Gömülü Doğruer Online Para Talep Portalı Görünümü."""

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.talep_process = None
        self.talep_hwnd = 0
        self.talep_queue = load_talep_queue()
        self.talep_queue_idx = 0
        self._build_ui()

    def _build_ui(self):
        f_box = tk.Frame(self, bg="#ffffff", padx=8, pady=8, relief=tk.FLAT, bd=0)
        f_box.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(f_box, bg="#ffffff")
        top_row.pack(fill=tk.X, pady=(0, 4))

        lbl_title = tk.Label(
            top_row,
            text="💸 Doğruer Online Para Talep Portalı (Gömülü Arayüz)",
            font=("Segoe UI", 11, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        lbl_title.pack(side=tk.LEFT)

        btn_refresh = tk.Button(
            top_row,
            text="🔄 Sayfayı Yenile",
            font=("Segoe UI", 8, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.reload_talep_page
        )
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        btn_new_talep = tk.Button(
            top_row,
            text="➕ Formu Sıfırla",
            font=("Segoe UI", 8, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.reload_talep_page
        )
        btn_new_talep.pack(side=tk.RIGHT, padx=4)

        btn_copy_bm = tk.Button(
            top_row,
            text="⭐ Kodu Kopyala",
            font=("Segoe UI", 8, "bold"),
            bg="#f59e0b",
            fg="#ffffff",
            activebackground="#d97706",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.copy_talep_bookmarklet_code
        )
        btn_copy_bm.pack(side=tk.RIGHT, padx=4)

        # QNB FATURA KUYRUK KONTROL BARI
        self.f_talep_queue_bar = tk.Frame(f_box, bg="#f0fdf4", padx=10, pady=6, relief=tk.FLAT, bd=0)
        self.f_talep_queue_bar.pack(fill=tk.X, pady=(0, 6))

        self.lbl_q_status = tk.Label(
            self.f_talep_queue_bar,
            text="📦 QNB Fatura Kuyruğu: Henüz fatura aktarılmadı",
            font=("Segoe UI", 9, "bold"),
            fg="#166534",
            bg="#f0fdf4",
            anchor="w"
        )
        self.lbl_q_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_q_fill = tk.Button(
            self.f_talep_queue_bar,
            text="▶️ Form Doldur",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.fill_current_queue_item
        )
        self.btn_q_fill.pack(side=tk.RIGHT, padx=(4, 0))

        self.btn_q_next = tk.Button(
            self.f_talep_queue_bar,
            text="⏭️ Sonraki",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#334155",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.skip_queue_item
        )
        self.btn_q_next.pack(side=tk.RIGHT, padx=4)

        self.btn_q_prev = tk.Button(
            self.f_talep_queue_bar,
            text="⏮️ Önceki",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#334155",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.prev_queue_item
        )
        self.btn_q_prev.pack(side=tk.RIGHT, padx=4)

        self.btn_q_clear = tk.Button(
            self.f_talep_queue_bar,
            text="🗑️ Temizle",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#dc2626",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.clear_talep_queue
        )
        self.btn_q_clear.pack(side=tk.RIGHT, padx=4)

        self.talep_container = tk.Frame(f_box, bg="#e2e8f0", bd=2, relief=tk.SUNKEN)
        self.talep_container.pack(fill=tk.BOTH, expand=True)
        self.talep_container.bind("<Configure>", self.on_talep_container_resize)
        self.update_talep_queue_ui()

    def on_activate(self):
        self.ensure_talep_embedded()
        self.talep_queue = load_talep_queue()
        self.update_talep_queue_ui()
        self.after(50, lambda: refresh_embedded_hwnd(self.talep_hwnd, self.talep_container))
        self.after(200, lambda: refresh_embedded_hwnd(self.talep_hwnd, self.talep_container))

    def launch_talep_browser(self):
        if getattr(self, "talep_process", None) or getattr(self, "talep_hwnd", 0):
            return

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        script_candidates = [
            os.path.join(root_dir, "tools", "dogruer_para_talep", "dogruer_talep_embed.py"),
            os.path.join(os.getcwd(), "tools", "dogruer_para_talep", "dogruer_talep_embed.py"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dogruer_para_talep", "dogruer_talep_embed.py"))
        ]
        runner_path = next((p for p in script_candidates if os.path.exists(p)), script_candidates[0])

        if not os.path.exists(runner_path):
            messagebox.showerror("Hata", f"Para Talep çalıştırıcı bulunamadı: {runner_path}")
            return

        env = os.environ.copy()
        env["QT_OPENGL"] = "software"
        site_pkgs = os.path.join(root_dir, "Lib", "site-packages")
        env["PYTHONPATH"] = f"{site_pkgs};{root_dir};{env.get('PYTHONPATH', '')}"

        def run_proc():
            try:
                self.talep_process = subprocess.Popen(
                    [sys.executable, runner_path],
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
            except Exception as e:
                print(f"Talep Process Hatası: {e}")

        threading.Thread(target=run_proc, daemon=True).start()

        def find_hwnd():
            hwnds = []

            def enum_cb(h, _):
                if win32gui and win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h)
                    if "TALEP_PYQT_EMBED_WINDOW" in t or "Para Talep" in t:
                        hwnds.append(h)
                return True

            for _ in range(25):
                time.sleep(0.4)
                hwnds.clear()
                if win32gui:
                    win32gui.EnumWindows(enum_cb, None)
                if hwnds:
                    self.talep_hwnd = hwnds[0]
                    break

            if self.talep_hwnd and win32gui:
                parent_hwnd = self.talep_container.winfo_id()
                win32gui.SetParent(self.talep_hwnd, parent_hwnd)
                style = win32gui.GetWindowLong(self.talep_hwnd, win32con.GWL_STYLE)
                style = style | win32con.WS_CHILD
                style = style & ~win32con.WS_POPUP
                style = style & ~win32con.WS_CAPTION
                style = style & ~win32con.WS_THICKFRAME
                win32gui.SetWindowLong(self.talep_hwnd, win32con.GWL_STYLE, style)

                w = self.talep_container.winfo_width()
                h = self.talep_container.winfo_height()
                win32gui.MoveWindow(self.talep_hwnd, 0, 0, w if w > 10 else 1000, h if h > 10 else 700, True)
                win32gui.ShowWindow(self.talep_hwnd, win32con.SW_SHOW)

        threading.Thread(target=find_hwnd, daemon=True).start()

    def on_talep_container_resize(self, event):
        if self.talep_hwnd and win32gui:
            win32gui.MoveWindow(self.talep_hwnd, 0, 0, event.width, event.height, True)

    def ensure_talep_embedded(self):
        if not self.talep_process:
            lbl = tk.Label(
                self.talep_container,
                text="💸 Doğruer Online Para Talep Portalı yükleniyor, lütfen bekleyin...",
                font=("Segoe UI", 12),
                bg="#e2e8f0",
                fg="#64748b"
            )
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.launch_talep_browser()
            self.after(4000, lbl.destroy)

    def reload_talep_page(self):
        if self.talep_process and self.talep_process.stdin:
            try:
                self.talep_process.stdin.write("RELOAD\n")
                self.talep_process.stdin.flush()
            except Exception:
                pass

    def resolve_exact_referance_for_talep(self, item):
        dosya = str(item.get("dosyaNo") or "").strip()
        ref = str(item.get("ref") or "").strip()
        bl = str(item.get("blNo") or item.get("bl") or "").strip()
        beyan = str(item.get("beyanNo") or item.get("beyanname_no") or "").strip()

        if re.match(r"^26-\d{5,7}$", dosya):
            return dosya

        evrim_records = getattr(self.app, "evrim_records", []) or load_evrim_cached_data()
        for ev in evrim_records:
            ev_dosya = ev.get("dosya_no", "").strip()
            ev_beyan = ev.get("beyanname_no", "").strip()
            ev_ref = ev.get("hankook_ref", "").strip()

            if beyan and ev_beyan and (beyan in ev_beyan or ev_beyan in beyan):
                return ev_dosya or ev_ref
            if bl and ((ev_ref and bl in ev_ref) or (ev_beyan and bl in ev_beyan)):
                return ev_dosya or ev_ref
            if ref and ev_ref and (ref in ev_ref or ev_ref in ref):
                return ev_dosya or ev_ref

        records = getattr(self.engine, "records", [])
        for rec in records:
            rec_dosya = str(rec.get("dosya") or "").strip()
            rec_ref = str(rec.get("ref") or "").strip()
            rec_bl = str(rec.get("bl") or "").strip()
            rec_beyan = str(rec.get("beyan") or "").strip()

            if beyan and rec_beyan and (beyan in rec_beyan or rec_beyan in beyan):
                return rec_dosya or rec_ref
            if bl and rec_bl and (bl == rec_bl or rec_bl in bl or bl in rec_bl):
                return rec_dosya or rec_ref
            if ref and rec_ref and (ref == rec_ref or rec_ref in ref):
                return rec_dosya or rec_ref

        return dosya or ref or bl

    def update_talep_queue_ui(self):
        if not hasattr(self, "lbl_q_status"):
            return

        if self.talep_queue and len(self.talep_queue) > 0:
            if self.talep_queue_idx >= len(self.talep_queue):
                self.talep_queue_idx = 0
            if self.talep_queue_idx < 0:
                self.talep_queue_idx = len(self.talep_queue) - 1

            cur = self.talep_queue_idx
            item = self.talep_queue[cur]
            f_no = item.get("faturaNo", "—")
            tutar = item.get("tutar", "0")
            dosya = self.resolve_exact_referance_for_talep(item)
            note = item.get("aciklama", "FATURA")

            self.lbl_q_status.config(
                text=f"📦 Kuyruk: {cur + 1} / {len(self.talep_queue)} | Fatura: {f_no} ({note}) | Tutar: {tutar} TL | Referans: {dosya}",
                fg="#166534"
            )
            self.btn_q_fill.config(text=f"▶️ {cur + 1}. Formu Doldur ({note})", state=tk.NORMAL, bg="#334155")
            self.btn_q_next.config(state=tk.NORMAL)
            if hasattr(self, "btn_q_prev"):
                self.btn_q_prev.config(state=tk.NORMAL)
            self.btn_q_clear.config(state=tk.NORMAL)
            self.f_talep_queue_bar.config(bg="#f0fdf4")
        else:
            self.lbl_q_status.config(
                text="📦 QNB Fatura Kuyruğu: Boş (QNB'de bulunan faturaları 'Para Talep Kuyruğuna Aktar' diyerek buraya gönderebilirsiniz)",
                fg="#64748b"
            )
            self.btn_q_fill.config(text="▶️ Form Doldur", state=tk.DISABLED, bg="#94a3b8")
            self.btn_q_next.config(state=tk.DISABLED)
            if hasattr(self, "btn_q_prev"):
                self.btn_q_prev.config(state=tk.DISABLED)
            self.btn_q_clear.config(state=tk.DISABLED)
            self.f_talep_queue_bar.config(bg="#f8fafc")

    def fill_current_queue_item(self):
        if not self.talep_queue:
            messagebox.showwarning("Uyarı", "Kuyrukta fatura bulunamadı.")
            return

        if self.talep_queue_idx >= len(self.talep_queue):
            self.talep_queue_idx = 0

        item = self.talep_queue[self.talep_queue_idx]
        self.send_to_talep_form(item)

        self.talep_queue_idx = (self.talep_queue_idx + 1) % len(self.talep_queue)
        self.update_talep_queue_ui()

    def prev_queue_item(self):
        if self.talep_queue:
            self.talep_queue_idx = (self.talep_queue_idx - 1) % len(self.talep_queue)
            self.update_talep_queue_ui()

    def skip_queue_item(self):
        if self.talep_queue:
            self.talep_queue_idx = (self.talep_queue_idx + 1) % len(self.talep_queue)
            self.update_talep_queue_ui()

    def clear_talep_queue(self):
        self.talep_queue = []
        self.talep_queue_idx = 0
        if os.path.exists(TALEP_QUEUE_PATH):
            try:
                os.remove(TALEP_QUEUE_PATH)
            except Exception:
                pass
        self.update_talep_queue_ui()
        messagebox.showinfo("Temizlendi", "🗑️ Para Talep kuyruğu temizlendi.")

    def send_to_talep_form(self, payload):
        if hasattr(self.app, "switch_tab"):
            self.app.switch_tab("TALEP")

        resolved_ref = self.resolve_exact_referance_for_talep(payload)
        payload_copy = dict(payload)
        payload_copy["dosyaNo"] = resolved_ref
        payload_copy["ref"] = resolved_ref

        def _deliver():
            for _ in range(5):
                if self.talep_process and self.talep_process.poll() is None and self.talep_process.stdin:
                    try:
                        json_str = json.dumps(payload_copy, ensure_ascii=False)
                        msg = f"FILL_FORM:{json_str}\n"
                        self.talep_process.stdin.write(msg)
                        self.talep_process.stdin.flush()
                        break
                    except Exception:
                        pass
                time.sleep(0.8)

        threading.Thread(target=_deliver, daemon=True).start()
        if hasattr(self.app, "lbl_head_subtitle"):
            self.app.lbl_head_subtitle.config(text=f"✅ {resolved_ref} bilgileri Para Talep formuna aktarıldı!", fg="#16a34a")

    def copy_talep_bookmarklet_code(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        candidates = [
            os.path.join(root_dir, "tools", "dogruer_para_talep", "dogruer_para_talep_doldurucu.js"),
            os.path.join(os.getcwd(), "tools", "dogruer_para_talep", "dogruer_para_talep_doldurucu.js"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dogruer_para_talep", "dogruer_para_talep_doldurucu.js"))
        ]
        p = next((x for x in candidates if os.path.exists(x)), candidates[0])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            bookmarklet = "javascript:" + code.replace("\n", " ")
            self.clipboard_clear()
            self.clipboard_append(bookmarklet)
            messagebox.showinfo("Kopyalandı", "✅ Para Talep bookmarklet kodu panoya kopyalandı!")
        else:
            messagebox.showwarning("Bulunamadı", f"dogruer_para_talep_doldurucu.js bulunamadı:\n{p}")


class PortalsView(BaseView):
    """
    Tüm gömülü web portal görünümlerini (QNB, GLP, Doğruer Online, Para Talep)
    bir arada barındıran veya tekil açabilen ana portal konteyneri.
    """

    def __init__(self, parent, app, portal_type="all", *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self.portal_type = portal_type
        self.qnb_view = None
        self.glp_view = None
        self.dogruer_view = None
        self.talep_view = None
        self._build_ui()

    def _build_ui(self):
        if self.portal_type == "qnb":
            self.qnb_view = QNBPortalView(self, self.app)
            self.qnb_view.pack(fill=tk.BOTH, expand=True)
        elif self.portal_type == "glp":
            self.glp_view = GLPPortalView(self, self.app)
            self.glp_view.pack(fill=tk.BOTH, expand=True)
        elif self.portal_type == "dogruer":
            self.dogruer_view = DogruerPortalView(self, self.app)
            self.dogruer_view.pack(fill=tk.BOTH, expand=True)
        elif self.portal_type == "talep":
            self.talep_view = TalepPortalView(self, self.app)
            self.talep_view.pack(fill=tk.BOTH, expand=True)
        else:
            # Tabbed multi-portal container
            self.nb = ttk.Notebook(self)
            self.nb.pack(fill=tk.BOTH, expand=True)

            tab_qnb = ttk.Frame(self.nb)
            self.nb.add(tab_qnb, text="  🌐 QNB eSolutions  ")
            self.qnb_view = QNBPortalView(tab_qnb, self.app)
            self.qnb_view.pack(fill=tk.BOTH, expand=True)

            tab_glp = ttk.Frame(self.nb)
            self.nb.add(tab_glp, text="  🚛 Hankook GLP  ")
            self.glp_view = GLPPortalView(tab_glp, self.app)
            self.glp_view.pack(fill=tk.BOTH, expand=True)

            tab_dogruer = ttk.Frame(self.nb)
            self.nb.add(tab_dogruer, text="  🌐 Doğruer Online  ")
            self.dogruer_view = DogruerPortalView(tab_dogruer, self.app)
            self.dogruer_view.pack(fill=tk.BOTH, expand=True)

            tab_talep = ttk.Frame(self.nb)
            self.nb.add(tab_talep, text="  💸 Para Talep  ")
            self.talep_view = TalepPortalView(tab_talep, self.app)
            self.talep_view.pack(fill=tk.BOTH, expand=True)

    def on_activate(self):
        if self.qnb_view and hasattr(self.qnb_view, "on_activate"):
            self.qnb_view.on_activate()
        if self.glp_view and hasattr(self.glp_view, "on_activate"):
            self.glp_view.on_activate()
        if self.dogruer_view and hasattr(self.dogruer_view, "on_activate"):
            self.dogruer_view.on_activate()
        if self.talep_view and hasattr(self.talep_view, "on_activate"):
            self.talep_view.on_activate()

    def ensure_qnb_embedded(self):
        if self.qnb_view:
            self.qnb_view.ensure_qnb_embedded()

    def ensure_glp_embedded(self):
        if self.glp_view:
            self.glp_view.ensure_glp_embedded()

    def ensure_dogruer_embedded(self):
        if self.dogruer_view:
            self.dogruer_view.ensure_dogruer_embedded()

    def ensure_talep_embedded(self):
        if self.talep_view:
            self.talep_view.ensure_talep_embedded()
