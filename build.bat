@echo off
:: ============================================================
:: Phoenix Macro — Windows build script
:: Requirements: Python 3.10+, pip
:: Run this file once to install deps and build PhoenixMacro.exe
:: ============================================================

echo.
echo  ==========================================
echo    PHOENIX MACRO  —  Build Script
echo  ==========================================
echo.

:: 1) Install / upgrade dependencies
echo [1/3] Installing dependencies...
pip install --upgrade PyQt5 pynput pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: pip install failed. Make sure Python is in your PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Building executable...
echo.

:: 2) PyInstaller — single .exe, windowed (no console), high-DPI manifest
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "PhoenixMacro" ^
    --icon "phoenix.ico" ^
    --add-data "phoenix.ico;." ^
    --add-data "scripts;scripts" ^
    --runtime-tmpdir . ^
    phoenix_macro.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: PyInstaller failed. See output above.
    pause
    exit /b 1
)

echo.
echo [3/3] Copying scripts folder into dist...
if not exist "dist\scripts" mkdir "dist\scripts"

echo.
echo  ==========================================
echo    BUILD COMPLETE
echo    Executable: dist\PhoenixMacro.exe
echo  ==========================================
echo.
echo  NOTE: Windows Defender or antivirus may flag PyInstaller EXEs.
echo  If prompted, add an exception for PhoenixMacro.exe.
echo.
echo  NOTE: pynput uses Windows accessibility APIs (WinHooks).
echo  No admin rights required for most setups. If recording
echo  doesn't work inside elevated (admin) windows, try running
echo  PhoenixMacro.exe as Administrator.
echo.
pause
