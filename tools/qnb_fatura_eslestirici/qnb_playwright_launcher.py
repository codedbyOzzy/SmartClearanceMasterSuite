"""
==============================================================================
🚀 QNB eSolutions Playwright Otomatik Eşleştirici Yükleyici
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
Özellikler:
- Microsoft Edge tarayıcısını açar.
- portal.qnbesolutions.com.tr sayfasına gider.
- 'Üzerimdeki İşler' veya fatura listesi ekranda belirdiği anda eşleştiriciyi KENDİLİĞİNDEN otomatik basar!
- Asla kapanmaz, oturum açık kalır.
==============================================================================
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

QNB_PORTAL_URL = "https://portal.qnbesolutions.com.tr/yonetim/"

def get_matcher_js():
    p = os.path.join(os.path.dirname(__file__), "fatura_eslestirici.js")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def main():
    js_code = get_matcher_js()
    user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Dogruer_QNB_Browser_Profile")

    with sync_playwright() as p:
        # Kullanıcının kurulu Microsoft Edge tarayıcısını kalıcı oturum profiliyle başlat
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="msedge",
            viewport=None,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        page.goto(QNB_PORTAL_URL)

        # Sayfa üzerinde izleyici döngü: Her 1.5 saniyede bir paneli kontrol et ve bas
        while True:
            try:
                if page.is_closed():
                    break

                exists = page.evaluate("Boolean(document.getElementById('gumruk-eslestirici-panel'))")
                if not exists:
                    # Sayfada herhangi bir tablo veya menü yüklendiyse scripti enjekte et
                    has_table = page.evaluate("Boolean(document.body && (document.querySelector('tr') || document.querySelector('.brow') || document.body.innerText.includes('Üzerimdeki İşler') || document.body.innerText.includes('Fatura')))")
                    if has_table and js_code:
                        page.evaluate(js_code)
            except Exception as e:
                # Sayfa yenilenirken veya yönlenirken hata olursa devam et
                pass

            time.sleep(1.5)

if __name__ == "__main__":
    main()
