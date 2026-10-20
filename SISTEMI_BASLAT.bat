@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Dogruer SmartClearance MasterSuite

echo ================================================
echo   Dogruer SmartClearance MasterSuite
echo   Dogruer Gumruk Musavirligi A.S.
echo ================================================
echo.

set "PY=python-embed\python.exe"

if not exist "%PY%" (
    echo HATA: python-embed\python.exe bulunamadi!
    pause
    exit /b 1
)

echo Sistem baslatiliyor..
echo.

set TCL_LIBRARY=%~dp0tcl\tcl8.6
set TK_LIBRARY=%~dp0tk
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0

"%PY%" tools\dogruer_master_suite\Dogruer_Master_Suite.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Sistem bir hata ile karsilasti.
    pause
)
