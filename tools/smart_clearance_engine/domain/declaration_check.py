# -*- coding: utf-8 -*-
"""
declaration_check.py — Beyannameyi eslesen faturayla (Packing List +
Commercial Invoice) karsilastirir.

Mantik AYNEN eski sistemden tasindi ve 8 gercek beyanname (1..23 kalemli)
ile dogrulandi. Fatura tarafi icin BURADA AYRI BIR PARSER YOK — mevcut
app.parsers.process_pdf() ciktisi (EvrakSeti) dogrudan kullanilir.

Onemli tasarim karari (gercek veriyle dogrulandi): ayni urun kodu bir
faturada BIRDEN FAZLA farkli miktar/agirlikla gecebilir (orn. ayni model
2 ayri kalem olarak beyan edilmis). Bu yuzden kod bazinda TEK deger
tutmak yerine, her kod icin bir SATIR HAVUZU tutulur ve en yakin
miktar/agirlik eslesen satir "tuketilir" (bir daha kullanilmaz).
"""
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from tools.smart_clearance_engine.parsers.beyanname import Beyanname, BELGE_KODLARI, ZORUNLU_BELGELER
from tools.smart_clearance_engine.domain.declaration_rules import evaluate_transfer_notification

_DMY_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _parse_dmy(raw: Optional[str]) -> Optional[date]:
    """Beyanname kalemindeki fatura tarihi HER ZAMAN DD.MM.YYYY olarak
    yazilir (gercek veriyle dogrulandi). Belirsiz ikinci yorum (MM.DD)
    kasitli olarak uretilmez — yanlis pozitif eslesmeye yol acar."""
    if not raw:
        return None
    m = _DMY_RE.fullmatch(raw.strip())
    if not m:
        return None
    day, month, year = (int(v) for v in m.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


@dataclass
class BeyannameSonuc:
    source_file: str
    kimlik: str
    hata_list: list = field(default_factory=list)
    uyari_list: list = field(default_factory=list)
    bilgi_list: list = field(default_factory=list)
    fatura_dosya: Optional[str] = None
    kalem_sayisi: int = 0
    taslak: bool = True
    beyanname_path: Optional[str] = None
    fatura_path: Optional[str] = None
    kalem_durumlar: dict = field(default_factory=dict)  # {kalem_no: {alan: "ok"/"hata"/"eksik"}}


def find_matching_evrak(beyanname: Beyanname, by_po_no: dict, by_invoice_no: dict):
    """Eslestirme onceligi: once Kalem 1'in beyan ettigi fatura no (en
    kesin), o yoksa Referans'taki PO no."""
    ilk_fatura_no = beyanname.kalemler[0].fatura_no if beyanname.kalemler else None
    if ilk_fatura_no and ilk_fatura_no in by_invoice_no:
        return by_invoice_no[ilk_fatura_no]
    if beyanname.po_no and beyanname.po_no in by_po_no:
        return by_po_no[beyanname.po_no]
    return None


def check_beyanname(beyanname: Beyanname, by_po_no: dict, by_invoice_no: dict) -> BeyannameSonuc:
    hata, uyari, bilgi = [], [], []

    evrak = find_matching_evrak(beyanname, by_po_no, by_invoice_no)
    pl = evrak.packing_list if evrak else None
    inv = evrak.invoice if evrak else None

    for eksik in beyanname.eksik_alanlar:
        hata.append(f"Zorunlu alan eksik: {eksik}")
    bilgi.extend(beyanname.bilgi_notlari)

    if evrak and not beyanname.referans:
        po = pl.po_no if pl else None
        if po:
            uyari.append(
                f"Dosya referansı/PO-HNKRE alanı boş veya PDF metninde okunamadı; "
                f"fatura no ile eşleşme sağlandı. Faturadaki PO: {po}. "
                f"Beyanname referans alanını kontrol edin."
            )
        else:
            uyari.append(
                "Dosya referansı/PO-HNKRE alanı boş veya PDF metninde okunamadı; "
                "fatura no ile eşleşme sağlandı fakat faturada PO okunamadı. Referans alanını manuel kontrol edin."
            )

    if not evrak:
        hata.append("Bu beyannameye karşılık gelen fatura PDF'i yüklenen dosyalar arasında bulunamadı!")

    material_index, used = _build_material_index(pl.items if pl else [])

    qty_none_k, weight_none_k, rejim_missing_k = [], [], []
    belge_eksik = {}
    transfer_eksik_k, transfer_mevcut_k, transfer_belirsiz_k = [], [], []
    fatura_ref_eksik_k, konteyner_eksik_k, malzeme_bulunamadi_k = [], [], []
    fatura_no_mismatch, fatura_tarih_mismatch = [], []
    konteyner_mismatch, miktar_mismatch, agirlik_mismatch = [], [], []

    # DÜZELTME: "Fatura No" ve "Fatura Tarihi" kalem kontrolleri (kutucuk
    # işaretleme dahil) artık Packing List'in cross-reference alanı DEĞİL,
    # doğrudan Commercial Invoice belgesinin kendi invoice_no/invoice_date
    # alanları esas alınarak yapılıyor — kullanıcı gerçek dosyada Packing
    # List'e bakıldığını fark etti, bu yanlıştı (bkz. AI_GELISTIRICI_NOTLARI.md).
    invoice_no = inv.invoice_no if inv else None
    invoice_date = _shipment_date(inv) if inv else None
    # Konteyner no SADECE Packing List'te var (Commercial Invoice'da hiç
    # basılmıyor) — bu alan kasıtlı olarak pl'den okunmaya devam ediyor.
    ctr_no = pl.ctr_no if pl else None

    durumlar = {}

    for k in beyanname.kalemler:
        kn = k.kalem_no
        d = durumlar.setdefault(kn, {})
        if k.qty is None:
            qty_none_k.append(kn)
        if k.net_weight is None:
            weight_none_k.append(kn)
        if not k.rej_bulundu:
            rejim_missing_k.append(kn)

        for zorunlu in ZORUNLU_BELGELER:
            if not k.belgeler.get(zorunlu):
                belge_eksik.setdefault(zorunlu, []).append(kn)

        transfer_karari = evaluate_transfer_notification(
            form_present=bool(k.belgeler.get("Transfer Bildirim Formu")),
            registration_date=_parse_tescil(beyanname.tescil_tarihi),
            payment_method=k.odeme_sekli,
        )
        if transfer_karari["status"] == "required":
            transfer_eksik_k.append(kn)
        elif transfer_karari["status"] == "present":
            transfer_mevcut_k.append(kn)
        else:
            transfer_belirsiz_k.append(kn)

        if evrak:
            if k.fatura_no is None:
                fatura_ref_eksik_k.append(kn)
                d["fatura_no"] = "eksik"
            else:
                d["fatura_no"] = "ok"
                if invoice_no and k.fatura_no != invoice_no:
                    fatura_no_mismatch.append((kn, k.fatura_no, invoice_no))
                    d["fatura_no"] = "hata"
                k_date = _parse_dmy(k.fatura_tarihi_raw)
                d["fatura_tarihi"] = "ok"
                if k_date and invoice_date and k_date != invoice_date:
                    fatura_tarih_mismatch.append((kn, k.fatura_tarihi_raw, invoice_date))
                    d["fatura_tarihi"] = "hata"

            if k.konteyner_no is None:
                konteyner_eksik_k.append(kn)
                d["konteyner"] = "eksik"
            else:
                d["konteyner"] = "ok"
                if ctr_no and k.konteyner_no != ctr_no:
                    konteyner_mismatch.append((kn, k.konteyner_no, ctr_no))
                    d["konteyner"] = "hata"

            if k.material and k.material in material_index:
                match = _best_match(k, material_index[k.material], used)
                if match is None:
                    malzeme_bulunamadi_k.append(kn)
                    d["malzeme"] = "eksik"
                else:
                    d["malzeme"] = "ok"
                    d["agirlik"] = "ok"
                    d["miktar"] = "ok"
                    if k.qty is not None and match.quantity is not None and k.qty != match.quantity:
                        miktar_mismatch.append((kn, k.qty, match.quantity))
                        d["miktar"] = "hata"
                    if k.net_weight is not None and match.net_weight is not None:
                        # Tolerans: _AGIRLIK_TOLERANSI — virgülden sonrası dahil tam eşleşme
                        if abs(k.net_weight - match.net_weight) > _AGIRLIK_TOLERANSI:
                            agirlik_mismatch.append((kn, k.net_weight, match.net_weight))
                            d["agirlik"] = "hata"
            elif k.material:
                malzeme_bulunamadi_k.append(kn)
                d["malzeme"] = "eksik"

    _append_grouped_issues(hata, uyari, bilgi, locals())

    _check_toplam(beyanname, pl, hata, uyari, inv)

    fatura_dosya = None
    fatura_path = None
    if evrak:
        raw = evrak.files[0] if evrak.files else evrak.source_pdf
        fatura_dosya = os.path.basename(str(raw))
        fatura_path = str(raw)

    return BeyannameSonuc(
        source_file=beyanname.source_file,
        kimlik=beyanname.dosya_no or beyanname.referans or beyanname.po_no or "???",
        hata_list=hata,
        uyari_list=uyari,
        bilgi_list=bilgi,
        fatura_dosya=fatura_dosya,
        kalem_sayisi=len(beyanname.kalemler),
        taslak=beyanname.taslak,
        beyanname_path=beyanname.source_path,
        fatura_path=fatura_path,
        kalem_durumlar=durumlar,
    )


def _shipment_date(belge):
    """belge: Invoice ya da PackingList nesnesi (ikisi de invoice_date
    alanına sahip) — artik cagiran yer (check_beyanname) burada Commercial
    Invoice'u (inv) gonderiyor, Packing List'i (pl) degil."""
    from tools.smart_clearance_engine.parsers.common import parse_invoice_date
    return parse_invoice_date(belge.invoice_date) if belge else None


def _parse_tescil(raw):
    return _parse_dmy(raw) if raw else None


def _build_material_index(items):
    index = {}
    for it in items:
        if it.code:
            index.setdefault(it.code, []).append(it)
    return index, set()


def _best_match(kalem, candidates, used):
    """Ayni kod icin birden fazla aday satir varsa, miktar+agirlik en
    yakin olani secer ve 'kullanildi' isaretler (bir daha secilmesin)."""
    available = [it for it in candidates if id(it) not in used]
    if not available:
        return None

    def score(item):
        qty_diff = 0 if kalem.qty is None or item.quantity == kalem.qty else 1
        if kalem.net_weight is None or item.net_weight is None:
            weight_diff = 0
        else:
            weight_diff = abs(kalem.net_weight - item.net_weight)
        return (qty_diff, 0 if weight_diff <= 0.05 else 1, weight_diff)

    best = min(available, key=score)
    used.add(id(best))
    return best


def _kl(kalemler):
    return ", ".join(str(x) for x in kalemler)


def _append_grouped_issues(hata, uyari, bilgi, ctx):
    if ctx["qty_none_k"]:
        hata.append(f"Miktar okunamadı -> Kalem {_kl(ctx['qty_none_k'])}")
    if ctx["weight_none_k"]:
        hata.append(f"Net kilo okunamadı -> Kalem {_kl(ctx['weight_none_k'])}")
    if ctx["rejim_missing_k"]:
        uyari.append(f"Rejim kodu (4000) bulunamadı -> Kalem {_kl(ctx['rejim_missing_k'])}")
    for belge, kalemler in ctx["belge_eksik"].items():
        kod = BELGE_KODLARI[belge]
        hata.append(f"Zorunlu belge eksik -> {belge} (Kod: {kod}) -> Kalem {_kl(kalemler)}")

    if ctx["transfer_eksik_k"]:
        hata.append(
            f"Transfer Bildirim Formu (Kod: 0887) eksik -> Kalem {_kl(ctx['transfer_eksik_k'])} "
            "(transfer tarihi tescil tarihinden önce/tescil tarihinde)"
        )
    if ctx["transfer_mevcut_k"]:
        bilgi.append(f"0887 Transfer Bildirim Formu mevcut -> Kalem {_kl(ctx['transfer_mevcut_k'])}.")
    if ctx["transfer_belirsiz_k"]:
        uyari.append(
            f"0887 gerekliliği kanıtla kesinleştirilemedi -> Kalem {_kl(ctx['transfer_belirsiz_k'])}. "
            "Ödeme şekli tek başına yeterli değildir; transferin yapılıp yapılmadığını ve "
            "transfer/tescil tarihlerini doğrulayın (2017/20 sayılı Genelge)."
        )
    if ctx["fatura_ref_eksik_k"]:
        hata.append(f"Fatura referansı okunamadı -> Kalem {_kl(ctx['fatura_ref_eksik_k'])}")
    for kn, b, g in ctx["fatura_no_mismatch"]:
        hata.append(f"Kalem {kn}: Fatura no uyuşmuyor (Beyanname={b} / Fatura={g})")
    for kn, b, g in ctx["fatura_tarih_mismatch"]:
        hata.append(f"Kalem {kn}: Fatura tarihi uyuşmuyor (Beyanname={b} / Fatura={g})")
    if ctx["konteyner_eksik_k"]:
        uyari.append(f"Konteyner no okunamadı (konşimento doğrulanamadı) -> Kalem {_kl(ctx['konteyner_eksik_k'])}")
    for kn, b, g in ctx["konteyner_mismatch"]:
        hata.append(f"Kalem {kn}: Konteyner no uyuşmuyor (Beyanname={b} / Fatura={g})")
    for kn, b, g in ctx["miktar_mismatch"]:
        hata.append(f"Kalem {kn}: Miktar uyuşmuyor (Beyanname={b} / Fatura={g})")
    for kn, b, g in ctx["agirlik_mismatch"]:
        hata.append(f"Kalem {kn}: Net ağırlık uyuşmuyor (Beyanname={b} / Fatura={g})")
    if ctx["malzeme_bulunamadi_k"]:
        hata.append(f"Malzeme faturada bulunamadı (eşleştirme yapılamadı) -> Kalem {_kl(ctx['malzeme_bulunamadi_k'])}")


# Ağırlık toleransı: Gümrük beyannamelerinde ondalık basamak dahil tam eşleşme
# zorunludur (ör. 9511,31 ≠ 9511,306). 0.001 kg eşiği, yalnızca kayan nokta
# hassasiyetinden kaynaklanan önemsiz çevrim hatalarını (< 1 gram) geçirir.
_AGIRLIK_TOLERANSI = 0.001  # kg
# Tutar toleransı: Beyanname kalemleri virgüle kadar fatura ile aynı olmalı.
# 0.01 TRY eşiği yalnızca kayan nokta çevrim hatalarını geçirir.
_TUTAR_TOLERANSI = 0.01  # TRY


def _check_toplam(beyanname, pl, hata, uyari, inv=None):
    if not (pl and beyanname.toplam):
        hata.append("TOPLAM karşılaştırması yapılamadı (fatura veya beyanname toplamı bulunamadı)")
        return

    bt = beyanname.toplam
    if bt["qty"] is not None and pl.sub_total_qty is not None and int(bt["qty"]) != int(pl.sub_total_qty):
        hata.append(f"TOPLAM miktar uyuşmuyor (Beyanname={bt['qty']:.0f} / Fatura={pl.sub_total_qty})")
    elif pl.sub_total_qty is None:
        hata.append("Fatura toplam miktarı okunamadı; toplam kontrolü tamamlanamadı")

    # Tolerans: 0.001 kg — virgülden sonrası dahil tam eşleşme zorunlu.
    # UYARI (HATA değil): Beyanname PDF'te 2 ondalık, fatura 3 ondalık yazabilir;
    # ufak format farkı işlemi bloklamaz ama kontrol edilmeli.
    if bt["net"] is not None and pl.sub_total_net is not None:
        if abs(bt["net"] - pl.sub_total_net) > _AGIRLIK_TOLERANSI:
            uyari.append(
                f"TOPLAM net ağırlık kontrol edilmeli "
                f"(Beyanname={bt['net']} / Fatura={pl.sub_total_net} / "
                f"Fark={abs(bt['net'] - pl.sub_total_net):.4f} kg)"
            )
    elif pl.sub_total_net is None:
        uyari.append("Fatura toplam net ağırlığı okunamadı; ağırlık toplamı doğrulanamadı")

    # Tolerans: 0.001 kg — virgülden sonrası dahil tam eşleşme zorunlu.
    # UYARI (HATA değil): aynı gerekçe.
    if bt.get("brut") is not None and pl.sub_total_gross is not None:
        if abs(bt["brut"] - pl.sub_total_gross) > _AGIRLIK_TOLERANSI:
            uyari.append(
                f"TOPLAM brüt ağırlık kontrol edilmeli "
                f"(Beyanname={bt['brut']} / Fatura={pl.sub_total_gross} / "
                f"Fark={abs(bt['brut'] - pl.sub_total_gross):.4f} kg)"
            )
    elif pl.sub_total_gross is None:
        uyari.append("Fatura toplam brüt ağırlığı okunamadı; ağırlık toplamı doğrulanamadı")

    fatura_tutar = None
    if inv is not None:
        fatura_tutar = inv.sub_total_amount if inv.sub_total_amount is not None else inv.net_amount
    if bt.get("kal_fiyat_toplam") is not None and fatura_tutar is not None:
        # Tolerans: 0.01 TRY — virgüle kadar tam eşleşme zorunlu, HATA olarak işaretle
        if abs(bt["kal_fiyat_toplam"] - fatura_tutar) > _TUTAR_TOLERANSI:
            hata.append(
                f"TOPLAM kıymet (tutar) uyuşmuyor "
                f"(Beyanname={bt['kal_fiyat_toplam']} / Fatura={fatura_tutar} / "
                f"Fark={abs(bt['kal_fiyat_toplam'] - fatura_tutar):.2f} TRY)"
            )
    elif bt.get("kal_fiyat_toplam") is not None and fatura_tutar is None:
        hata.append("Fatura toplam tutarı okunamadı; kıymet kontrolü tamamlanamadı")
