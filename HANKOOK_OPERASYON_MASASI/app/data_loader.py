"""
data_loader.py
==============
İş Takip Raporu'ndan veri okuyup kategorilere ayırır.
QThread ile arka planda çalışır, ana thread'i bloke etmez.
"""

import datetime
import openpyxl
from PyQt6.QtCore import QThread, pyqtSignal

from .config import rapor_yolu as _cfg_rapor_yolu

# Dinamik: config'den okunur; main_window tarafından güncellenebilir
def get_rapor_yolu() -> str:
    return _cfg_rapor_yolu()

# Geriye uyumluluk için module-level alias (eski importlar için)
RAPOR_YOLU = get_rapor_yolu()

# Renk kategorileri için sabitler
class Durum:
    DEMURAJ_RISKI    = "DEMURAJ_RISKI"     # Kırmızı  — Banka ID bekleyen + 7+ gün geçmiş
    BANKA_ID_BEKLER  = "BANKA_ID_BEKLER"   # Turuncu  — Banka ID bekleyen
    TAREKS_DENETIM   = "TAREKS_DENETIM"    # Mor      — TAREKS fiili denetimde
    ORDINO_BEKLER    = "ORDINO_BEKLER"     # Sarı     — Ordino bekleniyor
    ETA_YAKLASAN     = "ETA_YAKLASAN"      # Mavi     — ETA ≤ 7 gün
    TESCIL_BEKLER    = "TESCIL_BEKLER"     # Gri açık — Tescil olmuş, kapanış bekliyor
    DOSYA_YOK        = "DOSYA_YOK"         # Koyu gri — Dosya no'su boş, sadece PO var
    NORMAL           = "NORMAL"            # Beyaz    — Diğer açık dosyalar


def _safe_date(val):
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    return None


