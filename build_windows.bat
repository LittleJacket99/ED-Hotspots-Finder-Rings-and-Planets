@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo ED Hotspots ^& Landables Finder v7.11 - Windows release
echo =======================================================
echo.

py -3.10 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 was not found via the Windows py launcher.
    goto :fail
)

echo [1/5] Validating local credentials and assets...
py -3.10 validate_release.py
if errorlevel 1 goto :fail

echo.
echo [2/5] Installing build dependencies...
py -3.10 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo.
echo [3/5] Cleaning previous temporary build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [4/5] Building Windows executable...
py -3.10 -m PyInstaller --noconfirm --clean HotspotsFinder.spec
if errorlevel 1 goto :fail
if not exist "dist\ED Hotspots & Landables Finder.exe" goto :fail

echo.
echo [5/5] Packaging Windows release...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0package_release.ps1"
if errorlevel 1 goto :fail

echo.
echo Release ZIP: release\HotspotsFinder-v7.11-Windows.zip
echo The EXE includes your Desktop OAuth credentials and logo.
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Read the error above. Existing release ZIP was not published.
echo.
pause
exit /b 1
