# -*- coding: utf-8 -*-
"""
benim_masam.py — Anasayfa'daki "Bugün Masanda" bölümü için kişisel iş
kuyruğu. Hiçbir yeni veri toplamıyor — notlar/talepler/risklerden, giriş
yapmış kullanıcının İSMİNE göre süzerek türetiyor.

Kişi eşleştirme İSİM üzerinden yapılır (kullanıcı id'si değil) çünkü
notlar/talepler zaten yazan/kabul eden İSMİ saklıyor (3 kişilik ekipte
isim çakışması pratik bir sorun değil — kimlik sistemi de zaten bu
varsayımla "hafif" tasarlandı, bkz. storage_kullanici.py docstring'i).
"""
from datetime import date

from app import storage_takip
from app import storage_takip_notlar
from app import storage_talepler
from app import storage_takvim
from tools.smart_clearance_engine.domain import risk_analizi

# Anasayfada her listeden en fazla kaç satır gösterilir (gerisi sayıyla
# özetlenir) — sabah tek bakışta okunabilirlik için.
MAX_SATIR = 5

# Özet "Güncel Akış" şeridinde en fazla kaç satır gösterilir — bu, alttaki
# detaylı listelerin YERİNE değil, ÜSTÜNE eklenen kısa bir önizleme.
MAX_AKIS_SATIR = 4


