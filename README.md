# ED Hotspots Finder - Rings & Planets

A standalone Windows companion for **Elite Dangerous** that searches multiple star systems for mining hotspots, landable bodies and related surface-mining information using **Spansh** and the **ED Alliance Community Deposits** database.

The current interface is fully local: no Google Sheets connection and no Google OAuth are required.

[Download the latest Windows release](https://github.com/LittleJacket99/ED-Hotspots-Landables-Finder/releases/latest) · [v1.0.0 release notes](RELEASE_NOTES.md)

## Main features

- Search a manual list of systems in **System Input**.
- Automatically normalize manual system names through Spansh before scanning.
- Find systems with **System Filters** using Faction, Powerplay power, Power States, Reference System and maximum distance.
- Search for mining hotspots with ring-type and mineral filters, including **Only Pristine**.
- Search planets with body-type filters, **Only Landables**, volcanism and arrival-distance data where available.
- Display **Community Deposits** stored in the shared ED Alliance Community Deposits database.
- Optional RhinoSpotter integration for synchronizing local deposit cards with the community database.
- Sort and filter result tables directly in the desktop app.
- Export the current result tab to **CSV** or **XLSX**.
- Expand/restore the results area and open the detailed activity log.
- Choose between **Deep Black** and **Green Warm** themes.
- UI scaling options: 100%, 110%, 115% and 125%.

Spansh and the Community Deposits service are community-data sources. Missing or outdated data can affect results; no match is not proof that a system or body contains no relevant feature.

## Quick start

1. Download the Windows executable or ZIP from **Releases**.
2. Run **ED Hotspots Finder - Rings & Planets.exe**.
3. Enter one or more systems in **System Input**, or leave it empty and configure **System Filters**.
4. Enable **Hotspots**, **Planets** and/or **Community Deposits** as needed.
5. Set the relevant filters.
6. Click **SCAN**.
7. Review the result tabs, use column filters if needed, and export the current tab to CSV or XLSX.

Python is not required for the public Windows build.

## System Input and normalization

Enter one system per line. Before the scan starts, each manual system name is resolved against Spansh and converted to its canonical capitalization.

For example:

```text
mehit   -> Mehit
wuRANgo -> Wurango
SEEDI   -> Seedi
```

Duplicate systems are removed after normalization. If a name cannot be resolved, the scan reports the error instead of silently querying an invalid system.

## System Filters

When **System Input** is empty, the app can resolve systems from filters instead.

Available controls include:

- **Faction**
- **Power**
- **Power States**
- **Reference System**
- **Distance**

The Reference System is normalized through the same Spansh system-name lookup used for manual input.

## Hotspots

Hotspot searches can be filtered by ring type and mineral/material. **Only Pristine** limits results to pristine systems where the available source data supports that classification.

Results are shown locally in the app rather than written to a spreadsheet.

## Planets

Planet searches support body-type filters and **Only Landables**. Returned data can include landability, volcanism and arrival distance where supplied by Spansh.

## Community Deposits

The **Community Deposits** option queries the ED Alliance Community Deposits service and displays known player-reported deposits alongside the normal search workflow.

The public API is maintained separately from the desktop executable. Network access is required to retrieve community records.

## RhinoSpotter integration

The app can read RhinoSpotter JSON cards from the configured cards folder and synchronize valid deposit reports with the Community Deposits database.

By default the app looks in:

```text
%LOCALAPPDATA%\RhinoSpotter\cards
```

A custom cards directory can be configured in Settings. The sync reuses the same validation and normalization logic as the standalone RhinoSpotter sync helper.

## Export

The current result tab can be exported to:

- **CSV** — UTF-8 with BOM and semicolon delimiters for convenient opening in European Excel installations.
- **XLSX** — generated locally by the application, with a frozen header row and autofilter.

No spreadsheet account or external office suite integration is required.

## Settings

Application settings are stored locally in:

```text
%APPDATA%\HotspotsFinder\config.json
```

Current settings include startup filter defaults, RhinoSpotter options, theme and UI scale.

The standalone release does not use Google authorization and does not create `token.json`.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| A system name is rejected | Check the spelling and whether Spansh can resolve the system. |
| A scan returns unexpected or incomplete data | Open **Log Details**, verify the active filters and retry with a small system list. |
| Community Deposits cannot be loaded | Check the Internet connection and retry later; the community API may be temporarily unavailable. |
| RhinoSpotter sync finds no cards | Verify the configured cards directory and that it contains valid `.json` cards. |
| The interface is too large or too small | Open **Settings**, change UI Scale, save and restart the app. |
| Windows SmartScreen appears | The executable is currently unsigned. Confirm that it was downloaded from this repository's Releases page. |

## Build from source

These steps are for developers and release maintainers.

1. Install Python on Windows.
2. Clone or download this repository.
3. Install runtime requirements:

```powershell
python -m pip install -r requirements.txt
```

4. Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

5. Run:

```text
build_windows_v8.bat
```

The current internal build files still use **v8** in their filenames because that was the final development iteration before the first public release. The public release version starts at **v1.0.0**.

The build uses `HotspotsFinder-v8.spec`, bundles `app.ico` and `ED_Hotspots_Finder.png`, and uses `hotspots_finder_gui_v8_final.py` as the entry point. The public executable is named **ED Hotspots Finder - Rings & Planets.exe**.

## Project structure

| Component | Role |
| --- | --- |
| `hotspots_finder_gui_v8_final.py` | Final desktop entry point and application-level behaviour |
| `hotspots_finder_gui_v8_*.py` | Modular GUI layers used by the final interface |
| `finder_engine.py` | Shared scan/filter helpers |
| `local_scan.py` | Local scan orchestration |
| `system_filter_search.py` | Faction/Power/Reference System resolution and system-name canonicalization |
| `community_deposits.py` | Community Deposits API client |
| `rhinospotter_sync.py` | RhinoSpotter card normalization and upload logic |
| `rhinospotter_sync_service.py` | GUI-friendly RhinoSpotter sync wrapper |
| `results_export.py` | CSV/XLSX export helpers |
| `app_settings.py` | Persistent local settings |
| `startup_splash.py` | Startup splash and first-window reveal handling |
| `HotspotsFinder-v8.spec` | PyInstaller configuration used by the current Windows build |

## Privacy and network access

The application may make network requests to:

- **Spansh** for Elite Dangerous system/body data and system-name resolution.
- **ED Alliance Community Deposits** for community deposit retrieval and RhinoSpotter report synchronization.

Application settings remain local in `%APPDATA%\HotspotsFinder\config.json`.

No Google Sheets access, Google OAuth token or Google account is required by the standalone release.
