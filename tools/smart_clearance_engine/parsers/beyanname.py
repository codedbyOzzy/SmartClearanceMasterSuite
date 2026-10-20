# -*- coding: utf-8 -*-
"""
beyanname.py — T.C. Gumruk Beyannamesi (TBeyanname) PDF'inden alan cikarma.

Mantik AYNEN eski sistemden (declaration_check.py) tasindi ve 8 gercek
2026 beyannamesiyle (1..23 kalemli) dogrulandi. Iki farkli PDF bolumu var:
  - Sayfa 1 (ozet sayfasi): Kalem 1 farkli bir duzende yaziyor.
  - Sayfa 2+ ("EKLI LISTE"): Kalem 2..N tablo halinde, farkli desenle.
Bu yuzden kalem 1 ve digerleri AYRI regex ile okunur — birlestirmek
kalem kaybina yol acar.

Konteyner no formati da kalem 1 ile ekli listede FARKLI ("No:XXXX" vs
"No : ['XXXX']") — ikisi de denenir.
"""
import os
import re

import pdfplumber
from dataclasses import dataclass, field
from typing import Optional

from tools.smart_clearance_engine.parsers.common import to_number_tr

# ---------------------------------------------------------------------------
# Regex sabitleri (2026 gercek beyannameleriyle dogrulandi)
# ---------------------------------------------------------------------------
REFERANS_RE = re.compile(r"(\d{10})/HNKRE")
DOSYA_NO_RE = re.compile(r"DOSYA NO\s*:\s*(\S+)")
DOSYA_NO_FALLBACK_RE = re.compile(r"\b(\d{2}-\d{6})\b")
GEMI_RE = re.compile(r"GEM[İI]\s*-\s*([A-ZÇĞİÖŞÜ0-9 .]+?)(?:\n|\s{2,})")
TESCIL_TARIHI_RE = re.compile(r"([A-ZÇĞİÖŞÜÂ]{3,})\s+(\d{2}\.\d{2}\.\d{4})\s*\n")

TOPLAM_SATIRI_RE = re.compile(
    r"TOPLAM:\s*([\d.,]+)\s*AD\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
)
TOPLAM_MIKTAR_FALLBACK_RE = re.compile(r"Toplam Miktar\s*:\s*([\d.,]+)\s*AD")
TOPLAM_AGIRLIK_FALLBACK_RE = re.compile(
    r"Toplam Net/ Br[uü]t Kg\s*:\s*([\d.,]+)KG\s*/\s*([\d.,]+)\s*KG"
)
TOPLAM_TUTAR_FALLBACK_RE = re.compile(r"MalBed\.\s*([\d.,]+)")

KALEM1_MATERIAL_RE = re.compile(r"\[(\d{6,8})\]")
KALEM1_QTY_RE = re.compile(r"(\d{1,4})(?:,00)?\s*AD\b")
KALEM1_WEIGHT_RE = re.compile(r"4000\s+([\d.,]+)\b")
KALEM_BASLANGIC_RE = re.compile(r"(?m)^(\d{1,2}) (\d{4}) ")
KALEM_QTY_RE = re.compile(
    r"(\d{1,4})(?:,00)?\s*AD\s+4000\s+(\d{3})\s+\S+\s+([\d.,]+)\s+([\d.,]+)\s+0\s*Adet"
)

KALEM_FATURA_RE = re.compile(r"Fatura \(V\).{0,80}?(\d{2})\.(\d{2})\.(\d{4})/(\d+)", re.DOTALL)
KALEM_KONTEYNER_RE_A = re.compile(r"No\s*:\s*\['([A-Z0-9]+)'\]")
KALEM_KONTEYNER_RE_B = re.compile(r"\bNo:([A-Z0-9]{6,})\b")
ODEME_LABEL_RE = re.compile(r"[ÖO]DEME\s*[ŞS]EKL[İI]\s*[:=-]?\s*([^\n\r]+)", re.I)

