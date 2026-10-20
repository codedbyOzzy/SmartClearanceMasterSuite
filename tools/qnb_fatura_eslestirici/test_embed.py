import os
import sys
import time
import threading
import tkinter as tk
import win32gui
import win32con
import webview

def get_matcher_js():
    p = os.path.join(r"C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools\qnb_fatura_eslestirici", "fatura_eslestirici.js")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def test_embed():
    root = tk.Tk()
    root.title("Test Embedding")
    root.geometry("1100x750")

    container = tk.Frame(root, bg="#ffffff")
    container.pack(fill=tk.BOTH, expand=True)

    title = "QNB_EMBEDDED_INTERNAL_TARGET"

    def run_webview():
        window = webview.create_window(
            title=title,
            url="https://portal.qnbesolutions.com.tr/yonetim/",
            width=1000,
            height=700,
            frameless=True
        )

        def inject_loop():
            js_code = get_matcher_js()
            while True:
                time.sleep(1.5)
                try:
                    exists = window.evaluate_js("Boolean(document.getElementById('gumruk-eslestirici-panel'))")
                    if not exists:
                        has_content = window.evaluate_js("Boolean(document.body && document.body.innerText && document.body.innerText.length > 30)")
                        if has_content:
                            window.evaluate_js(js_code)
                except Exception:
                    pass

        threading.Thread(target=inject_loop, daemon=True).start()
        webview.start(private_mode=False)

    threading.Thread(target=run_webview, daemon=True).start()

    def embed_worker():
        hwnd_child = 0
        for _ in range(50):
            time.sleep(0.2)
            hwnd_child = win32gui.FindWindow(None, title)
            if hwnd_child:
                break

        if hwnd_child:
            hwnd_parent = container.winfo_id()
            win32gui.SetParent(hwnd_child, hwnd_parent)
            
            style = win32gui.GetWindowLong(hwnd_child, win32con.GWL_STYLE)
            style &= ~win32con.WS_POPUP
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            style &= ~win32con.WS_MINIMIZEBOX
            style &= ~win32con.WS_MAXIMIZEBOX
            style |= win32con.WS_CHILD
            win32gui.SetWindowLong(hwnd_child, win32con.GWL_STYLE, style)
            
            w = container.winfo_width() or 1000
            h = container.winfo_height() or 700
            win32gui.MoveWindow(hwnd_child, 0, 0, w, h, True)

            def on_resize(event):
                if event.width > 10 and event.height > 10:
                    win32gui.MoveWindow(hwnd_child, 0, 0, event.width, event.height, True)

            container.bind("<Configure>", on_resize)
            print("EMBED SUCCESSFUL!")
        else:
            print("HWND NOT FOUND")

    threading.Thread(target=embed_worker, daemon=True).start()

    # root.after(3000, root.destroy) # test
    root.update()
    time.sleep(1)
    root.destroy()

test_embed()
