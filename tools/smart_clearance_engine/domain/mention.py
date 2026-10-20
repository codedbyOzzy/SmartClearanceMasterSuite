# -*- coding: utf-8 -*-
"""
mention.py — Not metinlerinde "@İsim" bahsetmelerini bulur ve güvenli
şekilde (XSS'e karşı escape ederek) vurgular.
"""
import re

import markupsafe

_BAHSETME_DESENI = re.compile(r"@(\w+)")


def bahsedilenleri_bul(metin: str, kullanicilar: list) -> list:
    """metin içinde '@İsim' şeklinde geçen ve bilinen kullanıcı isimleriyle
    (büyük/küçük harf duyarsız) eşleşen kullanıcı kayıtlarını döner."""
    if not metin:
        return []
    adaylar = {m.lower() for m in _BAHSETME_DESENI.findall(metin)}
    if not adaylar:
        return []
    return [k for k in kullanicilar if k["isim"].lower() in adaylar]


def vurgula(metin: str) -> markupsafe.Markup:
    """'@İsim' geçen yerleri vurgulu bir span içine alır; geri kalan TÜM
    metni HTML-escape eder (kullanıcı girdisinde XSS riskine karşı)."""
    # re.split capture group ile "duz metin, isim, duz metin, isim, ..."
    # seklinde bir liste doner; ciftler halinde isliyoruz.
    parcalar_ham = _BAHSETME_DESENI.split(metin or "")
    sonuc = []
    i = 0
    while i < len(parcalar_ham):
        sonuc.append(str(markupsafe.escape(parcalar_ham[i])))
        if i + 1 < len(parcalar_ham):
            sonuc.append(f'<span class="mention-etiket">@{markupsafe.escape(parcalar_ham[i + 1])}</span>')
        i += 2
    return markupsafe.Markup("".join(sonuc))
