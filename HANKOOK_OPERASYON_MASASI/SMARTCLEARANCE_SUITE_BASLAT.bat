@echo off
setlocal enabledelayedexpansion
cd /d "C:\HANKOOK_OPERASYON_MASASI"
title "SmartClearance Master Suite - Apex & Horizon Pro"

echo =================================================================
echo   SmartClearance Master Suite - Apex ^& Horizon Pro
echo   Gumruk Operasyon Masasi ^& Kuresel Konteyner Radari
echo   Linear / Dark Obsidian Integrated Workspace (v1.0 Pro)
echo =================================================================
echo.

set "PY=C:\Users\ozan.gemici\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PY%" (
    set "PY=python"
)

"%PY%" smartclearance_suite.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program kapandi veya bir hata olustu.
    pause
)
