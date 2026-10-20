# -*- coding: utf-8 -*-
"""
mail_export.py — Sonuc sayfalarindaki "Mail Hazirla" butonu icin konu/govde
metnini hazirlar. Hicbir mail GONDERMEZ — sadece mailto: linkinde kullanilacak
duz metni uretir, gonderme islemini kullanici kendi mail programinda yapar.
"""


def build_excel_mail(inv: dict) -> dict:
    lines = [
        f"Fatura No: {inv['invoice_no']}",
        f"Kaynak dosya(lar): {', '.join(inv.get('source_files') or [])}",
        "",
    ]
    if inv.get("warnings"):
        lines.append("UYARILAR:")
        lines += [f"- {w}" for w in inv["warnings"]]
        lines.append("")
    if inv.get("unconfirmed_count"):
        lines.append(f"{inv['unconfirmed_count']} satır kontrol gerektiriyor (sarı işaretli).")
    return {
        "subject": f"Excel Aktarım Sonucu - Fatura {inv['invoice_no']}",
        "body": "\n".join(lines),
    }


def build_beyanname_mail(s: dict) -> dict:
    lines = [
        f"Kimlik: {s['kimlik']}",
        f"Durum: {s['durum']}",
        f"Eşleşen fatura: {s.get('fatura_dosya') or 'BULUNAMADI'}",
        f"Kalem sayısı: {s.get('kalem_sayisi', 0)}",
        "",
    ]
    if s.get("hata_list"):
        lines.append("HATALAR:")
        lines += [f"- {h}" for h in s["hata_list"]]
        lines.append("")
    if s.get("uyari_list"):
        lines.append("UYARILAR:")
        lines += [f"- {u}" for u in s["uyari_list"]]
        lines.append("")
    if s.get("bilgi_list"):
        lines.append("BİLGİ:")
        lines += [f"- {b}" for b in s["bilgi_list"]]
    return {
        "subject": f"Beyanname Kontrol Sonucu - {s['kimlik']} ({s['durum']})",
        "body": "\n".join(lines),
    }


def build_islem_kayitlari_mail(kayitlar: list, tur_etiketi) -> dict:
    """Şefe "bugün şunları yaptık" özetini hazırlar — İşlem Kayıtları
    listesindeki (filtrelenmiş) satırlardan. tur_etiketi: storage_islem_
    kayitlari.tur_etiketi fonksiyonu (döngüsel import olmasın diye burada
    hazır sözlük yerine fonksiyon olarak alınıyor)."""
    lines = [f"{len(kayitlar)} kayıt:", ""]
    for k in kayitlar:
        satir = f"- {k['po_no']} — {tur_etiketi(k)}"
        if k.get("referans_not"):
            satir += f" (ref: {k['referans_not']})"
        lines.append(satir)
        if k.get("aciklama"):
            lines.append(f"  {k['aciklama']}")
    return {
        "subject": f"İşlem Kayıtları Özeti - {len(kayitlar)} kayıt",
        "body": "\n".join(lines),
    }


def build_master_mail(report: dict) -> dict:
    lines = [
        f"Fatura kalemleri: {report.get('total', 0)} ürün",
        f"Eşleşti: {report.get('matched_count', 0)}",
        f"Tanım uyuşmuyor: {report.get('mismatch_count', 0)}",
        f"Master'da yok: {report.get('missing_count', 0)}",
        "",
    ]
    missing = [r for r in (report.get("rows") or []) if r.get("status") == "missing_code"]
    if missing:
        lines.append("MASTER'DA OLMAYAN ÜRÜNLER:")
        lines += [f"- {r['product_code']} ({r.get('invoice_description') or ''})" for r in missing]
    return {
        "subject": "Master Data Kontrol Sonucu",
        "body": "\n".join(lines),
    }
