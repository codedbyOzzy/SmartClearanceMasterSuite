# -*- coding: utf-8 -*-
"""
dashboard.py — Performans Paneli için istatistik toplama katmanı.

Hiçbir şeye YAZMAZ — sadece mevcut storage fonksiyonlarını reuse ederek
okur ve ekrana sunulmaya hazır istatistikler üretir. Yeni SQL sorgusu
içermez; tüm filtreleme/hesaplama Python tarafında yapılır (veri miktarı
3 kişilik bir ofis için bu yaklaşım için çok küçük).

Katman sırası (projenin mimari kuralına uygun):
  storage_* (ham veri) → domain/dashboard.py (hesaplama) → routers/pages.py (HTTP)
"""
from datetime import date

from app import storage_takip
from app import storage_talepler
from app import storage_islem_kayitlari
from app import storage_kullanici
from tools.smart_clearance_engine.domain import risk_analizi


def genel_istatistikler() -> dict:
    """İş Takip Raporu'ndaki tüm kayıtların anlık sayım özeti."""
    tum_dosyalar = storage_takip.guncel_durumlar()
    acik = [d for d in tum_dosyalar if not (d.get("kapanis_tarihi") or "").strip()]
    kapanmis = [d for d in tum_dosyalar if (d.get("kapanis_tarihi") or "").strip()]
    acilmamis = [d for d in tum_dosyalar if not (d.get("dosya_no") or "").strip()]

    return {
        "toplam": len(tum_dosyalar),
        "acik": len(acik),
        "kapanmis": len(kapanmis),
        "acilmamis": len(acilmamis),          # Dosya No'su boş: henüz gümrük dosyası açılmamış
    }


def risk_ozeti() -> dict:
    """Açık dosyalardaki risk dağılımı (Demuraj / TAREKS / Kırmızı Hat).

    Kapalı dosyalar risk_analizi.riskleri_bul() tarafından zaten atlanır,
    burada da açık filtresi ekleniyor — tutarlılık için.
    """
    acik_dosyalar = storage_takip.guncel_durumlar(acik="acik")

    demuraj_yuksek = 0
    demuraj_orta = 0
    tareks_yuksek = 0
    tareks_orta = 0
    kirmizi_hat = 0
    riskli_toplam = set()    # Birden fazla risk türü olan dosyayı bir kez say

    for kayit in acik_dosyalar:
        riskler = risk_analizi.riskleri_bul(kayit)
        if not riskler:
            continue
        riskli_toplam.add(kayit.get("referans_no"))
        for r in riskler:
            if r["tur"] == "demuraj":
                if r["seviye"] == "yuksek":
                    demuraj_yuksek += 1
                else:
                    demuraj_orta += 1
            elif r["tur"] == "tareks":
                if r["seviye"] == "yuksek":
                    tareks_yuksek += 1
                else:
                    tareks_orta += 1
            elif r["tur"] == "kirmizi_hat":
                kirmizi_hat += 1

    return {
        "riskli_toplam": len(riskli_toplam),
        "acik_toplam": len(acik_dosyalar),
        "demuraj_yuksek": demuraj_yuksek,
        "demuraj_orta": demuraj_orta,
        "tareks_yuksek": tareks_yuksek,
        "tareks_orta": tareks_orta,
        "kirmizi_hat": kirmizi_hat,
    }


def aylik_tescil_trendi() -> list:
    """Son 6 aya ait 'Tescil Oldu' kayıtlarını ay ay gruplar.

    Döner: [{"etiket": "Oca", "yil": 2026, "ay": 1, "sayi": 12}, ...]
    En eski ay başta, en yeni ay sonda (grafik soldan sağa okunacak şekilde).
    """
    AY_ETIKET = {
        1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
        7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara",
    }

    # Son 6 ayın (yıl, ay) listesini üret
    bugun = date.today()
    aylar = []
    yil, ay = bugun.year, bugun.month
    for _ in range(6):
        aylar.insert(0, (yil, ay))
        ay -= 1
        if ay == 0:
            ay = 12
            yil -= 1

    # Sadece "tescil_oldu" kayıtlarını çek
    tesciller = storage_islem_kayitlari.kayitlar_listele(tur="tescil_oldu")

    # (yil, ay) → sayi
    sayac = {(y, m): 0 for y, m in aylar}
    for k in tesciller:
        zaman_str = k.get("zaman") or ""
        try:
            # ISO format: "2026-07-21T14:30:00"
            yil_k = int(zaman_str[:4])
            ay_k = int(zaman_str[5:7])
            if (yil_k, ay_k) in sayac:
                sayac[(yil_k, ay_k)] += 1
        except (ValueError, IndexError):
            continue

    return [
        {"etiket": AY_ETIKET[m], "yil": y, "ay": m, "sayi": sayac[(y, m)]}
        for y, m in aylar
    ]


