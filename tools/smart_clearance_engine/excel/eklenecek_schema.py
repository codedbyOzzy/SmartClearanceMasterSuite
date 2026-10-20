# -*- coding: utf-8 -*-
"""
eklenecek_schema.py — "mastera eklenecek ürünler" sablonunun sutun duzeni
(gercek kullanici dosyasiyla dogrulandi, 2026-07-14).

Sadece MASTER'DA OLMAYAN (yeni) urunler icin satir uretilir. GTIP/Turkce
Tanim/Anlasma Kodu gibi gercek siniflandirma bilgisi gerektiren alanlar
BILINCLI OLARAK BOS BIRAKILIR — bunlar insan gumruk uzmanligi gerektirir,
tahmin edilmez.
"""

FIRST_DATA_ROW = 3  # 1. satir "ZORUNLU" etiketi, 2. satir gercek sutun adi, veri 3'ten baslar
TOTAL_COLS = 37

COL_FIRMA_EVRIM_NO = 1
COL_IHRACATCI_EVRIM_NO = 2
COL_YABANCI_TANIM = 3
COL_TURKCE_TANIM = 4
COL_URUN_KODU = 5
COL_GTIP = 7
COL_MUAF1 = 8
COL_MUAF2 = 9
COL_MENSEI = 10
COL_ANLASMA_KODU = 12
COL_TARIM_FONU = 13
COL_ILISKI = 14
COL_ROYALTI = 15
COL_DFIF = 16
COL_AMBARGO = 17
COL_KDV_ORAN = 18
COL_KALEM_NOTU = 20
COL_TIP = 34

# --- Kullanici onayladigi sabitler (2026-07-14) ---------------------------
FIRMA_EVRIM_NO = 9122
IHRACATCI_EVRIM_NO = 413049
ILISKI_SABIT = "VAR"
ROYALTI_SABIT = "YOK"
DFIF_SABIT = "YOK"
AMBARGO_SABIT = "YOK"
KDV_ORAN_SABIT = 20
TIP_SABIT = "T"

# Mense ulke -> Evrim'de yazilan Turkce ulke adi
ORIGIN_DISPLAY_NAME = {
    "KOREA": "Kore Cumhuriyeti",
    "HUNGARY": "Macaristan",
    "CHINA": "Çin",
}
