"""
apex_data_engine.py — SmartClearance Apex Veri Yükleme ve Operasyonel Risk Analiz Motoru
"""

import os
import datetime
import openpyxl
from PyQt6.QtCore import QThread, pyqtSignal

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.exists(r"C:\HANKOOK_OPERASYON_MASASI\ayarlar.json"):
    DEFAULT_CONFIG_PATH = r"C:\HANKOOK_OPERASYON_MASASI\ayarlar.json"
else:
    DEFAULT_CONFIG_PATH = os.path.join(_BASE_DIR, "ayarlar.json")


def _safe_date(val):
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    return None


class Durum:
    DEMURAJ_RISKI   = "DEMURAJ_RISKI"    # 🔴 Varış üzerinden 7+ gün geçmiş, tescilsiz
    BANKA_ID_BEKLER = "BANKA_ID_BEKLER"  # 🟠 Banka ID / Dekont bekleyenler
    TAREKS_DENETIM  = "TAREKS_DENETIM"   # 🟣 TAREKS fiili denetime gidenler
    ORDINO_BEKLER   = "ORDINO_BEKLER"    # 🟡 Ordino bekleniyor
    ETA_YAKLASAN    = "ETA_YAKLASAN"     # 🔵 ETA ≤ 7 gün olanlar
    TESCIL_BEKLER   = "TESCIL_BEKLER"    # 🟢 Tescil olmuş, kapanış bekliyor
    DOSYA_YOK       = "DOSYA_YOK"        # ⚪ Raporlanmış ama dosya no açılmamış
    NORMAL          = "NORMAL"           # ⚪ Diğer açık dosyalar


DURUM_BILGILERI = {
    Durum.DEMURAJ_RISKI:   {"label": "Demuraj Riski",    "color": "#f43f5e", "bg": "rgba(244, 63, 94, 0.15)",  "icon": "🚨"},
    Durum.BANKA_ID_BEKLER: {"label": "Banka ID Bekler",  "color": "#f97316", "bg": "rgba(249, 115, 22, 0.15)", "icon": "🏦"},
    Durum.TAREKS_DENETIM:  {"label": "TAREKS Denetim",   "color": "#a855f7", "bg": "rgba(168, 85, 247, 0.15)", "icon": "🔬"},
    Durum.ORDINO_BEKLER:   {"label": "Ordino Bekler",    "color": "#eab308", "bg": "rgba(234, 179, 8, 0.15)",  "icon": "⚓"},
    Durum.ETA_YAKLASAN:    {"label": "Yaklaşan ETA",     "color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.15)", "icon": "🚢"},
    Durum.TESCIL_BEKLER:   {"label": "Tescilli / Açık",  "color": "#10b981", "bg": "rgba(16, 185, 129, 0.15)", "icon": "🟢"},
    Durum.DOSYA_YOK:       {"label": "Dosya Açılmadı",   "color": "#94a3b8", "bg": "rgba(148, 163, 184, 0.12)","icon": "⚪"},
    Durum.NORMAL:          {"label": "Normal Açık",      "color": "#cbd5e1", "bg": "rgba(203, 213, 225, 0.10)","icon": "📁"},
}


