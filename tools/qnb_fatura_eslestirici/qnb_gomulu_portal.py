"""
==============================================================================
🏦 QNB eSolutions - Özel Web Tarayıcısı & Eşleştirici v3.2
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
Özellikler:
- QNB Portalını (portal.qnbesolutions.com.tr) yüksek performanslı WebView2 ile açar.
- Sayfa açıldığında veya geçiş yapıldığında fatura_eslestirici.js kodunu anında enjekte eder.
- Kararma veya çökme yaşanmaz.
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

    # Güvenli enjeksiyon kodu
    safe_wrapper = f"""
    (function() {{
        try {{
            if (!document.getElementById('gumruk-eslestirici-panel')) {{
                {js_code}
            }}
        }} catch(e) {{
            console.error('Eşleştirici yükleme hatası:', e);
        }}
    }})();
    """

    while True:
        time.sleep(1.5)
        try:
            exists = window.evaluate_js("Boolean(document.getElementById('gumruk-eslestirici-panel'))")
            if not exists:
                has_content = window.evaluate_js("Boolean(document.body && document.body.innerText && document.body.innerText.length > 20)")
                if has_content:
                    window.evaluate_js(safe_wrapper)
        except Exception:
            pass

def main():
    window = webview.create_window(
        title="🏦 QNB eSolutions Portalı & Hankook Fatura Eşleştirici - Doğruer",
        url=QNB_PORTAL_URL,
        width=1340,
        height=860,
        resizable=True,
        confirm_close=False
    )

    t = threading.Thread(target=inject_script_loop, args=(window,), daemon=True)
    t.start()

    webview.start(private_mode=False)

if __name__ == "__main__":
    main()
