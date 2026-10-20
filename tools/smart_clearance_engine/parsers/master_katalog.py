# -*- coding: utf-8 -*-
"""
master_katalog.py — Master Excel (ürün kodu -> GTİP/tanım/menşe referans
kataloğu) okuyucusu.

Kullanıcı bu dosyayı istediği zaman silip güncel halini yeniden
yükleyebiliyor; bu yüzden sütun sırasına güvenilmez, başlık satırı
ESNEK/bulanık eşleşmeyle (kelime eşleştirme) tespit edilir. Gerçek
kullanıcı dosyasıyla doğrulanmış başlıklar: Firma, İhracatçı, İlişki,
Royalti, Dfif, Ambargo, Ürün Adı, Türkçe Tanım, Ürün Kodu, GTIP, Menşei,
Anş.Kodu, KDV, Durum (+ bazı ek sütunlar kullanılmıyor).
"""
import re
from dataclasses import dataclass, field
from typing import Optional

import openpyxl

HEADER_ALIASES = {
    "product_code": ["urun kodu", "product code", "material code", "malzeme kodu", "stok kodu"],
    "description": ["urun adi", "yabanci tanim", "description", "item description"],
    "turkish_description": ["turkce tanim", "turkish description"],
    "gtip": ["gtip", "hs code", "tarife"],
    "origin": ["mensei", "origin", "country of origin"],
    "agreement_code": ["ans kodu", "anlasma kodu"],
    "status": ["durum"],
}


@dataclass
class MasterRow:
    product_code: str
    description: str
    turkish_description: Optional[str] = None
    gtip: Optional[str] = None
    origin: Optional[str] = None
    agreement_code: Optional[str] = None
    status: Optional[str] = None
    row_number: int = 0


@dataclass
class MasterKatalog:
    rows_by_code: dict = field(default_factory=dict)
    columns_found: dict = field(default_factory=dict)
    duplicate_codes: list = field(default_factory=list)
    row_count: int = 0