def masa_verisi(kullanici_isim: str) -> dict:
    """Anasayfa'nın "Bugün Masanda" bölümünün ihtiyaç duyduğu her şeyi
    tek sözlükte toplar. kullanici_isim boşsa çağrılmamalı (bölüm sadece
    ismini girmiş kullanıcılara gösterilir)."""
    bugunku_takvim_notlari = storage_takvim.notlar_tarih_icin(date.today().isoformat(), kullanici_isim)

    acik_sorular = storage_takip_notlar.acik_sorular_detayli()
    cevabin_bekleniyor = [s for s in acik_sorular if s["yazan"] != kullanici_isim]
    cevap_bekliyorsun = [s for s in acik_sorular if s["yazan"] == kullanici_isim]

    acik_talepler = storage_talepler.talepler_listele(durum="acik")
    ustlendiklerin = [t for t in acik_talepler
                      if t["durum"] == "kabul_edildi" and t["kabul_eden_isim"] == kullanici_isim]
    sahipsiz_talepler = [t for t in acik_talepler if t["durum"] == "acik"]

    # Risk taraması: sadece açık (kapanmamış) dosyalar üzerinde. Riskler
    # kişiye atanamaz (sistemde dosya sahipliği yok) — herkese aynı görünür.
    riskli_dosyalar = []
    orta_risk_sayisi = 0
    eta_yaklasanlar = []
    
    from datetime import datetime
    bugun = date.today()

    for kayit in storage_takip.guncel_durumlar(acik="acik"):
        riskler = risk_analizi.riskleri_bul(kayit)
        if not riskler:
            pass
        else:
            seviye = risk_analizi.en_yuksek_seviye(riskler)
            if seviye == "yuksek":
                riskli_dosyalar.append({
                    "referans_no": kayit.get("referans_no") or "",
                    "dosya_no": kayit.get("dosya_no") or "",
                    "riskler": riskler,
                    "en_gec_gun": max(r["gun"] for r in riskler),
                })
            else:
                orta_risk_sayisi += 1

        # ETA Yaklasanlar hesaplama
        eta_str = str(kayit.get("eta") or "").strip()
        if eta_str:
            try:
                if "-" in eta_str:
                    eta_dt = datetime.strptime(eta_str[:10], "%Y-%m-%d").date()
                else:
                    eta_dt = datetime.strptime(eta_str[:10], "%d.%m.%Y").date()
                fark_gun = (eta_dt - bugun).days
                if 0 <= fark_gun <= 7:
                    eta_yaklasanlar.append({
                        "referans_no": kayit.get("referans_no") or "",
                        "dosya_no": kayit.get("dosya_no") or "",
                        "acenta": kayit.get("acenta") or "",
                        "liman": kayit.get("liman") or "",
                        "gemi": kayit.get("gemi") or "",
                        "konteyner": kayit.get("konteyner") or "",
                        "konsimento": kayit.get("konsimento") or "",
                        "eta": eta_dt.strftime("%d.%m.%Y"),
                        "fark_gun": fark_gun
                    })
            except Exception:
                pass

    # En uzun süredir bekleyen en üstte — sabah önce en yanan işi görsün.
    riskli_dosyalar.sort(key=lambda r: r["en_gec_gun"], reverse=True)
    eta_yaklasanlar.sort(key=lambda x: x["fark_gun"])

    toplam_is = (len(cevabin_bekleniyor) + len(ustlendiklerin)
                 + len(sahipsiz_talepler) + len(riskli_dosyalar) + len(bugunku_takvim_notlari))

    # Üstteki özet şeridin "Güncel Akış" kısmı: zaman damgası olan
    # kategorileri (soru/talep/hatırlatıcı) TEK bir zaman sırasına göre
    # karıştırır. Riskli dosyalar dahil edilmez — onların "ne zaman
    # oluştu"su yok, sadece "kaç gündür açık"ı var (en_gec_gun), yanlış
    # bir an izlenimi vermemek için akışa değil sadece stat karta girer.
    akis = []
    for s in cevabin_bekleniyor:
        akis.append({"tur": "soru", "zaman": s["zaman"],
                     "metin": f"{s['yazan']} sordu: {s['metin'][:70]}",
                     "link": f"/takip-raporu/{s['referans_no']}#notlar"})
    for s in cevap_bekliyorsun:
        akis.append({"tur": "soru_bekliyorsun", "zaman": s["zaman"],
                     "metin": f"Sorduğun soru hâlâ cevapsız: {s['metin'][:70]}",
                     "link": f"/takip-raporu/{s['referans_no']}#notlar"})
    for t in ustlendiklerin:
        akis.append({"tur": "ustlenildi", "zaman": t["olusturma_zamani"],
                     "metin": f"Talep #{t['id']} · Üstlendin: {', '.join(t['po_numaralari'])}",
                     "link": f"/talepler/{t['id']}"})
    for t in sahipsiz_talepler:
        akis.append({"tur": "sahipsiz", "zaman": t["olusturma_zamani"],
                     "metin": f"{t['olusturan_isim']} açtı: {', '.join(t['po_numaralari'])} · Sahiplenme bekliyor",
                     "link": f"/talepler/{t['id']}"})
    for n in bugunku_takvim_notlari:
        akis.append({"tur": "takvim", "zaman": n["olusturma_zamani"],
                     "metin": f"Bugün için not: {n['metin'][:70]}",
                     "link": "/#takvim"})
    akis.sort(key=lambda a: a["zaman"], reverse=True)

    return {
        "guncel_akis": akis[:MAX_AKIS_SATIR],
        "bekleyen_yanit_toplam": len(cevabin_bekleniyor) + len(cevap_bekliyorsun),
        "bugunku_takvim_notlari": bugunku_takvim_notlari,
        "cevabin_bekleniyor": cevabin_bekleniyor[:MAX_SATIR],
        "cevabin_bekleniyor_toplam": len(cevabin_bekleniyor),
        "cevap_bekliyorsun": cevap_bekliyorsun[:MAX_SATIR],
        "cevap_bekliyorsun_toplam": len(cevap_bekliyorsun),
        "ustlendiklerin": ustlendiklerin[:MAX_SATIR],
        "ustlendiklerin_toplam": len(ustlendiklerin),
        "sahipsiz_talepler": sahipsiz_talepler[:MAX_SATIR],
        "sahipsiz_talepler_toplam": len(sahipsiz_talepler),
        "riskli_dosyalar": riskli_dosyalar[:MAX_SATIR],
        "riskli_dosyalar_toplam": len(riskli_dosyalar),
        "orta_risk_sayisi": orta_risk_sayisi,
        "eta_yaklasanlar": eta_yaklasanlar[:MAX_SATIR],
        "eta_yaklasanlar_toplam": len(eta_yaklasanlar),
        "acilmamis_sayisi": storage_takip.acilmamis_dosya_sayisi(),
        "toplam_is": toplam_is,
    }
