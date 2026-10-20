"""
config.py — Kullanıcı ayarlarını JSON dosyasına kaydeder/okur.
"""

import json, os

CONFIG_PATH = r"C:\HANKOOK_OPERASYON_MASASI\ayarlar.json"

VARSAYILAN = {
    "rapor_yolu": r"\\Dgfile01\ithalat\ITH28\Halit ENGELEK\RAPOR\HANKOOK İŞ TAKİP RAPORU.xlsx",
}


def oku() -> dict:
    """Config dosyasını okur. Yoksa varsayılanları döner."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Eksik anahtarları varsayılanla doldur
            for k, v in VARSAYILAN.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(VARSAYILAN)


def kaydet(data: dict):
    """Config dosyasına yazar."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def rapor_yolu() -> str:
    return oku()["rapor_yolu"]


def rapor_yolu_kaydet(yol: str):
    data = oku()
    data["rapor_yolu"] = yol
    kaydet(data)
