# -*- coding: utf-8 -*-
"""
risk_analizi.py — İş Takip Raporu'ndaki tarihlerden otomatik risk/gecikme
tespiti. Hiçbir yeni veri toplamıyor — sadece zaten sistemde olan
alanlardan (Varış/ETA, Liman Çıkış, Tareks tarihleri, Hat Bilgisi, Tescil)
türetiyor.

⚠️ EŞİK GÜN SAYILARI TAHMİNDİR — gerçek liman/hat sözleşmelerindeki serbest
depolama süreleri ve TAREKS ortalama sonuçlanma süresi bilinmediği için
makul varsayılan değerler kondu (bkz. AI_GELISTIRICI_NOTLARI.md). Kullanıcı
gerçek değerleri verirse burada güncellenmeli.
"""
import datetime as dt

# Eşikler artık araştırılmış gerçek verilere dayanıyor (bkz. AI_GELISTIRICI_NOTLARI.md):
# - Demuraj: Türkiye limanlarında standart serbest süre 7 gün, anlaşmalı uzatmalarda
#   14-21 gün (birden fazla bağımsız kaynak, 2026).
# - TAREKS: Kullanıcının kendi saha bilgisi ("en uzun 1 hafta, denetlemeye düşerse
#   2-3 hafta") + TSE/Ticaret Bakanlığı kaynaklarıyla doğrulandı — denetime
#   düşmeyen başvurular günler içinde, fiili denetime düşen başvurular 1-3
#   haftaya kadar sürebiliyor.
# - KIRMIZI hat: TAREKS'teki fiili denetimle aynı mantık (gümrükte fiziki
#   kontrol kuyruğu) — ayrı bir dış kaynak bulunamadığı için TAREKS ile aynı
#   eşik kullanıldı; gerçek veriyle farklı çıkarsa ayarlanmalı.
DEMURAJ_ORTA_GUN = 7
DEMURAJ_YUKSEK_GUN = 14
TAREKS_ORTA_GUN = 7
TAREKS_YUKSEK_GUN = 14
KIRMIZI_HAT_ORTA_GUN = 7
KIRMIZI_HAT_YUKSEK_GUN = 14

RISK_ETIKETLERI = {
    "demuraj": "Demuraj/Depolama Riski",
    "tareks": "TAREKS Gecikmesi",
    "kirmizi_hat": "KIRMIZI Hat Gecikmesi",
}


def _tarihi_ayristir(metin):
    if not metin:
        return None
    try:
        return dt.datetime.strptime(metin.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def riskleri_bul(kayit: dict, bugun=None) -> list:
    """Bir takip kaydı (guncel_durumlar()'dan gelen dict) için risk
    uyarılarını döner. Kapanmış (Kapanış Tarihi dolu) dosyalarda risk
    hesaplanmaz — iş zaten bitmiştir."""
    bugun = bugun or dt.date.today()
    riskler = []

    if _tarihi_ayristir(kayit.get("kapanis_tarihi")):
        return riskler

    varis = _tarihi_ayristir(kayit.get("varis_tarihi")) or _tarihi_ayristir(kayit.get("eta"))
    liman_cikis = _tarihi_ayristir(kayit.get("liman_cikis_tarihi"))
    if varis and not liman_cikis:
        gun = (bugun - varis).days
        if gun >= DEMURAJ_ORTA_GUN:
            riskler.append({
                "tur": "demuraj",
                "seviye": "yuksek" if gun >= DEMURAJ_YUKSEK_GUN else "orta",
                "mesaj": f"Konteyner limana varalı {gun} gün oldu, Liman Çıkış Tarihi hâlâ girilmemiş.",
                "gun": gun,
            })

    tareks_basvuru = _tarihi_ayristir(kayit.get("tareks_basvuru_tarihi"))
    tareks_sonuc = _tarihi_ayristir(kayit.get("tareks_sonuc_tarihi"))
    if tareks_basvuru and not tareks_sonuc:
        gun = (bugun - tareks_basvuru).days
        if gun >= TAREKS_ORTA_GUN:
            riskler.append({
                "tur": "tareks",
                "seviye": "yuksek" if gun >= TAREKS_YUKSEK_GUN else "orta",
                "mesaj": f"TAREKS başvurusu {gun} gündür sonuçlanmadı.",
                "gun": gun,
            })

    tescil = _tarihi_ayristir(kayit.get("tescil_tarihi"))
    if (kayit.get("hat_bilgisi") or "").strip().upper() == "KIRMIZI" and tescil:
        gun = (bugun - tescil).days
        if gun >= KIRMIZI_HAT_ORTA_GUN:
            riskler.append({
                "tur": "kirmizi_hat",
                "seviye": "yuksek" if gun >= KIRMIZI_HAT_YUKSEK_GUN else "orta",
                "mesaj": f"KIRMIZI hat — tescilden bu yana {gun} gündür kapanmadı.",
                "gun": gun,
            })

    return riskler


def en_yuksek_seviye(riskler: list) -> str:
    if any(r["seviye"] == "yuksek" for r in riskler):
        return "yuksek"
    if riskler:
        return "orta"
    return ""
