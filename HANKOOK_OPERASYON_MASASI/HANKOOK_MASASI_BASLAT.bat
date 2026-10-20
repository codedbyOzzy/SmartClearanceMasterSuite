@echo off
title Hankook Gümrük Operasyon Masası
cd /d "C:\HANKOOK_OPERASYON_MASASI"

set PYTHON="C:\Users\ozan.gemici\AppData\Local\Programs\Python\Python312\python.exe"

if exist %PYTHON% (
    %PYTHON% main.py
) else (
    echo HATA: Python bulunamadı!
    pause
)
pause
