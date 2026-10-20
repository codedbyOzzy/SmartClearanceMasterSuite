# -*- coding: utf-8 -*-
"""Giriş fail-open koruması — auth yoksa veya login hata verirse admin açılmaz."""


def resolve_startup_user(prompt_login_dialog, get_auth_manager):
    """
    Başarılı girişte kullanıcı dict, iptalde None.
    Auth yüklenemezse veya dialog patlarsa None (admin'e düşmez).
    """
    if prompt_login_dialog is None or get_auth_manager is None:
        return None
    try:
        user = prompt_login_dialog()
    except Exception:
        return None
    if not user or not isinstance(user, dict):
        return None
    if not user.get("username"):
        return None
    return user
