# Hotspots Finder Deposits Companion

**Hotspots Finder Deposits Companion** is the focused EDMarketConnector extension of the **ED Hotspots Finder - Rings & Planets** ecosystem.

The desktop Finder remains the general search, planning and analysis client. The Companion is designed for quick in-game Community Deposits access without duplicating the full desktop application.

## Product roles

### ED Hotspots Finder - Rings & Planets

- multi-system Hotspots, Planets and Community Deposits searches;
- system discovery and filtering;
- analysis, table filtering and export;
- RhinoSpotter contribution synchronization.

### Hotspots Finder Deposits Companion

- compact EDMC interface;
- RhinoSpotter bookmark synchronization;
- current-system Community Deposits lookup;
- cached reopening of already scanned system results;
- manual refresh when synchronized data for the current system changed;
- selected-deposit surface navigation through a small always-on-top HUD;
- direct launch of the desktop Finder.

Both clients use the same Community Deposits service.

## Runtime flow

```text
RhinoSpotter rs_api
        |
        | Sync Bookmarks
        v
Community Deposits API
        ^
        |
        | Scan System / Refresh Deposits
        |
EDMC current system
        |
        v
Results window
        |
        | Start Tracking
        v
Status.json / dashboard_entry
        |
        v
Navigator HUD
```

## Main EDMC controls

The Companion exposes three compact actions inside EDMC:

- **Sync Bookmarks** — reads RhinoSpotter through its documented `rs_api.py` interface and synchronizes compatible bookmarks.
- **Scan System** — queries Community Deposits for the current EDMC system.
- **Open Finder** — launches the configured ED Hotspots Finder executable.

After a successful scan, the middle action becomes:

- **Open Deposits** when the current result snapshot is still valid;
- **Refresh Deposits** when a sync changed Community Deposits data relevant to the current system;
- **No Deposits** when the scanned system returned no records.

Closing the results window does not force another API query while the commander remains in the same system.

## Synchronization semantics

A stable `report_id` is generated for each RhinoSpotter bookmark so repeated synchronization does not intentionally create duplicate report identities.

The Community Deposits backend distinguishes:

- `inserted` — a new deposit/report;
- `matched_existing_deposit` — a new report matched to an already known deposit;
- `updated_report` — an existing report whose meaningful mutable state changed;
- `unchanged` — the same report was synchronized again without a meaningful change.

Repeated syncs therefore do not refresh the displayed update timestamp just because the user pressed **Sync Bookmarks**.

Current deposit update policy keeps **Rigs** and **Density** stable after the deposit is created. **Amount** and depletion state may change. Technical fields such as missing body IDs or planet radius may be completed without being treated as a meaningful deposit update.

## RhinoSpotter integration

Current RhinoSpotter releases are consumed through the documented external API:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\RhinoSpotter\rs_api.py
```

The Companion supports RhinoSpotter API `SCHEMA = 1`.

The desktop Finder retains direct SQLite/legacy JSON readers only as compatibility fallbacks for older RhinoSpotter installations. The EDMC Companion intentionally uses `rs_api.py` only.

If RhinoSpotter is missing, **Sync Bookmarks** reports that RhinoSpotter 5.1+ must be installed as an EDMC plugin.

## Results window

The Community Deposits results window:

- inherits the current EDMC colour theme;
- shows Body, Location, Material, Rigs, Amount, Density, Latitude, Longitude, Reports and Updated;
- displays up to 10 rows before adding a vertical scrollbar;
- provides **Start Tracking** for the selected deposit.

## Navigator HUD

The tracker is intentionally minimal and uses a fixed high-contrast palette independent of the EDMC theme.

It is:

- frameless;
- always on top;
- draggable;
- independently position-persistent;
- reopened cleanly when tracking starts again.

The HUD shows the compact body name together with material and RhinoSpotter Location. It combines the selected target coordinates with live `Status.json` data from `dashboard_entry()` to calculate great-circle surface separation, bearing and a heading-relative direction arrow. When altitude is available, it is combined with the surface separation to give a useful target distance during aerial approach.

## Release packaging

The Companion is versioned independently from the desktop Finder. The first release line is **v1.0.0**.

The plugin source lives in:

```text
edmc_plugin/EDHF_Community_Navigator/
```

From the repository root, the Windows release package can be generated with:

```powershell
.\build_companion_release.ps1
```

The script reads the version from `load.py` and creates:

```text
release\companion\v1.0.0\Hotspots-Finder-Deposits-Companion-v1.0.0.zip
release\companion\v1.0.0\SHA256.txt
```

The ZIP contains the complete `EDHF_Community_Navigator` folder ready to place under the EDMarketConnector plugins directory.

Development remains on the `edmc-companion-dev` branch until the packaged build passes the final installation smoke test.
