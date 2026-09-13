$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$exe = Join-Path $root 'dist\ED Hotspots & Landables Finder.exe'
$releaseRoot = Join-Path $root 'release'
$releaseFolder = Join-Path $releaseRoot 'ED-Hotspots-Landables-Finder-v7.11'
$zip = Join-Path $releaseRoot 'ED-Hotspots-Landables-Finder-v7.11-Windows.zip'

if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Windows executable missing: $exe"
}

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
if (Test-Path -LiteralPath $releaseFolder) {
    Remove-Item -LiteralPath $releaseFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseFolder | Out-Null
Copy-Item -LiteralPath $exe -Destination $releaseFolder
Copy-Item -LiteralPath (Join-Path $root 'README.md') -Destination $releaseFolder
Copy-Item -LiteralPath (Join-Path $root 'RELEASE_NOTES.md') -Destination $releaseFolder

$hash = (Get-FileHash -LiteralPath (Join-Path $releaseFolder 'ED Hotspots & Landables Finder.exe') -Algorithm SHA256).Hash
"$hash  ED Hotspots & Landables Finder.exe" |
    Set-Content -LiteralPath (Join-Path $releaseFolder 'SHA256.txt') -Encoding ASCII

Compress-Archive -LiteralPath $releaseFolder -DestinationPath $zip -Force
$zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
@("$hash  ED Hotspots & Landables Finder.exe", "$zipHash  ED-Hotspots-Landables-Finder-v7.11-Windows.zip") |
    Set-Content -LiteralPath (Join-Path $releaseRoot 'SHA256.txt') -Encoding ASCII
Write-Host "Release ready: $zip"
