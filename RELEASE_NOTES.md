# v1.0.1 — RhinoSpotter compatibility update

This maintenance release updates the RhinoSpotter integration for the storage format used by current RhinoSpotter releases.

## Changes

- Added automatic detection of the RhinoSpotter SQLite bookmark database at `%LOCALAPPDATA%\RhinoSpotter\db\rhinospotter.db`.
- Reads the RhinoSpotter database in SQLite read-only mode.
- Preserves support for legacy JSON card folders as a fallback.
- Preserves stable report IDs so previously synchronized bookmarks are updated rather than duplicated.
- Updated Settings to show the detected RhinoSpotter source and bookmark count.
- Updated the upload confirmation and completion summary to use bookmark/database terminology.
- Improved Settings window initialization so it opens already rendered instead of exposing intermediate layout states.
- Updated RhinoSpotter and Community Deposits documentation for the current workflow.

The integration was tested with newly created RhinoSpotter 4.4.3 bookmarks as well as previously migrated records.

---

# v1.0.0 — First public Windows release

This is the **first public release** of **ED Hotspots Finder - Rings & Planets**.

The project went through several internal development iterations before release; those internal version labels are not part of the public release history. Public versioning therefore starts at **v1.0.0**.

ED Hotspots Finder is built around **multi-system search and filtering**, with a particular focus on finding systems that satisfy the strategic and physical requirements of **Powerplay-oriented research**.

## Highlights

- Standalone Windows interface.
- Manual **System Input** with Spansh-backed system-name normalization before scanning.
- **System Filters** for Faction, Powerplay power, Power States, Reference System and distance.
- Search large candidate groups for the ring, hotspot and planetary characteristics required by a task.
- Hotspot searches with ring/mineral filters and **Only Pristine**.
- Planet searches with body-type filters, **Only Landables**, volcanism and arrival-distance data where available.
- Integrated **Community Deposits** results from the ED Alliance Community Deposits service.
- Optional RhinoSpotter synchronization for contributing compatible local discoveries to the shared database.
- Local result tables with sorting/filtering.
- Export of the current result tab to **CSV** and **XLSX**.
- Expand/Restore results view and detailed activity log.
- Themes: **Deep Black** and **Green Warm**.
- UI Scale options: 100%, 110%, 115% and 125%, with 115% as the default.
- Startup splash and first-window reveal handling designed to avoid visible initialization flicker on Windows.
- Application icon and Windows executable metadata prepared for the first public release.

## Search behavior

Manual system names are canonicalized through the same Spansh lookup used by Reference System. For example, differently cased inputs such as `mehit`, `wuRANgo` or `SEEDI` are resolved to the canonical names before the scan proceeds.

Duplicates are removed after canonicalization.

The same workflow can also begin from System Filters, allowing commanders to define a Powerplay, faction or distance-based search area before checking the resulting systems for the required hotspot, ring and planetary characteristics.

## Community Deposits and RhinoSpotter

The desktop app can query the **ED Alliance Community Deposits** service and display known player-reported surface deposits.

The long-term goal is to build a useful shared database of planetary deposits from discoveries contributed by the community.

The current release includes optional synchronization of compatible local RhinoSpotter records with Community Deposits. RhinoSpotter is an independent EDMC project developed by **Fumlop**:

https://github.com/Fumlop/EDRhinoSpotter

See the repository documentation for more information about Community Deposits and the current RhinoSpotter workflow.

## Local settings

The application stores its settings in:

```text
%APPDATA%\HotspotsFinder\config.json
```

## Export

Results can be exported locally:

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
- executable name: `ED Hotspots Finder - Rings & Planets.exe`

The public Windows executable is currently unsigned, so Windows SmartScreen may display an unknown-publisher warning.

## Notes

Spansh and Community Deposits are community-data sources. Missing or outdated source data can affect search results.

The **Check for updates on startup** option remains disabled for the initial `v1.0.0` release and can be enabled after the first public GitHub Release is available for the application to query.
