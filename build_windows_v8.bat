@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo ED Hotspots Finder - Rings ^& Planets v1.0.0 - Windows test build
echo =======================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in the current environment.
    goto :fail
)

python -c "import hotspots_finder_gui_v8_final, finder_engine, local_scan, system_filter_search, community_deposits, results_export, rhinospotter_sync_service, requests; print('V8 final GUI imports OK')"
if errorlevel 1 goto :fail

if not exist app.ico (
    echo ERROR: app.ico is missing from the repository root.
    goto :fail
)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed in the current environment.
    goto :fail
)

if exist build-v8 rmdir /s /q build-v8
if exist dist-v8 rmdir /s /q dist-v8

echo Building executable...
python -m PyInstaller --noconfirm --clean --workpath build-v8 --distpath dist-v8 HotspotsFinder-v8.spec
if errorlevel 1 goto :fail

if not exist "dist-v8\ED Hotspots Finder - Rings & Planets.exe" (
    echo ERROR: Expected executable was not created.
    goto :fail
)

echo.
echo BUILD OK
echo EXE: dist-v8\ED Hotspots Finder - Rings ^& Planets.exe
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Read the error above.
echo.
pause
exit /b 1
