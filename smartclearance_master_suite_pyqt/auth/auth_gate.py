# -*- coding: utf-8 -*-
"""
🛡️ SmartClearance MasterSuite - Auth Gate (PyQt6)
Giriş doğrulaması ve oturum çözümleyici.
"""

def resolve_startup_user(prompt_login_dialog, get_auth_manager):
    """
    Başarılı girişte kullanıcı dict, iptalde None döndürür.
    Auth yüklenemezse veya diyalog kapatılırsa None döner.
    """
    if prompt_login_dialog is None or get_auth_manager is None:
        return None
    try:
        user = prompt_login_dialog()
    except Exception as e:
        print(f"Auth gate error: {e}")
        return None
    if not user or not isinstance(user, dict):
        return None
    if not user.get("username"):
        return None
    return user
