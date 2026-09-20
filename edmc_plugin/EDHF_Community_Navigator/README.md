# Hotspots Finder Deposits Companion

EDMarketConnector plugin for the **ED Hotspots Finder - Rings & Planets** ecosystem.

The desktop application remains the general browser/search client. The Companion is the focused in-game client for synchronizing RhinoSpotter bookmarks, checking Community Deposits in the current system and navigating to a selected surface deposit.

## Current functionality

- **Sync Bookmarks** — reads RhinoSpotter through its documented `rs_api.py` interface and synchronizes compatible bookmarks with Community Deposits.
- **Scan System** — queries Community Deposits for the system currently reported by EDMC.
- **Open Deposits** — reopens the cached result snapshot without another API request.
- **Refresh Deposits** — appears when a synchronization changed relevant data for the currently cached system.
- Results table with body, material, rigs, amount, density, coordinates, report count and update time.
- **Start Tracking** — opens the compact surface-navigation HUD.
- Live distance and relative-heading arrow from EDMC `dashboard_entry()` / Elite Dangerous `Status.json`.
- **Open Finder** — launches the desktop ED Hotspots Finder executable.

Synchronization responses distinguish new, matched, updated and unchanged reports so a repeated sync does not falsely refresh every deposit's update time.

## Development installation

Copy the whole `EDHF_Community_Navigator` folder into:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\
```

so the installed path becomes:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\EDHF_Community_Navigator\load.py
```

Then restart EDMarketConnector completely.

RhinoSpotter should be installed alongside it:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\RhinoSpotter\rs_api.py
```

The Companion currently supports RhinoSpotter API `SCHEMA = 1`.

## Community Deposits API

The plugin uses the same service as the desktop application:

```text
GET  /v1/deposits?system=<system>
POST /v1/deposits/batch
```

No separate plugin database is introduced.

## Result caching

The Companion queries a system once and keeps that result snapshot locally while the commander remains in the same system.

The middle EDMC action changes between:

```text
Scan System
Open Deposits
Refresh Deposits
No Deposits
```

A system change clears the cache. A sync only marks the cached snapshot stale when the server reports a relevant data change.

## Navigator notes

The HUD is a frameless always-on-top Tk window intended for borderless/windowed Elite Dangerous desktop-overlay use.

It keeps a fixed palette for readability, remembers only its own screen position, and does not intentionally modify the EDMC main window geometry.

The tracker displays the compact body name, material, a relative direction arrow and surface distance.