def _fold(value) -> str:
    """UYARI: Python'un yerleşik str.lower()'ı Türkçe 'İ' harfini önce
    'i' + BİRLEŞTİRİCİ NOKTA (U+0307) olarak ikiye böler (locale-bağımsız
    varsayılan davranış) — bu yüzden çeviri tablosu .lower()'DAN ÖNCE
    uygulanmalı, sonra değil (aynı hata app/parsers/takip_raporu.py'de
    bulunup düzeltilmişti; burada şu an kullanılan gerçek başlıklarda
    aktif bir soruna yol açmıyor çünkü hiçbiri büyük İ içermiyor, ama
    ileride 'İhracatçı' gibi bir alan eklenirse aynı hataya düşerdi —
    önlem amaçlı düzeltildi)."""
    text = str(value or "").strip()
    table = str.maketrans("çÇğĞıİöÖşŞüÜI", "ccggiioossuui")
    folded = text.translate(table).lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def clean_code(value) -> str:
    """'[1026344]' -> '1026344' (köşeli parantez/boşluk temizler).

    ÖNEMLİ DÜZELTME: openpyxl, bir Excel hücresi sayısal olduğunda bazen
    onu Python float olarak döner (örn. 1029458.0), bazen int (1029458) —
    bu, hücrenin Excel'deki iç biçimlendirmesine bağlıdır ve kullanıcının
    kontrolü dışındadır (SAP'tan aktarılan dosyalarda sık görülür).
    str(1029458.0) -> '1029458.0' olur; noktayı silince '10294580' gibi
    YANLIŞ, fazladan '0' eklenmiş bir kod ortaya çıkardı — bu da faturadaki
    doğru koda ASLA eşleşmiyordu ve gerçekte var olan ürünler sistemde
    'master'da yok' olarak görünüyordu. Düzeltme: tam sayı değerli float'lar
    ondalık atılmadan ÖNCE int'e çevrilir."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"[^0-9A-Za-z]", "", str(value or ""))


def clean_gtip(value) -> str:
    """'[401110009012]' -> '401110009012'."""
    return re.sub(r"[^0-9.]", "", str(value or ""))


def _find_header_row(sheet_rows):
    best_row_idx, best_columns = 0, {}
    for row_idx, values in enumerate(sheet_rows[:20]):
        columns = {}
        for col_idx, value in enumerate(values):
            folded = _fold(value)
            if not folded:
                continue
            for field_name, aliases in HEADER_ALIASES.items():
                if field_name in columns:
                    continue
                if any(_fold(alias) == folded or _fold(alias) in folded for alias in aliases):
                    columns[field_name] = col_idx
        if len(columns) > len(best_columns):
            best_row_idx, best_columns = row_idx, columns
    return best_row_idx, best_columns


def load_master_katalog(path) -> MasterKatalog:
    """Master Excel'i okur. Ayni kod birden fazla kez geciyorsa ILK
    gorulen kullanilir, digerleri 'duplicate_codes' listesinde bilgi
    amacli tutulur (gercek kullanici dosyasinda bu tur yinelemeler
    genelde zararsiz/idari kopyalardir, isleme engel olmaz)."""
    sheet_rows = []
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.active
            sheet_rows = [tuple(row) for row in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
    except Exception:
        # Fallback: Eger dosya .xls (aslinda HTML tablosu) formatindaysa
        # openpyxl BadZipFile/InvalidFileException firlatir. Bu durumda HTML tablosunu isleriz.
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tr_blocks = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.IGNORECASE | re.DOTALL)
            if not tr_blocks:
                raise ValueError("Bozuk veya desteklenmeyen Excel formatı.")
            
            for tr in tr_blocks:
                td_blocks = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.IGNORECASE | re.DOTALL)
                row_vals = []
                for td in td_blocks:
                    val = re.sub(r'<[^>]+>', ' ', td)
                    val = re.sub(r'\s+', ' ', val).strip()
                    val = val.replace('&amp;', '&').replace('&nbsp;', ' ')
                    row_vals.append(int(val) if val.isdigit() else (val or None))
                if any(row_vals):
                    sheet_rows.append(tuple(row_vals))
        except Exception as e:
            raise ValueError(f"Dosya okunamadı (XLS/HTML ayrıştırma hatası): {str(e)}")

    if not sheet_rows:
        raise ValueError("Excel dosyası boş.")
    header_row_idx, columns = _find_header_row(sheet_rows)

    # Eger sutun eslestirmesi basarisiz olursa veya tum alanlar tek bir sutuna
    # denk gelmisse (ornek: metin/baski ciktisi olarak kaydedilmis tek sutunlu Excel'ler)
    unique_col_indices = set(columns.values())
    if "product_code" not in columns or len(unique_col_indices) <= 1:
        # ---- ESNEK SATIR/METİN AYRIŞTIRICI FALLBACK ----
        katalog = MasterKatalog(columns_found={"fallback_text_mode": 0})
        for row_idx, values in enumerate(sheet_rows, start=1):
            line_str = " ".join(str(v or "") for v in values if v is not None)
            code_m = re.search(r"\[(\d{6,8})\]", line_str)
            gtip_m = re.search(r"\[(\d{12})\]", line_str)
            if code_m and gtip_m:
                code = clean_code(code_m.group(1))
                gtip = clean_gtip(gtip_m.group(1))
                if not code or code in katalog.rows_by_code:
                    if code:
                        katalog.duplicate_codes.append(code)
                    continue

                agreement = None
                for ag in ["KORE", "AT", "DÜ", "DU"]:
                    if re.search(r"\b" + ag + r"\b", line_str, re.IGNORECASE):
                        agreement = "KORE" if ag.upper() == "KORE" else ("AT" if ag.upper() == "AT" else "DÜ")
                        break

                katalog.rows_by_code[code] = MasterRow(
                    product_code=code,
                    description="TYRE",
                    turkish_description=None,
                    gtip=gtip,
                    origin=None,
                    agreement_code=agreement,
                    status="Active",
                    row_number=row_idx,
                )
        katalog.row_count = len(katalog.rows_by_code)
        if katalog.row_count > 0:
            return katalog

        raise ValueError(
            "Master Excel'de 'Ürün Kodu' sütunu bulunamadı ve esnek metin arama da ürün tespiti yapamadı."
        )

    def cell(values, field_name):
        idx = columns.get(field_name)
        if idx is None or idx >= len(values):
            return None
        return values[idx]

    katalog = MasterKatalog(columns_found=columns)
    for row_idx, values in enumerate(sheet_rows[header_row_idx + 1:], start=header_row_idx + 2):
        code = clean_code(cell(values, "product_code"))
        if not code:
            continue
        if code in katalog.rows_by_code:
            katalog.duplicate_codes.append(code)
            continue
        katalog.rows_by_code[code] = MasterRow(
            product_code=code,
            description=str(cell(values, "description") or "").strip(),
            turkish_description=(str(cell(values, "turkish_description") or "").strip() or None),
            gtip=(clean_gtip(cell(values, "gtip")) or None),
            origin=(str(cell(values, "origin") or "").strip() or None),
            agreement_code=(str(cell(values, "agreement_code") or "").strip().upper() or None),
            status=(str(cell(values, "status") or "").strip() or None),
            row_number=row_idx,
        )
    katalog.row_count = len(katalog.rows_by_code)
    if not katalog.rows_by_code:
        raise ValueError("Master Excel'de kullanılabilir hiçbir ürün kaydı bulunamadı.")
    return katalog