def load_shipments(rapor_yolu: str = None):
    """
    İş takip raporunu okuyup satırları sözlük listesi olarak döner.
    rapor_yolu verilmezse config'den alınır.
    """
    yol = rapor_yolu or get_rapor_yolu()

    today = datetime.date.today()
    rows = []

    wb = openpyxl.load_workbook(yol, data_only=True, read_only=True)
    ws = wb.active

    for r_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Sütun indeksleri (0-tabanlı, başlık satırı 1=idx0)
        dosya_no      = row[0]   # A — DOSYA NO
        po            = row[2]   # C — REFERANS NO
        ordino        = row[6]   # G — ORDİNO TESLİM TARİHİ
        tareks_b      = row[8]   # I — TAREKS BAŞVURU TARİHİ
        tareks_s      = row[9]   # J — TAREKS SONUÇ TARİHİ
        fiili_denetim = row[10]  # K — FİİLİ DENETİM TARİHİ
        tescil        = row[11]  # L — TESCİL TARİHİ
        kapanis       = row[13]  # N — KAPANIŞ TARİHİ
        varis         = row[18]  # S — VARIŞ TARİHİ
        eta           = row[19]  # T — ETA
        liman         = row[21]  # V — Liman
        gemi          = row[22]  # W — Gemi
        aciklama1     = row[16]  # Q — AÇIKLAMALAR 1
        aciklama2     = row[17]  # R — AÇIKLAMALAR 2

        # Boş satır atla
        if not po and not dosya_no:
            continue

        acik2_str = str(aciklama2 or "").upper()
        acik1_str = str(aciklama1 or "").upper()
        fd_str    = str(fiili_denetim or "").upper()

        varis_d   = _safe_date(varis)
        eta_d     = _safe_date(eta)

        # Kapalı dosyaları atla (kapanış tarihi varsa)
        if kapanis:
            continue

        # --- Durum belirleme (öncelik sırası önemli) ---
        if tescil and not kapanis:
            durum = Durum.TESCIL_BEKLER
            gun_gecti = (today - _safe_date(tescil)).days if _safe_date(tescil) else 0
        elif "DENET" in fd_str:
            durum = Durum.TAREKS_DENETIM
            gun_gecti = (today - varis_d).days if varis_d else 0
        elif "BANKA" in acik2_str or "ID BEKLER" in acik2_str:
            if varis_d:
                gun_gecti = (today - varis_d).days
                durum = Durum.DEMURAJ_RISKI if gun_gecti >= 7 else Durum.BANKA_ID_BEKLER
            else:
                gun_gecti = 0
                durum = Durum.BANKA_ID_BEKLER
        elif "ORD" in acik2_str:
            durum = Durum.ORDINO_BEKLER
            gun_gecti = (today - varis_d).days if varis_d else 0
        elif eta_d and (eta_d - today).days <= 7 and (eta_d - today).days >= 0:
            durum = Durum.ETA_YAKLASAN
            gun_gecti = (eta_d - today).days  # ETA için kalan gün
        elif not dosya_no and po:
            durum = Durum.DOSYA_YOK
            gun_gecti = 0
        else:
            durum = Durum.NORMAL
            gun_gecti = 0

        rows.append({
            "row":           r_idx,
            "dosya_no":      str(dosya_no) if dosya_no else "—",
            "po":            str(int(po)) if po else "—",
            "gemi":          str(gemi) if gemi else "—",
            "liman":         str(liman) if liman else "—",
            "varis":         varis_d.strftime("%d.%m.%Y") if varis_d else "—",
            "eta":           eta_d.strftime("%d.%m.%Y") if eta_d else "—",
            "ordino":        _safe_date(ordino).strftime("%d.%m.%Y") if _safe_date(ordino) else "—",
            "tareks_s":      _safe_date(tareks_s).strftime("%d.%m.%Y") if _safe_date(tareks_s) else "—",
            "fiili_denetim": str(fiili_denetim) if fiili_denetim else "—",
            "tescil":        _safe_date(tescil).strftime("%d.%m.%Y") if _safe_date(tescil) else "—",
            "aciklama":      str(aciklama2 or aciklama1 or "—"),
            "durum":         durum,
            "gun_gecti":     gun_gecti,
        })

    wb.close()
    return rows


def compute_kpis(rows):
    """KPI kartları için sayım döner."""
    today = datetime.date.today()
    return {
        "demuraj":     sum(1 for r in rows if r["durum"] == Durum.DEMURAJ_RISKI),
        "banka_id":    sum(1 for r in rows if r["durum"] == Durum.BANKA_ID_BEKLER),
        "tareks":      sum(1 for r in rows if r["durum"] == Durum.TAREKS_DENETIM),
        "ordino":      sum(1 for r in rows if r["durum"] == Durum.ORDINO_BEKLER),
        "eta_7":       sum(1 for r in rows if r["durum"] == Durum.ETA_YAKLASAN),
        "dosya_yok":   sum(1 for r in rows if r["durum"] == Durum.DOSYA_YOK),
        "tescil":      sum(1 for r in rows if r["durum"] == Durum.TESCIL_BEKLER),
        "toplam":      len(rows),
        "tarih":       today.strftime("%d.%m.%Y %H:%M"),
    }


# ─── QThread veri yükleyici ───────────────────────────────────────────────────

class DataLoaderThread(QThread):
    """Raporu arka planda okur, bitti sinyali ile sonucu iletir."""
    finished = pyqtSignal(list, dict)   # (rows, kpis)
    error    = pyqtSignal(str)

    def __init__(self, rapor_yolu: str = None, parent=None):
        super().__init__(parent)
        # None ise config'den alınır
        self._rapor_yolu = rapor_yolu or get_rapor_yolu()

    def run(self):
        try:
            rows = load_shipments(self._rapor_yolu)
            kpis = compute_kpis(rows)
            self.finished.emit(rows, kpis)
        except Exception as e:
            self.error.emit(str(e))
