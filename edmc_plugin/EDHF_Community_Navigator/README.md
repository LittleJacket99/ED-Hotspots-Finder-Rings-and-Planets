# EDHF Community Navigator

Development EDMarketConnector plugin for the **ED Hotspots Finder - Rings & Planets** ecosystem.

The desktop application remains the general browser/search client for Hotspots, Planets and Community Deposits. This plugin is the focused in-game client for synchronizing RhinoSpotter bookmarks, scanning the current system and navigating to a selected community deposit.

## Current development scope

The first prototype provides:

- **Sync Bookmarks** — reads RhinoSpotter through its documented `rs_api.py` interface and synchronizes compatible bookmarks with Community Deposits.
- **Scan Deposits** — queries Community Deposits for the star system currently reported by EDMC.
- A results window with body, material, rigs, amount, density, coordinates, report count and update time.
- **Track Selected** — opens a small always-on-top surface-navigation HUD.
- Live HUD updates from EDMC `dashboard_entry()`, which is fed by Elite Dangerous `Status.json`.
- Surface distance, bearing and relative heading arrow using the current latitude/longitude/heading and planet radius.

This is an early development build and is not part of a public release yet.

## Development installation

Copy the whole `EDHF_Community_Navigator` folder into:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\
```

so the installed path becomes:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\EDHF_Community_Navigator\load.py
```

Then restart EDMarketConnector.

RhinoSpotter should be installed alongside it:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\RhinoSpotter\rs_api.py
```

The current prototype supports RhinoSpotter `SCHEMA = 1`.

## Runtime flow

```text
RhinoSpotter rs_api
        |
        | Sync Bookmarks
        v
Community Deposits API
        ^
        |
        | Scan Deposits
        |
EDMC current system
        |
        v
Results window
        |
        | Track Selected
        v
Status.json / dashboard_entry
        |
        v
Surface Navigator HUD
```

## Community Deposits API

The plugin uses the same service as the desktop application:

```text
GET  /v1/deposits?system=<system>
POST /v1/deposits/batch
```

No separate plugin database is introduced.

## Navigator notes

The HUD is a frameless always-on-top Tk window intended for the same desktop-overlay workflow as EDMC. Borderless/windowed Elite Dangerous is the safest mode for desktop overlays; exclusive fullscreen behavior can depend on Windows and the game.

The initial HUD shows:

- target material and body;
- direction arrow relative to current ship/SRV heading;
- surface distance;
- target bearing;
- current heading.

More navigator controls, overlay preferences and persistence can be added after the first live EDMC test.
