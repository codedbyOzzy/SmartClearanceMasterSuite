
import os
import sys
import json
import time
import re
import uuid
import mimetypes
import urllib.request
import urllib.parse
import threading
import datetime

# Path Ayarları
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kantar_engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "gtb_engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from kantar_sorgu import kantar_otomatik_sorgula, kantar_pdf_indir
    from kantar_tracker_service import get_kantar_tracker_service
except Exception:
    try:
        from tools.kantar_engine.kantar_sorgu import kantar_otomatik_sorgula, kantar_pdf_indir
        from tools.kantar_engine.kantar_tracker_service import get_kantar_tracker_service
    except Exception as e:
        print(f"[TG-IMPORT-ERROR] {e}")
        kantar_otomatik_sorgula = None
        kantar_pdf_indir = None
        get_kantar_tracker_service = None

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

try:
    from tools.secrets_store import get_secret
except Exception:
    try:
        from secrets_store import get_secret
    except Exception:
        get_secret = lambda name, default="": default

# Teams Köprüsü (Outlook → Teams kanal e-postası)
try:
    from tools.teams_bridge.teams_bridge import get_teams_bridge
except Exception:
    try:
        import sys as _sys, os as _os
        _sys.path.append(_os.path.join(_os.path.dirname(__file__), "..", "teams_bridge"))
        from teams_bridge import get_teams_bridge
    except Exception:
        get_teams_bridge = None

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
TELEGRAM_CONFIG_PATH = os.path.join(CONFIG_DIR, "telegram_config.json")
TEMP_VAULT_DIR = os.path.join(CONFIG_DIR, "temp_evrak_vault")
DEFAULT_TOKEN = get_secret("telegram_bot_token", "")

os.makedirs(TEMP_VAULT_DIR, exist_ok=True)

def load_telegram_config():
    if os.path.exists(TELEGRAM_CONFIG_PATH):
        try:
            with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "bot_token": DEFAULT_TOKEN,
        "enabled": True,
        "authorized_chat_ids": [],
        "notify_kirmizi_hat": True,
        "notify_tescil": True
    }

def save_telegram_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TELEGRAM_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Telegram Config Save Error: {e}")
        return False


