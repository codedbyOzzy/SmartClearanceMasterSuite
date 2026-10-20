# -*- coding: utf-8 -*-
"""
outlook_memory_guard.py — Outlook COM Nesne Bellek Yalıtımı ve Güvenlik Yöneticisi
Amaç:
- win32com.client çağrılarının thread içinde güvenle (CoInitialize / CoUninitialize) çalışmasını sağlamak.
- COM referanslarını açık bırakmayarak OUTLOOK.EXE işlemlerinin kilitlenmesini veya bellek sızıntısını engellemek.
- Hata durumunda UI thread'inin kilitlenmesini önlemek.
"""
import os
import gc
import sys
import time
import contextlib

_cur_file = os.path.abspath(__file__)
_root_dir = os.path.abspath(os.path.join(os.path.dirname(_cur_file), "..", ".."))

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

try:
    import pythoncom
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    pythoncom = None
    win32com = None
    HAS_WIN32COM = False

_OUTLOOK_PROGIDS = (
    "Outlook.Application",
    "Outlook.Application.16",
    "Outlook.Application.15",
)
_outlook_fail_until = 0.0
_outlook_fail_logged = False


def get_outlook_application():
    """Klasik masaüstü Outlook COM nesnesini açar. Yeni Outlook COM vermez."""
    global _outlook_fail_until, _outlook_fail_logged
    if not HAS_WIN32COM:
        return None
    now = time.time()
    if now < _outlook_fail_until:
        return None
    last_err = None
    for progid in _OUTLOOK_PROGIDS:
        try:
            return win32com.client.Dispatch(progid)
        except Exception as e:
            last_err = e
    try:
        return win32com.client.GetObject(Class="Outlook.Application")
    except Exception as e:
        last_err = e
    _outlook_fail_until = now + 300
    if not _outlook_fail_logged:
        _outlook_fail_logged = True
        print(
            "Outlook Motor Hatası: Klasik masaüstü Outlook COM kaydı bulunamadı "
            f"({last_err}). Yeni Outlook (Store / Microsoft 365) otomasyona açılmaz. "
            "Klasik Outlook kurulu ve açık olmalı. Mail tarama 5 dakika atlanacak."
        )
    return None


@contextlib.contextmanager
def safe_com_scope():
    """
    COM işlemlerini güvenli bir scope içinde çalıştırır.
    İşlem sonunda pythoncom.CoUninitialize() ve gc.collect() çağrılır.
    """
    if not HAS_WIN32COM:
        yield None
        return

    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()
        gc.collect()


def safe_get_sent_folder_count():
    """
    Outlook Giden Kutusu (Sent Items - Folder 5) öğe sayısını bellek sızıntısı yapmadan okur.
    Hata alırsa veya Outlook açık değilse None döner.
    """
    if not HAS_WIN32COM:
        return None

    with safe_com_scope():
        outlook = None
        namespace = None
        sent_folder = None
        items = None
        try:
            outlook = get_outlook_application()
            if not outlook:
                return None
            namespace = outlook.GetNamespace("MAPI")
            sent_folder = namespace.GetDefaultFolder(5)
            items = sent_folder.Items
            return items.Count
        except Exception:
            return None
        finally:
            del items
            del sent_folder
            del namespace
            del outlook


def safe_open_mail_by_entry_id(entry_id):
    """
    Belirli bir EntryID'ye sahip maili güvenle açar ve ekranda gösterir.
    """
    if not HAS_WIN32COM or not entry_id:
        return False

    with safe_com_scope():
        outlook = None
        namespace = None
        item = None
        try:
            outlook = get_outlook_application()
            if not outlook:
                return False
            namespace = outlook.GetNamespace("MAPI")
            item = namespace.GetItemFromID(entry_id)
            if item:
                item.Display(False)
                return True
            return False
        except Exception:
            return False
        finally:
            del item
            del namespace
            del outlook


def safe_create_mail_draft(to_recipients, subject, html_body, attachments=None, display=True):
    """
    Outlook üzerinden güvenli bir şekilde mail taslağı oluşturur ve ekranda açar.
    attachments: Liste halinde dosya yolları
    """
    if not HAS_WIN32COM:
        return False

    with safe_com_scope():
        outlook = None
        mail = None
        try:
            outlook = get_outlook_application()
            if not outlook:
                return False
            mail = outlook.CreateItem(0)  # 0 = olMailItem
            if to_recipients:
                mail.To = to_recipients
            mail.Subject = subject
            mail.HTMLBody = html_body

            if attachments:
                for att in attachments:
                    if os.path.exists(att):
                        mail.Attachments.Add(att)

            if display:
                mail.Display(False)
            return True
        except Exception as e:
            print("Safe Create Mail Draft Error:", e)
            return False
        finally:
            del mail
            del outlook
