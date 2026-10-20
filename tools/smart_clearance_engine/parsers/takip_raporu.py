# -*- coding: utf-8 -*-
"""
takip_raporu.py — Şefin firmaya (Hankook) gönderdiği "İş Takip Raporu"
Excel'ini OKUR. Bu dosyanın yapısına ASLA yazılmaz/dokunulmaz — firma
formatı hassas, sistem sadece mevcut halini web'e yansıtmak için parse
eder (master_katalog.py'deki esnek başlık eşleştirme deseniyle aynı).

Gerçek dosyada (HANKOOK_İŞ_TAKİP_RAPORU.xlsx) doğrulanmış başlıklar:
DOSYA NO, GÜMRÜK, REFERANS NO, BAYİ, Gemi acenta Bilgisi, Konşimento,
ORDİNO TESLİM TARİHİ, TRANSFER TARİHİ, TAREKS BAŞVURU TARİHİ,
TAREKS SONUÇ TARİHİ, FİİLİ DENETİM TARİHİ, TESCİL TARİHİ, HAT BİLGİSİ,
KAPANIŞ TARİHİ, VERGİ ÖDEME TARİHİ, LİMAN ÇIKIŞ TARİHİ, AÇIKLAMALAR 1,
AÇIKLAMALAR 2, VARIŞ TARİHİ, ETA, Konteyner, Liman, Gemi, Kantar talebi.

BİRİNCİL ANAHTAR: REFERANS NO (PO numarası), DOSYA NO DEĞİL.
Gerçek dosyada 665 satırın 101'inde (kullanıcı ile birlikte doğrulandı)
Dosya No BOŞ ama Referans No dolu — bunlar "PO açıldı ama Evrim'de gümrük
dosyası henüz açılmamış" işleridir ve tam olarak takip edilmesi gereken,
aksiyon bekleyen kayıtlardır. Referans No ise gözlemlenen tüm satırlarda
her zaman dolu ("firmanın kalbi", kullanıcının kendi tabiriyle). Bu yüzden
Dosya No BOŞSA satır ATLANMAZ; sadece normal bir alan olarak boş kalır ve
arayüzde "DOSYA AÇILMAMIŞ" uyarısı üretir (bkz. app/routers/takip.py).

NOT: TRANSFER TARİHİ sütunu bazen gerçek bir tarih, bazen "MAL MUKABİLİ"
gibi bir ÖDEME ŞEKLİ metni taşıyor (0887 Transfer Bildirim Formu kuralıyla
aynı ayrım — bkz. app/domain/declaration_rules.py). Bu yüzden bu alan
tarih olarak PARSE EDİLMEZ, olduğu gibi metin olarak saklanır.
"""
import datetime as dt
import re

import openpyxl

# field_name -> bu alanın gerçek dosyada karşılık geldiği başlık(lar).
# Eşleştirme TAM (fold edilmiş) metin üzerinden yapılır; yanlışlıkla bir
# alanın bir diğerinin alt-string'i olması riskine karşı (örn. "Gemi" ile
# "Gemi acenta Bilgisi") substring eşleşmesi KULLANILMAZ.
HEADER_ALIASES = {
    "referans_no": ["referans no"],
    "dosya_no": ["dosya no"],
    "gumruk": ["gumruk"],
    "bayi": ["bayi"],
    "acenta": ["gemi acenta bilgisi", "acenta bilgisi"],
    "konsimento": ["konsimento"],
    "ordino_teslim_tarihi": ["ordino teslim tarihi"],
    "transfer_tarihi": ["transfer tarihi"],
    "tareks_basvuru_tarihi": ["tareks basvuru tarihi"],
    "tareks_sonuc_tarihi": ["tareks sonuc tarihi"],
    "fiili_denetim_tarihi": ["fiili denetim tarihi"],
    "tescil_tarihi": ["tescil tarihi"],
    "hat_bilgisi": ["hat bilgisi"],
    "kapanis_tarihi": ["kapanis tarihi"],
    "vergi_odeme_tarihi": ["vergi odeme tarihi"],
    "liman_cikis_tarihi": ["liman cikis tarihi"],
    "aciklamalar_1": ["aciklamalar 1"],
    "aciklamalar_2": ["aciklamalar 2"],
    "varis_tarihi": ["varis tarihi"],
    "eta": ["eta"],
    "konteyner": ["konteyner"],
    "liman": ["liman"],
    "gemi": ["gemi"],
    "kantar_talebi": ["kantar talebi"],
}

