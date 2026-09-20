# EDMC Community Navigator

`EDHF Community Navigator` is the in-game extension of the **ED Hotspots Finder - Rings & Planets** ecosystem.

It is intentionally not a second general-purpose Elite Dangerous database browser.

## Product roles

**ED Hotspots Finder - Rings & Planets**

- general search and planning client;
- multi-system Hotspots, Planets and Community Deposits searches;
- filtering, analysis and export;
- RhinoSpotter contribution synchronization.

**EDHF Community Navigator**

- compact EDMC in-game client;
- current-system Community Deposits lookup;
- RhinoSpotter bookmark synchronization without opening the desktop application;
- selected-deposit surface navigation.

Both clients use the same Community Deposits service.

## Shared architecture

```text
                         RhinoSpotter
                            rs_api
                              |
                 +------------+------------+
                 |                         |
                 v                         v
        ED Hotspots Finder        EDHF Community Navigator
          desktop client               EDMC plugin
                 |                         |
                 +------------+------------+
                              |
                              v
                     Community Deposits
                    /v1/deposits API
                              |
                 +------------+------------+
                 |                         |
                 v                         v
         multi-system search       current-system scan
                                             |
                                             v
                                      Track Selected
                                             |
                                             v
                                      Navigator HUD
```

## RhinoSpotter integration

Current RhinoSpotter releases are consumed through the documented external API:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\RhinoSpotter\rs_api.py
```

The desktop application still retains direct SQLite/legacy JSON readers only as compatibility fallbacks for older RhinoSpotter installations.

The EDMC plugin does **not** need those fallbacks: because it runs alongside RhinoSpotter inside the EDMC plugin environment, its supported contribution path is `rs_api.py`.

The bookmark-to-Community-Deposits normalization and stable `report_id` identity match the desktop synchronization behavior so syncing the same bookmark from either client does not intentionally create a second independent report identity.

## EDMC data sources

The plugin uses two EDMC hooks for different jobs:

- `journal_entry()` maintains the current star system/body context.
- `dashboard_entry()` receives updates derived from Elite Dangerous `Status.json` and supplies the live surface navigation data.

Network work is performed on worker threads. Tkinter widgets are only updated on the EDMC main thread, following the EDMC plugin requirements.

## Initial navigator calculation

For a selected deposit the plugin combines:

- target latitude/longitude from Community Deposits;
- current latitude/longitude from `Status.json`;
- current heading from `Status.json`;
- planet radius from `Status.json`, falling back to the stored deposit radius when available.

It calculates the great-circle surface distance and initial bearing to the target, then compares bearing with current heading to produce a directional arrow.

## Development location

The prototype is currently kept in this repository under:

```text
edmc_plugin/EDHF_Community_Navigator/
```

Development happens on the `edmc-companion-dev` branch until the integration is ready for release packaging.
