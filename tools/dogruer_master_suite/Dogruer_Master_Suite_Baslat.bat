@echo off
title Dogruer SmartClearance Master Suite
cd /d "%~dp0"

echo ==============================================================================
echo  DOGRUER SMARTCLEARANCE MASTER SUITE BASLATILIYOR...
echo ==============================================================================
echo.

python "master_suite.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bir hata olustu!
    pause
)