class TelegramBotService:
    def __init__(self, data_engine=None, evrim_data_provider=None, gtb_tracker_provider=None, kantar_tracker_provider=None):
        self.config = load_telegram_config()
        self.token = self.config.get("bot_token", DEFAULT_TOKEN)
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.data_engine = data_engine
        self.evrim_data_provider = evrim_data_provider
        self.gtb_tracker_provider = gtb_tracker_provider
        self.kantar_tracker_provider = kantar_tracker_provider
        self.is_running = False
        self.last_update_id = 0
        self.thread = None

    def update_token(self, new_token: str) -> dict:
        """Tokeni doğrular, geçerliyse kaydeder ve servisi günceller."""
        token_clean = new_token.strip()
        if not token_clean:
            return {"ok": False, "error": "Token boş olamaz"}
        test_url = f"https://api.telegram.org/bot{token_clean}/getMe"
        try:
            req = urllib.request.Request(test_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("ok"):
                    self.token = token_clean
                    self.config["bot_token"] = token_clean
                    save_telegram_config(self.config)
                    self.base_url = f"https://api.telegram.org/bot{self.token}"
                    print(f"[TELEGRAM] Bot Token başarıyla güncellendi: @{res.get('result', {}).get('username')}")
                    return {"ok": True, "bot": res.get("result", {})}
                return {"ok": False, "error": res.get("description", "Geçersiz token")}
        except Exception as ex:
            return {"ok": False, "error": str(ex)}

    def api_request(self, endpoint, payload=None):
        if not self.token:
            return {"ok": False, "error": "Bot token girilmemiş"}
        url = f"{self.base_url}/{endpoint}"
        try:
            if payload:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.api_request("sendMessage", payload)

    def _normalized_authorized_ids(self):
        ids = self.config.get("authorized_chat_ids") or []
        usernames = self.config.get("authorized_usernames") or []
        return {str(x).strip() for x in ids if str(x).strip()}, {str(x).strip().lstrip("@").lower() for x in usernames if str(x).strip()}

    def _is_chat_authorized(self, chat_id, username=None) -> bool:
        allowed_ids, allowed_names = self._normalized_authorized_ids()
        if not allowed_ids and not allowed_names:
            return False
        if chat_id is not None and str(chat_id) in allowed_ids:
            return True
        if username:
            uname = str(username).strip().lstrip("@").lower()
            if uname and uname in allowed_names:
                return True
        return False

    def _deny_unauthorized(self, chat_id, callback_query_id=None):
        text = (
            "Yetkisiz sohbet. Bu bot yalnızca yöneticinin Ayarlar / telegram_config.json "
            "içinde eklediği chat id'lere yanıt verir."
        )
        if callback_query_id:
            self.answer_callback_query(callback_query_id, "Yetkisiz.")
        if chat_id:
            self.send_message(chat_id, text)

    def answer_callback_query(self, callback_query_id, text=""):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return self.api_request("answerCallbackQuery", payload)

    def send_document(self, chat_id, file_path, caption=""):
        """Gerçek PDF/Excel dosyasını multipart/form-data ile Telegram'a yükler."""
        if not os.path.exists(file_path):
            return {"ok": False, "error": "Dosya bulunamadı"}

        boundary = uuid.uuid4().hex
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/pdf"

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            body_parts = []
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))

            if caption:
                body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
                body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))

            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: {mime_type}\r\n\r\n".encode("utf-8")
            )
            body_parts.append(file_bytes)
            body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

            payload = b"".join(body_parts)
            req = urllib.request.Request(f"{self.base_url}/sendDocument", data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": str(e)}


    # ── GÜNLÜK SABAH BÜLTENİ & AKŞAM KAPANIŞ ROBOTU ──────────────────────────
    def generate_morning_briefing(self) -> str:
        """Her sabah 08:30'da veya /bulten komutunda canlı operasyon brifingi üretir."""
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # GTB İstatistikleri
        gtb_recs = []
        if self.gtb_tracker_provider:
            gt = self.gtb_tracker_provider()
            if gt: gtb_recs = gt.list_tracked()

        gtb_total = len(gtb_recs)
        gtb_kirmizi = [r for r in gtb_recs if "KIRMIZI" in (r.get("hat") or "").upper() or "Muayene" in (r.get("durum") or "")]
        gtb_tescil = [r for r in gtb_recs if not (r.get("kapandi") or "Kapandı" in (r.get("durum") or ""))]

        # Kantar İstatistikleri
        kantar_recs = []
        if self.kantar_tracker_provider:
            kt = self.kantar_tracker_provider()
            if kt: kantar_recs = kt.list_tracked()
        
        kantar_ready = [k for k in kantar_recs if k.get("kilo") and str(k.get("kilo")).strip()]
        kantar_waiting = len(kantar_recs) - len(kantar_ready)

        # Outlook Vergi Maili Bekleyenler
        tax_pending_count = 0
        approaching = []
        if self.data_engine and hasattr(self.data_engine, "records"):
            tax_pending_count = sum(1 for r in self.data_engine.records if not r.get("kapanis") and r.get("is_tax_pending") and r.get("mail_badge") == "red")
            today = datetime.datetime.now().date()
            for rec in self.data_engine.records:
                if rec.get("kapanis"):
                    continue
                eta_raw = str(rec.get("eta") or "").strip()
                if not eta_raw:
                    continue
                clean_str = eta_raw.replace("T", " ").split(" ")[0].strip()
                eta_dt = None
                for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y.%m.%d"):
                    try:
                        eta_dt = datetime.datetime.strptime(clean_str[:10], fmt).date()
                        break
                    except Exception:
                        pass
                if not eta_dt:
                    continue
                fark = (eta_dt - today).days
                if 0 <= fark <= 7:
                    approaching.append((fark, rec, eta_dt))
            approaching.sort(key=lambda x: x[0])

        eta_sample = ""
        if approaching:
            samples = []
            for fark, rec, eta_dt in approaching[:3]:
                label = rec.get("konteyner") or rec.get("bl") or rec.get("ref") or rec.get("dosya") or "—"
                samples.append(f"<code>{label}</code> ({eta_dt.strftime('%d.%m.%Y')})")
            eta_sample = "• <i>Örnek yaklaşan:</i> " + ", ".join(samples) + "\n"

        tax_warn = ""
        if tax_pending_count > 0:
            tax_warn = f"\n📧 <b>Outlook Uyarısı:</b> ⚠️ <b>{tax_pending_count} dosya</b> için vergi maili atılması bekleniyor!\n"

        msg = (
            "☀️ <b>GÜNAYDIN DOĞRUER EKİBİ!</b>\n"
            "📋 <b>GÜNLÜK OPERASYON VE İŞ BÜLTENİ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Tarih:</b> {now_str}\n\n"
            f"🏛️ <b>Ticaret Bakanlığı (GTB) Havuzu:</b>\n"
            f"• <b>Toplam Takipte:</b> {gtb_total} beyanname\n"
            f"• 🔴 <b>Kırmızı Hat / Muayene:</b> {len(gtb_kirmizi)} dosya\n"
            f"• 🔵 <b>Tescilde / İşlemde:</b> {len(gtb_tescil)} dosya\n\n"
            f"⚖️ <b>DP World Kantar & DBA Durumu:</b>\n"
            f"• 🟢 <b>Tartımı Biten (Tike Hazır):</b> {len(kantar_ready)} konteyner\n"
            f"• ⏳ <b>Tartım Bekleyen:</b> {kantar_waiting} konteyner\n\n"
            f"🚢 <b>Yaklaşan Gemiler (Excel ETA, 7 gün):</b>\n"
            f"• <b>Yaklaşan açık dosya:</b> {len(approaching)} adet\n"
            f"{eta_sample}"
            f"{tax_warn}"
            "\n━━━━━━━━━━━━━━━━━━━━━━\n"
            "📱 <i>Cebinizden canlı izlemek için Mobil Paneli açabilirsiniz.</i>\n"
            "🚀 <i>Hayırlı işler ve bol operasyonlu bir gün dileriz!</i>"
        )
        return msg

    def generate_evening_report(self) -> str:
        """Her akşam 18:00'de veya /kapanis komutunda gün sonu kapanış raporu üretir."""
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        gtb_recs = []
        if self.gtb_tracker_provider:
            gt = self.gtb_tracker_provider()
            if gt: gtb_recs = gt.list_tracked()

        gtb_closed = [r for r in gtb_recs if r.get("kapandi") or "Kapandı" in (r.get("durum") or "")]
        gtb_ongoing = len(gtb_recs) - len(gtb_closed)

        kantar_recs = []
        if self.kantar_tracker_provider:
            kt = self.kantar_tracker_provider()
            if kt: kantar_recs = kt.list_tracked()
        kantar_ready = [k for k in kantar_recs if k.get("kilo") and str(k.get("kilo")).strip()]

        msg = (
            "🌙 <b>GÜN SONU İŞ VE İŞLEM KAPANIŞ RAPORU</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Kapanış Zamanı:</b> {now_str}\n\n"
            f"✅ <b>GTB Kapanan / Tamamlanan:</b> {len(gtb_closed)} beyanname\n"
            f"⏳ <b>Yarına Devreden İşlemde GTB:</b> {gtb_ongoing} beyanname\n"
            f"⚖️ <b>Bugün Alınan Kantar Tikeleri:</b> {len(kantar_ready)} konteyner tartıldı\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "👏 <i>Bugünkü tüm emekleriniz için teşekkür eder, iyi akşamlar ve iyi dinlenmeler dileriz!</i>"
        )
        return msg

    def broadcast_message(self, text: str):
        """Yetkili tüm Telegram sohbetlerine toplu bildirim gönderir. Teams kanalına da iletir."""
        chat_ids = self.config.get("authorized_chat_ids", [])
        for cid in chat_ids:
            try:
                self.send_message(cid, text)
            except Exception as e:
                print(f"[TG-BROADCAST-ERR] {cid}: {e}")
        # Teams köprüsüne de gönder
        try:
            if get_teams_bridge:
                get_teams_bridge().notify_broadcast(text)
        except Exception as te:
            print(f"[TEAMS-BROADCAST-ERR] {te}")

    def _daily_scheduler_loop(self):
        """Her gün 08:30 ve 18:00 saatlerini otonom kontrol eden zamanlayıcı."""
        last_morning_date = ""
        last_evening_date = ""
        while self.is_running:
            try:
                now = datetime.datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                curr_hour_min = now.strftime("%H:%M")

                # Sabah Bülteni (08:30)
                if curr_hour_min == "08:30" and last_morning_date != today_str:
                    last_morning_date = today_str
                    bulten = self.generate_morning_briefing()
                    self.broadcast_message(bulten)
                    # Teams'e özel başlıkla ayrıca gönder
                    try:
                        if get_teams_bridge:
                            get_teams_bridge().notify_morning_briefing(bulten)
                    except Exception:
                        pass

                # Akşam Kapanış Raporu (18:00)
                if curr_hour_min == "18:00" and last_evening_date != today_str:
                    last_evening_date = today_str
                    rapor = self.generate_evening_report()
                    self.broadcast_message(rapor)
                    # Teams'e özel başlıkla ayrıca gönder
                    try:
                        if get_teams_bridge:
                            get_teams_bridge().notify_evening_report(rapor)
                    except Exception:
                        pass

                time.sleep(25)
            except Exception:
                time.sleep(30)

    def get_main_keyboard(self):
        mobile_url = self.config.get("mobile_web_app_url", "").strip()
        top_row = []
        if mobile_url:
            top_row = [{"text": "📱 Mobil Kokpit (TMA)", "web_app": {"url": mobile_url}}]
        else:
            top_row = [{"text": "📱 Mobil Kokpit"}]

        rows = [
            top_row,
            [{"text": "📊 Genel Durum"}, {"text": "🏛️ GTB Takip Havuzu"}],
            [{"text": "☕ Sabah Bülteni"}, {"text": "🌙 Akşam Kapanış"}],
            [{"text": "🔴 Kırmızı Hat"}, {"text": "🔵 Tescildekiler"}],
            [{"text": "⚖️ Kantar Takip"}, {"text": "🏢 Hankook Dosyaları"}],
            [{"text": "✉️ Son Mailler"}]
        ]
        return {
            "keyboard": rows,
            "resize_keyboard": True,
            "is_persistent": True
        }

    def start_polling(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.thread.start()
        
        # Otonom Sabah (08:30) & Aksam (18:00) Zamanlayicisi
        self.scheduler_thread = threading.Thread(target=self._daily_scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        try:
            print("[INFO] SmartClearance Telegram Asistani & GTB Robotu Baslatildi (@scMASTERSUITbot)!")
        except Exception:
            pass

    def stop_polling(self):
        self.is_running = False

    def _polling_loop(self):
        while self.is_running:
            if not self.token:
                time.sleep(3)
                continue
            try:
                updates_resp = self.api_request(f"getUpdates?offset={self.last_update_id + 1}&timeout=10")
                if updates_resp.get("ok"):
                    results = updates_resp.get("result", [])
                    for u in results:
                        self.last_update_id = max(self.last_update_id, u.get("update_id", 0))
                        
                        if "message" in u:
                            self._handle_message(u["message"])
                        elif "callback_query" in u:
                            self._handle_callback_query(u["callback_query"])

                time.sleep(1)
            except Exception as e:
                time.sleep(3)

    def _handle_callback_query(self, cb):
        cb_id = cb.get("id")
        data = cb.get("data", "")
        chat_id = (cb.get("message") or {}).get("chat", {}).get("id")
        if not chat_id:
            chat_id = (cb.get("from") or {}).get("id")
        from_user = cb.get("from") or {}
        username = from_user.get("username")

        if not chat_id or not data:
            return

        if not self._is_chat_authorized(chat_id, username):
            self._deny_unauthorized(chat_id, callback_query_id=cb_id)
            return

        if data.startswith("doc:"):
            target_key = data[4:].strip()
            self.answer_callback_query(cb_id, f"📄 {target_key} evrakları taranıyor...")
            self._send_file_documents(chat_id, target_key)

        elif data.startswith("mail:"):
            target_key = data[5:].strip()
            self.answer_callback_query(cb_id, f"✉️ {target_key} mail akışı açılıyor...")
            self._send_conversation_flow(chat_id, target_key)

        elif data.startswith("kantar:"):
            target_key = data[7:].strip()
            self.answer_callback_query(cb_id, f"⚖️ {target_key} kantar tikesi taranıyor...")
            self._send_kantar_live_inquiry(chat_id, target_key)

        elif data.startswith("gtb:"):
            target_key = data[4:].strip()
            self.answer_callback_query(cb_id, f"🏛️ {target_key} için GTB Bakanlık sorgusu başlatıldı...")
            self._send_gtb_live_inquiry(chat_id, target_key)

    def _handle_message(self, msg):
        chat_id = msg.get("chat", {}).get("id")
        user_name = msg.get("from", {}).get("first_name", "Kullanıcı")
        raw_text = (msg.get("text") or "").strip()

        if not chat_id or not raw_text:
            return

        username = (msg.get("from") or {}).get("username")
        cmd = raw_text.lower().strip()

        # START & YARDIM: İlk /start atan kişiyi otomatik yetkilendir (Otomatik Eşleştirme)
        if cmd in ("/start", "❓ yardım & komutlar", "/yardim", "/help") or cmd.startswith("/start"):
            allowed_ids = self.config.get("authorized_chat_ids", [])
            if str(chat_id) not in [str(x) for x in allowed_ids]:
                allowed_ids.append(chat_id)
                self.config["authorized_chat_ids"] = allowed_ids
                save_telegram_config(self.config)
                print(f"[TELEGRAM] Kullanıcı otomatik yetkilendirildi: chat_id={chat_id}, username={username}")
        elif not self._is_chat_authorized(chat_id, username):
            self._deny_unauthorized(chat_id)
            return

        # SABAH BÜLTENİ (/bulten, /sabah, ☕ Sabah Bülteni)
        if cmd in ("/bulten", "/sabah", "/morning", "☕ sabah bülteni", "sabah bülteni"):
            bulten = self.generate_morning_briefing()
            self.send_message(chat_id, bulten)
            return

        # AKŞAM KAPANIŞ RAPORU (/kapanis, /aksam, 🌙 Akşam Kapanış)
        if cmd in ("/kapanis", "/aksam", "/evening", "🌙 akşam kapanış", "akşam kapanış"):
            rapor = self.generate_evening_report()
            self.send_message(chat_id, rapor)
            return

        # MOBİL PANEL LINKI & DOSYASI (/mobil, /panel, 📱 Mobil Panel)
        if cmd in ("/mobil", "/panel", "📱 mobil panel", "mobil panel"):
            ip_link = "http://192.168.32.13:8080"
            txt = (
                "📱 <b>MasterSuite Canlı Mobil Web Paneli</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>Doğrudan Safari Linki:</b> {ip_link}\n\n"
                "💡 <i>Aynı WiFi / şirket ağına bağlıyken yukarıdaki linke dokunarak Safari'de anında açabilirsiniz.</i>\n"
                "📌 <i>Safari'de açtıktan sonra 'Ana Ekrana Ekle' diyerek uygulama simgesi yapabilirsiniz.</i>"
            )
            self.send_message(chat_id, txt)
            html_path = os.path.join(os.path.dirname(__file__), "..", "..", "MasterSuite_Mobil_Paneli.html")
            if os.path.exists(html_path):
                self.send_document(chat_id, html_path, caption="📱 Offline / Dosya olarak açmak için HTML dosyası")
            return

        # 1. BAŞLANGIÇ & YARDIM
        if cmd in ("/start", "❓ yardım & komutlar", "/yardim", "/help"):
            welcome = (
                f"👋 <b>Merhaba {user_name}!</b>\n\n"
                f"🛡️ <b>SmartClearance MasterSuite Mobil Asistanı & GTB Robotu</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Doğruer Gümrük Müşavirliği canlı kokpit, Evrim, Outlook, <b>GTB Bakanlık Otonom Takibi</b> ve <b>PDF Evrak Kasasına</b> 7/24 cebinizden ulaşabilirsiniz.\n\n"
                f"🔍 <b>Tekli / Çoklu Dosya Sorgulama:</b>\n"
                f"Tek bir dosya no veya <b>alt alta birden fazla referans/dosya</b> yazabilirsiniz:\n"
                f"<code>4200781520\n4200775287\n4200800547</code>\n\n"
                f"🏛️ <b>Ticaret Bakanlığı (GTB) Canlı Sorgulama:</b>\n"
                f"• <code>/gtb 26410300IM00046507</code> ➡️ Bakanlık sistemine anlık bağlanıp captcha'yı çözer ve canlı durumu getirir.\n"
                f"• <code>/gtbtakip</code> ➡️ Otonom takipteki tüm beyannameleri listeler.\n"
                f"• <code>/gtbekle 4200788048</code> ➡️ Beyannameyi 10 dk'lık otomatik izleme havuzuna ekler.\n\n"
                f"📄 <b>Mobil PDF Evrak Kasası:</b>\n"
                f"• <code>/evrak 4200788048</code> ➡️ Beyanname, Fatura, BL PDF'lerini telefona indirir!\n\n"
                f"✉️ <b>Mail & Yazışma Akışı:</b>\n"
                f"• <code>/mail 4200788048</code> ➡️ Dosyaya ait tüm mail zinciri adımları\n"
                f"• <code>/sonmailler</code> ➡️ Son gelen gümrük mailleri\n\n"
                f"📌 <b>Hızlı Durum Komutları:</b>\n"
                f"• 📊 <code>/durum</code> ➡️ Canlı Operasyon Özeti\n"
                f"• 🔴 <code>/kirmizi</code> ➡️ Kırmızı Hattaki Dosyalar\n"
                f"• 🔵 <code>/tescil</code> ➡️ Tescil Aşamasındakiler\n"
            )
            self.send_message(chat_id, welcome, reply_markup=self.get_main_keyboard())
            return

        # MOBİL KOKPİT (TMA & PWA)
        if cmd in ("/mobil", "📱 mobil kokpit", "📱 mobil kokpit (tma)", "/kokpit", "/app"):
            mobile_url = self.config.get("mobile_web_app_url", "").strip()
            if mobile_url:
                msg = (
                    "📱 <b>SmartClearance Mobil Kokpit & Gemi Radarı (TMA)</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Apple / Vercel standartlarında canlı mobil operasyon kokpiti ve küresel konteyner haritasını açmak için aşağıdaki butona dokunun:"
                )
                inline_kb = {
                    "inline_keyboard": [
                        [{"text": "🚀 Canlı Mobil Kokpiti Aç (TMA)", "web_app": {"url": mobile_url}}]
                    ]
                }
                self.send_message(chat_id, msg, reply_markup=inline_kb)
            else:
                msg = (
                    "📱 <b>SmartClearance Mobil Kokpit (TMA & PWA)</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Mobil sunucunuz bilgisayarınızda şu adreste aktiftir:\n"
                    "🌐 <code>http://localhost:8888</code>\n\n"
                    "💡 <b>Telefonunuzdan ve Telegram içinden açmak için:</b>\n"
                    "1. Bilgisayarınızda <code>SMARTCLEARANCE_MOBIL_BASLAT.bat</code> dosyasını çalıştırın.\n"
                    "2. Dış dünya erişim adresinizi (örn. Cloudflare tüneli) <code>/mobilurl https://adresiniz</code> komutu ile bota tanıtın.\n"
                    "3. Ardından tek dokunuşla tam ekran Telegram Mini App olarak açılacaktır!"
                )
                self.send_message(chat_id, msg, reply_markup=self.get_main_keyboard())
            return

        if cmd.startswith("/mobilurl "):
            new_url = raw_text.split(None, 1)[1].strip()
            self.config["mobile_web_app_url"] = new_url
            save_telegram_config(self.config)
            self.send_message(chat_id, f"✅ <b>Mobil WebApp Adresi Güncellendi:</b>\n<code>{new_url}</code>\n\nArtık '📱 Mobil Kokpit' butonuna basıldığında bu adres Telegram Mini App olarak açılacaktır!", reply_markup=self.get_main_keyboard())
            return

        # KANTAR TİKESİ SORGULAMA (/kantar <konteyner> veya /tike <konteyner>)
        if cmd.startswith("/kantar ") or cmd == "/kantar" or cmd.startswith("/tike ") or cmd == "/tike":
            q_term = re.sub(r"^/(kantar|tike)", "", raw_text, flags=re.I).strip()
            if not q_term:
                self.send_message(chat_id, "💡 Lütfen kantar tikesini sorgulamak istediğiniz konteyner numarasını yazın.\n<i>Örn: <code>/kantar HAMU4241680</code> veya <code>/kantar BEAU5869801</code></i>")
                return
            self._send_kantar_live_inquiry(chat_id, q_term)
            return

        # KANTAR HAVUZU
        if cmd in ("/kantartakip", "⚖️ kantar takip", "⚖️ kantar takip havuzu", "/kantarlar"):
            if self.kantar_tracker_provider:
                kt = self.kantar_tracker_provider()
                tracked = kt.list_tracked() if kt else []
                msg = f"⚖️ <b>DP WORLD KANTAR TAKİP LİSTESİ ({len(tracked)} Konteyner)</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                for item in tracked[:15]:
                    c_no = item.get("konteyner_no")
                    durum = item.get("durum")
                    t_no = item.get("tartim_no") or "—"
                    msg += f"• <code>{c_no}</code>: {durum} (Tartım: {t_no})\n"
                if len(tracked) > 15:
                    msg += f"<i>...ve {len(tracked)-15} konteyner daha.</i>"
                self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "Kantar takip servisi aktif değil.")
            return

        # 2. GTB CANLI SORGULAMA (/gtb <key>)
        if cmd.startswith("/gtb ") or cmd == "/gtb":
            q_term = raw_text[4:].strip()
            if not q_term:
                self.send_message(chat_id, "💡 Lütfen sorgulamak istediğiniz beyanname no, dosya no veya referansı yazın.\n<i>Örn: <code>/gtb 4200788048</code> veya <code>/gtb 26410300IM00046507</code></i>")
                return
            self._send_gtb_live_inquiry(chat_id, q_term)
            return

        # 3. GTB TAKİP HAVUZU LİSTESİ (/gtbtakip)
        if cmd in ("/gtbtakip", "🏛️ gtb takip havuzu", "/gtbliste"):
            self._send_gtb_tracking_summary(chat_id)
            return

        # 4. GTB TAKİBE EKLE (/gtbekle <key>)
        if cmd.startswith("/gtbekle"):
            q_term = raw_text[8:].strip()
            if not q_term:
                self.send_message(chat_id, "💡 Lütfen takibe eklemek istediğiniz beyanname, referans veya dosya noyu belirtin.\n<i>Örn: <code>/gtbekle 4200788048</code></i>")
                return
            self._handle_gtb_add_command(chat_id, q_term)
            return

        # 5. GENEL DURUM & ÖZET
        if cmd in ("/durum", "/bugun", "📊 genel durum", "📈 günlük özet", "/ozet"):
            self._send_status_summary(chat_id)
            return

        # 6. KIRMIZI HAT DOSYALARI
        if cmd in ("/kirmizi", "🔴 kırmızı hat", "/muayene"):
            self._send_kirmizi_list(chat_id)
            return

        # 7. TESCİLDEKİ DOSYALAR
        if cmd in ("/tescil", "🔵 tescildekiler", "/tescilde"):
            self._send_tescil_list(chat_id)
            return

        # 8. HANKOOK DOSYALARI
        if cmd in ("/hankook", "🏢 hankook dosyaları"):
            self._send_company_list(chat_id, "HANKOOK")
            return

        # 9. SON MAİLLER
        if cmd in ("/sonmailler", "✉️ son mailler", "/mailler"):
            self._send_recent_mails(chat_id)
            return

        # 10. EVRAK / PDF İNDİRME KOMUTLARI
        if cmd.startswith("/evrak") or cmd.startswith("/pdf") or cmd.startswith("/fatura") or cmd.startswith("/beyanname"):
            key_term = re.sub(r"^/(evrak|pdf|fatura|beyanname)", "", raw_text, flags=re.I).strip()
            if not key_term:
                self.send_message(chat_id, "💡 Lütfen evraklarını indirmek istediğiniz referans veya dosya numarasını girin.\n<i>Örn: <code>/evrak 4200788048</code></i>")
                return
            self._send_file_documents(chat_id, key_term)
            return

        # 11. ÖZEL MAİL ZİNCİRİ SORGUSU
        if cmd.startswith("/mail ") or cmd.startswith("/mail"):
            mail_q = raw_text.replace("/mail", "").strip()
            if not mail_q:
                self.send_message(chat_id, "💡 Lütfen sorgulamak istediğiniz referans veya dosya numarasını belirtin.\n<i>Örn: <code>/mail 4200788048</code></i>")
                return
            self._send_conversation_flow(chat_id, mail_q)
            return

        # 12. ÇOKLU VEYA TEKLİ SERBEST ARAMA (DOSYA, REF, BL, BEYANNAME)
        self._handle_batch_search_query(chat_id, raw_text)

    def _get_all_records(self):
        """Excel ve Evrim kayıtlarını harmanlayıp 16 haneli Beyanname No ve Liman bilgileriyle zenginleştirir."""
        records = []
        evrim_map = {}

        if self.evrim_data_provider:
            try:
                evrim_list = self.evrim_data_provider()
                for ev in evrim_list:
                    d_clean = re.sub(r"[^A-Z0-9]", "", str(ev.get("dosya_no") or "").upper())
                    r_clean = re.sub(r"[^A-Z0-9]", "", str(ev.get("hankook_ref") or ev.get("musteri_referans") or "").upper())
                    b_clean = re.sub(r"[^A-Z0-9]", "", str(ev.get("beyanname_no") or "").upper())

                    if d_clean: evrim_map[d_clean] = ev
                    if r_clean: evrim_map[r_clean] = ev
                    if b_clean: evrim_map[b_clean] = ev
            except Exception:
                pass

        if self.data_engine and hasattr(self.data_engine, "records"):
            for r in self.data_engine.records:
                rec_copy = dict(r)
                d_c = re.sub(r"[^A-Z0-9]", "", str(rec_copy.get("dosya") or "").upper())
                r_c = re.sub(r"[^A-Z0-9]", "", str(rec_copy.get("ref") or "").upper())

                ev_match = None
                if d_c and d_c in evrim_map:
                    ev_match = evrim_map[d_c]
                elif r_c and r_c in evrim_map:
                    ev_match = evrim_map[r_c]
                else:
                    for k_ev, ev_obj in evrim_map.items():
                        if (d_c and len(d_c) >= 6 and (d_c in k_ev or k_ev in d_c)) or (r_c and len(r_c) >= 6 and (r_c in k_ev or k_ev in r_c)):
                            ev_match = ev_obj
                            break

                if ev_match:
                    if not rec_copy.get("beyan") or rec_copy.get("beyan") == "—":
                        rec_copy["beyan"] = ev_match.get("beyanname_no") or ""
                    if not rec_copy.get("liman") or rec_copy.get("liman") in ("—", "", "Belirtilmemiş"):
                        rec_copy["liman"] = ev_match.get("liman") or ""
                    if not rec_copy.get("gumruk") or rec_copy.get("gumruk") == "—":
                        rec_copy["gumruk"] = ev_match.get("gumruk") or ""
                    if ev_match.get("statu"):
                        rec_copy["evrim_statu"] = f"{ev_match.get('statu')} ({ev_match.get('ilerleme', '')})"
                        if ev_match.get("asama"):
                            rec_copy["evrim_statu"] += f" - {ev_match.get('asama')}"
                    if ev_match.get("teslim_tarihi"):
                        rec_copy["teslim_tarihi"] = ev_match.get("teslim_tarihi")

                records.append(rec_copy)

        if self.evrim_data_provider:
            try:
                for ev in self.evrim_data_provider():
                    dosya = ev.get("dosya_no") or ""
                    ref = ev.get("hankook_ref") or ev.get("musteri_referans") or ""
                    beyan = ev.get("beyanname_no") or ""

                    d_clean = re.sub(r"[^A-Z0-9]", "", dosya.upper())
                    r_clean = re.sub(r"[^A-Z0-9]", "", ref.upper())

                    already_exists = any(
                        (d_clean and d_clean == re.sub(r"[^A-Z0-9]", "", str(r.get("dosya") or "").upper())) or
                        (r_clean and len(r_clean) >= 6 and r_clean in re.sub(r"[^A-Z0-9]", "", str(r.get("ref") or "").upper()))
                        for r in records
                    )

                    if not already_exists:
                        st_txt = f"{ev.get('statu', 'Evrim')} ({ev.get('ilerleme', '')})"
                        if ev.get("asama"):
                            st_txt += f" - {ev.get('asama')}"

                        records.append({
                            "dosya": dosya,
                            "ref": ref,
                            "bl": ev.get("konsimento_no") or "",
                            "beyan": beyan,
                            "bayi": ev.get("yurt_disi_firma") or ev.get("firma_adi") or "WH-HANKOOK",
                            "gumruk": ev.get("gumruk") or "—",
                            "liman": ev.get("liman") or "—",
                            "stage_title": st_txt,
                            "stage": "EVRIM",
                            "hat": "KIRMIZI" if "KIRMIZI" in str(ev).upper() else ("SARI" if "SARI" in str(ev).upper() else "—"),
                            "tescil": ev.get("beyanname_tarihi") or "—",
                            "ordino": "—",
                            "tareks": "—",
                            "mail_status": "—",
                            "mail_date": "—",
                            "evrim_statu": st_txt,
                            "aciklama": ev.get("not") or ev.get("dosya_durumu_aciklama") or ""
                        })
            except Exception:
                pass

        return records

    def _find_matching_records(self, token, all_recs):
        q = token.strip().upper()
        clean_q = re.sub(r"[^A-Z0-9]", "", q)
        if not clean_q:
            return []

        exact_matches = []
        partial_matches = []

        for r in all_recs:
            dosya_c = re.sub(r"[^A-Z0-9]", "", str(r.get("dosya") or "").upper())
            ref_c = re.sub(r"[^A-Z0-9]", "", str(r.get("ref") or "").upper())
            bl_c = re.sub(r"[^A-Z0-9]", "", str(r.get("bl") or "").upper())
            beyan_c = re.sub(r"[^A-Z0-9]", "", str(r.get("beyan") or "").upper())
            bayi_c = str(r.get("bayi") or "").upper()

            if (dosya_c and clean_q == dosya_c) or (ref_c and clean_q == ref_c) or (bl_c and clean_q == bl_c) or (beyan_c and clean_q == beyan_c):
                exact_matches.append(r)
                continue

            is_match = False
            if dosya_c and (clean_q in dosya_c or (len(clean_q) >= 6 and dosya_c in clean_q)):
                is_match = True
            elif ref_c and (clean_q in ref_c or (len(clean_q) >= 6 and ref_c in clean_q)):
                is_match = True
            elif bl_c and (clean_q in bl_c or (len(clean_q) >= 6 and bl_c in clean_q)):
                is_match = True
            elif beyan_c and (clean_q in beyan_c or (len(clean_q) >= 6 and beyan_c in clean_q)):
                is_match = True
            elif len(q) >= 4 and q in bayi_c:
                is_match = True

            if is_match:
                partial_matches.append(r)

        return exact_matches if exact_matches else partial_matches


    def _send_kantar_live_inquiry(self, chat_id, target_key):
        """Körfez veya Yarımca kantarından canlı tike sorgular ve PDF'i gönderir."""
        cntr = re.sub(r"[^A-Z0-9]", "", str(target_key or "").upper())
        if not cntr:
            self.send_message(chat_id, "❌ Lütfen geçerli bir Konteyner numarası belirtin. (Örn: <code>/kantar ONEU5983515</code>)")
            return

        self.send_message(chat_id, f"🔍 <b>[DP WORLD KANTAR SORGUSU]</b>\n<code>{cntr}</code> konteyneri için Körfez & Yarımca kantar portallarına bağlanılıyor...")

        def _worker():
            if kantar_otomatik_sorgula:
                res = kantar_otomatik_sorgula(cntr)
            else:
                res = {"success": False, "error": "Kantar sorgu modülü yüklenemedi."}

            if not res.get("success"):
                self.send_message(chat_id, f"❌ <b>Kantar Sorgu Hatası:</b>\n{res.get('error', 'Sonuç alınamadı.')}")
                return

            hazir = res.get("hazir", False)
            kaynak = res.get("kaynak", "Liman")
            tartim_no = res.get("tartim_no", "—")
            tarih = res.get("tarih", "—")
            plaka = res.get("plaka", "—")
            firma = res.get("firma", "—")
            dba = res.get("dba", "—")
            agirlik = res.get("agirlik", "—")
            pdf_url = res.get("pdf_url")

            durum_icon = "🟢" if hazir else "⏳"
            durum_baslik = "TARTIM BELGESİ HAZIR!" if hazir else "TARTIM BEKLENİYOR"

            msg = (
                f"⚖️ {durum_icon} <b>[DP WORLD {kaynak.upper()} KANTAR TİKESİ]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 <b>Konteyner:</b> <code>{cntr}</code>\n"
                f"📊 <b>Durum:</b> {durum_baslik}\n"
                f"🧾 <b>Tartım No:</b> <code>{tartim_no}</code>\n"
                f"📅 <b>Tartım Tarihi:</b> {tarih}\n"
                f"🚛 <b>Çekici Plaka:</b> <code>{plaka}</code>\n"
                f"🏢 <b>Firma:</b> {firma}\n"
            )
            if dba: msg += f"⚖️ <b>DBA (VGM):</b> {dba}\n"
            if agirlik: msg += f"⚖️ <b>Brüt Ağırlık:</b> {agirlik}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"

            if hazir and pdf_url:
                msg += f"<i>📥 Kantar tikesi PDF belgesi indiriliyor ve sohbete yükleniyor...</i>"
                self.send_message(chat_id, msg)

                # PDF indir ve yolla
                config_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "Kantar_Tickets")
                os.makedirs(config_dir, exist_ok=True)
                pdf_dest = os.path.join(config_dir, f"Kantar_{cntr}_{tartim_no or 'tike'}.pdf")
                if kantar_pdf_indir and kantar_pdf_indir(pdf_url, pdf_dest):
                    self.send_document(chat_id, pdf_dest, caption=f"📄 Kantar Tikesi — Konteyner: {cntr} (Tartım: {tartim_no})")
            else:
                msg += f"<i>Konteyner henüz kantar tartımına girmemiştir veya tike oluşturulmamıştır.</i>"
                self.send_message(chat_id, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _send_gtb_live_inquiry(self, chat_id, target_key):
        """GTB Bakanlık sunucusuna anında canlı bağlanıp captcha'yı çözerek sonucu döker."""
        try:
            from tools.gtb_engine.gtb_sorgu import gtb_beyanname_sorgula
        except ImportError:
            self.send_message(chat_id, "⚠️ GTB Otonom Sorgu Motoru yüklenemedi.")
            return

        q_clean = target_key.strip().upper()
        all_recs = self._get_all_records()
        matches = self._find_matching_records(q_clean, all_recs)

        beyan_target = q_clean
        dosya_name = "—"
        ref_name = "—"
        bayi_name = "WH-HANKOOK"

        if matches:
            r = matches[0]
            if r.get("beyan") and len(str(r.get("beyan"))) >= 10:
                beyan_target = str(r.get("beyan")).strip()
            dosya_name = r.get("dosya") or "—"
            ref_name = r.get("ref") or "—"
            bayi_name = r.get("bayi") or bayi_name

        clean_beyan = re.sub(r"[^A-Z0-9]", "", beyan_target)
        if len(clean_beyan) < 10:
            self.send_message(
                chat_id,
                f"❌ <b>'{target_key}'</b> için geçerli bir 16 haneli Beyanname Numarası bulunamadı.\n\n"
                f"💡 Lütfen tam beyanname numarasını (örn: <code>26410300IM00046507</code>) veya tescil edilmiş bir referansı giriniz."
            )
            return

        self.send_message(chat_id, f"🏛️ <i>'{clean_beyan}' için Ticaret Bakanlığı GTB sunucusuna bağlanılıyor, güvenlik kodu çözülüyor...</i>")

        # Sorguyu çalıştır
        res = gtb_beyanname_sorgula(clean_beyan)

        if res.get("success"):
            durum_txt = res.get("durum") or "Bilgi alınamadı"
            is_kapandi = res.get("kapandi", False)
            t_stamp = res.get("timestamp") or datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

            badge = "🟢 BEYANNAME KAPANDI / TAMAMLANDI" if is_kapandi else "🟡 BEYANNAME İŞLEMDE"
            
            # GTB Tracker servisinde de güncelle
            if self.gtb_tracker_provider:
                try:
                    tracker = self.gtb_tracker_provider()
                    tracker.add_to_tracking(clean_beyan, dosya_no=dosya_name, firma=bayi_name, ref=ref_name)
                    tracker.query_single_now(clean_beyan)
                except Exception:
                    pass

            card = (
                f"🏛️ <b>TİCARET BAKANLIĞI (GTB) CANLI SONUÇ</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📑 <b>Beyanname No:</b> <code>{clean_beyan}</code>\n"
                f"📦 <b>Dosya / Ref:</b> {dosya_name} | <code>{ref_name}</code>\n"
                f"🏢 <b>Firma:</b> {bayi_name}\n\n"
                f"🚦 <b>Bakanlık Durumu:</b> {badge}\n"
                f"📝 <b>Resmi Açıklama:</b>\n<i>\"{durum_txt}\"</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕒 <i>Sorgulama Zamanı: {t_stamp}</i>"
            )
            self.send_message(chat_id, card, reply_markup=self.get_main_keyboard())
        else:
            err = res.get("error") or "Bilinmeyen hata"
            self.send_message(
                chat_id,
                f"⚠️ <b>GTB Bakanlık Sorgu Hatası:</b>\n{err}\n\n"
                f"💡 Lütfen birkaç saniye sonra tekrar deneyiniz.",
                reply_markup=self.get_main_keyboard()
            )

    def _send_gtb_tracking_summary(self, chat_id):
        """GTB Tracker servisinde izlenen beyannameleri listeler."""
        if not self.gtb_tracker_provider:
            self.send_message(chat_id, "⚠️ GTB Takip Servisine erişilemedi.")
            return

        tracker = self.gtb_tracker_provider()
        tracked = tracker.list_tracked(only_active=True)

        if not tracked:
            self.send_message(chat_id, "ℹ️ Şu anda GTB otonom takip havuzunda aktif beyanname bulunmuyor.\n\n💡 Eklemek için: <code>/gtbekle &lt;beyanname veya ref&gt;</code> yazabilirsiniz.")
            return

        kapananlar = [r for r in tracked if r.get("kapandi")]
        islemdekiler = [r for r in tracked if not r.get("kapandi")]

        lines = [
            f"🏛️ <b>GTB OTONOM BEYANNAME TAKİP HAVUZU</b>\n"
            f"<b>Toplam İzlenen:</b> {len(tracked)} Adet (🟢 {len(kapananlar)} Kapandı / 🟡 {len(islemdekiler)} İşlemde)\n"
            f"<b>Son Otonom Tarama:</b> {tracker.last_scan_time}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        ]

        for idx, r in enumerate(tracked[:10], 1):
            b_no = r.get("beyanname_no")
            dosya = r.get("dosya_no") or "—"
            ref = r.get("ref") or "—"
            durum = r.get("durum") or "Bekliyor"
            icon = "🟢" if r.get("kapandi") else "🟡"
            
            lines.append(
                f"\n{idx}. {icon} <b>{b_no}</b> ({dosya})\n"
                f"   📍 Ref: <code>{ref}</code>\n"
                f"   📊 <i>{durum[:50]}...</i>"
            )

        if len(tracked) > 10:
            lines.append(f"\n<i>...ve {len(tracked)-10} beyanname daha izleniyor.</i>")

        lines.append("\n💡 <i>Anlık tekil sorgu için: <code>/gtb &lt;beyanname&gt;</code></i>")
        self.send_message(chat_id, "\n".join(lines), reply_markup=self.get_main_keyboard())

    def _handle_gtb_add_command(self, chat_id, target_key):
        """Kullanıcının girdiği beyanname veya referansı GTB takip havuzuna kaydeder."""
        if not self.gtb_tracker_provider:
            self.send_message(chat_id, "⚠️ GTB Takip Servisi hazır değil.")
            return

        all_recs = self._get_all_records()
        matches = self._find_matching_records(target_key, all_recs)

        beyan_target = target_key
        dosya_name = "—"
        ref_name = "—"
        bayi_name = "WH-HANKOOK"

        if matches:
            r = matches[0]
            if r.get("beyan") and len(str(r.get("beyan"))) >= 10:
                beyan_target = str(r.get("beyan")).strip()
            dosya_name = r.get("dosya") or "—"
            ref_name = r.get("ref") or "—"
            bayi_name = r.get("bayi") or bayi_name

        clean_beyan = re.sub(r"[^A-Z0-9]", "", beyan_target)
        if len(clean_beyan) < 10:
            self.send_message(chat_id, f"❌ <b>'{target_key}'</b> için geçerli bir beyanname numarası bulunamadı.")
            return

        tracker = self.gtb_tracker_provider()
        res = tracker.add_to_tracking(clean_beyan, dosya_no=dosya_name, firma=bayi_name, ref=ref_name)

        if res.get("success"):
            self.send_message(
                chat_id,
                f"✅ <b>GTB OTONOM TAKİBE EKLENDİ!</b>\n\n"
                f"📑 <b>Beyanname No:</b> <code>{clean_beyan}</code>\n"
                f"📦 <b>Dosya / Ref:</b> {dosya_name} | <code>{ref_name}</code>\n"
                f"🏢 <b>Firma:</b> {bayi_name}\n\n"
                f"🤖 <i>Sistem 10 dakikada bir durumu kontrol edecek, kapandığı veya değiştiği an telefonunuza alarm gönderecektir.</i>",
                reply_markup=self.get_main_keyboard()
            )
        else:
            self.send_message(chat_id, f"⚠️ Ekleme hatası: {res.get('error')}")

    def _fast_search_outlook_direct(self, search_keys, max_results=3):
        """Outlook MAPI üzerinden SQL Restrict kullanarak milisaniyeler içinde kesin eşleşen mailleri ve zincirleri bulur."""
        if not win32com or not pythoncom:
            return []

        results = []
        seen_convs = set()

        try:
            pythoncom.CoInitialize()
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")

            for key in search_keys:
                clean_k = re.sub(r"[^A-Z0-9]", "", str(key).upper())
                if not clean_k or len(clean_k) < 4:
                    continue

                filter_sql = f"@SQL=\"urn:schemas:httpmail:subject\" LIKE '%{clean_k}%'"

                for folder_id, direction in [(6, "IN"), (5, "OUT")]:
                    try:
                        folder = namespace.GetDefaultFolder(folder_id)
                        matched_items = folder.Items.Restrict(filter_sql)
                        time_field = "[ReceivedTime]" if folder_id == 6 else "[SentOn]"
                        matched_items.Sort(time_field, True)

                        for item in matched_items:
                            if len(results) >= max_results:
                                break
                            try:
                                subj = str(item.Subject or "")
                                topic = str(getattr(item, "ConversationTopic", "") or subj)
                                conv_key = topic.strip().upper()

                                if conv_key in seen_convs:
                                    continue
                                seen_convs.add(conv_key)

                                conv = item.GetConversation()
                                messages = []

                                if conv:
                                    tbl = conv.GetTable()
                                    while not tbl.EndOfTable:
                                        r_row = tbl.GetNextRow()
                                        e_id = r_row("EntryID")
                                        try:
                                            m = namespace.GetItemFromID(e_id)
                                            m_sender = str(getattr(m, "SenderName", "") or "")
                                            m_to = str(getattr(m, "To", "") or "")
                                            m_subj = str(m.Subject or "")
                                            m_body = str(getattr(m, "Body", "") or "").strip()
                                            snippet = " ".join([l.strip() for l in m_body.split("\n") if l.strip() and not l.strip().startswith(">") and not l.strip().startswith("From:")][:2])[:120]

                                            m_t = getattr(m, "SentOn", None) or getattr(m, "ReceivedTime", None)
                                            try: t_str = m_t.strftime("%d.%m.%Y %H:%M")
                                            except Exception: t_str = str(m_t)[:16]

                                            m_atts = [a.FileName for a in m.Attachments if not re.match(r"^image\d+\.", a.FileName, re.I)]
                                            is_out = "OZAN" in m_sender.upper() or "DOGRUER" in m_sender.upper()

                                            messages.append({
                                                "direction": "OUT" if is_out else "IN",
                                                "sender": m_sender if not is_out else "Ben (Ozan Gemici)",
                                                "to": m_to,
                                                "time": t_str,
                                                "time_raw": m_t,
                                                "subject": m_subj,
                                                "snippet": snippet,
                                                "attachments": len(m_atts)
                                            })
                                        except Exception:
                                            pass
                                else:
                                    m_t = getattr(item, "SentOn", None) or getattr(item, "ReceivedTime", None)
                                    try: t_str = m_t.strftime("%d.%m.%Y %H:%M")
                                    except Exception: t_str = str(m_t)[:16]
                                    sender = str(getattr(item, "SenderName", "") or "")
                                    is_out = direction == "OUT"
                                    messages.append({
                                        "direction": direction,
                                        "sender": sender if not is_out else "Ben (Ozan Gemici)",
                                        "to": str(getattr(item, "To", "") or ""),
                                        "time": t_str,
                                        "time_raw": m_t,
                                        "subject": subj,
                                        "snippet": str(getattr(item, "Body", "") or "")[:120],
                                        "attachments": len(item.Attachments)
                                    })

                                messages.sort(key=lambda x: str(x.get("time_raw") or ""))
                                for s_idx, m in enumerate(messages, 1):
                                    m["step"] = s_idx

                                results.append({
                                    "topic": topic,
                                    "msg_count": len(messages),
                                    "latest_time": messages[-1]["time"] if messages else "—",
                                    "last_sender": messages[-1]["sender"] if messages else "—",
                                    "messages": messages
                                })
                            except Exception:
                                continue
                    except Exception:
                        pass
        except Exception as e:
            print("Outlook Search Error:", e)
        finally:
            try: pythoncom.CoUninitialize()
            except Exception: pass

        return results

    def _find_all_pdfs_for_keys(self, search_keys):
        """Diskteki arşiv klasörlerini ve gerekirse Outlook eklerini tarayarak ilgili tüm PDF dosyalarını toplar."""
        found_pdfs = []
        clean_keys = [re.sub(r"[^A-Z0-9]", "", str(k).upper()) for k in search_keys if k and len(str(k)) >= 4]

        custom_pdf_dir = os.path.join(os.path.expanduser("~"), "OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş", "Masaüstü", "kapanan")

        search_dirs = [
            custom_pdf_dir,
            os.path.join(custom_pdf_dir, "mailatıldı"),
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Documents")
        ]

        max_files = 400
        max_depth = 3
        max_age_days = 120
        cutoff = time.time() - (max_age_days * 86400)

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            try:
                base_depth = s_dir.rstrip(os.sep).count(os.sep)
                for root, dirs, files in os.walk(s_dir):
                    depth = root.rstrip(os.sep).count(os.sep) - base_depth
                    if depth > max_depth:
                        dirs[:] = []
                        continue
                    for f in files:
                        if len(found_pdfs) >= max_files:
                            return found_pdfs
                        if not f.lower().endswith(".pdf"):
                            continue
                        full_p = os.path.join(root, f)
                        try:
                            if os.path.getmtime(full_p) < cutoff:
                                continue
                        except OSError:
                            continue
                        f_clean = re.sub(r"[^A-Z0-9]", "", f.upper())
                        for ck in clean_keys:
                            if ck in f_clean:
                                if full_p not in found_pdfs:
                                    found_pdfs.append(full_p)
                                break
            except Exception:
                pass

        if not found_pdfs and win32com and pythoncom:
            try:
                pythoncom.CoInitialize()
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")

                for ck in clean_keys:
                    filter_sql = f"@SQL=\"urn:schemas:httpmail:subject\" LIKE '%{ck}%'"
                    for folder_id in [6, 5]:
                        try:
                            folder = namespace.GetDefaultFolder(folder_id)
                            items = folder.Items.Restrict(filter_sql)
                            for item in items:
                                for att in item.Attachments:
                                    if att.FileName.lower().endswith(".pdf") and not re.match(r"^image\d+\.", att.FileName, re.I):
                                        save_path = os.path.join(TEMP_VAULT_DIR, f"{ck}_{att.FileName}")
                                        att.SaveAsFile(save_path)
                                        if save_path not in found_pdfs:
                                            found_pdfs.append(save_path)
                                if len(found_pdfs) >= 3:
                                    break
                        except Exception:
                            pass
            except Exception:
                pass
            finally:
                try: pythoncom.CoUninitialize()
                except Exception: pass

        return found_pdfs

    def _send_file_documents(self, chat_id, target_key):
        """İlgili dosyanın PDF evraklarını bulup Telegram sohbetine yükler."""
        q_clean = target_key.strip().upper()
        all_recs = self._get_all_records()
        matches = self._find_matching_records(q_clean, all_recs)

        search_keys = [q_clean]
        bayi_name = "WH-HANKOOK"
        dosya_name = target_key

        if matches:
            r = matches[0]
            dosya_name = r.get("dosya") or target_key
            bayi_name = r.get("bayi") or bayi_name
            for k in [r.get("ref"), r.get("bl"), r.get("dosya"), r.get("beyan")]:
                if k and k not in search_keys and k != "—":
                    search_keys.append(str(k))

        self.send_message(chat_id, f"🔍 <i>'{dosya_name}' için arşiv ve mail kasasından PDF evraklar taranıyor...</i>")
        pdfs = self._find_all_pdfs_for_keys(search_keys)

        if not pdfs:
            self.send_message(
                chat_id,
                f"⚠️ <b>'{dosya_name}' için indirilebilir PDF evrak bulunamadı.</b>\n\n"
                f"💡 Evraklar İndirilenler klasörüne veya mail arşivine düştüğünde anında çekilebilir.",
                reply_markup=self.get_main_keyboard()
            )
            return

        self.send_message(chat_id, f"📥 <b>{len(pdfs)} Adet PDF Evrak Bulundu, Telefonunuza Gönderiliyor:</b>")

        for idx, pdf_path in enumerate(pdfs[:4], 1):
            fname = os.path.basename(pdf_path)
            fsize_kb = os.path.getsize(pdf_path) // 1024
            caption = (
                f"📄 <b>Evrak #{idx}: {fname}</b>\n"
                f"📦 <b>Dosya:</b> {dosya_name} | 🏢 {bayi_name}\n"
                f"💾 <b>Boyut:</b> {fsize_kb} KB"
            )
            self.send_document(chat_id, pdf_path, caption=caption)
            time.sleep(0.5)

    def _build_rich_detail_card(self, r):
        """Operasyon Kokpiti, Evrim ve Mail zenginliğini içeren eksiksiz kart ve Hızlı Eylem Butonları oluşturur."""
        dosya = r.get("dosya") or "—"
        ref = r.get("ref") or "—"
        bl = r.get("bl") or "—"
        beyan = r.get("beyan") or "—"
        bayi = r.get("bayi") or "—"
        gumruk = r.get("gumruk") or "—"
        liman = r.get("liman") or "—"
        stage_title = r.get("stage_title") or r.get("stage") or "İşlemde"
        tescil_dt = r.get("tescil") or "Bekliyor / —"
        ordino_dt = r.get("ordino") or "—"
        tareks_dt = r.get("tareks") or "—"
        mail_st = r.get("mail_status") or "—"
        mail_dt = r.get("mail_date") or "—"
        evrim_statu = r.get("evrim_statu") or ""
        aciklama = r.get("aciklama") or ""

        # Hat İkonu
        hat_raw = str(r.get("hat") or "").upper()
        if "KIRMIZI" in hat_raw or "KIRMIZI" in stage_title.upper():
            hat_str = "🔴 KIRMIZI HAT (Fiziki Muayenede)"
        elif "SARI" in hat_raw or "SARI" in stage_title.upper():
            hat_str = "🟡 SARI HAT (Belge Kontrolü)"
        elif "YESIL" in hat_raw or "YEŞİL" in stage_title.upper():
            hat_str = "🟢 YEŞİL HAT (Hızlı Geçiş)"
        else:
            hat_str = "⚪ Hat Belirlenmedi"

        # Vergi Maili Durumu
        if "GÖNDERİLDİ" in mail_st.upper() or "ATILDI" in mail_st.upper() or r.get("mail_badge") == "green":
            mail_badge = f"✅ Gönderildi ({mail_dt})"
        elif "GÖNDERİLMEDİ" in mail_st.upper() or r.get("mail_badge") == "red":
            mail_badge = "🔴 BEKLİYOR (Acil Gönderilmeli!)"
        else:
            mail_badge = f"⚠️ {mail_st} ({mail_dt})" if mail_dt else f"⚠️ {mail_st}"

        # Ordino & Tareks Durumu
        ordino_str = f"✅ {ordino_dt}" if (ordino_dt and ordino_dt != "—") else "⏳ Bekliyor"
        tareks_str = f"✅ {tareks_dt}" if (tareks_dt and tareks_dt != "—") else "⏳ Bekliyor / Muaf"

        # Outlook İlgili Mail Bilgisini Çapraz Ara
        search_keys = [k for k in [ref, bl, dosya] if k and k != "—"]
        conv_list = self._fast_search_outlook_direct(search_keys, max_results=1)
        mail_section = ""

        action_target = ref if (ref and ref != "—") else dosya

        if conv_list:
            conv_info = conv_list[0]
            topic = conv_info.get("topic") or "Gümrük Yazışması"
            sender = conv_info.get("last_sender") or "Outlook"
            t_str = conv_info.get("latest_time") or "—"
            step_c = conv_info.get("msg_count", 1)
            mail_section = (
                f"\n✉️ <b>OUTLOOK MAİL HAREKETİ:</b>\n"
                f"• <b>Son Mail:</b> {t_str} | <i>{sender}</i>\n"
                f"• <b>Konu:</b> {topic[:45]}...\n"
                f"• <b>Sohbet:</b> 🧵 {step_c} Aşamalı İletişim\n"
            )

        card = (
            f"📦 <b>DOSYA KÜNYESİ: {dosya}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 <b>Firma:</b> {bayi}\n"
            f"📍 <b>Referans No:</b> <code>{ref}</code>\n"
            f"📑 <b>Beyanname No:</b> <code>{beyan}</code>\n"
            f"🚢 <b>Konşimento (BL):</b> <code>{bl}</code>\n"
            f"⚓ <b>Gümrük / Liman:</b> {gumruk} / {liman}\n\n"
            f"🚦 <b>OPERASYONEL AŞAMA & STATÜ:</b>\n"
            f"• <b>Aşama:</b> {stage_title}\n"
            f"• <b>Hat Rengi:</b> {hat_str}\n"
            f"• <b>Tescil Tarihi:</b> {tescil_dt}\n"
            f"• <b>Ordino / Tareks:</b> {ordino_str} | {tareks_str}\n"
            f"• <b>Vergi Maili:</b> {mail_badge}\n"
        )

        if evrim_statu:
            card += f"• <b>Evrim Statüsü:</b> <i>{evrim_statu}</i>\n"

        card += mail_section

        if aciklama:
            card += f"\n📝 <b>Açıklama / Not:</b> <i>{aciklama}</i>\n"

        # İNTERAKTİF EYLEM BUTONLARI (PDF İndir + GTB Canlı Sorgula + Mail Akışı)
        gtb_key = beyan if (beyan and beyan != "—") else action_target
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏛️ GTB Canlı Sorgula", "callback_data": f"gtb:{gtb_key}"},
                    {"text": "📥 PDF İndir", "callback_data": f"doc:{action_target}"}
                ],
                [
                    {"text": "✉️ Mail Akışını Göster", "callback_data": f"mail:{action_target}"}
                ]
            ]
        }

        return card, inline_keyboard

    def _handle_batch_search_query(self, chat_id, raw_text):
        """Birden fazla referansı (alt alta veya virgülle girilenleri) ayrıştırıp tek tek döker."""
        tokens = [t.strip() for t in re.split(r"[\n,;]+|\s{2,}", raw_text) if t.strip()]

        if not tokens:
            return

        all_recs = self._get_all_records()

        # Tekli arama
        if len(tokens) == 1:
            tok = tokens[0]
            matches = self._find_matching_records(tok, all_recs)
            if not matches:
                self.send_message(
                    chat_id,
                    f"❌ <b>'{tok}'</b> ile eşleşen dosya, referans veya konşimento bulunamadı.\n\n"
                    f"💡 Lütfen dosya no (örn: <code>26-085915</code>) veya referans no (örn: <code>4200788048</code>) giriniz.",
                    reply_markup=self.get_main_keyboard()
                )
                return

            for r in matches[:3]:
                card, inline_kb = self._build_rich_detail_card(r)
                self.send_message(chat_id, card, reply_markup=inline_kb)

            if len(matches) > 3:
                self.send_message(chat_id, f"<i>...toplam {len(matches)} eşleşme bulundu.</i>")
            return

        # ÇOKLU SORGULAMA (Batch Multi-Query)
        header_msg = f"🔍 <b>TOPLU DOSYA SORGULAMA ({len(tokens)} Kalem)</b>\n━━━━━━━━━━━━━━━━━━━━━━"
        self.send_message(chat_id, header_msg)

        found_count = 0
        not_found = []

        for idx, tok in enumerate(tokens[:10], 1):
            matches = self._find_matching_records(tok, all_recs)
            if matches:
                found_count += 1
                r = matches[0]
                card, inline_kb = self._build_rich_detail_card(r)
                self.send_message(chat_id, card, reply_markup=inline_kb)
                time.sleep(0.3)
            else:
                not_found.append(tok)

        if not_found:
            nf_txt = "\n• ".join(not_found)
            self.send_message(
                chat_id,
                f"⚠️ <b>Aşağıdaki {len(not_found)} kalem sistemde bulunamadı:</b>\n• {nf_txt}",
                reply_markup=self.get_main_keyboard()
            )

        if len(tokens) > 10:
            self.send_message(chat_id, f"<i>...performans için ilk 10 kalem listelendi ({len(tokens)-10} kalem atlandı).</i>")

    def _send_conversation_flow(self, chat_id, query):
        """Dosya veya referansa ait Outlook konuşma zincirini adım adım döker."""
        q_clean = query.strip().upper()
        all_recs = self._get_all_records()
        matches = self._find_matching_records(q_clean, all_recs)

        search_keys = [q_clean]
        if matches:
            r = matches[0]
            for k in [r.get("ref"), r.get("bl"), r.get("dosya")]:
                if k and k not in search_keys and k != "—":
                    search_keys.append(str(k))

        self.send_message(chat_id, f"🔍 <i>'{query}' için Outlook yazışma zincirleri taranıyor...</i>")
        convs = self._fast_search_outlook_direct(search_keys, max_results=3)

        if not convs:
            self.send_message(
                chat_id,
                f"❌ <b>'{query}'</b> ile ilgili Outlook'ta herhangi bir mail zinciri bulunamadı.\n\n"
                f"💡 Lütfen tam referans no (örn: <code>4200788048</code>) veya konşimento numarası ile tekrar deneyiniz.",
                reply_markup=self.get_main_keyboard()
            )
            return

        for conv in convs:
            topic = conv.get("topic") or "Gümrük Yazışması"
            step_c = conv.get("msg_count", 0)
            messages = conv.get("messages", [])

            lines = [
                f"🧵 <b>MAİL ZAMAN TÜNELİ & YAZIŞMA AKIŞI</b>\n"
                f"<b>Konu:</b> {topic}\n"
                f"<b>Toplam Aşama:</b> {step_c} Adım\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            ]

            for m in messages:
                step = m.get("step", 1)
                direction = "📤 BİZ" if m.get("direction") == "OUT" else "📥 KARŞI TARAF"
                sender = m.get("sender") or "—"
                to = m.get("to") or "—"
                t_str = m.get("time") or "—"
                preview = m.get("snippet") or ""
                att_c = m.get("attachments", 0)
                att_txt = f"\n   📎 <b>Ek:</b> {att_c} Dosya" if att_c > 0 else ""

                lines.append(
                    f"\n<b>Adım {step}: {direction}</b> | 📅 {t_str}\n"
                    f"   👤 <b>Kimden:</b> {sender}\n"
                    f"   📩 <b>Kime:</b> {to[:40]}\n"
                    f"   💬 <i>\"{preview[:120]}...\"</i>{att_txt}"
                )

            self.send_message(chat_id, "\n".join(lines), reply_markup=self.get_main_keyboard())
            time.sleep(0.3)

    def _send_recent_mails(self, chat_id):
        """Son gelen gümrük ve operasyon maillerini listeler."""
        if not win32com or not pythoncom:
            self.send_message(chat_id, "⚠️ Outlook modülüne erişilemedi.")
            return

        try:
            pythoncom.CoInitialize()
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            inbox = namespace.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            lines = ["✉️ <b>OUTLOOK'TAKİ EN SON GÜNCEL YAZIŞMALAR</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
            count = 0
            for item in items:
                if count >= 5:
                    break
                try:
                    subj = str(item.Subject or "Konu Yok")
                    sender = str(getattr(item, "SenderName", "Bilinmiyor") or "Bilinmiyor")
                    t_val = getattr(item, "ReceivedTime", None)
                    try: t_str = t_val.strftime("%d.%m.%Y %H:%M")
                    except Exception: t_str = str(t_val)[:16]

                    count += 1
                    lines.append(f"<b>{count}. {subj[:45]}...</b>\n   👤 <i>{sender}</i> | 📅 {t_str}\n")
                except Exception:
                    continue

            lines.append("💡 <i>Bir dosyanın tüm adımlarını görmek için: <code>/mail &lt;ref&gt;</code> yazabilirsiniz.</i>")
            self.send_message(chat_id, "\n".join(lines), reply_markup=self.get_main_keyboard())
        except Exception as e:
            self.send_message(chat_id, f"⚠️ Mail okuma hatası: {e}")
        finally:
            try: pythoncom.CoUninitialize()
            except Exception: pass

    def _send_status_summary(self, chat_id):
        recs = self._get_all_records()
        if not recs:
            self.send_message(chat_id, "⚠️ Henüz hafızada kayıtlı operasyon verisi bulunamadı.")
            return

        kirmizi = [r for r in recs if (r.get("hat") == "KIRMIZI" or "KIRMIZI" in (r.get("stage_title") or "").upper())]
        tescilde = [r for r in recs if "TESCIL" in (r.get("stage") or "").upper() or "TESCİL" in (r.get("stage_title") or "").upper()]
        ordino = [r for r in recs if "ORDINO" in (r.get("stage") or "").upper() or "TAREKS" in (r.get("stage") or "").upper()]
        kapandi = [r for r in recs if "KAPANDI" in (r.get("stage") or "").upper() or "TESLİM" in (r.get("stage_title") or "").upper()]

        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        txt = (
            f"📊 <b>GÜNCEL OPERASYON TABLOSU</b>\n"
            f"<i>📅 {now_str} İtibarıyla</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Toplam İzlenen Dosya:</b> {len(recs)} Adet\n\n"
            f"🔴 <b>Kırmızı Hat (Muayenede):</b> {len(kirmizi)} Dosya\n"
            f"🔵 <b>Tescilde / Tescil Oldu:</b> {len(tescilde)} Dosya\n"
            f"🟠 <b>Ordino / Tareks İşlemde:</b> {len(ordino)} Dosya\n"
            f"🟢 <b>Kapandı / Teslim Edildi:</b> {len(kapandi)} Dosya\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Detay görmek için <code>/kirmizi</code> veya dosya no yazabilirsiniz.</i>"
        )
        self.send_message(chat_id, txt, reply_markup=self.get_main_keyboard())

    def _send_kirmizi_list(self, chat_id):
        recs = self._get_all_records()
        kirmizi = [r for r in recs if (r.get("hat") == "KIRMIZI" or "KIRMIZI" in (r.get("stage_title") or "").upper())]

        if not kirmizi:
            self.send_message(chat_id, "✅ <b>Harika haber!</b> Şu anda Kırmızı Hatta bekleyen dosya bulunmuyor.", reply_markup=self.get_main_keyboard())
            return

        lines = [f"🚨 <b>KIRMIZI HATTAKİ DOSYALAR ({len(kirmizi)} Adet)</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for idx, r in enumerate(kirmizi[:10], 1):
            dosya = r.get("dosya") or "Dosya No Yok"
            ref = r.get("ref") or "—"
            bayi = r.get("bayi") or "—"
            liman = r.get("liman") or r.get("gumruk") or "—"
            lines.append(f"<b>{idx}. {dosya}</b> | {bayi}\n   📍 Ref: <code>{ref}</code> | Liman: {liman}\n")

        if len(kirmizi) > 10:
            lines.append(f"<i>...ve {len(kirmizi)-10} dosya daha.</i>")

        self.send_message(chat_id, "\n".join(lines), reply_markup=self.get_main_keyboard())

    def _send_tescil_list(self, chat_id):
        recs = self._get_all_records()
        tescilde = [r for r in recs if "TESCIL" in (r.get("stage") or "").upper() or "TESCİL" in (r.get("stage_title") or "").upper()]

        if not tescilde:
            self.send_message(chat_id, "ℹ️ Şu anda tescil aşamasında aktif dosya bulunamadı.", reply_markup=self.get_main_keyboard())
            return

        lines = [f"🔵 <b>TESCİL AŞAMASINDAKİ DOSYALAR ({len(tescilde)} Adet)</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for idx, r in enumerate(tescilde[:8], 1):
            dosya = r.get("dosya") or "—"
            ref = r.get("ref") or "—"
            bayi = r.get("bayi") or "—"
            lines.append(f"<b>{idx}. {dosya}</b> | {bayi}\n   📍 Ref: <code>{ref}</code> | Tescil: {r.get('tescil') or 'Bekliyor'}\n")

        if len(tescilde) > 8:
            lines.append(f"<i>...ve {len(tescilde)-8} dosya daha.</i>")

        self.send_message(chat_id, "\n".join(lines), reply_markup=self.get_main_keyboard())

    def _send_company_list(self, chat_id, company_name="HANKOOK"):
        recs = self._get_all_records()
        matching = [r for r in recs if company_name.upper() in str(r.get("bayi", "")).upper() or company_name.upper() in str(r.get("ref", "")).upper()]

        if not matching:
            self.send_message(chat_id, f"ℹ️ {company_name} için aktif dosya bulunamadı.", reply_markup=self.get_main_keyboard())
            return

        lines = [f"🏢 <b>{company_name.upper()} AKTİF DOSYALARI ({len(matching)} Adet)</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for idx, r in enumerate(matching[:8], 1):
            dosya = r.get("dosya") or "—"
            ref = r.get("ref") or "—"
            st = r.get("stage_title") or "İşlemde"
            lines.append(f"<b>{idx}. {dosya}</b> | <code>{ref}</code>\n   🚦 {st}\n")

        if len(matching) > 8:
            lines.append(f"<i>...ve {len(matching)-8} dosya daha.</i>")

        self.send_message(chat_id, "\n".join(lines), reply_markup=self.get_main_keyboard())

    def notify_critical_event(self, event_title, event_text):
        """Kritik olayları (Kırmızı Hat, Tescil Onayı, GTB Kapanışı) kayıtlı kullanıcılara push mesajı olarak atar. Teams kanalına da iletir."""
        chat_ids = self.config.get("authorized_chat_ids", [])
        if not chat_ids:
            return

        msg = f"🚨 <b>{event_title}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n{event_text}"
        for cid in chat_ids:
            try:
                self.send_message(cid, msg, reply_markup=self.get_main_keyboard())
            except Exception:
                pass

        # Teams köprüsüne de gönder
        try:
            if get_teams_bridge:
                get_teams_bridge().notify_critical(event_title, event_text)
        except Exception as te:
            print(f"[TEAMS-CRITICAL-ERR] {te}")


# Global Singleton Instance
_global_telegram_service = None

def get_telegram_service(data_engine=None, evrim_data_provider=None, gtb_tracker_provider=None):
    global _global_telegram_service
    if _global_telegram_service is None:
        _global_telegram_service = TelegramBotService(data_engine, evrim_data_provider, gtb_tracker_provider)
    else:
        if data_engine and not _global_telegram_service.data_engine:
            _global_telegram_service.data_engine = data_engine
        if evrim_data_provider and not _global_telegram_service.evrim_data_provider:
            _global_telegram_service.evrim_data_provider = evrim_data_provider
        if gtb_tracker_provider and not _global_telegram_service.gtb_tracker_provider:
            _global_telegram_service.gtb_tracker_provider = gtb_tracker_provider
    return _global_telegram_service
