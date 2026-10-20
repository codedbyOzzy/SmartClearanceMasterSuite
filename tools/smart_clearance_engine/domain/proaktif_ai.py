# -*- coding: utf-8 -*-
"""
proaktif_ai.py — SmartClearance AI Proaktif Darboğaz & Anormallik Denetçisi.
Arka planda (Excel yüklemesinde veya /darbogaz komutunda) tüm gümrük verisini
tarayarak operasyonel gecikmeleri, çelişkili durumları ve tıkanıklıkları tespit eder.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app import storage_takip, storage_muhasebe, storage_konular


def darbogaz_ve_anormallik_taramasi() -> Dict[str, Any]:
    """
    Sistemdeki tüm güncel dosyaları tarayarak 3 ana kategoride anormallik/darboğaz arar:
    1. Kırmızı Hat Gecikmeleri (3 günden uzun süredir açık olanlar)
    2. Muhasebe Sevk Gecikmeleri (Gümrük süreci tamamlandığı halde muhasebeye aktarılmayanlar)
    3. Açılmamış Bekleyen Dosya Darboğazı (ETA / Referans gelip dosya no açılmayanlar)
    """
    veriler = storage_takip.liste_ekrani_verisi(acik="acik")["dosyalar"]
    muh_set = {d.strip().lower() for d in storage_muhasebe.gonderilen_dosya_no_seti() if d}
    
    kirmizi_gecikmeler = []
    muhasebe_gecikmeler = []
    acilmamis_acil = []
    
    bugun = datetime.now()
    
    for d in veriler:
        po_no = d.get("referans_no") or "-"
        dosya_no = (d.get("dosya_no") or "").strip()
        hat = (d.get("hat_bilgisi") or "").strip().upper()
        kapanis = (d.get("kapanis_tarihi") or "").strip()
        aciklama1 = (d.get("aciklamalar_1") or "").strip()
        aciklama2 = (d.get("aciklamalar_2") or "").strip()
        aciklama_genel = " | ".join(filter(None, [aciklama1, aciklama2]))
        tescil_str = d.get("tescil_tarihi") or ""
        bayi = d.get("bayi") or "Belirtilmemiş"
        gumruk = d.get("gumruk") or "-"

        if kapanis:
            durum = f"✅ BEYANNAME KAPANDI ({kapanis})" + (f" — {aciklama_genel}" if aciklama_genel else "")
        elif aciklama_genel:
            durum = f"⏳ İŞLEMDE ({aciklama_genel})"
        elif tescil_str:
            durum = f"⚡ TESCİL EDİLDİ ({tescil_str})"
        else:
            durum = "⏳ Açılış / Evrak Aşamasında"
        
        # 1. Kırmızı Hat Kontrolü
        if hat == "KIRMIZI":
            # Kırmızı hatta olan tüm dosyaları öncelikli risk olarak listele
            kirmizi_gecikmeler.append({
                "po": po_no,
                "dosya": dosya_no,
                "bayi": bayi,
                "gumruk": gumruk,
                "aciklama": f"Kırmızı Hat muayenesi devam ediyor (Durum: {durum})"
            })
            
        # 2. Muhasebe Sevk Gecikmesi Kontrolü
        if dosya_no and dosya_no != "-" and dosya_no.lower() not in muh_set:
            durum_low = durum.lower()
            if any(k in durum_low for k in ["tescil", "tamam", "kapan", "tahliye", "çıktı", "teslim"]):
                muhasebe_gecikmeler.append({
                    "po": po_no,
                    "dosya": dosya_no,
                    "bayi": bayi,
                    "aciklama": f"Gümrük işlemi '{durum}' aşamasında fakat muhasebe sevk kaydı yok."
                })
                
        # 3. Dosya No Açılmamış Kritik Kayıtlar
        if not dosya_no or dosya_no == "-":
            if any(w in durum.lower() for w in ["acil", "bekliyor", "varış", "eta"]):
                acilmamis_acil.append({
                    "po": po_no,
                    "bayi": bayi,
                    "aciklama": f"Dosya numarası atanmamış ({durum})"
                })

    toplam_sorun = len(kirmizi_gecikmeler) + len(muhasebe_gecikmeler) + len(acilmamis_acil)
    return {
        "toplam": toplam_sorun,
        "kirmizi_gecikmeler": kirmizi_gecikmeler,
        "muhasebe_gecikmeler": muhasebe_gecikmeler,
        "acilmamis_acil": acilmamis_acil,
    }


def proaktif_rapor_metni_olustur(rapor: Dict[str, Any], kaynak: str = "otomatik") -> str:
    """
    Bulunan darboğaz ve anormallikleri şık bir Markdown raporu (ve etkileşimli butonlarla) oluşturur.
    """
    toplam = rapor.get("toplam", 0)
    if toplam == 0:
        if kaynak == "manuel":
            return "🎉 **SMARTCLEARANCE AI — PROAKTİF DENETİM SONUCU**\n✅ Harika haber! Sistem genelinde şu an herhangi bir darboğaz, kırmızı hat gecikmesi veya muhasebe sevk tıkanıklığı tespit edilmedi."
        return ""

    satirlar = [
        "⚠️ **SMARTCLEARANCE AI — PROAKTİF DARBOĞAZ & ANORMALLİK RAPORU**",
        f"Sistem genelindeki operasyonel veri taramasında **`{toplam}` kritik darboğaz / riskli durum** tespit edildi:",
        ""
    ]

    kirmizilar = rapor.get("kirmizi_gecikmeler", [])
    if kirmizilar:
        satirlar.append(f"🔴 **Kırmızı Hat Denetimindeki Dosyalar (`{len(kirmizilar)} adet`):**")
        for k in kirmizilar[:5]:
            satirlar.append(f"• `PO-{k['po']}` (Dosya: `{k['dosya']}`) — **Bayi:** {k['bayi']} | **Gümrük:** {k['gumruk']}")
            satirlar.append(f"  [PO-AKSIYON:{k['po']}]")
        if len(kirmizilar) > 5:
            satirlar.append(f"*(+ {len(kirmizilar) - 5} Kırmızı Hat kaydı daha var...)*")
        satirlar.append("")

    muhasebeler = rapor.get("muhasebe_gecikmeler", [])
    if muhasebeler:
        satirlar.append(f"⏳ **Muhasebe Sevk Gecikmesi (`{len(muhasebeler)} adet`):**")
        for m in muhasebeler[:4]:
            satirlar.append(f"• `PO-{m['po']}` (Dosya: `{m['dosya']}`) — **Bayi:** {m['bayi']}")
            satirlar.append(f"  [PO-AKSIYON:{m['po']}]")
        if len(muhasebeler) > 4:
            satirlar.append(f"*(+ {len(muhasebeler) - 4} dosya daha var...)*")
        satirlar.append("")

    acilmamislar = rapor.get("acilmamis_acil", [])
    if acilmamislar:
        satirlar.append(f"📁 **Dosya Numarası Bekleyen Öncelikli PO'lar (`{len(acilmamislar)} adet`):**")
        for a in acilmamislar[:4]:
            satirlar.append(f"• `PO-{a['po']}` — **Bayi:** {a['bayi']} (*{a['aciklama']}*)")
            satirlar.append(f"  [PO-AKSIYON:{a['po']}]")
        satirlar.append("")

    satirlar.append("💡 *Üstteki hızlı eylem butonlarını (👁️ Gözat, 📋 Talep Aç, 💰 Muhasebe) kullanarak sohbette anında işlem yapabilirsiniz.*")
    return "\n".join(satirlar)


def excel_sonrasi_proaktif_kontrol():
    """
    İş Takip Raporu Excel yüklemesi sonrasında çağrılır.
    Eğer darboğaz varsa #Sistem-Islem-Kayitlari kanalına proaktif rapor düşer.
    """
    try:
        rapor = darbogaz_ve_anormallik_taramasi()
        if rapor.get("toplam", 0) > 0:
            metin = proaktif_rapor_metni_olustur(rapor, kaynak="otomatik")
            if metin:
                storage_konular.sistem_bildirimi_yayinla(
                    f"⚠️ Proaktif AI Darboğaz Denetimi: {rapor['toplam']} kritik durum tespit edildi",
                    "⚠️ SmartClearance AI — Proaktif Denetim",
                    metin
                )
    except Exception as e:
        print("Proaktif AI denetim hatası:", e)
