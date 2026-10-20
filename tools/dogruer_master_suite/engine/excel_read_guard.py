# -*- coding: utf-8 -*-
"""Excel okuma hatalarını sınıflandır — kilit vs diğer."""


def is_excel_lock_error(exc) -> bool:
    if isinstance(exc, PermissionError):
        return True
    s = str(exc or "").lower()
    needles = (
        "permission denied",
        "being used by another process",
        "winerror 32",
        "error 32",
        "erişim reddedildi",
        "kullanımda",
    )
    return any(n in s for n in needles)


def should_skip_hankook_prune(excel_read_ok: bool, record_count: int, last_good_count: int) -> bool:
    """Eksik/kilitli okumada uzak panodan satır silme."""
    if not excel_read_ok:
        return True
    if last_good_count >= 10 and record_count < int(last_good_count * 0.5):
        return True
    if record_count <= 0:
        return True
    return False
