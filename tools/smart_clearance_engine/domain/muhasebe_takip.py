# -*- coding: utf-8 -*-
"""
muhasebe_takip.py — Muhasebe Takip panelinin eşleştirme mantığı.

Referans dosya listesi şefin İş Takip Raporu'ndan (storage_takip.py) TÜM
kayıtlar olarak okunur (kullanıcı onayladı — sadece açık dosyalar değil).
Dosya No'su boş olan kayıtlar (PO açıldı ama gümrük dosyası henüz
açılmamış) hariç tutulur.

Her eşleşen kayıt için `id` de döner — böylece tabloda hatalı işaretlenmiş
veya mükerrer kaydın silinmesi/düzenlenmesi sağlanır.
"""
import re

from app import storage_takip
from app import storage_muhasebe


def metinden_dosya_no_cikar(metin: str) -> list:
    """Textarea'ya alt alta/virgülle/boşlukla yapıştırılmış dosya no'ları
    ayrıştırır. Sıra korunur, boş satırlar ve tekrarlar atlanır."""
    if not metin:
        return []
    parcalar = re.split(r"[\n\r,;]+", metin)
    gorulen = set()
    sonuc = []
    for parca in parcalar:
        deger = parca.strip()
        if not deger or deger in gorulen:
            continue
        gorulen.add(deger)
        sonuc.append(deger)
    return sonuc


def _normalize(dosya_no: str) -> str:
    return (dosya_no or "").strip().upper()


def muhasebe_verisi() -> dict:
    """Panelin ihtiyaç duyduğu her şeyi tek sözlükte toplar: satırlar
    (eşleşme durumuyla işaretlenmiş) + özet sayılar + textarea'yı önceden
    doldurmak için mevcut gönderilen listesi."""
    kayitlar = storage_takip.guncel_durumlar()
    harita = storage_muhasebe.gonderilen_sozluk_haritasi()

    satirlar = []
    eslesen = 0
    for i, k in enumerate(kayitlar, start=1):
        dosya_no = (k.get("dosya_no") or "").strip()
        norm_no = _normalize(dosya_no)
        gonderildi = bool(norm_no and norm_no in harita)
        kayit_id = harita.get(norm_no)
        if gonderildi:
            eslesen += 1
        satirlar.append({
            "id": kayit_id,
            "sira_no": i,
            "liman": k.get("gumruk") or "",
            "dosya_no": dosya_no,
            "po_no": k.get("referans_no") or "",
            "tasiyici": k.get("acenta") or "",
            "konsimento_no": k.get("konsimento") or "",
            "gonderildi": gonderildi,
            "eslesme_durumu": "Muhasebeye Gönderildi" if gonderildi else "Henüz Gönderilmedi",
            "aciklama": "Tamamlandı" if gonderildi else "Fatura bekliyor",
        })

    toplam = len(satirlar)
    bosta_kalan = toplam - eslesen

    return {
        "satirlar": satirlar,
        "toplam": toplam,
        "eslesen": eslesen,
        "bosta_kalan": bosta_kalan,
        "fatura_bekleyenler": bosta_kalan,
        "gonderilen_liste_metni": "\n".join(storage_muhasebe.gonderilen_liste()),
    }
