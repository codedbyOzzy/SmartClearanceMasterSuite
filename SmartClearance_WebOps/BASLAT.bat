@echo off
setlocal
cd /d "%~dp0"
title SmartClearance WebOps

echo ============================================================
echo  SmartClearance WebOps  (hafif paket)
echo  Kokpit · GTB Beyanname · Kantar DBA
echo ============================================================
echo.

set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
  where py >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [HATA] Python bulunamadi. Python 3.12 kurun.
  pause
  exit /b 1
)

echo [1/2] Bagimliliklar kontrol ediliyor...
%PY% -m pip install -q -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
  echo [UYARI] pip kurulumu sorunlu olabilir; yine de baslatiliyor...
)

set "PYTHONPATH=%CD%;%PYTHONPATH%"
set "WEBOPS_HOST=127.0.0.1"
set "WEBOPS_PORT=8060"

echo [2/2] Yerel sunucu aciliyor: http://127.0.0.1:8060
echo Durdurmak icin CTRL+C
echo ============================================================
echo.

%PY% server.py
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Sunucu kapandi.
  pause
)
