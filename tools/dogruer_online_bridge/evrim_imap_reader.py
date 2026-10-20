# -*- coding: utf-8 -*-
"""
tools/dogruer_online_bridge/evrim_imap_reader.py
================================================
Doğruer Online Aktivasyon Kodu'nu otomatik olarak okur.

Öncelik sırası:
  1. Outlook COM API  — kurumsal M365 hesabı zaten Outlook'ta açık, Basic Auth gerekmez
  2. IMAP SSL         — Outlook yoksa veya başarısız olursa fallback

Mail: ozan.gemici@dogruer.com
Gönderen: Dogruer.Online (No-Reply)
Konu: Dogruer.Online Aktivasyon Kodu
Kod: 6 haneli sayısal (ör: 570282)
"""

import email
import os
import re
import time
import json
import datetime
from typing import Optional, Tuple

CONFIG_DIR  = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Doğruer Online mail filtresi
SENDER_KEYWORDS  = ["dogruer.online", "noreply@dogruer", "no-reply@dogruer"]
SUBJECT_KEYWORDS = ["aktivasyon kodu", "dogruer.online aktivasyon", "giris kodu", "doğrulama kodu"]
CODE_PATTERN     = re.compile(r"\b(\d{6})\b")


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ---------------------------------------------------------------------------
# Yardımcı: 6 haneli kodu metinden çıkar
# ---------------------------------------------------------------------------
def _extract_code_from_text(text: str) -> Optional[str]:
    """HTML/plain text içinden 6 haneli Doğruer aktivasyon kodunu çıkarır."""
    # HTML taglerini temizle
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&nbsp;|&amp;|&lt;|&gt;", " ", clean)

    # Bağlamlı arama (en güvenilir)
    context_match = re.search(
        r"(?:kodunuz|kodu|code|aktivasyon|giris|doğrulama)[:\s\-]*(\d{6})",
        clean, re.IGNORECASE
    )
    if context_match:
        return context_match.group(1)

    # Fallback: bağımsız 6 haneli sayı (yılları vs. filtrele)
    codes = CODE_PATTERN.findall(clean)
    valid = [c for c in codes if not c.startswith("202") and not c.startswith("20")]
    return valid[0] if valid else None


def _is_dogruer_mail(subject: str, sender: str) -> bool:
    s = subject.lower()
    f = sender.lower()
    return (
        any(kw in f for kw in SENDER_KEYWORDS) or
        any(kw in s for kw in SUBJECT_KEYWORDS)
    )


