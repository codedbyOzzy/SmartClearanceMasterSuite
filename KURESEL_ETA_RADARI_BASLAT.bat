@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title "Dogruer - Kuresel Konteyner ve Canli ETA Takip Radari"

echo =================================================================
echo   Dogruer SmartClearance - Kuresel Konteyner ve Canli ETA Radari
echo =================================================================
echo.

set "PY=python-embed\python.exe"

if not exist "%PY%" (
    set "PY=python"
)

set TCL_LIBRARY=%~dp0tcl\tcl8.6
set TK_LIBRARY=%~dp0tk
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0

"%PY%" standalone_global_tracker\global_eta_radar.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program kapandi veya bir hata olustu.
    pause
)