def ekip_is_yuku() -> list:
    """Sistemde kayıtlı tüm kullanıcılar için iş yükü özeti.

    Her kullanıcı için: kaç adet açık talep üstlenmiş, kaç adet açık
    soruya cevap bekliyor. Böylece kimin masası dolu, kimin boş görünür.

    Döner: [{"isim": "Ozan", "ustlenilen_talep": 2, "bekleyen_soru": 1}, ...]

    NOT: Aynı isimde birden fazla cookie kaydı olabilir (farklı tarayıcı
    veya tekrar giriş). İsme göre tekilletin,; en son görülen kaydın
    son_gorulme değeri büyük olan esas alınır.
    """
    from app import storage_takip_notlar

    tum_kullanicilar = storage_kullanici.tum_kullanicilar()

    # İsme göre tekilletin — aynı isimde birden fazla varsa en son
    # görülenı tut (son_gorulme tarihi büyük olan kazanır).
    tekil: dict = {}
    for k in tum_kullanicilar:
        isim = (k.get("isim") or "").strip()
        if not isim:
            continue
        isim_l = isim.lower()
        mevcut = tekil.get(isim_l)
        if mevcut is None or (k.get("son_gorulme") or "") > (mevcut.get("son_gorulme") or ""):
            tekil[isim_l] = k

    kullanicilar = list(tekil.values())
    acik_talepler = storage_talepler.talepler_listele(durum="kabul_edildi")
    acik_sorular = storage_takip_notlar.acik_sorular_detayli()

    sonuc = []
    for k in kullanicilar:
        isim = k["isim"]
        ustlenilen = sum(
            1 for t in acik_talepler
            if t.get("kabul_eden_isim") == isim
        )
        # "Cevabın bekleniyor": başkasının yazdığı, henüz cevaplanmamış soru
        bekleyen = sum(
            1 for s in acik_sorular
            if s.get("yazan") != isim
        )
        sonuc.append({
            "isim": isim,
            "ustlenilen_talep": ustlenilen,
            "bekleyen_soru": bekleyen,
            "son_gorulme": k.get("son_gorulme") or "",
        })

    # Toplam yüke göre azalan sırada (en yoğun kişi üstte)
    sonuc.sort(key=lambda x: x["ustlenilen_talep"] + x["bekleyen_soru"], reverse=True)
    return sonuc


def muhasebe_ozeti() -> dict:
    """Performans paneli için muhasebeye gönderilen dosya oranını hesaplar."""
    from app import storage_muhasebe
    from app import storage_takip

    storage_muhasebe.init_db()
    kayitlar = storage_takip.guncel_durumlar(dosya_durumu="acilmis")
    gonderilen_set = storage_muhasebe.gonderilen_dosya_no_seti()

    toplam = len(kayitlar)
    eslesen = sum(
        1 for k in kayitlar
        if (k.get("dosya_no") or "").strip().upper() in gonderilen_set
    )
    bekleyen = toplam - eslesen
    yuzde = round((eslesen / toplam) * 100) if toplam > 0 else 0

    return {
        "toplam": toplam,
        "eslesen": eslesen,
        "bekleyen": bekleyen,
        "yuzde": yuzde,
    }


def hat_ve_gumruk_ozeti() -> dict:
    """Gümrük Hat Kadranı (Sarı/Kırmızı/Yeşil oranları) & Sıcaklık Haritası (Gümrük Müdürlüğü yoğunlukları)."""
    from datetime import datetime
    tum_dosyalar = storage_takip.guncel_durumlar()
    toplam = len(tum_dosyalar)

    hatlar = {"YESIL": 0, "SARI": 0, "KIRMIZI": 0, "DIGER": 0}
    gumrukler = {}

    toplam_sure_gun = 0
    kapanmis_sayisi = 0

    for d in tum_dosyalar:
        hat = (d.get("hat_bilgisi") or "").strip().upper()
        if "YEŞİL" in hat or "YESIL" in hat:
            hatlar["YESIL"] += 1
        elif "SARI" in hat:
            hatlar["SARI"] += 1
        elif "KIRMIZI" in hat:
            hatlar["KIRMIZI"] += 1
        else:
            hatlar["DIGER"] += 1

        g = (d.get("gumruk") or "").strip()
        if not g:
            g = "BELİRTİLMEMİŞ"
        gumrukler[g] = gumrukler.get(g, 0) + 1

        tt = (d.get("tescil_tarihi") or "").strip()
        kt = (d.get("kapanis_tarihi") or "").strip()
        if tt and kt:
            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    dt1 = datetime.strptime(tt[:10], fmt)
                    dt2 = datetime.strptime(kt[:10], fmt)
                    fark = (dt2 - dt1).days
                    if 0 <= fark <= 180:
                        toplam_sure_gun += fark
                        kapanmis_sayisi += 1
                    break
                except ValueError:
                    continue

    yuzde_yesil = round((hatlar["YESIL"] / max(1, toplam)) * 100)
    yuzde_sari = round((hatlar["SARI"] / max(1, toplam)) * 100)
    yuzde_kirmizi = round((hatlar["KIRMIZI"] / max(1, toplam)) * 100)
    yuzde_diger = max(0, 100 - (yuzde_yesil + yuzde_sari + yuzde_kirmizi))

    ort_sure = round(toplam_sure_gun / max(1, kapanmis_sayisi), 1) if kapanmis_sayisi > 0 else 0

    gumruk_listesi = sorted(
        [{"ad": k, "sayi": v, "yuzde": round((v / max(1, toplam)) * 100)} for k, v in gumrukler.items()],
        key=lambda x: x["sayi"],
        reverse=True
    )[:6]

    return {
        "toplam": toplam,
        "yesil_yuzde": yuzde_yesil,
        "sari_yuzde": yuzde_sari,
        "kirmizi_yuzde": yuzde_kirmizi,
        "diger_yuzde": yuzde_diger,
        "yesil_sayi": hatlar["YESIL"],
        "sari_sayi": hatlar["SARI"],
        "kirmizi_sayi": hatlar["KIRMIZI"],
        "ort_sure": ort_sure,
        "gumruk_listesi": gumruk_listesi
    }