# ---------------------------------------------------------------------------
# YÖNTEM 1: Outlook COM API (Basic Auth gerektirmez)
# ---------------------------------------------------------------------------
class OutlookOtpReader:
    """
    Yerel Outlook uygulaması üzerinden Doğruer aktivasyon kodunu okur.
    win32com kullanır — Outlook 2016+ ve M365 Outlook ile çalışır.
    """

    def test_connection(self) -> Tuple[bool, str]:
        try:
            import win32com.client
            ol = win32com.client.Dispatch("Outlook.Application")
            ns = ol.GetNamespace("MAPI")
            inbox = ns.GetDefaultFolder(6)   # 6 = Inbox
            count = inbox.Items.Count
            return True, f"✅ Outlook bağlantısı başarılı (Gelen Kutusu: {count} mesaj)"
        except Exception as e:
            return False, f"❌ Outlook COM hatası: {e}"

    def fetch_latest_otp(self, timeout_seconds: int = 90,
                         on_progress=None) -> Optional[str]:
        """
        Son `timeout_seconds` saniyede gelen Doğruer Online aktivasyon kodunu döner.
        ~5 saniyede bir Outlook Gelen Kutusu'nu kontrol eder.
        """
        try:
            import win32com.client
        except ImportError:
            if on_progress:
                on_progress("⚠️ win32com bulunamadı, Outlook okuma devre dışı.")
            return None

        deadline  = time.time() + timeout_seconds
        attempt   = 0
        last_seen = set()   # Daha önce kontrol ettiğimiz mail EntryID'leri

        while time.time() < deadline:
            attempt += 1
            remaining = int(deadline - time.time())
            if on_progress:
                on_progress(f"📬 Outlook Gelen Kutusu kontrol ediliyor... ({remaining}s kaldı)")

            try:
                ol    = win32com.client.Dispatch("Outlook.Application")
                ns    = ol.GetNamespace("MAPI")
                inbox = ns.GetDefaultFolder(6)
                items = inbox.Items
                items.Sort("[ReceivedTime]", True)   # En yeni önce

                # Son 20 maile bak
                count = min(items.Count, 20)
                for i in range(1, count + 1):
                    try:
                        mail        = items[i]
                        entry_id    = mail.EntryID
                        received    = mail.ReceivedTime
                        subject     = mail.Subject or ""
                        sender_addr = ""
                        try:
                            sender_addr = mail.SenderEmailAddress or ""
                        except Exception:
                            try:
                                sender_addr = mail.Sender.Address or ""
                            except Exception:
                                pass
                        sender_name = mail.SenderName or ""

                        # Son 10 dakikada mı geldi?
                        # win32com ReceivedTime tz-aware datetime döner
                        try:
                            import pytz
                            now_utc = datetime.datetime.now(pytz.utc)
                        except ImportError:
                            now_utc = datetime.datetime.utcnow().replace(
                                tzinfo=datetime.timezone.utc
                            )

                        # received tz bilgisi olmayabilir, güvenli karşılaştır
                        try:
                            rec_dt = received
                            if rec_dt.tzinfo is None:
                                rec_dt = rec_dt.replace(tzinfo=datetime.timezone.utc)
                            age_minutes = (now_utc - rec_dt).total_seconds() / 60
                        except Exception:
                            age_minutes = 0   # bilinmiyorsa kontrol et

                        if age_minutes > 15:
                            continue   # 15 dakikadan eski, atla

                        if entry_id in last_seen:
                            continue

                        # Doğruer maili mi?
                        full_sender = f"{sender_name} {sender_addr}"
                        if not _is_dogruer_mail(subject, full_sender):
                            continue

                        # Gövdeyi al ve kodu çıkar
                        body = ""
                        try:
                            body = mail.HTMLBody or mail.Body or ""
                        except Exception:
                            try:
                                body = mail.Body or ""
                            except Exception:
                                pass

                        code = _extract_code_from_text(body)
                        if code:
                            if on_progress:
                                on_progress(f"✅ Outlook'tan aktivasyon kodu alındı!")
                            return code

                        last_seen.add(entry_id)

                    except Exception:
                        continue

            except Exception as e:
                if on_progress:
                    on_progress(f"⚠️ Outlook okuma hatası: {e}")

            time.sleep(5)

        return None


# ---------------------------------------------------------------------------
# YÖNTEM 2: IMAP SSL (fallback — Basic Auth gerektirir)
# ---------------------------------------------------------------------------
class ImapOtpReader:
    """
    IMAP SSL üzerinden Doğruer Online aktivasyon kodunu okur.
    Microsoft 365 'Basic authentication is disabled' hatası verirse çalışmaz.
    """

    def __init__(self):
        cfg = _load_config()
        self.host     = cfg.get("imap_host", "outlook.office365.com")
        self.port     = int(cfg.get("imap_port", 993))
        self.username = cfg.get("imap_user", cfg.get("dogruer_user", ""))
        self.password = cfg.get("imap_pass", "")
        self.use_ssl  = cfg.get("imap_ssl", True)

    def test_connection(self) -> Tuple[bool, str]:
        if not self.password:
            return False, "⚠️ IMAP şifresi girilmemiş."
        try:
            conn = self._connect()
            conn.logout()
            return True, f"✅ IMAP bağlantısı başarılı ({self.host})"
        except Exception as e:
            return False, f"❌ IMAP bağlantı hatası: {e}"

    def fetch_latest_otp(self, timeout_seconds: int = 90,
                         on_progress=None) -> Optional[str]:
        if not self.password:
            if on_progress:
                on_progress("⚠️ IMAP şifresi girilmemiş, IMAP okuma devre dışı.")
            return None

        import imaplib
        deadline  = time.time() + timeout_seconds
        attempt   = 0
        last_uid  = self._get_latest_uid()

        while time.time() < deadline:
            attempt += 1
            remaining = int(deadline - time.time())
            if on_progress:
                on_progress(f"📬 IMAP kontrol ediliyor... ({remaining}s kaldı, deneme {attempt})")
            code = self._search_for_code(since_uid=last_uid)
            if code:
                if on_progress:
                    on_progress("✅ IMAP'ten aktivasyon kodu alındı!")
                return code
            time.sleep(5)
        return None

    def _connect(self):
        import imaplib, ssl
        if self.use_ssl:
            conn = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            conn = imaplib.IMAP4(self.host, self.port)
            conn.starttls()
        conn.login(self.username, self.password)
        conn.select("INBOX")
        return conn

    def _get_latest_uid(self) -> Optional[str]:
        try:
            conn = self._connect()
            typ, data = conn.uid("SEARCH", None, "ALL")
            conn.logout()
            if typ == "OK" and data and data[0]:
                uids = data[0].decode().split()
                return uids[-1] if uids else None
        except Exception:
            pass
        return None

    def _search_for_code(self, since_uid: Optional[str] = None) -> Optional[str]:
        try:
            import imaplib
            conn = self._connect()
            today_str = datetime.date.today().strftime("%d-%b-%Y")
            typ, data = conn.uid("SEARCH", None, f'(SINCE "{today_str}")')
            if typ != "OK" or not data or not data[0]:
                conn.logout()
                return None
            all_uids = data[0].decode().split()
            if not all_uids:
                conn.logout()
                return None

            if since_uid and since_uid in all_uids:
                idx = all_uids.index(since_uid)
                candidate_uids = all_uids[idx + 1:]
            else:
                candidate_uids = all_uids[-10:]

            for uid in reversed(candidate_uids):
                typ, msg_data = conn.uid("FETCH", uid, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_header_str(msg.get("Subject", ""))
                from_hdr = msg.get("From", "")
                if not _is_dogruer_mail(subject, from_hdr):
                    continue

                body = _extract_body(msg)
                code = _extract_code_from_text(body)
                if code:
                    conn.logout()
                    return code

            conn.logout()
        except Exception as e:
            print(f"[IMAP-READER] Hata: {e}")
        return None


def _decode_header_str(raw: str) -> str:
    from email.header import decode_header
    try:
        parts = decode_header(raw)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)
    except Exception:
        return raw


