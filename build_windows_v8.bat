@echo off
setlocal
cd /d "%~dp0"

set "VERSION=v1.0.2"
set "BUILD_EXE_NAME=ED Hotspots Finder - Rings & Planets.exe"
set "ASSET_EXE_NAME=ED-Hotspots-Finder-Rings-and-Planets.exe"
set "ZIP_NAME=ED-Hotspots-Finder-Rings-and-Planets-%VERSION%-Windows.zip"
set "RELEASE_DIR=%CD%\release\%VERSION%"
set "DIST_EXE=%CD%\dist-v8\%BUILD_EXE_NAME%"
set "RELEASE_EXE=%RELEASE_DIR%\%ASSET_EXE_NAME%"
set "RELEASE_ZIP=%RELEASE_DIR%\%ZIP_NAME%"
set "SHA_FILE=%RELEASE_DIR%\SHA256.txt"

echo =======================================================
echo ED Hotspots Finder - Rings ^& Planets %VERSION%
echo Windows release build
echo =======================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in the current environment.
    goto :fail
)

python -c "import hotspots_finder_gui_v8_final, finder_engine, local_scan, system_filter_search, community_deposits, results_export, rhinospotter_sync_service, requests; print('Release imports OK')"
if errorlevel 1 goto :fail

for %%F in ("app.ico" "ED_Hotspots_Finder.png" "version_info_v8.txt" "HotspotsFinder-v8.spec") do (
    if not exist "%%~F" (
        echo ERROR: Required build file is missing: %%~F
        goto :fail
    )
)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed in the current environment.
    echo Install it with: python -m pip install pyinstaller
    goto :fail
)

if exist "build-v8" rmdir /s /q "build-v8"
if exist "dist-v8" rmdir /s /q "dist-v8"

echo Building executable...
python -m PyInstaller --noconfirm --clean --workpath "build-v8" --distpath "dist-v8" "HotspotsFinder-v8.spec"
if errorlevel 1 goto :fail

if not exist "%DIST_EXE%" (
    echo ERROR: Expected executable was not created.
    goto :fail
)

if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"
if errorlevel 1 goto :fail

copy /y "%DIST_EXE%" "%RELEASE_EXE%" >nul
if errorlevel 1 goto :fail

echo Creating release ZIP...
rem The ZIP keeps the friendly executable name with spaces, while the direct
rem GitHub asset uses a URL-safe hyphenated filename.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath $env:DIST_EXE -DestinationPath $env:RELEASE_ZIP -CompressionLevel Optimal -Force"
if errorlevel 1 goto :fail

if not exist "%RELEASE_ZIP%" (
    echo ERROR: Release ZIP was not created.
    goto :fail
)

echo Calculating SHA256 checksums...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = @($env:RELEASE_EXE, $env:RELEASE_ZIP); $lines = foreach ($file in $files) { $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $file; ('{0}  {1}' -f $hash.Hash.ToLowerInvariant(), [IO.Path]::GetFileName($file)) }; Set-Content -LiteralPath $env:SHA_FILE -Value $lines -Encoding ASCII"
if errorlevel 1 goto :fail

if not exist "%SHA_FILE%" (
    echo ERROR: SHA256.txt was not created.
    goto :fail
)

echo.
echo =======================================================
echo RELEASE BUILD OK
echo =======================================================
echo EXE: "%RELEASE_EXE%"
echo ZIP: "%RELEASE_ZIP%"
echo SHA: "%SHA_FILE%"
echo.
echo These three files are ready for the GitHub Release %VERSION%.
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Read the error above.
echo.
pause
exit /b 1
