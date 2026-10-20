@echo off
title "Hankook ve Dogruer Canli Operasyon Kokpiti"
cd /d "%~dp0"
echo =========================================================
echo    Hankook ve Dogruer Canli Operasyon Kokpiti Baslatiliyor...
echo =========================================================
python hankook_operasyon_kokpiti.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Bir sorun olustu.
    pause
)
