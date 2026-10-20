# -*- coding: utf-8 -*-
"""
windows_notifier.py — Windows 10/11 Yerel Toast & Balon Bildirim Modülü
Doğruer MasterSuite GTB tescil ve DP World Kantar sonuçları için masaüstü bildirimleri üretir.
"""

import os
import sys
import json
import time
import queue
import threading
import subprocess

CONFIG_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "SmartClearance",
    "app_config.json"
)

_notify_queue = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def is_notifications_enabled() -> bool:
    """Kullanıcı ayarlarından masaüstü bildirimlerinin açık olup olmadığını denetler."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return bool(cfg.get("enable_desktop_notifications", True))
    except Exception:
        pass
    return True


def _show_gui_toast(title: str, message: str):
    """Antivirüslere takılmayan, tamamen yerel Python Tkinter bildirim kartı."""
    try:
        import tkinter as tk
        top = tk.Toplevel()
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        w, h = 380, 95
        top.geometry(f"{w}x{h}+{sw-w-25}+{sh-h-65}")
        top.configure(bg="#0f172a")

        # Kenarlık kartı
        border_frame = tk.Frame(top, bg="#38bdf8", bd=1)
        border_frame.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(border_frame, bg="#0f172a", padx=14, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(inner, bg="#0f172a")
        header.pack(fill=tk.X)

        lbl_t = tk.Label(header, text=title, font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#0f172a", anchor="w")
        lbl_t.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_x = tk.Label(header, text="✕", font=("Segoe UI", 9, "bold"), fg="#64748b", bg="#0f172a", cursor="hand2")
        btn_x.pack(side=tk.RIGHT)
        btn_x.bind("<Button-1>", lambda e: top.destroy())

        lbl_m = tk.Label(inner, text=message, font=("Segoe UI", 9), fg="#f8fafc", bg="#0f172a", anchor="w", justify="left")
        lbl_m.pack(fill=tk.X, pady=(4, 0))

        # 6 saniye sonra otomatik kapan
        top.after(6000, lambda: top.destroy() if top.winfo_exists() else None)
    except Exception:
        pass


def _run_win32_balloon(title: str, message: str) -> bool:
    """PowerShell başarısız olursa Win32 Tray Icon Balloon Tip ile bildirim gösterir."""
    try:
        import win32gui
        import win32con

        class BalloonTip:
            def __init__(self, t, m):
                self.title = t
                self.msg = m
                message_map = {win32con.WM_DESTROY: self.on_destroy}
                wc = win32gui.WNDCLASS()
                self.hinst = wc.hInstance = win32gui.GetModuleHandle(None)
                wc.lpszClassName = "SmartClearanceNotify"
                wc.lpfnWndProc = message_map
                try:
                    self.classAtom = win32gui.RegisterClass(wc)
                except Exception:
                    self.classAtom = win32gui.GetClassInfo(self.hinst, "SmartClearanceNotify")
                
                style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
                self.hwnd = win32gui.CreateWindow(
                    "SmartClearanceNotify", "Notify", style, 0, 0,
                    win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, 0, 0, self.hinst, None
                )
                win32gui.UpdateWindow(self.hwnd)
                
                icon_flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP | win32gui.NIF_INFO
                nid = (
                    self.hwnd, 0, icon_flags, win32con.WM_USER + 20,
                    win32gui.LoadIcon(0, win32con.IDI_APPLICATION), "SmartClearance",
                    self.msg, 200, self.title, win32gui.NIIF_INFO
                )
                win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
                time.sleep(3)
                win32gui.DestroyWindow(self.hwnd)

            def on_destroy(self, hwnd, msg, wparam, lparam):
                nid = (self.hwnd, 0)
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
                win32gui.PostQuitMessage(0)

        BalloonTip(title, message)
        return True
    except Exception:
        return False


def _notification_worker():
    """Arka planda bildirim kuyruğunu işleyen tekil iş parçacığı."""
    while True:
        try:
            item = _notify_queue.get()
            if item is None:
                break
            title, msg = item
            _show_gui_toast(title, msg)
            time.sleep(1.2)
            _notify_queue.task_done()
        except Exception:
            pass


def send_desktop_notification(title: str, message: str, force: bool = False):
    """
    Sisteme güvenli, asenkron Windows masaüstü bildirimi gönderir.
    Ayarlarda kapalıysa bildirim fırlatılmaz (force=True hariç).
    """
    if not force and not is_notifications_enabled():
        return

    global _worker_started
    with _worker_lock:
        if not _worker_started:
            t = threading.Thread(target=_notification_worker, daemon=True, name="DesktopNotifierWorker")
            t.start()
            _worker_started = True

    _notify_queue.put((title, message))