BELGE_KODLARI = {
    "Fatura": "0100",
    "Mense Beyani": "0842",
    "TPS-Tareks Arac Parcalari Izni": "1005",
    "Transfer Bildirim Formu": "0887",
}
BELGE_ARAMA_METNI = {
    "Fatura": "Fatura (V)",
    "Mense Beyani": "Menşe Beyanı (V)",
    "TPS-Tareks Arac Parcalari Izni": "TPS-Tareks Araç Parçaları İzni (V)",
    "Transfer Bildirim Formu": "Transfer Bildirim Formu (V)",
}
ZORUNLU_BELGELER = ["Fatura"]  # 0887 ayri kuralla (declaration_rules.py) degerlendirilir


def is_beyanname_pdf(pdf_path) -> bool:
    """Hizli Islem'de bir klasorden toplu secilen PDF'leri beyanname/fatura
    olarak otomatik ayirmak icin kullanilir. NOT: baslikta gorunen 'T.C.
    GUMRUK BEYANNAMESI' yazisi bu PDF'lerin ozel Kore fontu yuzunden
    pdfplumber ile metin olarak cikarilamiyor (Turkce karakterler bozuluyor,
    bkz. AI_GELISTIRICI_NOTLARI.md). Bunun yerine, ayni sayfada her zaman
    duzgun okunabilen REFERANS_RE deseni ("1234567890/HNKRE") kullanilir —
    8 gercek beyannamede dogrulandi, faturalarda hic gorulmuyor."""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return False
        text = pdf.pages[0].extract_text() or ""
    return REFERANS_RE.search(text) is not None


# ---------------------------------------------------------------------------
# Veri yapilari
# ---------------------------------------------------------------------------
@dataclass
class BeyannameKalem:
    kalem_no: int
    material: Optional[str] = None
    qty: Optional[float] = None
    qty_raw: Optional[str] = None
    net_weight: Optional[float] = None
    net_weight_raw: Optional[str] = None
    men: Optional[str] = None
    belgeler: dict = field(default_factory=dict)
    rej_bulundu: bool = False
    fatura_no: Optional[str] = None
    fatura_tarihi_raw: Optional[str] = None
    konteyner_no: Optional[str] = None
    konteyner_no_miras: bool = False
    odeme_sekli: Optional[str] = None
    odeme_sekli_miras: bool = False


@dataclass
class Beyanname:
    source_file: str
    source_path: Optional[str] = None
    referans: Optional[str] = None
    po_no: Optional[str] = None
    dosya_no: Optional[str] = None
    gemi: Optional[str] = None
    tescil_tarihi: Optional[str] = None
    taslak: bool = True
    toplam: Optional[dict] = None
    kalemler: list = field(default_factory=list)
    eksik_alanlar: list = field(default_factory=list)
    bilgi_notlari: list = field(default_factory=list)
    odeme_sekilleri: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Kucuk yardimcilar
# ---------------------------------------------------------------------------
def _turkish_fold(value):
    if value is None:
        return ""
    text = str(value).upper()
    table = str.maketrans({"Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U"})
    text = text.translate(table)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", text)).strip()


def extract_odeme_sekli(block_text):
    """Donen: MAL MUKABILI / PESIN / VESAIK MUKABILI / AKREDITIF / None."""
    if not block_text:
        return None
    candidates = [m.group(1) for m in ODEME_LABEL_RE.finditer(block_text)]
    candidates.append(block_text)  # etiket kirilmissa yedek: tum blokta ara
    for raw in candidates:
        normalized = _turkish_fold(raw)
        if "MAL MUKABILI" in normalized or "MALMUKABILI" in normalized:
            return "MAL MUKABILI"
        if "VESAIK" in normalized:
            return "VESAIK MUKABILI"
        if "AKREDITIF" in normalized:
            return "AKREDITIF"
        if "PESIN" in normalized:
            return "PESIN"
    return None


