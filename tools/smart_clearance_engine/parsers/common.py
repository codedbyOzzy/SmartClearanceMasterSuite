# -*- coding: utf-8 -*-
"""
common.py — PDF sayfalarini okuma, belge turune gore gruplama ve
tum parser'larin ortak kullandigi kucuk yardimci fonksiyonlar.

Neden pdfplumber?: Bu PDF'lerin tablo hucrelerinde ozel bir Korece font
(Adobe-Korea1) var. `pdftotext` bu fontu cozemeyip satirlari kaybediyor;
pdfplumber dogru okuyor. Bu yuzden TUM metin cikarma islemleri burada,
tek yerden pdfplumber ile yapilir.
"""
import re
import pdfplumber
from datetime import datetime


def load_pages(pdf_path):
    """PDF'teki her sayfanin metnini dondurur (liste, sayfa basina 1 string)."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages


def split_documents(pages):
    """Sayfalari basliklarina gore PACKING_LIST / INVOICE / WAYBILL olarak
    gruplar. Konsimento sablonu (Hapag-Lloyd / ONE-MSC / Maersk) farkli
    olsa da bu gruplama sadece basliga bakar, sablon farkini umursamaz.
    """
    groups = {"PACKING_LIST": [], "INVOICE": [], "WAYBILL": []}
    current = None
    for text in pages:
        head = text[:200].upper()
        if "PACKING LIST" in head:
            current = "PACKING_LIST"
        elif "COMMERCIAL INVOICE" in head:
            current = "INVOICE"
        elif "SEA WAYBILL" in head or "BILL OF LADING" in head or "WAYBILL" in head:
            current = "WAYBILL"
        if current:
            groups[current].append(text)
    return {k: "\n".join(v) for k, v in groups.items() if v}


def search(pattern, text, group=1, flags=re.IGNORECASE):
    """re.search kisayolu: eslesme yoksa None, varsa strip'lenmis grup dondurur."""
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else None


def qty_raw_with_unit(qty, matched_text, unit="EA"):
    """Miktarin HAM metnini birimiyle birlikte dondurur (orn. '45 EA' veya '20 PCS')."""
    m = re.search(re.escape(str(qty)) + r"\s*(?:EA|PCS)", matched_text, re.IGNORECASE)
    return m.group(0) if m else str(qty)


def to_number(s):
    """ABD '13,519.053' ve TR '9.088,97' formatlarını float'a çevirir. Cevrilemezse None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    if re.search(r",\d{1,2}$", s) and s.count(",") == 1:
        return to_number_tr(s)
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def to_number_tr(s):
    """'9.088,97' -> 9088.97 (Turkce format: nokta=binlik, virgul=ondalik)."""
    if s is None:
        return None
    s = str(s).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def detect_origin(text):
    """Sevkiyatin mense ulkesini gonderici (Shipper) blogundan tespit eder.
    Gorulen kaynaklar: Kore, Macaristan, Cin.
    """
    if re.search(r"HANKOOK TIRE HUNGARY", text, re.IGNORECASE):
        return "HUNGARY"
    if re.search(r"HANKOOK TIRE\s*&\s*TECHNOLOGY", text, re.IGNORECASE):
        return "KOREA"
    if re.search(r"HANKOOK TIRE CHINA|ZHEJIANG,?\s*CHINA|SHANGHAI", text, re.IGNORECASE):
        return "CHINA"
    return None


def parse_invoice_date(date_str):
    """'JUN.04.2026' (Kore), '2026.08.05' (Cin) veya '2026.06.22' (Macaristan)
    formatindaki tarih metnini date nesnesine cevirir."""
    if not date_str:
        return None
    normalized = str(date_str).strip().title()
    for fmt in ("%b.%d.%Y", "%Y.%m.%d", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None
