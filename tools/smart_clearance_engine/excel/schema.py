# -*- coding: utf-8 -*-
"""
schema.py — EXCEL_AKTARIM sablonunun sutun duzeni (1-tabanli openpyxl index)
ve sabit degerler. Sablon degisirse SADECE bu dosya guncellenir.

Kullanicinin onayladigi sabitler (2026-07-14):
- A,B,C,D,E: HER ZAMAN BOS birakilir (dokunulmaz).
- Islem Niteligi=11, Kullanilmis="K1", Siparis turu=9, Edi Belge Kod="0100":
  HER SATIRDA SABIT (kullanici onayladi).
- Referans = [Siparis No]/HNKRE: HER ZAMAN BU FORMATTA (kullanici onayladi).
"""

FIRST_DATA_ROW = 2  # sadece 1. satir baslik
TOTAL_COLS = 24

COL_QUANTITY = 6          # F - Quantity
COL_BIRIM = 7              # G - (basliksiz) birim, orn. "AD"
COL_CMMF = 9                # I - CMMF (malzeme/urun kodu)
COL_NET_PRICE = 11           # K - Net price (birim fiyat)
COL_CURRENCY = 12             # L - (basliksiz) para birimi
COL_COO = 13                    # M - COO (mense ulke kodu)
COL_BRUT = 14                     # N - Brüt (brut agirlik, KG)
COL_NET = 15                        # O - Net (net agirlik, KG)
COL_FATURA = 16                       # P - Fatura (fatura no)
COL_FATURA_TARIHI = 17                  # Q - Fatura Tarihi
COL_REFERANS = 18                         # R - Referans ([Siparis No]/HNKRE)
COL_ISLEM_NITELIGI = 19                     # S - Islem Niteligi (sabit)
COL_KULLANILMIS = 20                          # T - Kullanilmis (sabit)
COL_SIPARIS_TURU = 21                           # U - Siparis turu (sabit)
COL_KAP = 22                                      # V - Kap (bos birakilir)
COL_EDI_BELGE_KOD = 24                              # X - Edi Belge Kod (sabit)

# --- Sabit degerler (kullanici onayladi, 2026-07-14) ---------------------
BIRIM_SABIT = "AD"
ISLEM_NITELIGI_SABIT = 11
KULLANILMIS_SABIT = "K1"
SIPARIS_TURU_SABIT = 9
EDI_BELGE_KOD_SABIT = "0100"
REFERANS_SUFFIX = "/HNKRE"
VARSAYILAN_PARA_BIRIMI = "TL"

# --- Mense ulke kodlari (Turkiye gumruk ulke kod listesi, ticaret.gov.tr) -
COO_CODE_MAP = {
    "KOREA": "728",    # Güney Kore Cumhuriyeti
    "HUNGARY": "064",  # Macaristan
    "CHINA": "052",    # Çin Halk Cumhuriyeti
}
