@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title SmartClearance Web Ops Hub (Kokpit / GTB / Kantar)

echo ================================================================
echo  SmartClearance Web Ops Hub
echo  Moduller: Operasyon Kokpiti · GTB · Kantar DBA
echo  Dogruer Gumruk Musavirligi A.S.
echo ================================================================
echo.

set "PYTHON_EXE="

if exist "python-embed\python.exe" (
    set "PYTHON_EXE=python-embed\python.exe"
    goto :START
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :START
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py -3"
    goto :START
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :START
)

echo [HATA] Python bulunamadi.
pause
exit /b 1

:START
set "PYTHONPATH=%CD%;%CD%\Lib\site-packages;%PYTHONPATH%"
set "WEB_OPS_HOST=127.0.0.1"
set "WEB_OPS_PORT=8060"

echo [BILGI] Yerel web hub baslatiliyor...
echo.
echo   Adres : http://127.0.0.1:8060
echo   Durdur: CTRL+C
echo.
echo [UYARI] Gumruk / musteri verisi icerir. Public GitHub Pages veya
echo         acik internet tuneline baglamayin. Gerekirse sadece LAN/VPN.
echo ================================================================
echo.

%PYTHON_EXE% -m tools.web_ops_hub.server

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BILGI] Sunucu kapandi veya baslatilamadi.
    pause
)
