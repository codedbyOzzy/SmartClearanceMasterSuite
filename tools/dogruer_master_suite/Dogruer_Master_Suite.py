# -*- coding: utf-8 -*-
"""
==============================================================================
🏛️ DOĞRUER SMARTCLEARANCE MASTER SUITE v4.0 (Modüler Mimari)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
==============================================================================
"""
import sys
import os
import atexit

# Root directory'yi sys.path'e ekle
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import tkinter as tk
from tools.dogruer_master_suite.app import DogruerMasterSuiteApp
from tools.dogruer_master_suite.auth_gate import resolve_startup_user
from tools.dogruer_master_suite.single_instance import acquire_single_instance, release_single_instance
from tools.dogruer_master_suite.engine import (
    MasterDataEngine, load_app_config, save_app_config, DEFAULT_CONFIG,
    DEFAULT_EXCEL_PATH, QNB_PORTAL_URL, DOGRUER_ONLINE_URL
)

try:
    from tools.auth_manager import get_auth_manager
    from tools.dogruer_master_suite.login_dialog import prompt_login_dialog, LoginDialog
except Exception:
    get_auth_manager = None
    prompt_login_dialog = None
    LoginDialog = None


def main():
    user = resolve_startup_user(prompt_login_dialog, get_auth_manager)
    if not user:
        print("Kimlik doğrulama başarısız veya iptal edildi. Uygulama açılmadı.")
        sys.exit(1)

    if not acquire_single_instance():
        msg = "MasterSuite zaten çalışıyor. İkinci kopya açılmadı."
        print(msg)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "Doğruer MasterSuite", 0x30)
        except Exception:
            pass
        sys.exit(1)
    atexit.register(release_single_instance)

    root = tk.Tk()
    app = DogruerMasterSuiteApp(root, current_user=user)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        code = e.code
        if code not in (0, None):
            raise
    except Exception:
        import traceback
        traceback.print_exc()
        try:
            with open("crash_log.txt", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        sys.exit(1)
