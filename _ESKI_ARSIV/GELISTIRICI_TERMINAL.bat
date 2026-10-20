@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Dogruer MasterSuite - Gelistirici Konsolu

echo =======================================================================
echo   DOGRUER MASTERSUITE - GELISTIRICI TERMINALI
echo =======================================================================
echo   Python Embed: %~dp0python-embed\python.exe
echo   Calisma Dizini: %~dp0
echo.
echo   Komut Ornekleri:
echo     python tools\dogruer_master_suite\master_suite.py  (Ana Arayuz)
echo     python tools\kantar_engine\kantar_sorgu.py          (Kantar Test)
echo     python tools\gtb_engine\gtb_sorgu.py                (GTB Test)
echo     python tools\eta_engine\eta_tracker_service.py      (ETA Test)
echo     python -m pip install <paket_adi>                   (Yeni Paket Kur)
echo =======================================================================
echo.

set PATH=%~dp0python-embed;%~dp0python-embed\Scripts;%PATH%
set TCL_LIBRARY=%~dp0tcl\tcl8.6
set TK_LIBRARY=%~dp0tk
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0

cmd /k