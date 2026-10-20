"""
==============================================================================
🏦 QNB eSolutions - Gömülü Web Tarayıcısı & Eşleştirici v3.1 (Subprocess Docking)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
==============================================================================
"""

import os
import sys
import time
import threading
import webview

QNB_PORTAL_URL = "https://portal.qnbesolutions.com.tr/yonetim/"

def get_matcher_js():
    p = os.path.join(os.path.dirname(__file__), "fatura_eslestirici.js")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def inject_script_loop(window):
    js_code = get_matcher_js()
    if not js_code:
        return

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

def main():
    target_title = sys.argv[1] if len(sys.argv) > 1 else "QNB_EMBEDDED_VIEW"

    window = webview.create_window(
        title=target_title,
        url=QNB_PORTAL_URL,
        width=1100,
        height=750,
        frameless=True
    )

    t = threading.Thread(target=inject_script_loop, args=(window,), daemon=True)
    t.start()

    webview.start(private_mode=False)

if __name__ == "__main__":
    main()
