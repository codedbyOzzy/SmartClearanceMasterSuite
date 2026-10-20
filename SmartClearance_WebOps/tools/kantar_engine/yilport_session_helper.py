import os, sys, json, time
from playwright.sync_api import sync_playwright

config_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), "SmartClearance")
os.makedirs(config_dir, exist_ok=True)
profile_dir = os.path.join(config_dir, "Yilport_Profile")
session_file = os.path.join(config_dir, "yilport_session.json")

def main():
    print("Yılport oturum penceresi açılıyor...")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://online.yilport.com/TRGEB/Unit?ExportFile=False&SearchType=UNITNO&SearchQuery=TRHU6719876", timeout=60000)
        
        # Wait up to 120 seconds for the user to check captcha or for card to appear
        success = False
        for i in range(120):
            time.sleep(1)
            # Check if captcha form is gone or unit result is loaded
            is_verified = page.evaluate("""() => {
                let hasForm = document.querySelector('#frmVerification');
                let hasCard = document.body && (document.body.innerText.includes('Records Found') || document.body.innerText.includes('Get Weighbridge Ticket') || document.body.innerText.includes('Container Waiting'));
                return !hasForm || hasCard;
            }""")
            
            if is_verified:
                print("Doğrulama başarılı! Çerezler kaydediliyor...")
                cookies = ctx.cookies()
                saved_cookies = {c['name']: c['value'] for c in cookies if 'yilport' in c['domain']}
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(saved_cookies, f, indent=2)
                print("Çerezler kaydedildi:", session_file)
                success = True
                time.sleep(2)
                break
                
        ctx.close()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
