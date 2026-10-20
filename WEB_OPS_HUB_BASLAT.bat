@echo off
REM Eski kisayol — yeni hafif paket: SmartClearance_WebOps\BASLAT.bat
cd /d "%~dp0SmartClearance_WebOps"
if not exist "BASLAT.bat" (
  echo SmartClearance_WebOps klasoru bulunamadi.
  pause
  exit /b 1
)
call BASLAT.bat