class ApexDataLoader:
    """Excel raporunu okur, verileri zenginleştirir ve iş akışı aşamalarını tayin eder."""

    @staticmethod
    def load_from_excel(file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Rapor dosyası bulunamadı: {file_path}")

        today = datetime.date.today()
        # Hafta sonu aralığını belirle (Pazartesi günü: Cumartesi ve Pazar)
        if today.weekday() == 0:  # Pazartesi
            sat_date = today - datetime.timedelta(days=2)
            sun_date = today - datetime.timedelta(days=1)
        elif today.weekday() == 5:  # Cumartesi
            sat_date = today
            sun_date = today + datetime.timedelta(days=1)
        elif today.weekday() == 6:  # Pazar
            sat_date = today - datetime.timedelta(days=1)
            sun_date = today
        else:  # Salı - Cuma: En son geçen hafta sonu
            sat_date = today - datetime.timedelta(days=today.weekday() + 2)
            sun_date = today - datetime.timedelta(days=today.weekday() + 1)

        rows = []

        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        ws = wb.active

        for r_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or len(row) < 3:
                continue

            dosya_no      = row[0] if len(row) > 0 else None
            gumruk        = row[1] if len(row) > 1 else None
            po            = row[2] if len(row) > 2 else None
            bayi          = row[3] if len(row) > 3 else None
            acenta_bilgi  = row[4] if len(row) > 4 else None
            bl_no         = row[5] if len(row) > 5 else None
            ordino_t      = row[6] if len(row) > 6 else None
            transfer_t    = row[7] if len(row) > 7 else None
            tareks_b      = row[8] if len(row) > 8 else None
            tareks_s      = row[9] if len(row) > 9 else None
            fiili_denetim = row[10] if len(row) > 10 else None
            tescil_t      = row[11] if len(row) > 11 else None
            hat_bilgi     = row[12] if len(row) > 12 else None
            kapanis_t     = row[13] if len(row) > 13 else None
            vergi_t       = row[14] if len(row) > 14 else None
            cikis_t       = row[15] if len(row) > 15 else None
            aciklama1     = row[16] if len(row) > 16 else None
            aciklama2     = row[17] if len(row) > 17 else None
            varis_t       = row[18] if len(row) > 18 else None
            eta_t         = row[19] if len(row) > 19 else None
            konteyner     = row[20] if len(row) > 20 else None
            liman         = row[21] if len(row) > 21 else None
            gemi          = row[22] if len(row) > 22 else None
            kantar        = row[23] if len(row) > 23 else None

            # Boş satırları atla
            if not po and not dosya_no:
                continue

            # Kapanmış dosyaları atla
            if kapanis_t:
                continue

            acik2_str = str(aciklama2 or "").upper()
            acik1_str = str(aciklama1 or "").upper()
            fd_str    = str(fiili_denetim or "").upper()

            varis_d   = _safe_date(varis_t)
            eta_d     = _safe_date(eta_t)
            tescil_d  = _safe_date(tescil_t)
            ordino_d  = _safe_date(ordino_t)

            gun_gecti = 0
            gun_kalan = -1

            # ─── Durum ve Risk Tespiti ─────────────────────────────────────────
            if varis_d:
                gun_gecti = (today - varis_d).days

            if eta_d:
                gun_kalan = (eta_d - today).days

            if tescil_d:
                durum = Durum.TESCIL_BEKLER
                stage = 5
                next_action = "Beyanname tescil edildi. Vergi ödemesi ve liman kapı çıkışı organize edilmeli."
            elif "DENET" in fd_str or "HEYET" in fd_str:
                durum = Durum.TAREKS_DENETIM
                stage = 4
                next_action = "TAREKS fiili denetim heyet randevusu ve numune/inceleme süreci takip edilmeli."
            elif ("BANKA" in acik2_str or "ID BEKLER" in acik2_str or "BANKA" in acik1_str):
                if varis_d and gun_gecti >= 7:
                    durum = Durum.DEMURAJ_RISKI
                    stage = 5
                    next_action = f"🚨 KRİTİK DEMURAJ: Varış üzerinden {gun_gecti} gün geçti! Müşteriden acil banka ID alınıp tescil verilmeli."
                else:
                    durum = Durum.BANKA_ID_BEKLER
                    stage = 5
                    next_action = "Müşteriden banka referans ID'si temin edilmeli ve tescil işlemi tamamlanmalı."
            elif varis_d and gun_gecti >= 7:
                durum = Durum.DEMURAJ_RISKI
                stage = 3 if not ordino_d else 5
                next_action = f"🚨 KRİTİK DEMURAJ: Varış üzerinden {gun_gecti} gün geçti! Liman serbest süresi aşılmış olabilir."
            elif "ORD" in acik2_str or (varis_d and not ordino_d):
                durum = Durum.ORDINO_BEKLER
                stage = 3
                next_action = "Acenta ordino bedeli ödenmeli ve ordino belgesi teslim alınmalı."
            elif eta_d and 0 <= gun_kalan <= 7:
                durum = Durum.ETA_YAKLASAN
                stage = 1
                next_action = f"Gemi {gun_kalan} gün içinde limana yanaşacak. Evrak ve master data kontrolleri yapılabilir."
            elif not dosya_no and po:
                durum = Durum.DOSYA_YOK
                stage = 1
                next_action = "Evrim sisteminde dosya numarası açılmalı ve operasyon takip raporuna işlenmeli."
            else:
                durum = Durum.NORMAL
                stage = 2 if varis_d else 1
                next_action = "Gemi ve sevkiyat seyri normal akışında takip ediliyor."

            # Hafta sonu ve bugün varış kontrolleri
            primary_d = varis_d or eta_d
            hafta_sonu_geldi = False
            hafta_sonu_gunu = ""
            bugun_geldi = False

            if primary_d:
                if primary_d == sat_date:
                    hafta_sonu_geldi = True
                    hafta_sonu_gunu = "Cumartesi"
                elif primary_d == sun_date:
                    hafta_sonu_geldi = True
                    hafta_sonu_gunu = "Pazar"
                elif primary_d == today:
                    bugun_geldi = True
                    hafta_sonu_gunu = "Bugün (Pazartesi)" if today.weekday() == 0 else "Bugün"

            # Dosya no kontrolü
            dosya_var = bool(dosya_no and str(dosya_no).strip() not in ("", "—", "None", "-"))
            hafta_sonu_dosyasiz = hafta_sonu_geldi and not dosya_var
            bugun_dosyasiz = bugun_geldi and not dosya_var

            # PO No format temizleme
            po_clean = str(int(po)) if isinstance(po, (int, float)) else str(po or "—")

            rows.append({
                "row_idx":             r_idx,
                "dosya_no":            str(dosya_no).strip() if dosya_no else "—",
                "gumruk":              str(gumruk or "—"),
                "po":                  po_clean,
                "bayi":                str(bayi or "—"),
                "acenta":              str(acenta_bilgi or "—"),
                "bl_no":               str(bl_no or "—"),
                "ordino_t":            ordino_d.strftime("%d.%m.%Y") if ordino_d else "—",
                "transfer_t":          str(transfer_t or "—"),
                "tareks_b":            str(tareks_b or "—"),
                "tareks_s":            str(tareks_s or "—"),
                "fiili_denetim":       str(fiili_denetim or "—"),
                "tescil_t":            tescil_d.strftime("%d.%m.%Y") if tescil_d else "—",
                "hat_bilgi":           str(hat_bilgi or "—"),
                "kapanis_t":           "—",
                "aciklama1":           str(aciklama1 or "").strip(),
                "aciklama2":           str(aciklama2 or "").strip(),
                "varis_t":             varis_d.strftime("%d.%m.%Y") if varis_d else "—",
                "eta_t":               eta_d.strftime("%d.%m.%Y") if eta_d else "—",
                "varis_date":          varis_d,
                "eta_date":            eta_d,
                "primary_date":        primary_d,
                "hafta_sonu_geldi":    hafta_sonu_geldi,
                "hafta_sonu_gunu":     hafta_sonu_gunu,
                "hafta_sonu_dosyasiz": hafta_sonu_dosyasiz,
                "bugun_geldi":         bugun_geldi,
                "bugun_dosyasiz":      bugun_dosyasiz,
                "konteyner":           str(konteyner or "—"),
                "liman":               str(liman or "—"),
                "gemi":                str(gemi or "—"),
                "kantar":              str(kantar or "—"),
                "durum":               durum,
                "durum_info":          DURUM_BILGILERI.get(durum, DURUM_BILGILERI[Durum.NORMAL]),
                "gun_gecti":           gun_gecti,
                "gun_kalan":           gun_kalan,
                "stage":               stage,
                "next_action":         next_action
            })

        wb.close()

        # KPI İstatistikleri
        kpi = {
            "total":               len(rows),
            "demuraj":             sum(1 for r in rows if r["durum"] == Durum.DEMURAJ_RISKI),
            "banka":               sum(1 for r in rows if r["durum"] == Durum.BANKA_ID_BEKLER),
            "tareks":              sum(1 for r in rows if r["durum"] == Durum.TAREKS_DENETIM),
            "ordino":              sum(1 for r in rows if r["durum"] == Durum.ORDINO_BEKLER),
            "eta":                 sum(1 for r in rows if r["durum"] == Durum.ETA_YAKLASAN),
            "dosyayok":            sum(1 for r in rows if r["durum"] == Durum.DOSYA_YOK),
            "haftasonu_gelen":     sum(1 for r in rows if r["hafta_sonu_geldi"]),
            "haftasonu_dosyasiz":  sum(1 for r in rows if r["hafta_sonu_dosyasiz"]),
            "bugun_gelen":         sum(1 for r in rows if r["bugun_geldi"]),
            "bugun_dosyasiz":      sum(1 for r in rows if r["bugun_dosyasiz"]),
            "is_monday":           today.weekday() == 0,
            "sat_date_str":        sat_date.strftime("%d.%m.%Y"),
            "sun_date_str":        sun_date.strftime("%d.%m.%Y"),
            "today_str":           today.strftime("%d.%m.%Y"),
        }

        # Sıralama: Demuraj en üstte, sonra Banka ID, sonra TAREKS, sonra Ordino
        oncelik_sirasi = {
            Durum.DEMURAJ_RISKI:   0,
            Durum.BANKA_ID_BEKLER: 1,
            Durum.TAREKS_DENETIM:  2,
            Durum.ORDINO_BEKLER:   3,
            Durum.ETA_YAKLASAN:    4,
            Durum.DOSYA_YOK:       5,
            Durum.TESCIL_BEKLER:   6,
            Durum.NORMAL:          7
        }
        rows.sort(key=lambda x: (oncelik_sirasi.get(x["durum"], 99), -x["gun_gecti"]))

        return rows, kpi


class DataLoaderThread(QThread):
    """Arayüzü dondurmadan Excel dosyasını arka planda okuyan iş parçacığı."""
    finished = pyqtSignal(list, dict)
    error    = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            items, kpi = ApexDataLoader.load_from_excel(self.file_path)
            self.finished.emit(items, kpi)
        except Exception as e:
            self.error.emit(str(e))
