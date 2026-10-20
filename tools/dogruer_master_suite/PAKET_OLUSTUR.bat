@echo off
cd /d "%~dp0"
title Dogruer MasterSuite - Tasınabilir Paket Olusturucu
color 0A

echo.
echo ======================================================
echo   DOGRUER MASTERSUITE - TASИНABILIR PAKET OLUSTURUCU
echo ======================================================
echo.
echo Bu islem internet baglantisi gerektirir.
echo Python 3.12 Embeddable (~16 MB) indirilecek.
echo Tum paketler embed Python'a kurulacak.
echo Sonunda masaustunde bir ZIP dosyasi olusacak.
echo.
echo Hazır mısınız? Devam etmek icin bir tusa basin...
pause >nul

python PAKET_OLUSTUR.py

echo.
pause
