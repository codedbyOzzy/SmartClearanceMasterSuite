# -*- coding: utf-8 -*-
"""
arama.py — Sidebar'daki genel arama kutusu (PO/Dosya No, site geneli).
İş Takip Raporu'ndaki ve Talepler'deki kayıtları TEK yerden arar; zaten
var olan `storage_takip.guncel_durumlar()` / `storage_talepler.talepler_listele()`
arama filtrelerini (referans_no/dosya_no/bayi/konteyner, po_numaralari)
yeniden kullanır — ayrı bir arama motoru YAZILMADI.

Sorgu bir kayda BİREBİR (referans_no/dosya_no ya da bir talebin PO
listesindeki bir numara) uyuyorsa ve toplamda TEK aday varsa, router bu
bilgiyle (`tek_sonuc`) sonuç listesi göstermek yerine doğrudan o kaydın
detay sayfasına yönlendirir — "PO yaz, direkt duruma git" hissi için.
"""
import re

from app import storage_takip
from app import storage_talepler
from app import storage_islem_kayitlari
from tools.smart_clearance_engine.domain import risk_analizi


def ara(sorgu: str) -> dict:
    sorgu = (sorgu or "").strip()
    if not sorgu:
        return {"sorgu": "", "takip": [], "talepler": [], "tek_sonuc": None}

    takip_sonuclari = storage_takip.guncel_durumlar(arama=sorgu)
    talep_sonuclari = storage_talepler.talepler_listele(arama=sorgu)

    return {
        "sorgu": sorgu,
        "takip": takip_sonuclari,
        "talepler": talep_sonuclari,
        "tek_sonuc": _tek_kesin_eslesme(sorgu, takip_sonuclari, talep_sonuclari),
    }


def _tek_kesin_eslesme(sorgu: str, takip_sonuclari: list, talep_sonuclari: list):
    """Toplamda TEK bir birebir (büyük/küçük harf duyarsız) eşleşme varsa
    onu döner ({"tur": "takip"|"talep", "hedef": ...}), yoksa None —
    birden fazla kesin eşleşme (örn. aynı numara hem takipte hem talepte)
    de belirsizlik sayılır, kullanıcı listeden seçer."""
    sorgu_l = sorgu.lower()
    adaylar = []

    for kayit in takip_sonuclari:
        if (kayit.get("referans_no") or "").strip().lower() == sorgu_l:
            adaylar.append({"tur": "takip", "hedef": kayit["referans_no"]})
        elif (kayit.get("dosya_no") or "").strip().lower() == sorgu_l:
            adaylar.append({"tur": "takip", "hedef": kayit["referans_no"]})

    for talep in talep_sonuclari:
        if any((po or "").strip().lower() == sorgu_l for po in talep.get("po_numaralari", [])):
            adaylar.append({"tur": "talep", "hedef": talep["id"]})

    if len(adaylar) == 1:
        return adaylar[0]
    return None


def toplu_ara(metin: str) -> dict:
    """Toplu Arama: bir seferde 20-30+ PO yapıştırılıp hepsinin GÜNCEL
    durumu tek sayfada görülebilsin diye — sidebar'daki tek-sorgulu
    canlı aramadan FARKLI bir ihtiyaç (o an "hangi kayıtlar bu metne
    benziyor" sorusunu cevaplıyor, bu ise "bu KESİN listedeki her PO'nun
    durumu ne" sorusunu). Virgül/satır/boşluk/tab ile ayrılmış PO'ları
    ayıklar, aynı PO birden fazla kez yazılmışsa TEKİLLEŞTİRİR (sırayı
    koruyarak), her biri için İş Takip Raporu'ndaki BİREBİR durumu +
    ilgili Talepler/İşlem Kayıtları sayısını + varsa risk uyarısını
    tek satırda toplar."""
    po_listesi_ham = [p for p in re.split(r"[,\n\r\t ]+", metin or "") if p.strip()]
    gorulen = set()
    po_listesi = []
    for po in po_listesi_ham:
        anahtar = po.strip().lower()
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        po_listesi.append(po.strip())

    durum_haritasi = storage_takip.coklu_durum(po_listesi)

    sonuclar = []
    for po in po_listesi:
        durum = durum_haritasi.get(po)
        riskler = risk_analizi.riskleri_bul(durum) if durum else []
        sonuclar.append({
            "po": po,
            "bulundu": durum is not None,
            "durum": durum,
            "risk_seviyesi": risk_analizi.en_yuksek_seviye(riskler),
            "talep_sayisi": len(storage_talepler.talepler_po_icin(po)),
            "kayit_sayisi": len(storage_islem_kayitlari.kayitlar_po_icin(po)),
        })

    return {
        "metin": metin or "",
        "sonuclar": sonuclar,
        "toplam": len(sonuclar),
        "bulunan": sum(1 for s in sonuclar if s["bulundu"]),
        "bulunmayan": sum(1 for s in sonuclar if not s["bulundu"]),
    }
