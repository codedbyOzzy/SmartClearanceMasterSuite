@echo off
title "Dogruer - Operasyon ve Mail Guvenlik Kalkani"
cd /d "%~dp0"
echo =========================================================
echo    Dogruer - Operasyon ve Mail Guvenlik Kalkani Baslatiliyor...
echo =========================================================
python mail_guvenlik_kalkani.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Bir sorun olustu.
    pause
)
