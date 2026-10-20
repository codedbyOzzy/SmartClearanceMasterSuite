@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title SmartClearance MasterSuite (PyQt6)

echo =====================================================================
echo  SmartClearance MasterSuite - Modern PyQt6 Platformu
echo  Dogruer Gumruk Musavirligi A.S. - Hankook Lastikleri A.S.
echo =====================================================================
echo.

:: 1. Ortam Degiskenleri (PYTHONPATH & TCL/TK & QT LOGGING)
set "PYTHONPATH=%~dp0HANKOOK_OPERASYON_MASASI;%~dp0standalone_global_tracker;%~dp0Lib\site-packages;%~dp0Lib\site-packages\win32;%~dp0Lib\site-packages\win32\lib;%~dp0Lib\site-packages\Pythonwin;%~dp0python-embed\Lib\site-packages;%~dp0python-embed\Lib\site-packages\win32;%~dp0python-embed\Lib\site-packages\win32\lib;%~dp0python-embed\Lib\site-packages\Pythonwin;%~dp0;%PYTHONPATH%"
set "PATH=%~dp0Lib\site-packages\pywin32_system32;%~dp0python-embed\Lib\site-packages\pywin32_system32;%PATH%"
set "QT_LOGGING_RULES=qt.qpa.*=false;qt.webenginecontext.*=false;js.*=false;*.debug=false"
set "QTWEBENGINE_CHROMIUM_FLAGS=--disable-logging --log-level=3 --disable-gpu-shader-disk-cache --no-sandbox"

if exist "%~dp0python-embed\tcl\tcl8.6" (
    set "TCL_LIBRARY=%~dp0python-embed\tcl\tcl8.6"
    set "TK_LIBRARY=%~dp0python-embed\tcl\tk8.6"
)

:: 2. Python Calistirici Arama Zinciri (Portable Fallback)
set "PYTHON_EXE="

if exist "%~dp0python-embed\python.exe" (
    set "PYTHON_EXE=%~dp0python-embed\python.exe"
    goto :PYTHON_FOUND
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -c "import PyQt6" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        goto :PYTHON_FOUND
    )
)

if exist "%ProgramFiles%\Python312\python.exe" (
    "%ProgramFiles%\Python312\python.exe" -c "import PyQt6" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
        goto :PYTHON_FOUND
    )
)

where py >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    py -3 -c "import PyQt6" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=py -3"
        goto :PYTHON_FOUND
    )
)

where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    python -c "import PyQt6" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=python"
        goto :PYTHON_FOUND
    )
)

echo [HATA] Sistemde veya tasinabilir klasorde PyQt6 destekli Python bulunamadi!
pause
exit /b 1

:PYTHON_FOUND
echo [BILGI] Kullanilan Python: %PYTHON_EXE%
echo [BILGI] PyQt6 MasterSuite Baslatiliyor...
echo.

%PYTHON_EXE% -m smartclearance_master_suite_pyqt.app_pyqt %*

set "EXIT_CODE=%ERRORLEVEL%"
if not "!EXIT_CODE!"=="0" (
    echo.
    echo [BILGI] Uygulama sonlandi - Cikis Kodu: !EXIT_CODE!
    pause
)

endlocal
