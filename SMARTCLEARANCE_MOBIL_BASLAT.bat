@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title SmartClearance Mobile Server (Apple / Vercel TMA & PWA)

echo =====================================================================
echo  SmartClearance Mobile Server (TMA & PWA Platformu)
echo  Dogruer Gumruk Musavirligi A.S. - Hankook Lastikleri A.S.
echo =====================================================================
echo.

:: Python Calistiriciyi Bul
set "PYTHON_EXE="

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :START_SERVER
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py -3"
    goto :START_SERVER
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :START_SERVER
)

echo [HATA] Python calistiricisi bulunamadi!
pause
exit /b 1

:START_SERVER
echo [BILGI] Mobil Sunucu Baslatiliyor (Port: 8888)...
echo.
echo  - Bilgisayardan Erisim : http://localhost:8888
echo  - Ayni Wi-Fi Agindan   : http://0.0.0.0:8888
echo.
echo [INFO] Telegram TMA veya Dis Dunyadan Baglanmak Icin:
echo        Cloudflare tüneli actiginizda: /mobilurl https://tüneliniz
echo.
echo Sunucuyu durdurmak icin CTRL+C tuslarina basiniz.
echo =====================================================================
echo.

%PYTHON_EXE% -m uvicorn smartclearance_mobile.mobile_server:app --host 0.0.0.0 --port 8888 --log-level info

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BILGI] Sunucu kapandi.
    pause
)
