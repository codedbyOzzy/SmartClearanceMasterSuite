# SmartClearance MasterSuite v4.85 PRO - Yedek

Ana baslatici: `SMARTCLEARANCE_MASTERSUITE_PYQT_BASLAT.bat` (`python -m smartclearance_master_suite_pyqt.app_pyqt`)

## Kurulum (yeni bilgisayar)
1. Python 3.12 (64-bit) kurun.
2. `pip install -r requirements.txt` (BAT, `python-embed\python.exe` yoksa sistemdeki Python 3.12'yi kullanir).
3. `SMARTCLEARANCE_MASTERSUITE_PYQT_BASLAT.bat` dosyasina cift tiklayin.

## Icerik
- `smartclearance_master_suite_pyqt/` - PyQt6 ana uygulama
- `HANKOOK_OPERASYON_MASASI/` - Apex operasyon masasi, ayarlar
- `standalone_global_tracker/` - Horizon / kuresel ETA radari
- `smartclearance_mobile/` - mobil sunucu
- `tools/` - yardimci motorlar (GTB, Kantar, QNB, Telegram, Teams vb.)
- `*.bat` baslaticilar, `HANKOOK_IS_TAKIP_RAPORU_YEDEK.xlsx` is takip yedegi
- `requirements.txt` - bagimliliklar (Lib/ ve python-embed/ repoda yok)

## Gizli anahtarlar
Hapag-Lloyd `hapag_client_secret` ve `cma_session_cookie` degerleri guvenlik nedeniyle repodan cikarildi. Yeni bilgisayarda `standalone_global_tracker/radar_config.json` icine tekrar girin.

> Sirket verisi icerir; repo **Private** kalmalidir.
