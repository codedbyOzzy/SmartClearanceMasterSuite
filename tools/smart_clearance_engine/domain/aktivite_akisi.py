# -*- coding: utf-8 -*-
"""
aktivite_akisi.py — Anasayfa'daki "Ekip Akışı" (Twitter tarzı feed) için
İş Takip Raporu notlarını VE Talepler'deki olay/dosyaları TEK bir zaman
sırasına göre birleştirir. İkisi ayrı SQLite dosyalarında olduğu için
(takip_raporu.db, talepler.db) birleştirme SQL'de değil, burada Python
tarafında yapılır.
"""
from app import storage_takip_notlar
from app import storage_talepler_notlar
from app import storage_konular

OLAY_ETIKETLERI = {
    "acildi": "yeni bir dosya oluşturma talebi açtı",
    "gorundu": "talebi gördü",
    "kabul_edildi": "talebi kabul etti",
    "kapatildi": "talebi kapattı",
}


def ekip_akisi(limit: int = 40, filtre: str = "hepsi"):
    """Tüm aktivite kaynaklarını birleştirerek tek bir zaman sırası oluşturur.

    filtre: "hepsi" | "notlar" | "talepler" | "konular"
    """
    ogeler = []
    fl = filtre.lower().strip()

    if fl in ("hepsi", "notlar"):
        for n in storage_takip_notlar.tum_notlar(limit=limit):
            ogeler.append({
                "tur": "not",
                "yazan": n["yazan"],
                "zaman": n["zaman"],
                "icerik": n["metin"],
                "soru_mu": bool(n["soru_mu"]),
                "referans_no": n["referans_no"],
                "link": f"/takip-raporu/{n['referans_no']}#notlar",
            })

    if fl in ("hepsi", "talepler"):
        olaylar, dosyalar, talep_notlari = storage_talepler_notlar.akis_ogeleri(limit=limit)
        for o in olaylar:
            ogeler.append({
                "tur": "talep_olay",
                "yazan": o["yapan_isim"] or "?",
                "zaman": o["zaman"],
                "icerik": OLAY_ETIKETLERI.get(o["olay"], o["olay"]),
                "talep_id": o["talep_id"],
                "po_numaralari": o["po_numaralari"],
                "link": f"/talepler/{o['talep_id']}",
            })
        for d in dosyalar:
            ogeler.append({
                "tur": "talep_dosya",
                "yazan": d["yukleyen_isim"],
                "zaman": d["yuklenme_zamani"],
                "icerik": d["dosya_adi"],
                "talep_id": d["talep_id"],
                "po_numaralari": d["po_numaralari"],
                "link": f"/talepler/{d['talep_id']}",
            })
        for n in talep_notlari:
            ogeler.append({
                "tur": "talep_not",
                "yazan": n["yazan"],
                "zaman": n["zaman"],
                "icerik": n["metin"],
                "talep_id": n["talep_id"],
                "po_numaralari": n["po_numaralari"],
                "link": f"/talepler/{n['talep_id']}#notlar",
            })

    if fl in ("hepsi", "konular"):
        for m in storage_konular.tum_mesajlar(limit=limit):
            ogeler.append({
                "tur": "konu_ilk" if m["ilk_mesaj_mi"] else "konu_mesaj",
                "yazan": m["yazan"],
                "zaman": m["zaman"],
                "icerik": m["metin"],
                "konu_id": m["konu_id"],
                "baslik": m["baslik"],
                "link": f"/ekip-akisi#{m['konu_id']}",
            })

    ogeler.sort(key=lambda o: o["zaman"], reverse=True)
    return ogeler[:limit]

