# Community Deposits

**Community Deposits** is the shared online database used by both **ED Hotspots Finder - Rings & Planets** and the **Hotspots Finder EDMC Plugin** for player-reported planetary surface deposits in **Elite Dangerous**.

The goal is to turn discoveries made by individual commanders into searchable community data that can be reused by other commanders.

## Why it exists

Surface deposits are useful only if someone knows where they are.

A commander may discover a valuable planetary location during normal gameplay, but that information would otherwise remain local to that player. Community Deposits provides a shared service where compatible reports can be stored, matched and retrieved later.

The desktop Finder can use these records during multi-system research. The EDMC Plugin can query the current system in-game and navigate to a selected deposit.

## Contribution flow

The intended workflow is:

**Discover → Bookmark → Synchronize → Share → Search**

1. A commander discovers a planetary surface deposit.
2. The location is recorded with RhinoSpotter.
3. ED Hotspots Finder or the Hotspots Finder EDMC Plugin compares compatible bookmarks with the local sync state and sends only new or modified records.
4. Community Deposits inserts a new deposit, matches the report to an existing nearby deposit, updates an existing report, or marks a sent report unchanged.
5. Other commanders can retrieve the shared deposit through the desktop Finder or the EDMC Plugin.

## Searching from ED Hotspots Finder

Enable **Community Deposits** before starting a Finder scan.

The Finder queries the shared service for the systems included in the current search and displays known player-reported deposits in the Community Deposits results tab.

Community Deposits can therefore be used with the same manual **System Input** or **System Filters** used for Hotspots and Planets searches.

Returned information can include:

- system;
- body;
- RhinoSpotter **Location**;
- material/commodity;
- Rigs;
- Amount;
- Density;
- depletion state / **Depleted at**;
- latitude and longitude;
- report count;
- Updated timestamp.

## Searching from the EDMC Plugin

The **Hotspots Finder EDMC Plugin** queries Community Deposits for the system currently reported by EDMC.

The plugin can:

- **Scan System** the first time;
- reopen the cached result snapshot with **Open Deposits**;
- use **Refresh Deposits** when relevant synchronized data changed;
- select a result and start the navigation HUD with **Start Tracking**.

The Finder and plugin use the same database. There is no separate EDMC deposit store.

## Help build the database

The database becomes more useful as more commanders contribute discoveries.

If you explore planetary surfaces or perform surface mining, you can help by recording the deposits you encounter with RhinoSpotter and synchronizing compatible bookmarks.

A contribution can improve future searches for everyone using the service.

## RhinoSpotter integration

Community Deposits contribution is integrated with **[RhinoSpotter](https://github.com/Fumlop/EDRhinoSpotter)**, an independent EDMC plugin developed by **Fumlop**.

RhinoSpotter 5.1+ exposes the documented external API:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\RhinoSpotter\rs_api.py
```

Both clients can use `rs_api.bookmarks()` as the source of compatible bookmarks.

The EDMC Plugin intentionally uses `rs_api.py` only. The desktop Finder prefers the same API but retains read-only SQLite and legacy JSON access as compatibility fallbacks for older RhinoSpotter installations.

See [RhinoSpotter integration](RHINOSPOTTER.md) for the detailed workflow.

## Report matching and updates

Each synchronized RhinoSpotter bookmark receives a stable `report_id`.

Finder and EDMC also keep local fingerprints keyed by stable RhinoSpotter bookmark identity. After the first successful synchronization, unchanged bookmarks are normally filtered locally and do not generate a Community Deposits POST or per-report D1 work.

The backend distinguishes:

- `inserted`;
- `matched_existing_deposit`;
- `updated_report`;
- `unchanged`.

Repeated synchronization of an unchanged report does not intentionally advance the deposit's visible **Updated** timestamp.

Current meaningful mutable fields for synchronized RhinoSpotter bookmarks are:

- **Location**;
- **Material**;
- **Rigs**;
- **Amount**;
- **Density**;
- depletion state.

Technical metadata such as a previously missing body ID or planet radius may be completed without being treated as a meaningful deposit update.

## Depletion state

RhinoSpotter records depletion as a timestamp rather than only a yes/no flag. Community Deposits stores this as `depleted_at`.

In Finder and EDMC result tables:

- an active deposit is displayed as **Active**;
- a depleted deposit is displayed with its depletion time as `YYYY-MM-DD HH:MM:SS`.

A commander can mark a RhinoSpotter bookmark **depleted**, synchronize it, and publish that state to Community Deposits. If the deposit is later found active again, setting the RhinoSpotter bookmark active and synchronizing it clears `depleted_at` in the shared record.

## Location

Community Deposits stores the RhinoSpotter bookmark location index as `location_index`.

Both the Finder and the EDMC Plugin expose this value as **Location** in results, and the EDMC navigation HUD also shows the selected deposit's Location.

## Nearby-report matching

When a new report does not already have a known stable report identity, the backend can match it to an existing deposit at the same body/material when the coordinates are within the configured nearby-distance threshold.

Candidate lookup combines technical Journal identifiers (`system_address` / `body_id`) when available with the canonical system/body/material lookup. This keeps older RhinoSpotter deposits that do not yet carry the technical IDs eligible for the same nearby-distance match.

This allows multiple reports to contribute to the same physical deposit rather than creating unnecessary duplicates.

## Data quality

Community Deposits contains community-reported information.

Reports may become outdated, incomplete or unavailable over time. A missing result does not prove that no relevant deposit exists in a system or on a body.

The service should be treated as a growing discovery database rather than a complete catalogue of every planetary deposit in Elite Dangerous.

## Network access

Community Deposits is an online service. Internet access is required to retrieve shared records or synchronize contributions.