# Alanların ekranda/tarihçede gösterileceği okunur Türkçe etiketler.
# (referans_no burada YOK — artık sayfa başlığı/anahtar, ayrı bir "alan"
# olarak tekrar gösterilmiyor.)
FIELD_LABELS = {
    "dosya_no": "Dosya No",
    "gumruk": "Gümrük",
    "bayi": "Bayi",
    "acenta": "Gemi Acenta Bilgisi",
    "konsimento": "Konşimento",
    "ordino_teslim_tarihi": "Ordino Teslim Tarihi",
    "transfer_tarihi": "Transfer Tarihi",
    "tareks_basvuru_tarihi": "Tareks Başvuru Tarihi",
    "tareks_sonuc_tarihi": "Tareks Sonuç Tarihi",
    "fiili_denetim_tarihi": "Fiili Denetim Tarihi",
    "tescil_tarihi": "Tescil Tarihi",
    "hat_bilgisi": "Hat Bilgisi",
    "kapanis_tarihi": "Kapanış Tarihi",
    "vergi_odeme_tarihi": "Vergi Ödeme Tarihi",
    "liman_cikis_tarihi": "Liman Çıkış Tarihi",
    "aciklamalar_1": "Açıklamalar 1",
    "aciklamalar_2": "Açıklamalar 2",
    "varis_tarihi": "Varış Tarihi",
    "eta": "ETA",
    "konteyner": "Konteyner",
    "liman": "Liman",
    "gemi": "Gemi",
    "kantar_talebi": "Kantar Talebi",
}

# Detay ekranında bu sırayla gösterilir. Dosya No EN BAŞTA — boşsa hemen
# fark edilsin diye (bkz. takip_raporu_detay.html'deki uyarı banner'ı).
DETAY_ALAN_SIRASI = [
    "dosya_no", "gumruk", "bayi", "acenta", "konsimento",
    "ordino_teslim_tarihi", "transfer_tarihi", "tareks_basvuru_tarihi",
    "tareks_sonuc_tarihi", "fiili_denetim_tarihi", "tescil_tarihi",
    "hat_bilgisi", "kapanis_tarihi", "vergi_odeme_tarihi",
    "liman_cikis_tarihi", "aciklamalar_1", "aciklamalar_2",
    "varis_tarihi", "eta", "konteyner", "liman", "gemi", "kantar_talebi",
]


def _fold(value) -> str:
    """UYARI: Python'un yerleşik str.lower()'ı Türkçe 'İ' harfini önce
    'i' + BİRLEŞTİRİCİ NOKTA (U+0307) olarak ikiye böler (locale-bağımsız
    varsayılan davranış) — bu yüzden çeviri tablosu .lower()'DAN ÖNCE
    uygulanmalı, sonra değil (master_katalog.py'deki sıra ['.lower()' önce]
    bu yüzden 'TARİHİ' gibi İ içeren kelimelerde sessizce eşleşme
    kaçırıyordu; gerçek dosyayla test ederken yakalandı)."""
    text = str(value or "").strip()
    table = str.maketrans("çÇğĞıİöÖşŞüÜI", "ccggiioossuui")
    folded = text.translate(table).lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def _normalize_cell(value) -> str:
    """Tarih hücrelerini GG.AA.YYYY metnine çevirir; metin hücreleri
    (örn. 'MAL MUKABİLİ') olduğu gibi bırakılır; boş hücre '' olur."""
    if value is None:
        return ""
    if isinstance(value, (dt.datetime, dt.date)):
        return value.strftime("%d.%m.%Y")
    return str(value).strip()


def _find_header_row(sheet_rows):
    best_row_idx, best_columns = 0, {}
    for row_idx, values in enumerate(sheet_rows[:5]):
        columns = {}
        for col_idx, value in enumerate(values):
            folded = _fold(value)
            if not folded:
                continue
            for field_name, aliases in HEADER_ALIASES.items():
                if field_name in columns:
                    continue
                if any(_fold(alias) == folded for alias in aliases):
                    columns[field_name] = col_idx
        if len(columns) > len(best_columns):
            best_row_idx, best_columns = row_idx, columns
    return best_row_idx, best_columns


def load_takip_raporu(path):
    """Şefin excel'ini okur, her satırı bir dict olarak döner (dosya
    sırasıyla — aynı Referans No birden fazla kez geçiyorsa, dosyadaki
    sırasıyla, en eski en üstte). Yazma YOK, sadece okuma.

    Dosya No BOŞ olsa bile satır dahil edilir (bkz. modül docstring'i) —
    sadece Referans No boşsa satır atlanır."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        sheet_rows = [tuple(row) for row in ws.iter_rows(values_only=True)]
    finally:
        wb.close()

    header_row_idx, columns = _find_header_row(sheet_rows)
    if "referans_no" not in columns:
        raise ValueError(
            "Excel'de 'REFERANS NO' benzeri bir sütun bulunamadı. Başlık "
            "satırının ilk 5 satır içinde olduğundan emin olun."
        )

    def cell(values, field_name):
        idx = columns.get(field_name)
        if idx is None or idx >= len(values):
            return None
        return values[idx]

    rows = []
    for values in sheet_rows[header_row_idx + 1:]:
        referans_no = _normalize_cell(cell(values, "referans_no"))
        if not referans_no:
            continue
        row = {"referans_no": referans_no}
        for field_name in HEADER_ALIASES:
            if field_name == "referans_no":
                continue
            row[field_name] = _normalize_cell(cell(values, field_name))
        rows.append(row)

    if not rows:
        raise ValueError("Excel'de kullanılabilir hiçbir kayıt bulunamadı.")
    return rows, columns
