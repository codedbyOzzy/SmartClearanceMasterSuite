"""
==============================================================================
📣 DOĞRUER - MICROSOFT TEAMS KÖPRÜSÜ (Teams Bridge)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI

Açıklama:
  Telegram bot bildirimlerini (broadcast_message, notify_critical_event)
  Microsoft Teams kanalına da yönlendiren köprü modülü.
  Outlook COM üzerinden e-posta gönderir → Teams kanalına mesaj düşer.
==============================================================================
"""

import os
import json
import datetime
import threading

try:
    import win32com.client
    import pythoncom
    WIN32_AVAILABLE = True
except ImportError:
    win32com = None
    pythoncom = None
    WIN32_AVAILABLE = False

# ── KONFİGÜRASYON ──────────────────────────────────────────────────────────
CONFIG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance"
)
TEAMS_CONFIG_PATH = os.path.join(CONFIG_DIR, "teams_config.json")

DEFAULT_CONFIG = {
    "enabled": True,
    # Teams kanalının e-posta adresi (OperasyonHankook kanalı)
    "teams_channel_email": "9b28ab9c.dogruer.com@emea.teams.ms",
    # Gönderen Outlook hesabı (boş bırakılırsa varsayılan hesap kullanılır)
    "sender_email": "",
    # Hangi olay türleri Teams'e gönderilsin?
    "notify_broadcast": True,
    "notify_critical": True,
    "notify_morning_briefing": True,
    "notify_evening_report": True,
    # Gönderilen mailin nereye kaydedileceği:
    #   "delete"  → Gönderilmiş Öğeler'e hiç düşmesin (kayıt olmaz)
    #   "folder"  → Outlook'ta özel bir klasöre taşı (sent_folder_name)
    #   "default" → Normal Gönderilmiş Öğeler (mevcut davranış)
    "sent_items_mode": "folder",
    "sent_folder_name": "Teams Bildirimleri"
}


