@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title "Dogruer - MSC Canli Konteyner ve ETA Takip Radari"

echo ========================================================
echo   Dogruer SmartClearance - MSC Canli Konteyner Radari
echo ========================================================
echo.

set "PY=python-embed\python.exe"

if not exist "%PY%" (
    set "PY=python"
)

set TCL_LIBRARY=%~dp0tcl\tcl8.6
set TK_LIBRARY=%~dp0tk
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0

"%PY%" standalone_msc_tracker\msc_tracker.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bir hata olustu veya program kapandi.
    pause
)
