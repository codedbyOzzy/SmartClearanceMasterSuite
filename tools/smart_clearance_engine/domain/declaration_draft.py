# -*- coding: utf-8 -*-
"""
declaration_draft.py — Fatura+konsimento kalemlerini, Evrim'e girilecek
BEYANNAME KALEMİ taslağına zenginleştirir (henüz beyanname yokken).

Master katalogdan GTİP/Türkçe tanım/anlaşma kodu okunur; marka description
içindeki HK/LF token'ından çıkarılır. Master'da olmayan/eksik alanlar
BOŞ bırakılıp 'warnings' ile işaretlenir — tahmin edilmez.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

# Anlasma Kodu -> Muafiyet metni. Kullanici onayladi (2026-07-21).
MUAFIYET_MAP = {
    "KORE": ("KORE-KORE ANLAŞMASI", True),
    "AT":   ("AT", True),
    "DÜ":   ("MUAF DEĞİL (standart tarife)", False),
}

# Urun kodu ilk rakamina gore standart GTİP + Turkce tanim.
# Master katalogda bulunmayan veya Turkce tanimi bos olan urunlere uygulanir.
# Kullanici onayladi (2026-07-22).
STANDARDT_TARIFE = {
    "1": {"gtip": "401110009012", "turkce_tanim": "RADYAL BİNEK OTO DIŞ LASTİĞİ"},
    "2": {"gtip": "401120100019", "turkce_tanim": "HAFİF TİCARİ ARAÇ DIŞ LASTİĞİ"},
    "3": {"gtip": "401120900011", "turkce_tanim": "RADYAL KAMYON LASTİĞİ"},
}

BRAND_TOKEN_RE = re.compile(r",(HK|LF|OP)(?:[,(\s]|$)")
BRAND_NAMES = {"HK": "HANKOOK", "LF": "LAUFEN", "OP": "HANKOOK"}

ORIGIN_EVRIM_CODES = {
    "KOREA": "728",
    "HUNGARY": "064",
    "CHINA": "052",
}
ORIGIN_DISPLAY_NAME = {
    "KOREA": "Kore Cumhuriyeti",
    "HUNGARY": "Macaristan",
    "CHINA": "Çin",
}


@dataclass
class DraftKalem:
    kalem_no: int
    urun_kodu: str
    ticari_tanim: str
    miktar: Optional[float]
    birim: str = "AD"
    gtip: Optional[str] = None
    gtip_bulundu: bool = False
    turkce_tanim: Optional[str] = None
    marka: Optional[str] = None
    muafiyet: Optional[str] = None
    muafiyet_dogrulanmis: bool = True
    kalem_fiyat: Optional[float] = None  # fatura toplam tutarı (miktar × birim fiyat)
    warnings: list = field(default_factory=list)


def _infer_brand(description: str) -> Optional[str]:
    """Description sonundaki ,HK veya ,LF token'indan marka çıkarır.
    HK -> HANKOOK, LF -> LAUFEN."""
    m = BRAND_TOKEN_RE.search(description or "")
    return BRAND_NAMES.get(m.group(1)) if m else None


def _ticari_tanim_kisalt(description: str) -> str:
    """Fatura açıklamasından TAREKS için kısa ticari tanım üretir.

    Fatura description formatı:
        BOYUT,YÜKLEME_ENDEKSİ,MODEL,YÜK_ENDEKSİ,YAPIM,HIZ,MARKA,...
    Örn: 315/80R22.5,20,AH31,L,B,-,HK

    TAREKS'e girilecek kısım yalnızca ilk üç alan:
        315/80R22.5,20,AH31
    (virgülden sonraki L,B,-,HK gibi alanlar TAREKS'te ayrı sütunlarda
    zaten bulunur; ticari tanıma dahil edilmez.)
    """
    if not description:
        return ""
    parts = description.split(",")
    return ",".join(parts[:3])


def _prefix_tarife(code: str) -> Optional[dict]:
    """Urun kodunun ILK rakamina gore standart tarife bilgisi doner.
    1→binek, 2→hafif ticari, 3→kamyon. Eslesmezse None."""
    return STANDARDT_TARIFE.get(str(code or "")[:1])


def build_draft_kalemler(items, katalog) -> list:
    """items: LineItem listesi. katalog: MasterKatalog (opsiyonel -
    None ise sadece fatura verisiyle, GTİP/tanım olmadan taslak üretir)."""
    kalemler = []
    for idx, item in enumerate(items, start=1):
        code = str(item.code or "").strip()
        master = katalog.rows_by_code.get(code) if katalog else None

        k = DraftKalem(
            kalem_no=idx,
            urun_kodu=code,
            # Sadece BOYUT,YÜKLEME_ENDEKSİ,MODEL_KODU — ilk 3 virgüle kadar
            ticari_tanim=_ticari_tanim_kisalt(item.description),
            miktar=item.quantity,
            kalem_fiyat=item.amount,
        )
        k.marka = _infer_brand(item.description)
        if not k.marka:
            k.warnings.append("Marka (HK/LF) tanımdan tespit edilemedi")

        if master is None:
            # ---- Master katalogda yok: prefix'e gore standart tarife dene ----
            tarife = _prefix_tarife(code)
            if tarife:
                k.gtip         = tarife["gtip"]
                k.gtip_bulundu = True
                k.turkce_tanim = tarife["turkce_tanim"]
                # Uyari: standart tarife uygulandigi bildirilir ama bloke etmez
                k.warnings.append(
                    "Master katalogda yok — standart tarife (prefix kural) uygulandı"
                )
            else:
                k.warnings.append(
                    "Ürün kodu master katalogda bulunamadı ve prefix kuralı da yok "
                    "— GTİP/tanım elle girilmeli"
                )
        else:
            k.gtip         = master.gtip
            k.gtip_bulundu = bool(master.gtip)
            if not master.gtip:
                k.warnings.append("Master kaydında GTİP boş")

            # Turkce tanim (Model): master'dan al; bos/yoksa prefix kuralini dene
            raw_tanim = (master.turkish_description or "").strip() or None
            if not raw_tanim:
                tarife = _prefix_tarife(code)
                if tarife:
                    raw_tanim = tarife["turkce_tanim"]
                else:
                    raw_tanim = master.description   # son care: genel aciklama
            
            if raw_tanim:
                k.turkce_tanim = raw_tanim.split(",")[0].strip()
            else:
                k.turkce_tanim = None

            agreement = (master.agreement_code or "").strip().upper()
            if agreement in MUAFIYET_MAP:
                text, confirmed = MUAFIYET_MAP[agreement]
                k.muafiyet = text
                k.muafiyet_dogrulanmis = confirmed
                if not confirmed:
                    k.warnings.append(
                        f"Anlaşma Kodu '{agreement}' için muafiyet metni DOĞRULANMADI (tahmin)"
                    )
            elif agreement:
                k.warnings.append(f"Bilinmeyen Anlaşma Kodu: '{agreement}'")

        kalemler.append(k)
    return kalemler


def resolve_origin(origin_country: Optional[str]):
    """Donen: (turkce_ad, evrim_kodu) — ikisi de None olabilir (bilinmeyen mense)."""
    if not origin_country:
        return None, None
    return ORIGIN_DISPLAY_NAME.get(origin_country), ORIGIN_EVRIM_CODES.get(origin_country)