def load_teams_config() -> dict:
    """Teams yapılandırmasını diskten yükler; yoksa varsayılanı döndürür."""
    if os.path.exists(TEAMS_CONFIG_PATH):
        try:
            with open(TEAMS_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Eksik anahtarları varsayılanla tamamla
                for k, v in DEFAULT_CONFIG.items():
                    cfg.setdefault(k, v)
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_teams_config(cfg: dict) -> bool:
    """Teams yapılandırmasını diske kaydeder."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TEAMS_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[TEAMS-CONFIG-SAVE-ERR] {e}")
        return False


# ── HTML FORMATLAYICI ───────────────────────────────────────────────────────
def _format_html_body(subject: str, body_text: str) -> str:
    """Mesajı Teams'te düzgün görünen HTML e-posta gövdesine çevirir."""
    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    # Telegram HTML etiketlerini temizle
    clean_text = (
        body_text
        .replace("<b>", "<strong>")
        .replace("</b>", "</strong>")
        .replace("<i>", "<em>")
        .replace("</i>", "</em>")
        .replace("\n", "<br>")
    )

    html = f"""
<html>
<body style="font-family: Segoe UI, Arial, sans-serif; font-size: 14px; color: #1a1a1a; margin: 0; padding: 0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4; padding: 20px;">
    <tr>
      <td>
        <table width="620" align="center" cellpadding="0" cellspacing="0"
               style="background:#ffffff; border-radius: 8px; overflow: hidden;
                      box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
          <!-- BAŞLIK -->
          <tr>
            <td style="background: #0078d4; padding: 18px 24px;">
              <span style="font-size:18px; font-weight:700; color:#ffffff;">
                📣 Doğruer Sistem Bildirimi
              </span>
            </td>
          </tr>
          <!-- KONU -->
          <tr>
            <td style="padding: 16px 24px 0 24px;">
              <p style="margin:0; font-size:16px; font-weight:600; color:#0078d4;">
                {subject}
              </p>
            </td>
          </tr>
          <!-- AYRAÇ -->
          <tr>
            <td style="padding: 8px 24px;">
              <hr style="border:none; border-top:1px solid #e0e0e0; margin:0;">
            </td>
          </tr>
          <!-- GÖVDE -->
          <tr>
            <td style="padding: 0 24px 16px 24px; line-height: 1.7;">
              {clean_text}
            </td>
          </tr>
          <!-- FOOTER -->
          <tr>
            <td style="background:#f9f9f9; padding: 10px 24px;
                       border-top: 1px solid #e0e0e0; color: #888;
                       font-size: 12px;">
              Doğruer Master Suite &nbsp;|&nbsp; {now_str}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html


# ── ANA KÖPRÜ SINIFI ────────────────────────────────────────────────────────
class TeamsOutlookBridge:
    """
    Outlook COM aracılığıyla Microsoft Teams kanalına bildirim gönderir.
    Telegram bot servisiyle yan yana çalışır.
    """

    def __init__(self):
        self.config = load_teams_config()
        self._lock = threading.Lock()

    def is_enabled(self) -> bool:
        return (
            self.config.get("enabled", True)
            and WIN32_AVAILABLE
            and bool(self.config.get("teams_channel_email", ""))
        )

    def reload_config(self):
        """Yapılandırmayı yeniden diskten yükler."""
        self.config = load_teams_config()

    def send_to_teams(self, subject: str, body_text: str, attachment_paths: list = None) -> bool:
        """
        Outlook üzerinden Teams kanalına e-posta gönderir.
        attachment_paths: PDF veya diğer dosyaların tam yollarının listesi (opsiyonel)
        Thread-safe, arka planda çalışır.
        """
        if not self.is_enabled():
            print("[TEAMS-BRIDGE] Devre disi veya Outlook mevcut degil, atlandi.")
            return False

        def _send():
            with self._lock:
                try:
                    pythoncom.CoInitialize()
                    outlook = win32com.client.Dispatch("Outlook.Application")
                    mail = outlook.CreateItem(0)  # 0 = olMailItem

                    mail.To = self.config["teams_channel_email"]
                    mail.Subject = subject
                    mail.HTMLBody = _format_html_body(subject, body_text)

                    # PDF / dosya ekleri
                    if attachment_paths:
                        for fpath in attachment_paths:
                            if fpath and os.path.exists(fpath):
                                mail.Attachments.Add(fpath)
                                print(f"[TEAMS-BRIDGE] Ek eklendi: {os.path.basename(fpath)}")

                    # Gönderen hesabı ayarla (opsiyonel)
                    sender = self.config.get("sender_email", "")
                    if sender:
                        for acc in outlook.Session.Accounts:
                            if acc.SmtpAddress.lower() == sender.lower():
                                mail._oleobj_.Invoke(
                                    0xF023, 0, 8, True, acc  # SendUsingAccount
                                )
                                break

                    mode = self.config.get("sent_items_mode", "folder")

                    if mode == "delete":
                        # Gönderilmiş Öğeler'e hiç düşmesin
                        mail.DeleteAfterSubmit = True
                        mail.Send()
                        print(f"[TEAMS-BRIDGE] OK - Gonderildi (kayit yok): {subject}")

                    elif mode == "folder":
                        # Göndermeden ÖNCE hedef klasörü ayarla → Outlook doğrudan oraya kaydeder
                        try:
                            namespace = outlook.GetNamespace("MAPI")
                            folder_name = self.config.get("sent_folder_name", "Teams Bildirimleri")
                            inbox = namespace.GetDefaultFolder(6)  # olFolderInbox
                            target_folder = None
                            for f in inbox.Parent.Folders:
                                if f.Name == folder_name:
                                    target_folder = f
                                    break
                            if target_folder is None:
                                target_folder = inbox.Parent.Folders.Add(folder_name)
                            # Göndermeden önce kayıt klasörünü ayarla
                            mail.SaveSentMessageFolder = target_folder
                        except Exception as fe:
                            print(f"[TEAMS-BRIDGE] UYARI - Klasor ayarlanamadi, varsayilan kullanilacak: {fe}")
                        mail.Send()
                        print(f"[TEAMS-BRIDGE] OK - Gonderildi -> '{folder_name}' klasorune kaydedildi: {subject}")

                    else:
                        # Normal: Gönderilmiş Öğeler'e düşer
                        mail.Send()
                        print(f"[TEAMS-BRIDGE] OK - Teams kanalina gonderildi: {subject}")

                    return True
                except Exception as e:
                    print(f"[TEAMS-BRIDGE] HATA - Gonderim hatasi: {e}")
                    return False
                finally:
                    try:
                        pythoncom.CoUninitialize()
                    except Exception:
                        pass

        t = threading.Thread(target=_send, daemon=True, name="TeamsMailSender")
        t.start()
        return True

    # ── Olay Türüne Göre Gönderim Metodları ────────────────────────────────

    def notify_broadcast(self, text: str) -> bool:
        """broadcast_message() çağrıldığında Teams'e de gönderir."""
        if not self.config.get("notify_broadcast", True):
            return False
        return self.send_to_teams("📢 Sistem Yayını", text)

    def notify_critical(self, event_title: str, event_text: str) -> bool:
        """notify_critical_event() çağrıldığında Teams'e de gönderir."""
        if not self.config.get("notify_critical", True):
            return False
        subject = f"🚨 KRİTİK: {event_title}"
        body = f"<strong>{event_title}</strong><br><br>{event_text}"
        return self.send_to_teams(subject, body)

    def notify_morning_briefing(self, briefing_text: str) -> bool:
        """Sabah bültenini Teams'e gönderir."""
        if not self.config.get("notify_morning_briefing", True):
            return False
        return self.send_to_teams("🌅 Sabah Operasyon Bülteni", briefing_text)

    def notify_evening_report(self, report_text: str) -> bool:
        """Akşam kapanış raporunu Teams'e gönderir."""
        if not self.config.get("notify_evening_report", True):
            return False
        return self.send_to_teams("🌆 Akşam Kapanış Raporu", report_text)

    def update_teams_email(self, new_email: str) -> bool:
        """Teams kanal e-posta adresini günceller ve kaydeder."""
        self.config["teams_channel_email"] = new_email.strip()
        return save_teams_config(self.config)

    def set_enabled(self, enabled: bool) -> bool:
        """Teams bildirimlerini etkinleştirir/devre dışı bırakır."""
        self.config["enabled"] = enabled
        return save_teams_config(self.config)


# ── GLOBAL SİNGLETON ────────────────────────────────────────────────────────
_bridge_instance: TeamsOutlookBridge = None


def get_teams_bridge() -> TeamsOutlookBridge:
    """Global Teams köprüsü örneğini döndürür (singleton)."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = TeamsOutlookBridge()
    return _bridge_instance
