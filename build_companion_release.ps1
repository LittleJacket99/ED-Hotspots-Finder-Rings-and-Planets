param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginSource = Join-Path $RepoRoot "edmc_plugin\EDHF_Community_Navigator"
$LoadPy = Join-Path $PluginSource "load.py"

if (-not (Test-Path $LoadPy)) {
    throw "Companion load.py not found: $LoadPy"
}

if (-not $Version) {
    $match = Select-String -Path $LoadPy -Pattern '^VERSION\s*=\s*"([^"]+)"$' | Select-Object -First 1
    if (-not $match) {
        throw "Could not read VERSION from $LoadPy"
    }

    $Version = $match.Matches[0].Groups[1].Value
}

$ReleaseDir = Join-Path $RepoRoot "release\v$Version"
$StageRoot = Join-Path $env:TEMP "Hotspots-Finder-EDMC-Plugin-$Version"
$StagePlugin = Join-Path $StageRoot "EDHF_Community_Navigator"
$ZipPath = Join-Path $ReleaseDir "Hotspots-Finder-EDMC-Plugin-v$Version.zip"
$HashPath = Join-Path $ReleaseDir "SHA256.txt"

if (Test-Path $StageRoot) {
    Remove-Item $StageRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $StagePlugin -Force | Out-Null
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

$legacyZip = Join-Path $ReleaseDir "Hotspots-Finder-Deposits-Companion-v$Version.zip"
if (Test-Path $legacyZip) {
    Remove-Item $legacyZip -Force
}

Copy-Item (Join-Path $PluginSource "*") $StagePlugin -Recurse -Force

Get-ChildItem $StagePlugin -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $StagePlugin -Recurse -File -Include "*.pyc","*.pyo" | Remove-Item -Force

Compress-Archive -Path $StagePlugin -DestinationPath $ZipPath -CompressionLevel Optimal -Force

$name = [System.IO.Path]::GetFileName($ZipPath)
$lines = @()
if (Test-Path $HashPath) {
    $lines = @(
        Get-Content $HashPath |
            Where-Object { $_ -notmatch ("  " + [regex]::Escape($name) + "$") }
    )
}
$hash = Get-FileHash $ZipPath -Algorithm SHA256
$lines += "$($hash.Hash.ToLowerInvariant())  $name"
$lines | Set-Content -Path $HashPath -Encoding ascii

Remove-Item $StageRoot -Recurse -Force

Write-Host ""
Write-Host "Hotspots Finder EDMC Plugin v$Version"
Write-Host "ZIP:    $ZipPath"
Write-Host "SHA256: $HashPath"
Write-Host ""
Write-Host "The ZIP contains the EDHF_Community_Navigator folder ready to copy into:"
Write-Host "%LOCALAPPDATA%\EDMarketConnector\plugins\"
