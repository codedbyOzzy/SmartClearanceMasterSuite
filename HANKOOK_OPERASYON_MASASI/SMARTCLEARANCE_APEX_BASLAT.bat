@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title "SmartClearance Apex - Hankook Gumruk Operasyon Masasi & Evrak Studyosu"

echo =================================================================
echo   SmartClearance Apex - Gumruk Operasyon Masasi ve Evrak Studyosu
echo   Linear / Dark Obsidian Multi-Panel Workspace (v1.0 Pro)
echo =================================================================
echo.

set "PY=C:\Users\ozan.gemici\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PY%" (
    set "PY=%~dp0..\python-embed\python.exe"
)
if not exist "%PY%" (
    set "PY=%~dp0python-embed\python.exe"
)
if not exist "%PY%" (
    set "PY=python"
)

set TCL_LIBRARY=%~dp0..\tcl\tcl8.6
set TK_LIBRARY=%~dp0..\tk
set PYTHONPATH=%~dp0..\Lib\site-packages;%~dp0..;%~dp0..\standalone_global_tracker;%~dp0;%PYTHONPATH%

"%PY%" smartclearance_apex.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program kapandi veya bir hata olustu.
    pause
)
