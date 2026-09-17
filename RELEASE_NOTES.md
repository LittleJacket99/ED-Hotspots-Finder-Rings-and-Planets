# v8.0.0 — Windows release

Version 8 is a major standalone rewrite of **ED Hotspots & Landables Finder**.

The previous Google Sheets/OAuth workflow has been removed from the runtime. Searches, filtering, results and exports now live directly in the Windows desktop application.

## Highlights

- New standalone local GUI for Windows.
- Manual **System Input** with Spansh-backed system-name normalization before scanning.
- **System Filters** for Faction, Powerplay power, Power States, Reference System and distance.
- Hotspot searches with ring/mineral filters and **Only Pristine**.
- Planet searches with body-type filters, **Only Landables**, volcanism and arrival-distance data where available.
- Integrated **Community Deposits** results from the ED Alliance Community Deposits service.
- Optional RhinoSpotter card synchronization with the community database.
- Local result tables with sorting/filtering.
- Export of the current result tab to **CSV** and **XLSX**.
- Expand/Restore results view and detailed activity log.
- Themes: **Deep Black** and **Green Warm**.
- UI Scale options: 100%, 110%, 115% and 125%, with 115% as the default.
- New startup splash and first-window reveal handling to reduce visible initialization/flicker on Windows.
- Application icon and Windows executable metadata updated for v8.

## Local settings

v8 stores its settings in:

```text
%APPDATA%\HotspotsFinder\config.json
```

No Google account, Google Sheets connection, OAuth consent or `token.json` is required by v8.

## Search behavior

Manual system names are canonicalized through the same Spansh lookup used by Reference System. For example, differently cased inputs such as `mehit`, `wuRANgo` or `SEEDI` are resolved to the canonical names before the scan proceeds.

Duplicates are removed after canonicalization.

## Community Deposits and RhinoSpotter

The desktop app can query the ED Alliance Community Deposits API and display known community-reported surface deposits.

RhinoSpotter users can synchronize valid local JSON cards with the same database through the integrated sync workflow. The default cards path is `%LOCALAPPDATA%\RhinoSpotter\cards`, with support for a custom directory in Settings.

## Export

Results can be exported locally without Google Sheets:

- CSV: UTF-8 with BOM and semicolon delimiter.
- XLSX: locally generated workbook with frozen headers and autofilter.

## Windows build

The v8 release build uses:

- entry point: `hotspots_finder_gui_v8_final.py`
- PyInstaller spec: `HotspotsFinder-v8.spec`
- icon: `app.ico`
- splash: `ED_Hotspots_Finder.png`
- version metadata: `8.0.0.0`

The public Windows executable is currently unsigned, so Windows SmartScreen may display an unknown-publisher warning.

## Notes

Spansh and Community Deposits are community-data sources. Missing or outdated source data can affect search results.

The **Check for updates on startup** option remains disabled for the initial v8 release and can be enabled once the first public v8 GitHub Release is available for the application to query.
