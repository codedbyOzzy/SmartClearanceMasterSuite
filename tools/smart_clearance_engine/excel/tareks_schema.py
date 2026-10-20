# -*- coding: utf-8 -*-
"""
tareks_schema.py — TAREKSTASLAK.xlsx'in 35 sutunlu yapisinin sabit degerleri.
Sutun numaralari 1-tabanli (openpyxl standardi).
Sablon degisirse SADECE bu dosya guncellenir.
"""

FIRST_DATA_ROW = 2   # 1. satir baslik, veri 2. satirdan baslar
TOTAL_COLS = 35
SHEET_NAME = "TAREKSTASLAK"

# --- Sutun numaralari -------------------------------------------------------
COL_GTIP          = 1    # A - Gtip No
COL_MENSE         = 2    # B - Mense Ulke Kodu
COL_BELGE_TURU    = 3    # C - Belge Turu
COL_BELGE_TARIHI  = 4    # D - Belge Tarihi
COL_BELGE_NO      = 5    # E - Belge No
COL_ON_IZIN       = 6    # F - On Izin          (bos)
COL_MUAFIYET      = 7    # G - Muafiyet
COL_MUAFIYET_NO   = 8    # H - Muafiyet No      (bos)
COL_TICARI_TANIM  = 9    # I - Ticari Tanim
COL_FATURA_TARIHI = 10   # J - Fatura Tarihi
COL_FATURA_NO     = 11   # K - Fatura No
COL_MIKTAR        = 12   # L - Miktar
COL_MIKTAR_CINSI  = 13   # M - Miktar Cinsi
COL_KALEM_FIYAT   = 14   # N - Kalem Fiyat
COL_KAP_ADEDI     = 15   # O - Kap Adedi
COL_TAREKS_REF    = 16   # P - Tareks Ref No    (bos)
COL_KONTEYNER     = 17   # Q - Konteyner No
COL_OZL_UNVAN     = 18   # R - OZL-Imalatci Unvani
COL_OZL_ADRES     = 19   # S - OZL-Imalatci Adresi
COL_OZL_TELEFON   = 20   # T - OZL-Imalatci Telefonu
COL_OZL_MARKA     = 21   # U - OZL-Marka
COL_OZL_MODEL     = 22   # V - OZL-Model
COL_OZL_URUN_ADI  = 23   # W - OZL-Urun Adi
# 24-33: TAREKS sistem alanlari (ID, Dosya No, Detay No vs.) — bos birakilir
COL_SOGUK_ZINCIR  = 34   # b - Soguk Zincir     (bos)
COL_KAPSAM_DI     = 35   # c - Kapsam Disi      (bos)

# --- Basliklar (1. satir) ---------------------------------------------------
HEADERS = {
    COL_GTIP:          "Gtip No",
    COL_MENSE:         "Men\u015fe \u00dclke Kodu",
    COL_BELGE_TURU:    "Belge T\u00fcr\u00fc",
    COL_BELGE_TARIHI:  "Belge Tarihi",
    COL_BELGE_NO:      "Belge No",
    COL_ON_IZIN:       "\u00d6n \u0130zin",
    COL_MUAFIYET:      "Muafiyet",
    COL_MUAFIYET_NO:   "Muafiyet No",
    COL_TICARI_TANIM:  "Ticari Tan\u0131m",
    COL_FATURA_TARIHI: "Fatura Tarihi",
    COL_FATURA_NO:     "Fatura No",
    COL_MIKTAR:        "Miktar",
    COL_MIKTAR_CINSI:  "Miktar Cinsi",
    COL_KALEM_FIYAT:   "Kalem Fiyat",
    COL_KAP_ADEDI:     "Kap Adedi",
    COL_TAREKS_REF:    "Tareks Ref No",
    COL_KONTEYNER:     "Konteyner No",
    COL_OZL_UNVAN:     "OZL-\u0130malat\u00e7\u0131 \u00dcnvan\u0131",
    COL_OZL_ADRES:     "OZL-\u0130malat\u00e7\u0131 Adresi",
    COL_OZL_TELEFON:   "OZL-\u0130malat\u00e7\u0131 Telefonu",
    COL_OZL_MARKA:     "OZL-Marka",
    COL_OZL_MODEL:     "OZL-Model",
    COL_OZL_URUN_ADI:  "OZL-\u00dcr\u00fcn Ad\u0131",
    24: "ID",
    25: "Dosya No",
    26: "Detay No",
    27: "G\u00f6nder",
    28: "Madde No",
    29: "Tebli\u011f \u00d6zel Soru",
    30: "Ba\u015fvuru Durumu",
    31: "Ba\u015fvuru Referans No",
    32: "Sat\u0131r No",
    33: "Ta\u015f\u0131ma Senedi No",
    COL_SOGUK_ZINCIR:  "So\u011fuk Zincir",
    COL_KAPSAM_DI:     "Kapsam D\u0131\u015f\u0131",
}

# --- Sabit degerler ---------------------------------------------------------
BELGE_TURU_SABIT   = "KON\u015e\u0130MENTO"
MIKTAR_CINSI_SABIT = "C62"
KAP_ADEDI_SABIT    = "1"
GONDER_SABIT       = True   # boolean True -> Excel t="b" <v>1</v> -> FireDAC NOT NULL icin garantili

# --- Mense ulke kodlari -----------------------------------------------------
MENSE_KOD_MAP = {
    "KOREA":   "728",
    "HUNGARY": "064",
    "CHINA":   "052",
}

# --- OZL-Imalatci bilgileri (marka bazli) -----------------------------------
# LAUFEN, Hankook'un bir markasidir — ayni imalatci bilgileri kullanilir.
OZL_IMALATCI_MAP = {
    "HANKOOK": {
        "unvan":   "HANKOOK TIRE & TECHNOLOGY CO. LTD",
        "adres":   "286, PANGYO-RO BUNDANG-GU, SEONGNAM-SI GYEONGGI-DO KOREA",
        "telefon": "-",
    },
    "LAUFEN": {
        "unvan":   "HANKOOK TIRE & TECHNOLOGY CO. LTD",
        "adres":   "286, PANGYO-RO BUNDANG-GU, SEONGNAM-SI GYEONGGI-DO KOREA",
        "telefon": "-",
    },
}