def _extract_body(msg) -> str:
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "text/html"):
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body_parts.append(part.get_payload(decode=True).decode(charset, errors="replace"))
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            body_parts.append(msg.get_payload(decode=True).decode(charset, errors="replace"))
        except Exception:
            pass
    return " ".join(body_parts)


# ---------------------------------------------------------------------------
# Ana EvrimImapReader sınıfı — Outlook önce, IMAP fallback
# ---------------------------------------------------------------------------
class EvrimImapReader:
    """
    Doğruer Online aktivasyon kodunu okur.
    Önce Outlook COM API, başarısız olursa IMAP dener.
    """

    def __init__(self):
        self._outlook = OutlookOtpReader()
        self._imap    = ImapOtpReader()

    def test_connection(self) -> Tuple[bool, str]:
        """
        Önce Outlook'u, sonra IMAP'i test eder.
        İlk başarılı olanın sonucunu döner.
        """
        ok, msg = self._outlook.test_connection()
        if ok:
            return True, f"[Outlook COM] {msg}"

        # Outlook başarısız → IMAP'i dene
        ok2, msg2 = self._imap.test_connection()
        if ok2:
            return True, f"[IMAP] {msg2}"

        # İkisi de başarısız
        return False, (
            f"Outlook: {msg}\n"
            f"IMAP: {msg2}\n\n"
            "💡 Çözüm: Outlook uygulaması açık olduğundan emin olun. "
            "IMAP için Microsoft 365 yöneticinizden Basic Auth iznini etkinleştirmesini isteyin."
        )

    def fetch_latest_otp(self, timeout_seconds: int = 90,
                         on_progress=None) -> Optional[str]:
        """
        Outlook COM → başarısız olursa IMAP ile OTP kodunu çeker.
        """
        # Yöntem 1: Outlook COM
        if on_progress:
            on_progress("📬 Outlook üzerinden aktivasyon kodu aranıyor...")
        code = self._outlook.fetch_latest_otp(timeout_seconds, on_progress)
        if code:
            return code

        # Yöntem 2: IMAP fallback
        cfg = _load_config()
        if cfg.get("imap_pass"):
            if on_progress:
                on_progress("📬 Outlook başarısız, IMAP ile deneniyor...")
            code = self._imap.fetch_latest_otp(timeout_seconds // 2, on_progress)

        return code


def get_imap_reader() -> EvrimImapReader:
    """Factory — her çağrıda config'den taze okur."""
    return EvrimImapReader()
