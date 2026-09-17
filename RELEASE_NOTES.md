# v1.0.0 — First public Windows release

This is the **first public release** of ED Hotspots & Landables Finder.

The project went through several internal development iterations before release; those internal version labels are not part of the public release history. Public versioning therefore starts at **v1.0.0**.

The application is now a standalone Windows tool: searches, filtering, results and exports all live directly in the desktop interface, with no Google Sheets or Google OAuth dependency.

## Highlights

- Standalone local GUI for Windows.
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
- Startup splash and first-window reveal handling designed to avoid visible initialization flicker on Windows.
- Application icon and Windows executable metadata prepared for the first public release.

## Local settings

The application stores its settings in:

```text
%APPDATA%\HotspotsFinder\config.json
```

No Google account, Google Sheets connection, OAuth consent or `token.json` is required.

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

The first public release uses Windows version metadata **1.0.0.0**.

The repository still contains internal source/build filenames using `v8` because that was the final development iteration before the public `v1.0.0` release. Those internal labels do not indicate previous public releases.

The Windows build uses:

- entry point: `hotspots_finder_gui_v8_final.py`
- PyInstaller spec: `HotspotsFinder-v8.spec`
- icon: `app.ico`
- splash: `ED_Hotspots_Finder.png`
- public version metadata: `1.0.0.0`

The public Windows executable is currently unsigned, so Windows SmartScreen may display an unknown-publisher warning.

## Notes

Spansh and Community Deposits are community-data sources. Missing or outdated source data can affect search results.

The **Check for updates on startup** option remains disabled for the initial `v1.0.0` release and can be enabled after the first public GitHub Release is available for the application to query.
