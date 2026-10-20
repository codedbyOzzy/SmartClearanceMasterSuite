# -*- coding: utf-8 -*-
"""
takvim.py — Anasayfadaki takvim widget'ının ay görünümünü (hafta/gün
ızgarası) hazırlar. Sunucu tarafında render edilir (yeni bir JS/AJAX
katmanı YOK) — ay değiştirme, gün seçme hepsi normal GET linkleri
(`?takvim_yil=&takvim_ay=&takvim_gun=`), pjax zaten bunu sorunsuz
yönetir (bkz. static/pjax.js).
"""
import calendar as _calendar
from datetime import date

from app import storage_takvim

AY_ADLARI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
GUN_KISALTMALARI = ["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz"]


def ay_gorunumu(yil: int, ay: int, secili_gun: int, kullanici_isim: str) -> dict:
    """secili_gun: takvimde "seçili" gösterilecek ve not ekleme formunun
    varsayılan tarihi olacak gün (genelde bugün, kullanıcı bir güne
    tıklarsa o gün)."""
    bugun = date.today()
    notlar_ay = storage_takvim.notlar_ay_icin(yil, ay, kullanici_isim)

    haftalar = []
    for hafta in _calendar.Calendar(firstweekday=0).monthdayscalendar(yil, ay):
        satir = []
        for gun in hafta:
            if gun == 0:
                satir.append(None)
                continue
            tarih_iso = f"{yil:04d}-{ay:02d}-{gun:02d}"
            satir.append({
                "gun": gun,
                "tarih_iso": tarih_iso,
                "notlar": notlar_ay.get(tarih_iso, []),
                "bugun_mu": date(yil, ay, gun) == bugun,
                "secili_mi": gun == secili_gun,
            })
        haftalar.append(satir)

    onceki_ay, onceki_yil = (ay - 1, yil) if ay > 1 else (12, yil - 1)
    sonraki_ay, sonraki_yil = (ay + 1, yil) if ay < 12 else (1, yil + 1)
    secili_tarih_iso = f"{yil:04d}-{ay:02d}-{secili_gun:02d}"

    return {
        "yil": yil,
        "ay": ay,
        "ay_adi": AY_ADLARI[ay - 1],
        "gun_kisaltmalari": GUN_KISALTMALARI,
        "haftalar": haftalar,
        "onceki_ay": onceki_ay, "onceki_yil": onceki_yil,
        "sonraki_ay": sonraki_ay, "sonraki_yil": sonraki_yil,
        "bugun_yil": bugun.year, "bugun_ay": bugun.month,
        "secili_tarih_iso": secili_tarih_iso,
        "secili_gun_notlari": notlar_ay.get(secili_tarih_iso, []),
    }
