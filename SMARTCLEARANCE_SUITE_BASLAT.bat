@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title "SmartClearance Master Suite - Apex ^& Horizon Pro"

echo =================================================================
echo   SmartClearance Master Suite - Apex ^& Horizon Pro
echo   Gumruk Operasyon Masasi ^& Kuresel Konteyner Radari
echo   Linear / Dark Obsidian Integrated Workspace (v1.0 Pro)
echo =================================================================
echo.

set "PY=%~dp0python-embed\python.exe"

if not exist "%PY%" (
    set "PY=C:\Users\ozan.gemici\AppData\Local\Programs\Python\Python312\python.exe"
)
if not exist "%PY%" (
    set "PY=python"
)

set TCL_LIBRARY=%~dp0tcl\tcl8.6
set TK_LIBRARY=%~dp0tk
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0HANKOOK_OPERASYON_MASASI;%~dp0standalone_global_tracker;%~dp0;%PYTHONPATH%

set "SUITE_SCRIPT=%~dp0HANKOOK_OPERASYON_MASASI\smartclearance_suite.py"
if not exist "%SUITE_SCRIPT%" (
    set "SUITE_SCRIPT=C:\HANKOOK_OPERASYON_MASASI\smartclearance_suite.py"
)
if not exist "%SUITE_SCRIPT%" (
    set "SUITE_SCRIPT=%~dp0smartclearance_suite.py"
)

"%PY%" "%SUITE_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program kapandi veya bir hata olustu.
    pause
)
