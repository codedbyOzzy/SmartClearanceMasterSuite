@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title "SmartClearance Horizon - Kuresel Konteyner ve Canli Rota Radari"

echo =================================================================
echo   SmartClearance Horizon - Kuresel Konteyner ve Canli Rota Radari
echo   Kuresel Denizcilik, Konteyner Takip ve Canli Rota Kokpiti (v1.0 Pro)
echo =================================================================
echo.

set "PY=python-embed\python.exe"

if not exist "%PY%" (
    set "PY=python"
)

set TCL_LIBRARY=%~dp0tcl\tcl8.6
set TK_LIBRARY=%~dp0tk
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0

"%PY%" standalone_global_tracker\smartclearance_horizon.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program kapandi veya bir hata olustu.
    pause
)
