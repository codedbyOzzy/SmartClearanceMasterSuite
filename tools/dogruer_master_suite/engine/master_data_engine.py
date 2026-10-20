# -*- coding: utf-8 -*-
"""
==============================================================================
🏛️ DOĞRUER SMARTCLEARANCE MASTER SUITE - MASTER DATA & INTEGRATION ENGINE
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
Modül: MasterDataEngine & Configuration Management
==============================================================================
"""

import sys
import os
import re
import time
import json
import shutil
import tempfile
import threading
from datetime import datetime, timedelta

# Ensure root and tools directories are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_suite_dir = os.path.abspath(os.path.join(_current_dir, ".."))
_tools_dir = os.path.abspath(os.path.join(_suite_dir, ".."))
_root_dir = os.path.abspath(os.path.join(_tools_dir, ".."))

for p in [_root_dir, _tools_dir, _suite_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Ensure pywin32 and local site-packages paths are accessible in any environment
for _sub in [
    os.path.join("Lib", "site-packages"),
    os.path.join("python-embed", "Lib", "site-packages"),
    os.path.join("python-embed", "Lib", "site-packages", "win32"),
    os.path.join("python-embed", "Lib", "site-packages", "win32", "lib"),
    os.path.join("python-embed", "Lib", "site-packages", "Pythonwin"),
    os.path.join("Lib", "site-packages", "win32"),
    os.path.join("Lib", "site-packages", "win32", "lib"),
    os.path.join("Lib", "site-packages", "Pythonwin"),
]:
    _p = os.path.join(_root_dir, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)

for _dll_sub in [
    os.path.join("python-embed", "Lib", "site-packages", "pywin32_system32"),
    os.path.join("Lib", "site-packages", "pywin32_system32"),
]:
    _dp = os.path.join(_root_dir, _dll_sub)
    if os.path.isdir(_dp):
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(_dp)
            except Exception:
                pass
        os.environ["PATH"] = _dp + os.pathsep + os.environ.get("PATH", "")

# Windows API / COM & Excel
try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None

try:
    from tools.dogruer_master_suite.outlook_memory_guard import (
        safe_open_mail_by_entry_id, get_outlook_application,
    )
except Exception:
    try:
        from outlook_memory_guard import safe_open_mail_by_entry_id, get_outlook_application
    except Exception:
        safe_open_mail_by_entry_id = None
        get_outlook_application = None

try:
    from tools.supabase_sync_manager import get_supabase_manager
except Exception:
    try:
        from supabase_sync_manager import get_supabase_manager
    except Exception:
        get_supabase_manager = None


CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
EVRIM_DATA_PATH = os.path.join(CONFIG_DIR, "evrim_live_data.json")
TALEP_QUEUE_PATH = os.path.join(CONFIG_DIR, "talep_queue.json")

DEFAULT_CONFIG = {
    "excel_path": r"\\Dgfile01\ithalat\ITH28\Halit ENGELEK\HANKOOK İŞ TAKİP RAPORU.xlsx",
    "pdf_folder": os.path.join(os.path.expanduser("~"), "OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş", "Masaüstü", "kapanan"),
    "mail_to": "muhasebe@hankookn.com",
    "mail_cc": "mete.karatas@hankookn.com; aysegul.cetiner@hankookn.com; kardelen.aksoy@dogruer.com; halit.engelek@dogruer.com; 71604640@hankookn.com",
    "qnb_user": "",
    "qnb_pass": "",
    "qnb_autofill": True,
    "glp_user": "",
    "glp_pass": "",
    "glp_autofill": True,
    "dogruer_user": "",
    "dogruer_pass": "",
    "dogruer_autofill": True,
    "enable_desktop_notifications": True
}

DEFAULT_EXCEL_PATH = DEFAULT_CONFIG["excel_path"]
QNB_PORTAL_URL = "https://portal.qnbesolutions.com.tr/yonetim/"
DOGRUER_ONLINE_URL = "https://dogruer.online"


def load_talep_queue():
    """SmartClearance Talep kuyruğunu diskten yükler."""
    if os.path.exists(TALEP_QUEUE_PATH):
        try:
            with open(TALEP_QUEUE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_talep_queue(queue_data):
    """SmartClearance Talep kuyruğunu diske kaydeder."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TALEP_QUEUE_PATH, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Talep Kuyruğu Kaydetme Hatası: {e}")
        return False


def load_app_config():
    """Uygulama yapılandırmasını yükler ve varsayılanlarla harmanlar."""
    cfg = DEFAULT_CONFIG.copy()
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                cfg.update(loaded)
    except Exception as e:
        print(f"Yapılandırma Okuma Hatası: {e}")
    return cfg


def save_app_config(cfg):
    """Uygulama yapılandırmasını diske kaydeder."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Yapılandırma Kaydetme Hatası: {e}")
        return False


def load_evrim_cached_data():
    """Önbelleğe alınmış Evrim canlı verilerini yükler."""
    try:
        if os.path.exists(EVRIM_DATA_PATH):
            with open(EVRIM_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception as e:
        print(f"Evrim Verisi Okuma Hatası: {e}")
    return []


def save_evrim_cached_data(data):
    """Evrim canlı verilerini önbellek dosyasına kaydeder."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(EVRIM_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Evrim Verisi Kaydetme Hatası: {e}")
        return False


# =============================================================================
# 1. MERKEZİ VERİ VE ENTEGRASYON MOTORU
# =============================================================================
class MasterDataEngine:
    def __init__(self, config=None):
        self.config = config or load_app_config()
        self.excel_path = self.config.get("excel_path", "")
        if not self.excel_path:
            self.excel_path = DEFAULT_CONFIG["excel_path"]
        self.last_excel_mtime = 0
        self.last_outlook_count = 0
        self.records = []
        self.outlook_cache = []
        self.is_loading = False
        self.excel_read_ok = True
        self.last_excel_error = None
        self._last_good_excel_count = 0

    def _dispatch_outlook(self):
        if get_outlook_application:
            return get_outlook_application()
        if not win32com:
            return None
        try:
            return win32com.client.Dispatch("Outlook.Application")
        except Exception:
            return None

    def fetch_outlook_sent_items(self, limit=350):
        cache = []
        if not win32com:
            return cache
        try:
            pythoncom.CoInitialize()
            outlook = self._dispatch_outlook()
            if not outlook:
                return cache
            namespace = outlook.GetNamespace("MAPI")
            sent_folder = namespace.GetDefaultFolder(5)
            items = sent_folder.Items
            items.Sort("[SentOn]", True)

            count = 0
            for item in items:
                if count >= limit:
                    break
                try:
                    subj = str(item.Subject or "")
                    to_addr = str(item.To or "")
                    sent_time = item.SentOn
                    try:
                        sent_str = sent_time.strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        sent_str = str(sent_time)[:16]

                    attachments = []
                    for att in item.Attachments:
                        fname = att.FileName
                        if not re.match(r"^image\d+\.(png|jpg|gif)$", fname, re.I):
                            attachments.append(fname)

                    body_snippet = str(getattr(item, "Body", "") or "")[:2000]

                    cache.append({
                        "subject": subj,
                        "to": to_addr,
                        "sent_on": sent_str,
                        "attachments": attachments,
                        "body": body_snippet,
                        "entry_id": str(item.EntryID or ""),
                        "is_reply": subj.strip().upper().startswith("RE:") or subj.strip().upper().startswith("FW:")
                    })
                    count += 1
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            pythoncom.CoUninitialize()

        return cache

    def search_outlook_conversations(self, query="", limit=200):
        """Outlook'taki tüm konuşma zincirlerini (threads) tarar, adım adım sıralar."""
        conversations = []
        if not win32com:
            return conversations

        try:
            pythoncom.CoInitialize()
            outlook = self._dispatch_outlook()
            if not outlook:
                return conversations
            namespace = outlook.GetNamespace("MAPI")

            seen_conv_ids = set()
            q_clean = query.strip().upper()

            for folder_id, direction in [(5, "OUT"), (6, "IN")]:
                try:
                    folder = namespace.GetDefaultFolder(folder_id)
                    items = folder.Items
                    time_field = "[SentOn]" if folder_id == 5 else "[ReceivedTime]"
                    items.Sort(time_field, True)

                    count = 0
                    for item in items:
                        if count >= limit:
                            break
                        try:
                            subj = str(item.Subject or "")
                            sender = str(getattr(item, "SenderName", "") or "")
                            to = str(getattr(item, "To", "") or "")

                            if q_clean:
                                matches_query = (
                                    q_clean in subj.upper() or
                                    q_clean in sender.upper() or
                                    q_clean in to.upper()
                                )
                                if not matches_query:
                                    count += 1
                                    continue

                            conv_id = str(getattr(item, "ConversationID", "") or "")
                            topic = str(getattr(item, "ConversationTopic", "") or subj)

                            if not conv_id:
                                conv_id = topic.strip().upper()

                            if conv_id in seen_conv_ids:
                                count += 1
                                continue

                            seen_conv_ids.add(conv_id)

                            conv_obj = item.GetConversation()
                            msgs = []
                            all_atts = set()

                            if conv_obj:
                                tbl = conv_obj.GetTable()
                                while not tbl.EndOfTable:
                                    row = tbl.GetNextRow()
                                    e_id = row("EntryID")
                                    try:
                                        m = namespace.GetItemFromID(e_id)
                                        m_subj = str(m.Subject or "")
                                        m_sender = str(getattr(m, "SenderName", "") or "")
                                        m_to = str(getattr(m, "To", "") or "")
                                        m_body = str(getattr(m, "Body", "") or "").strip()

                                        clean_lines = [l.strip() for l in m_body.split("\n") if l.strip() and not l.strip().startswith(">") and not l.strip().startswith("From:") and not l.strip().startswith("Kimden:")]
                                        snippet = " ".join(clean_lines[:3])[:250]

                                        m_atts = []
                                        for a in m.Attachments:
                                            if not re.match(r"^image\d+\.(png|jpg|gif)$", a.FileName, re.I):
                                                m_atts.append(a.FileName)
                                                all_atts.add(a.FileName)

                                        t_val = getattr(m, "SentOn", None) or getattr(m, "ReceivedTime", None)
                                        try:
                                            t_str = t_val.strftime("%d.%m.%Y %H:%M")
                                        except Exception:
                                            t_str = str(t_val)[:16]

                                        is_out = "OZAN" in m_sender.upper() or "DOGRUER" in m_sender.upper()

                                        msgs.append({
                                            "direction": "OUT" if is_out else "IN",
                                            "sender": m_sender if not is_out else "Ben",
                                            "to": m_to,
                                            "time_raw": t_val,
                                            "time_str": t_str,
                                            "subject": m_subj,
                                            "snippet": snippet,
                                            "attachments": m_atts,
                                            "entry_id": str(e_id)
                                        })
                                    except Exception:
                                        continue
                            else:
                                t_val = getattr(item, "SentOn", None) or getattr(item, "ReceivedTime", None)
                                try:
                                    t_str = t_val.strftime("%d.%m.%Y %H:%M")
                                except Exception:
                                    t_str = str(t_val)[:16]

                                is_out = direction == "OUT"
                                msgs.append({
                                    "direction": direction,
                                    "sender": sender if not is_out else "Ben",
                                    "to": to,
                                    "time_raw": t_val,
                                    "time_str": t_str,
                                    "subject": subj,
                                    "snippet": str(getattr(item, "Body", "") or "")[:250],
                                    "attachments": [],
                                    "entry_id": str(item.EntryID or "")
                                })

                            def _get_ts(t_obj):
                                if not t_obj: return 0
                                try:
                                    return t_obj.timestamp()
                                except Exception:
                                    try:
                                        import datetime
                                        if isinstance(t_obj, datetime.datetime):
                                            return t_obj.timestamp()
                                    except Exception: pass
                                return 0

                            msgs.sort(key=lambda x: _get_ts(x.get("time_raw")))
                            for step_idx, m in enumerate(msgs, 1):
                                m["step"] = step_idx

                            last_t_raw = msgs[-1]["time_raw"] if msgs else None
                            last_ts = _get_ts(last_t_raw)

                            conversations.append({
                                "conv_id": conv_id,
                                "topic": topic or subj,
                                "total_steps": len(msgs),
                                "latest_timestamp": last_ts,
                                "latest_date": msgs[-1]["time_str"] if msgs else "",
                                "latest_sender": msgs[-1]["sender"] if msgs else "",
                                "messages": msgs,
                                "all_attachments": list(all_atts)
                            })

                            count += 1
                        except Exception:
                            continue
                except Exception as fe:
                    print(f"Klasör Arama Hatası ({folder_id}): {fe}")

            conversations.sort(key=lambda x: x.get("latest_timestamp", 0), reverse=True)
        except Exception as e:
            print(f"Outlook Konuşma Arama Hatası: {e}")
        finally:
            pythoncom.CoUninitialize()

        return conversations

    def fetch_conversation_by_entry_id(self, entry_id):
        """Herhangi bir mailin ait olduğu tüm konuşma zincirini adım adım çeker."""
        if not win32com or not entry_id:
            return None
        try:
            pythoncom.CoInitialize()
            outlook = self._dispatch_outlook()
            if not outlook:
                return None
            namespace = outlook.GetNamespace("MAPI")
            item = namespace.GetItemFromID(entry_id)
            if not item:
                return None

            conv_obj = item.GetConversation()
            msgs = []
            all_atts = set()

            if conv_obj:
                tbl = conv_obj.GetTable()
                while not tbl.EndOfTable:
                    row = tbl.GetNextRow()
                    e_id = row("EntryID")
                    try:
                        m = namespace.GetItemFromID(e_id)
                        m_subj = str(m.Subject or "")
                        m_sender = str(getattr(m, "SenderName", "") or "")
                        m_to = str(getattr(m, "To", "") or "")
                        m_body = str(getattr(m, "Body", "") or "").strip()

                        clean_lines = [l.strip() for l in m_body.split("\n") if l.strip() and not l.strip().startswith(">") and not l.strip().startswith("From:") and not l.strip().startswith("Kimden:")]
                        snippet = " ".join(clean_lines[:3])[:250]

                        m_atts = []
                        for a in m.Attachments:
                            if not re.match(r"^image\d+\.(png|jpg|gif)$", a.FileName, re.I):
                                m_atts.append(a.FileName)
                                all_atts.add(a.FileName)

                        t_val = getattr(m, "SentOn", None) or getattr(m, "ReceivedTime", None)
                        try:
                            t_str = t_val.strftime("%d.%m.%Y %H:%M")
                        except Exception:
                            t_str = str(t_val)[:16]

                        is_out = "OZAN" in m_sender.upper() or "DOGRUER" in m_sender.upper()

                        msgs.append({
                            "direction": "OUT" if is_out else "IN",
                            "sender": m_sender if not is_out else "Ben (Ozan Gemici)",
                            "to": m_to,
                            "time_raw": t_val,
                            "time_str": t_str,
                            "subject": m_subj,
                            "snippet": snippet,
                            "attachments": m_atts,
                            "entry_id": str(e_id)
                        })
                    except Exception:
                        continue
            else:
                t_val = getattr(item, "SentOn", None) or getattr(item, "ReceivedTime", None)
                try:
                    t_str = t_val.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    t_str = str(t_val)[:16]

                sender = str(getattr(item, "SenderName", "") or "")
                is_out = "OZAN" in sender.upper() or "DOGRUER" in sender.upper()
                msgs.append({
                    "direction": "OUT" if is_out else "IN",
                    "sender": sender if not is_out else "Ben (Ozan Gemici)",
                    "to": str(getattr(item, "To", "") or ""),
                    "time_raw": t_val,
                    "time_str": t_str,
                    "subject": str(item.Subject or ""),
                    "snippet": str(getattr(item, "Body", "") or "")[:250],
                    "attachments": [],
                    "entry_id": str(item.EntryID or "")
                })

            msgs.sort(key=lambda x: x["time_raw"] if x["time_raw"] else 0)
            for step_idx, m in enumerate(msgs, 1):
                m["step"] = step_idx

            return {
                "topic": str(getattr(item, "ConversationTopic", "") or item.Subject or "Konuşma"),
                "total_steps": len(msgs),
                "messages": msgs,
                "all_attachments": list(all_atts)
            }
        except Exception as e:
            print(f"Konuşma Çekme Hatası: {e}")
        finally:
            pythoncom.CoUninitialize()
        return None

    def fetch_file_mail_timeline(self, rec):
        """Seçili dosyanın gelen ve giden tüm maillerini kronolojik sırayla toplar."""
        timeline = []
        if not win32com or not rec:
            return timeline

        ref_clean = re.sub(r"[^A-Z0-9]", "", (rec.get("ref") or "").upper())
        dosya_clean = re.sub(r"[^A-Z0-9]", "", (rec.get("dosya") or "").upper())
        bl_clean = re.sub(r"[^A-Z0-9]", "", (rec.get("bl") or "").upper())

        if not (ref_clean or (dosya_clean and len(dosya_clean) >= 6) or (bl_clean and len(bl_clean) >= 7)):
            return timeline

        try:
            pythoncom.CoInitialize()
            outlook = self._dispatch_outlook()
            if not outlook:
                return timeline
            namespace = outlook.GetNamespace("MAPI")

            for folder_id, direction, label in [(5, "OUT", "📤 Giden"), (6, "IN", "📥 Gelen")]:
                try:
                    folder = namespace.GetDefaultFolder(folder_id)
                    items = folder.Items
                    time_field = "[SentOn]" if folder_id == 5 else "[ReceivedTime]"
                    items.Sort(time_field, True)

                    count = 0
                    for item in items:
                        if count >= 250:
                            break
                        try:
                            subj = str(item.Subject or "")
                            subj_c = re.sub(r"[^A-Z0-9]", "", subj.upper())
                            entry_id = str(item.EntryID or "")

                            attachments = []
                            for att in item.Attachments:
                                fname = att.FileName
                                if not re.match(r"^image\d+\.(png|jpg|gif)$", fname, re.I):
                                    attachments.append(fname)
                            att_c = re.sub(r"[^A-Z0-9]", "", " ".join(attachments).upper())

                            is_match = (
                                (ref_clean and (ref_clean in subj_c or ref_clean in att_c)) or
                                (dosya_clean and len(dosya_clean) >= 6 and (dosya_clean in subj_c or dosya_clean in att_c)) or
                                (bl_clean and len(bl_clean) >= 7 and (bl_clean in subj_c or bl_clean in att_c))
                            )

                            if is_match:
                                t_val = item.SentOn if folder_id == 5 else item.ReceivedTime
                                try:
                                    time_str = t_val.strftime("%d.%m.%Y %H:%M")
                                except Exception:
                                    time_str = str(t_val)[:16]

                                party = str(item.To or "") if direction == "OUT" else str(item.SenderName or "")

                                timeline.append({
                                    "direction": direction,
                                    "label": label,
                                    "subject": subj,
                                    "party": party,
                                    "time_str": time_str,
                                    "attachments": attachments,
                                    "entry_id": entry_id
                                })
                            count += 1
                        except Exception:
                            continue
                except Exception as fe:
                    print(f"Klasör Hatası ({folder_id}): {fe}")

            timeline.sort(key=lambda x: x["time_str"], reverse=True)
        except Exception as e:
            print(f"Timeline Hatası: {e}")
        finally:
            pythoncom.CoUninitialize()

        return timeline

    def open_outlook_mail_by_id(self, entry_id):
        """Belirtilen EntryID'ye sahip maili Outlook ekranında açar."""
        if not win32com or not entry_id:
            return False
        try:
            from tools.dogruer_master_suite.outlook_memory_guard import safe_open_mail_by_entry_id
            return safe_open_mail_by_entry_id(entry_id)
        except Exception as e:
            print(f"Mail Açma Hatası: {e}")
            return False

    def create_tax_mail_draft(self, records):
        """Seçili tek veya çoklu dosyalar için standart Vergi Talebi mail taslağı oluşturur."""
        if not records:
            return False, "Seçili dosya kaydı bulunamadı veya dosya seçilmedi."
        if not win32com:
            return False, "Outlook COM bağlantı modülü (pywin32) yüklenemedi. Lütfen sistemde pywin32 modülünün kurulu olduğunu kontrol edin."

        if not isinstance(records, list):
            records = [records]

        import tempfile, shutil, re as _re

        # Geçici klasör: yeniden adlandırılan PDF kopyaları buraya gider
        tmp_dir = tempfile.mkdtemp(prefix="sc_mail_")
        tmp_copies = []  # Temizlik için

        try:
            pythoncom.CoInitialize()
            outlook = self._dispatch_outlook()
            if not outlook:
                return False, "Klasik masaüstü Outlook bulunamadı (Yeni Outlook COM vermez)."
            mail = outlook.CreateItem(0)

            # ── 1. Konu (Subject) ────────────────────────────────────────────
            refs = []
            for r in records:
                ref_val = (r.get("ref") or "").strip()
                if ref_val and ref_val not in refs:
                    refs.append(ref_val)
                elif not ref_val:
                    dosya_val = (r.get("dosya") or "").strip()
                    if dosya_val and dosya_val not in refs:
                        refs.append(dosya_val)

            mail.Subject = "Vergi Talebi/ " + "+".join(refs)

            # ── 2. Alıcılar ──────────────────────────────────────────────────
            mail.To = self.config.get("mail_to", "muhasebe@hankookn.com")
            mail.CC = self.config.get("mail_cc", "mete.karatas@hankookn.com; aysegul.cetiner@hankookn.com; kardelen.aksoy@dogruer.com; halit.engelek@dogruer.com; 71604640@hankookn.com")

            # ── 3. Gövde (imzayı koru) ───────────────────────────────────────
            # GetInspector = Outlook arayüzünü açar → DONMAYA NEDEN OLUR
            # Bunun yerine: önce Display() ile aç, imza HTMLBody'ye otomatik gelir
            msg_html = (
                '<div style="font-family:Arial,sans-serif;font-size:13px;color:#000;line-height:1.5;">'
                '<p style="margin:0 0 14px 0;">Merhaba,</p>'
                '<p style="margin:0 0 14px 0;">Ekteki beyannameler için vergi ödemelerini rica ederiz.<br>Teşekkürler.</p>'
                '<p style="margin:0 0 18px 0;">İyi çalışmalar dilerim.</p>'
                '</div>'
            )

            # ── 4. PDF Arama + Yeniden Adlandırma ────────────────────────────
            custom_pdf_dir = self.config.get("pdf_folder", "")
            if not custom_pdf_dir:
                custom_pdf_dir = os.path.join(os.path.expanduser("~"), "OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş", "Masaüstü", "kapanan")
            search_dirs = [
                custom_pdf_dir,
                os.path.join(custom_pdf_dir, "mailatıldı"),
                os.path.join(os.path.expanduser("~"), "Downloads"),
                os.path.join(os.path.expanduser("~"), "Desktop"),
                os.path.join(os.path.expanduser("~"), "Documents"),
            ]

            def _extract_ref_from_filename(fname: str) -> str:
                """
                T26-093518_4200800537_HNKRE.pdf gibi isimlerden
                ortadaki sayısal bloğu (referans numarası) çıkarır.
                Öncelik: alt çizgiyle ayrılmış 10 haneli sayısal blok.
                """
                stem = os.path.splitext(fname)[0]
                parts = stem.split("_")
                # 10 haneli sayısal blok ara (örn: 4200800537)
                for p in parts:
                    if _re.match(r"^\d{9,12}$", p):
                        return p
                # Fallback: herhangi bir sayısal parça
                for p in parts:
                    if _re.match(r"^\d{6,}$", p):
                        return p
                return stem  # Bulunamazsa orijinal isim

            def _find_pdf(ref, dosya):
                """Referans veya dosya no'ya göre PDF'i arar, bulursa (orijinal_path) döner."""
                keys = [k for k in [ref, dosya] if k]
                for s_dir in search_dirs:
                    if not os.path.isdir(s_dir):
                        continue
                    # Tam eşleşme: {ref}.pdf
                    if ref:
                        exact = os.path.join(s_dir, f"{ref}.pdf")
                        if os.path.exists(exact):
                            return exact
                    # Dosya adı içinde ara
                    try:
                        names = os.listdir(s_dir)
                        scanned = 0
                        for fname in names:
                            if scanned >= 800:
                                break
                            if not fname.lower().endswith(".pdf"):
                                continue
                            scanned += 1
                            for key in keys:
                                if key and key in fname:
                                    return os.path.join(s_dir, fname)
                    except Exception:
                        pass
                return None

            attached_display_names = []
            found_originals = []

            for r in records:
                ref   = (r.get("ref")   or "").strip()
                dosya = (r.get("dosya") or "").strip()

                orig_path = _find_pdf(ref, dosya)
                if not orig_path or orig_path in found_originals:
                    continue
                found_originals.append(orig_path)

                # PDF'i yeniden adlandır: referans numarasını çıkar
                orig_fname = os.path.basename(orig_path)
                new_stem   = _extract_ref_from_filename(orig_fname)
                new_fname  = new_stem + ".pdf"

                # Geçici kopyayı oluştur (orijinal dosyaya dokunulmaz)
                tmp_path = os.path.join(tmp_dir, new_fname)
                # Aynı isimde birden fazla dosya olabilir → numaralandır
                counter = 1
                while os.path.exists(tmp_path):
                    tmp_path = os.path.join(tmp_dir, f"{new_stem}_{counter}.pdf")
                    counter += 1
                shutil.copy2(orig_path, tmp_path)
                tmp_copies.append(tmp_path)

                try:
                    mail.Attachments.Add(tmp_path)
                    attached_display_names.append(new_fname)
                except Exception as ae:
                    print(f"[MAIL-EK-HATA] {ae}")

            # ── 5. Gövde: önce Display et (imzayı Outlook koyar), sonra metni başa ekle ──
            # Display(False) = modal değil, donmuyor
            # Uyarı: Display() çağrıldıktan sonra HTMLBody değiştirilebilir
            mail.Display(False)

            # Outlook imzasını koru, içeriği başa ekle
            try:
                current_body = mail.HTMLBody or ""
                mail.HTMLBody = msg_html + current_body
            except Exception:
                pass  # Bazen Display sonrası COM erişim hatası olabilir, önemli değil

            # COM nesnelerini temizle (bellek sızıntısı önleme)
            del mail
            del outlook

            # ── 5.5 Aktivite Günlüğüne Otomatik Kayıt ───────────────────────
            try:
                from tools.supabase_sync_manager import get_supabase_manager
                sm = get_supabase_manager()
                if sm:
                    mail_to_addr = self.config.get("mail_to", "muhasebe@hankookn.com")
                    for r in records:
                        d_val = (r.get("dosya") or "").strip()
                        r_val = (r.get("ref") or "").strip()
                        b_val = (r.get("beyanname") or "").strip()
                        att_info = f" ({len(attached_display_names)} ekli)" if attached_display_names else ""
                        sm.add_activity_log(
                            dosya_no=d_val,
                            ref_no=r_val,
                            beyanname_no=b_val,
                            islem_tipi="MAIL",
                            baslik=f"Vergi Talebi Maili Hazırlandı{att_info}",
                            icerik=f"Alıcı: {mail_to_addr}\nEklenen Dosyalar: {', '.join(attached_display_names[:5])}",
                            etiket="Tamamlandı",
                            metadata={"to": mail_to_addr, "attachments": attached_display_names}
                        )
            except Exception as _log_e:
                print(f"[MAIL-ACT-LOG-ERROR] {_log_e}")

            # ── 6. Sonuç mesajı ──────────────────────────────────────────────
            msg_res = f"✅ {len(records)} dosya için Vergi Talebi taslağı Outlook'ta açıldı!\n\n"
            if attached_display_names:
                msg_res += (
                    f"📎 {len(attached_display_names)} PDF maile eklendi"
                    f" (yeniden adlandırıldı):\n"
                    + ", ".join(attached_display_names[:6])
                    + ("..." if len(attached_display_names) > 6 else "")
                )
            else:
                msg_res += "ℹ️ Eşleşen PDF bulunamadı. İlgili PDF'leri sürükleyip bırakabilirsiniz."

            return True, msg_res

        except Exception as e:
            return False, f"Mail Taslağı Hatası: {e}"
        finally:
            pythoncom.CoUninitialize()
            # Geçici dosyaları 30 sn sonra temizle (Outlook eke erişmeye devam edebilir)
            def _cleanup():
                import time as _time
                _time.sleep(30)
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
            import threading as _th
            _th.Thread(target=_cleanup, daemon=True).start()



    def fetch_excel_records(self):
        from tools.dogruer_master_suite.engine.excel_read_guard import is_excel_lock_error

        if not openpyxl:
            self.excel_read_ok = False
            self.last_excel_error = "Excel okuyucu (openpyxl) yüklü değil."
            return list(self.records)

        if not self.excel_path or not os.path.exists(self.excel_path):
            self.excel_read_ok = False
            self.last_excel_error = "Excel dosyası bulunamadı."
            return list(self.records)

        records = []
        previous = list(self.records)
        
        # --- EVRIM LIVE DATA INTEGRATION ---
        try:
            evrim_data = load_evrim_cached_data()
        except Exception:
            evrim_data = []
            
        evrim_dict = {}
        for d in evrim_data:
            d_no = str(d.get("dosya_no") or "").strip()
            h_ref = str(d.get("hankook_ref") or "").strip().split("/")[0]
            if d_no: evrim_dict[d_no] = d
            if h_ref: evrim_dict[h_ref] = d

        # --- GTB TAKIP INTEGRATION ---
        try:
            from tools.gtb_engine.gtb_tracker_service import get_gtb_tracker_service
            tracker = get_gtb_tracker_service()
            tracked_list = tracker.list_tracked()
            tracked_dosya_nos = set(str(t.get("dosya_no") or "").strip().upper() for t in tracked_list if t.get("dosya_no"))
            tracked_refs = set(str(t.get("ref") or t.get("ref_no") or "").strip().split("/")[0].upper() for t in tracked_list if (t.get("ref") or t.get("ref_no")))
            tracked_beyans = set(str(t.get("beyanname_no") or "").strip().upper() for t in tracked_list if t.get("beyanname_no"))
        except Exception as e:
            print("GTB Takip Listesi Çekilemedi:", e)
            tracked_dosya_nos = set()
            tracked_refs = set()
            tracked_beyans = set()

        try:
            wb = openpyxl.load_workbook(self.excel_path, data_only=True)
            sheet_name = "GÜNCEL RAPOR" if "GÜNCEL RAPOR" in wb.sheetnames else wb.sheetnames[0]
            ws = wb[sheet_name]

            for r in range(2, ws.max_row + 1):
                dosya = str(ws.cell(r, 1).value or "").strip()
                gumruk = str(ws.cell(r, 2).value or "").strip()
                ref = str(ws.cell(r, 3).value or "").strip()
                
                evrim_rec = evrim_dict.get(dosya) or evrim_dict.get(ref) or {}

                bayi = str(ws.cell(r, 4).value or "").strip()
                acenta = str(ws.cell(r, 5).value or "").strip()
                bl = str(ws.cell(r, 6).value or "").strip()
                ordino = str(ws.cell(r, 7).value or "").strip()
                transfer = str(ws.cell(r, 8).value or "").strip()
                tareks = str(ws.cell(r, 9).value or "").strip()
                tareks_sonuc = str(ws.cell(r, 10).value or "").strip()
                tescil = str(ws.cell(r, 12).value or "").strip()
                hat = str(ws.cell(r, 13).value or "").strip().upper()
                kapanis = str(ws.cell(r, 14).value or "").strip()
                vergi = str(ws.cell(r, 15).value or "").strip()
                liman = str(ws.cell(r, 22).value or "").strip()
                aciklama = str(ws.cell(r, 17).value or "").strip()
                varis_val = str(ws.cell(r, 19).value or "").strip() # S Sütunu
                eta_val = str(ws.cell(r, 20).value or "").strip()   # T Sütunu
                
                # Eğer ETA sütunu boşaltılıp VARIŞ TARİHİ sütununa kaydırılmışsa, onu baz al
                if not eta_val and varis_val:
                    eta_val = varis_val
                    
                konteyner_val = str(ws.cell(r, 21).value or "").strip()
                gemi_val = str(ws.cell(r, 23).value or "").strip()

                def clean_date(d_val):
                    if not d_val or str(d_val).lower() == "none":
                        return ""
                    d_str = str(d_val).strip()
                    if " " in d_str:
                        d_str = d_str.split()[0]
                    if "-" in d_str:
                        parts = d_str.split("-")
                        if len(parts) == 3 and len(parts[0]) == 4:
                            return f"{parts[2]}.{parts[1]}.{parts[0]}"
                    return d_str

                ordino_clean = clean_date(ordino)
                tareks_clean = clean_date(tareks)
                tescil_clean = clean_date(tescil)
                kapanis_clean = clean_date(kapanis)
                vergi_clean = clean_date(vergi)

                if dosya or ref or bl:
                    evrim_statu = str(evrim_rec.get("statu") or "").upper()
                    evrim_beyan_no = str(evrim_rec.get("beyanname_no") or "").strip()
                    
                    # 1) GTB Takip kontrolü
                    in_gtb_takip = False
                    if dosya.upper() in tracked_dosya_nos or ref.upper() in tracked_refs or (evrim_beyan_no and evrim_beyan_no.upper() in tracked_beyans):
                        in_gtb_takip = True
                        
                    # 2) Eğer Vergi Ödendi bilgisi Evrim'de varsa, vergi dolu say
                    if not vergi_clean and ("VERGİ ÖDENDİ" in evrim_statu):
                        vergi_clean = "Evrim'de Ödendi"

                    # 3) Tescil Şartı: Excel'de dolu olması veya GTB takip havuzunda olması
                    is_tescil_stage = bool(tescil_clean) or ("TESCIL" in aciklama.upper()) or ("TESCİL" in aciklama.upper()) or in_gtb_takip
                    
                    if is_tescil_stage and not tescil_clean:
                        tescil_clean = "GTB Takipte"
                        
                    is_tax_pending = is_tescil_stage and (not vergi_clean)


                    if kapanis_clean:
                        stage = "5_KAPANDI"
                        stage_title = "🟢 Kapandı / Arşiv"
                        mail_status = "🟢 Dosya Kapandı"
                        mail_badge = "grey"
                    elif is_tescil_stage:
                        if hat == "KIRMIZI":
                            stage = "3_MUAYENE"
                            stage_title = "🔴 Kırmızı Hat (Muayenede)"
                        else:
                            stage = "3_TESCILDE"
                            stage_title = "🔵 Tescilde / Tescil Oldu"

                        if is_tax_pending:
                            mail_status = "🔴 Vergi Maili Bekliyor"
                            mail_badge = "red"
                        else:
                            mail_status = f"✅ Vergi Ödendi ({vergi_clean})"
                            mail_badge = "green"
                    elif ordino_clean or tareks_clean:
                        stage = "2_ORDINO_TAREKS"
                        stage_title = "🟠 Ordino / Tareks İşlemde"
                        mail_status = "⏳ Tareks/Ordino Aşamasında"
                        mail_badge = "grey"
                    else:
                        stage = "1_EVRAK"
                        stage_title = "🟡 Yeni Evrak / Hazırlık"
                        mail_status = "⏳ Hazırlık Aşamasında"
                        mail_badge = "grey"

                    records.append({
                        "row_idx": r,
                        "dosya": dosya,
                        "gumruk": gumruk,
                        "ref": ref,
                        "bayi": bayi,
                        "acenta": acenta,
                        "bl": bl,
                        "ordino": ordino_clean,
                        "transfer": transfer,
                        "tareks": tareks_clean,
                        "tareks_sonuc": tareks_sonuc,
                        "tescil": tescil_clean,
                        "hat": hat,
                        "kapanis": kapanis_clean,
                        "vergi": vergi_clean,
                        "liman": liman,
                        "aciklama": aciklama,
                        "eta": eta_val,
                        "konteyner": konteyner_val,
                        "gemi": gemi_val,
                        "stage": stage,
                        "stage_title": stage_title,
                        "is_tescil_stage": is_tescil_stage,
                        "is_tax_pending": is_tax_pending,
                        "mail_status": mail_status,
                        "mail_date": "",
                        "mail_badge": mail_badge,
                        "beyan": evrim_beyan_no,
                        "evrim_statu": evrim_statu
                    })
            if self._last_good_excel_count >= 10 and len(records) < int(self._last_good_excel_count * 0.5):
                self.excel_read_ok = False
                self.last_excel_error = "Excel beklenenden az satır döndü; önceki liste korundu."
                self.records = previous
                return previous
            self.records = records
            self.excel_read_ok = True
            self.last_excel_error = None
            self._last_good_excel_count = len(records)
        except Exception as e:
            print(f"Excel Okuma Hatası: {e}")
            self.excel_read_ok = False
            if is_excel_lock_error(e):
                self.last_excel_error = "Excel dosyası kilitli (başka uygulamada açık olabilir)."
            else:
                self.last_excel_error = f"Excel okunamadı: {e}"
            self.records = previous
            return previous

        return records

    def sync_all(self):
        if self.is_loading:
            return
        self.is_loading = True

        if os.path.exists(self.excel_path):
            try: self.last_excel_mtime = os.path.getmtime(self.excel_path)
            except Exception: pass

        records = self.fetch_excel_records()
        outlook_records = self.fetch_outlook_sent_items(limit=350)
        self.outlook_cache = outlook_records

        for r in records:
            ref_clean = re.sub(r"[^A-Z0-9]", "", str(r.get("ref") or "").upper())
            dosya_clean = re.sub(r"[^A-Z0-9]", "", str(r.get("dosya") or "").upper())
            bl_clean = re.sub(r"[^A-Z0-9]", "", str(r.get("bl") or "").upper())

            found_tax_mail = None
            for m in outlook_records:
                to_addr = str(m.get("to") or "").upper()
                subj = str(m.get("subject") or "").upper()

                # SADECE muhasebe@hankookn.com veya muhasebeye atılan VERGİ / DEKONT mailleri vergi maili sayılır
                is_to_muhasebe = ("MUHASEBE" in to_addr) or ("HANKOOKN.COM" in to_addr and "VERG" in subj)
                is_tax_subj = ("VERG" in subj) or ("DEKONT" in subj)

                if not (is_to_muhasebe and is_tax_subj):
                    continue

                subj_c = re.sub(r"[^A-Z0-9]", "", subj)
                att_c = re.sub(r"[^A-Z0-9]", "", " ".join(m.get("attachments") or []).upper())
                body_c = re.sub(r"[^A-Z0-9]", "", str(m.get("body") or "").upper())

                if (ref_clean and (ref_clean in subj_c or ref_clean in att_c or ref_clean in body_c)) or \
                   (dosya_clean and len(dosya_clean) >= 6 and (dosya_clean in subj_c or dosya_clean in att_c or dosya_clean in body_c)) or \
                   (bl_clean and len(bl_clean) >= 7 and (bl_clean in subj_c or bl_clean in att_c or bl_clean in body_c)):
                    found_tax_mail = m
                    break

            if found_tax_mail:
                # Sadece Muhasebe'ye vergi maili atılmışsa bekleme durumunu kapat
                r["is_tax_pending"] = False
                sent_time = found_tax_mail.get("sent_on", "")
                time_disp = sent_time[-5:] if len(sent_time) >= 5 else sent_time
                if found_tax_mail.get("attachments"):
                    r["mail_status"] = f"🟢 Vergi Maili Atıldı ({time_disp})"
                    r["mail_badge"] = "green"
                else:
                    r["mail_status"] = f"🟡 Vergi Talebi ({time_disp})"
                    r["mail_badge"] = "yellow"
                r["mail_date"] = found_tax_mail.get("sent_on", "")
                r["mail_to"] = found_tax_mail.get("to", "")
                r["mail_attachments"] = found_tax_mail.get("attachments", [])
                r["mail_subject"] = found_tax_mail.get("subject", "")
            else:
                if r.get("kapanis"):
                    r["mail_status"] = "🟢 Dosya Kapandı"
                    r["mail_badge"] = "grey"
                    r["is_tax_pending"] = False
                elif r.get("is_tax_pending"):
                    r["mail_status"] = "🔴 Vergi Maili Bekliyor"
                    r["mail_badge"] = "red"
                elif r.get("stage") == "2_ORDINO_TAREKS":
                    r["mail_status"] = "⏳ Tareks/Ordino Aşamasında"
                    r["mail_badge"] = "grey"
                else:
                    r["mail_status"] = "⏳ Hazırlık Aşamasında"
                    r["mail_badge"] = "grey"

                r["mail_date"] = ""
                r["mail_to"] = ""
                r["mail_attachments"] = []
                r["mail_subject"] = ""

        self.records = records
        self.is_loading = False

        # Arka planda web/mobil takip paneli için Supabase'i otomatik güncelle
        threading.Thread(target=self._push_to_supabase_async, daemon=True).start()

    def _push_to_supabase_async(self):
        """Tüm tescil ve Hankook Ref kayıtlarını arka planda sessizce Supabase'e senkronize eder."""
        try:
            from tools.supabase_sync_manager import get_supabase_manager
            sm = get_supabase_manager()
            if not sm:
                return

            active_files = [r for r in self.records if r.get('stage') != '5_KAPANDI']
            if not active_files:
                return

            from tools.dogruer_master_suite.engine.excel_read_guard import should_skip_hankook_prune
            prune = not should_skip_hankook_prune(
                getattr(self, "excel_read_ok", True),
                len(self.records),
                getattr(self, "_last_good_excel_count", 0),
            )
            sm.sync_hankook_board(active_files, prune_missing=prune)
        except Exception as e:
            print(f"[MasterDataEngine] Supabase push hatası: {e}")


# =============================================================================
# 2. ANA SUITE KULLANICI ARAYÜZÜ (MASTER GUI)
# =============================================================================
