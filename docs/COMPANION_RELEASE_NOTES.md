# Hotspots Finder EDMC Plugin — Release Notes

Inside EDMarketConnector the plugin is displayed as **Hotspots Finder Deposits Companion**.

## v1.0.3 — RhinoSpotter 5.3/5.4 editable bookmark compatibility

This maintenance release updates bookmark synchronization for the editable bookmark fields introduced in current RhinoSpotter releases.

### Changes

- Preserve RhinoSpotter bookmark identity while synchronizing through `rs_api.py`.
- Allow an existing synchronized bookmark to update **Location**, **Material**, **Rigs**, **Amount**, **Density** and depletion state without creating a duplicate report.
- Keep compatibility with reports created by v1.0.2 clients.
- Re-synchronizing an unchanged bookmark continues to return `unchanged` without advancing the visible **Updated** timestamp.
- Finder and EDMC Plugin continue to use the same Community Deposits backend and the same synchronization semantics.

### Installation

Download:

```text
Hotspots-Finder-EDMC-Plugin-v1.0.3.zip
```

Extract it so this folder exists:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\EDHF_Community_Navigator\
```

Then restart EDMarketConnector.

RhinoSpotter 5.1+ is required only for **Sync Bookmarks**. Community Deposits scanning and tracking can still be used independently.

---

## v1.0.2 — First public EDMC Plugin release

First public release of **Hotspots Finder EDMC Plugin**, included in the unified **ED Hotspots Finder v1.0.2** GitHub release.

### Features

- Synchronize RhinoSpotter 5.1+ bookmarks through the documented `rs_api.py` interface.
- Distinguish new, matched, updated and unchanged synchronization results.
- Scan Community Deposits for the current Elite Dangerous system.
- Cache the current-system result snapshot and reopen it without unnecessary API requests.
- Mark cached results for refresh only when synchronized data relevant to the current system changed.
- Display **Body, Location, Material, Rigs, Amount, Density, Latitude, Longitude, Reports and Updated**.
- Track a selected deposit with a compact always-on-top surface-navigation HUD.
- Show material and RhinoSpotter **Location** directly in the tracker.
- Show **Travel to <system>** when the tracked target is in another system.
- Show **Approach body <body>** while the ship is still too far from the target body for surface coordinates to be available.
- Combine surface separation with live altitude during aerial approach so the target distance remains meaningful before landing.
- Use live heading to display a relative direction arrow.
- Remember the tracker position independently from the main EDMC window.
- Launch ED Hotspots Finder directly from EDMC through **Open Finder**.
- Automatically check the shared Finder + EDMC Plugin GitHub release channel on EDMC startup and offer to open GitHub when a newer release is available.
- Follow the current EDMC theme in the main controls and results window while keeping the tracker on its fixed high-contrast palette.

### Community Deposits behavior

The plugin uses the same Community Deposits backend as ED Hotspots Finder. It does not create or maintain a separate deposit database.

Repeated synchronization of an unchanged RhinoSpotter report does not intentionally advance the deposit's visible **Updated** timestamp.

In v1.0.2, meaningful mutable fields included **Rigs**, **Amount** and depletion state. Current releases also support RhinoSpotter edits to **Location**, **Material** and **Density**.

### Installation

Download:

```text
Hotspots-Finder-EDMC-Plugin-v1.0.2.zip
```

Extract it so this folder exists:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\EDHF_Community_Navigator\
```

Then restart EDMarketConnector.

RhinoSpotter 5.1+ is required only for **Sync Bookmarks**. Community Deposits scanning and tracking can still be used independently.