def extract_kalem_belgeler(block_text):
    normalized = " ".join(block_text.split())
    return {key: (arama in normalized) for key, arama in BELGE_ARAMA_METNI.items()}


def extract_kalem_fatura_referans(block_text):
    """Fatura (V) numarasi + HAM tarihini (DD.MM.YYYY string) dondurur.
    Tarih yorumu (DD.MM oldugu) declaration_check.py tarafinda yapilir —
    burada sadece ham metin cikarilir."""
    m = KALEM_FATURA_RE.search(block_text)
    if not m:
        return None, None
    left, right, year, invno = m.groups()
    return invno, f"{left}.{right}.{year}"


def extract_kalem_konteyner(block_text):
    m = KALEM_KONTEYNER_RE_A.search(block_text)
    if m:
        return m.group(1)
    m = KALEM_KONTEYNER_RE_B.search(block_text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Kalem parserlari (Kalem 1 vs Ekli Liste — farkli PDF duzeni)
# ---------------------------------------------------------------------------
def parse_kalem1(page0_text):
    k = BeyannameKalem(kalem_no=1)
    m = KALEM1_MATERIAL_RE.search(page0_text)
    k.material = m.group(1) if m else None
    m = KALEM1_QTY_RE.search(page0_text)
    k.qty = float(m.group(1)) if m else None
    k.qty_raw = m.group(0) if m else None
    m = KALEM1_WEIGHT_RE.search(page0_text)
    k.net_weight = to_number_tr(m.group(1)) if m else None
    k.net_weight_raw = m.group(1) if m else None
    k.belgeler = extract_kalem_belgeler(page0_text)
    k.rej_bulundu = "4000" in page0_text
    k.fatura_no, k.fatura_tarihi_raw = extract_kalem_fatura_referans(page0_text)
    k.konteyner_no = extract_kalem_konteyner(page0_text)
    k.odeme_sekli = extract_odeme_sekli(page0_text)
    return k


def parse_ekli_liste_kalemleri(pages_text_2plus):
    kalemler = []
    matches = list(KALEM_BASLANGIC_RE.finditer(pages_text_2plus))
    for i, m in enumerate(matches):
        kalem_no = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(pages_text_2plus)
        block = pages_text_2plus[start:end]
        toplam_idx = block.find("TOPLAM:")
        if toplam_idx != -1:
            block = block[:toplam_idx]

        k = BeyannameKalem(kalem_no=kalem_no)
        mat = KALEM1_MATERIAL_RE.search(block)
        k.material = mat.group(1) if mat else None

        qm = KALEM_QTY_RE.search(block)
        if qm:
            k.qty = float(qm.group(1))
            k.men = qm.group(2)
            k.net_weight = to_number_tr(qm.group(4))
            k.net_weight_raw = qm.group(4)
            qty_prefix = re.match(r"\d{1,4}(?:,00)?\s*AD", qm.group(0))
            k.qty_raw = qty_prefix.group(0) if qty_prefix else None

        k.belgeler = extract_kalem_belgeler(block)
        k.rej_bulundu = "4000" in block
        k.fatura_no, k.fatura_tarihi_raw = extract_kalem_fatura_referans(block)
        k.konteyner_no = extract_kalem_konteyner(block)
        k.odeme_sekli = extract_odeme_sekli(block)
        kalemler.append(k)
    return kalemler


# ---------------------------------------------------------------------------
# Ana giris noktasi
# ---------------------------------------------------------------------------
def parse_beyanname(pdf_path) -> Beyanname:
    with pdfplumber.open(pdf_path) as pdf:
        pages_text = [(p.extract_text() or "") for p in pdf.pages]
    full_text = "\n".join(pages_text)

    result = Beyanname(source_file=os.path.basename(str(pdf_path)), source_path=str(pdf_path))

    m = REFERANS_RE.search(full_text)
    if m:
        result.referans = m.group(0)
        result.po_no = m.group(1)
    else:
        result.bilgi_notlari.append(
            "PO/HNKRE referansı bu beyanname PDF düzeninde görünmedi; "
            "fatura numarası, tarih ve konteyner üzerinden kontrol sürdürüldü."
        )

    m = DOSYA_NO_RE.search(full_text)
    result.dosya_no = m.group(1) if m else None
    if not result.dosya_no:
        m = DOSYA_NO_FALLBACK_RE.search(full_text)
        result.dosya_no = m.group(1) if m else None
    if not result.dosya_no:
        result.eksik_alanlar.append("Dosya No bulunamadi")

    m = GEMI_RE.search(full_text)
    result.gemi = m.group(1).strip() if m else None
    if not result.gemi:
        result.eksik_alanlar.append("Gemi/tasima araci adi bulunamadi")

    tescil_matches = TESCIL_TARIHI_RE.findall(pages_text[0]) if pages_text else []
    result.tescil_tarihi = tescil_matches[-1][1] if tescil_matches else None
    # Tescil tarihi sadece beyanname gumruge TESCIL EDILDIKTEN sonra olusur;
    # bos olmasi HATA degil, henuz taslak asamasinda oldugu anlamina gelir.
    result.taslak = result.tescil_tarihi is None

    m = TOPLAM_SATIRI_RE.search(full_text)
    if m:
        result.toplam = {
            "qty": to_number_tr(m.group(1)),
            "brut": to_number_tr(m.group(2)),
            "net": to_number_tr(m.group(3)),
            "kal_fiyat_toplam": to_number_tr(m.group(5)),
        }
    else:
        mq = TOPLAM_MIKTAR_FALLBACK_RE.search(full_text)
        mw = TOPLAM_AGIRLIK_FALLBACK_RE.search(full_text)
        mt = TOPLAM_TUTAR_FALLBACK_RE.search(full_text)
        if mq and mw:
            result.toplam = {
                "qty": to_number_tr(mq.group(1)),
                "net": to_number_tr(mw.group(1)),
                "brut": to_number_tr(mw.group(2)),
                "kal_fiyat_toplam": to_number_tr(mt.group(1)) if mt else None,
            }
        else:
            result.eksik_alanlar.append("TOPLAM satiri bulunamadi")

    if pages_text:
        result.kalemler.append(parse_kalem1(pages_text[0]))
    if len(pages_text) > 1:
        result.kalemler.extend(parse_ekli_liste_kalemleri("\n".join(pages_text[1:])))

    _inherit_konteyner(result)
    _inherit_odeme_sekli(result, pages_text)
    result.odeme_sekilleri = sorted({k.odeme_sekli for k in result.kalemler if k.odeme_sekli})

    return result


def _inherit_konteyner(result):
    """Konteyner no bazen sadece kalem 1'de acikca yazar; tek konteynerli
    sevkiyatlarda digerlerine miras birakilir (ayri bir alan hatasi degil)."""
    kalem1_konteyner = result.kalemler[0].konteyner_no if result.kalemler else None
    if kalem1_konteyner:
        for k in result.kalemler[1:]:
            if not k.konteyner_no:
                k.konteyner_no = kalem1_konteyner
                k.konteyner_no_miras = True


def _inherit_odeme_sekli(result, pages_text):
    """Odeme sekli bazen sadece ilk sayfada genel bilgi olarak yazar.
    Birden fazla FARKLI odeme sekli acikca goruluyorsa miras BIRAKILMAZ
    (guvensiz olur) — sadece tek tur gorulmusse veya hic gorulmemisse."""
    genel = extract_odeme_sekli(pages_text[0]) if pages_text else None
    acik = {k.odeme_sekli for k in result.kalemler if k.odeme_sekli}
    if genel and len(acik) <= 1:
        for k in result.kalemler:
            if not k.odeme_sekli:
                k.odeme_sekli = genel
                k.odeme_sekli_miras = True
