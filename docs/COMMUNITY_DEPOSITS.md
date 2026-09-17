# Community Deposits

**Community Deposits** is a shared database of player-reported planetary surface deposits for **Elite Dangerous**.

The goal is to turn discoveries made by individual commanders into searchable community data that can be reused during multi-system research in **ED Hotspots Finder - Rings & Planets**.

## Why it exists

Surface deposits are useful only if someone knows where they are.

A commander may discover a valuable planetary location during normal gameplay, but that information usually remains local to that player. Community Deposits provides a way to collect compatible reports in one shared service so that future searches can surface known deposits across many systems.

This is especially useful when ED Hotspots Finder is used to narrow large groups of candidate systems for Powerplay-oriented activity and other targeted searches.

## Contribution flow

The intended workflow is:

**Discover → Bookmark → Synchronize → Share → Search**

1. A commander discovers a planetary surface deposit.
2. The location is recorded with a compatible tool such as RhinoSpotter.
3. ED Hotspots Finder can synchronize compatible local records with the Community Deposits service.
4. The shared database stores the contributed report.
5. Other commanders can retrieve known deposits when searching the relevant systems.

## Searching Community Deposits

Enable **Community Deposits** in ED Hotspots Finder before starting a scan.

The application queries the shared service for the systems included in the current search and displays known player-reported deposits in the Community Deposits results tab.

Community Deposits can therefore be used together with the same manual System Input or System Filters used for Hotspots and Planets searches.

## Help build the database

The database becomes more useful as more commanders contribute discoveries.

If you explore planetary surfaces or perform surface mining, you can help by recording the deposits you encounter and synchronizing compatible records with the shared database.

A contribution can improve future searches for everyone using the service.

## RhinoSpotter

ED Hotspots Finder currently supports optional synchronization of compatible local records created by **[RhinoSpotter](https://github.com/Fumlop/EDRhinoSpotter)**, an independent EDMC plugin developed by **Fumlop**.

RhinoSpotter is used to record discoveries in-game; ED Hotspots Finder provides the synchronization path to Community Deposits.

See [RhinoSpotter integration](RHINOSPOTTER.md) for the current workflow.

## Data quality

Community Deposits contains community-reported information.

Reports may become outdated, incomplete or unavailable over time. A missing result does not prove that no relevant deposit exists in a system or on a body.

The service should be treated as a growing discovery database rather than a complete catalogue of every planetary deposit in Elite Dangerous.

## Network access

Community Deposits is an online service. Internet access is required to retrieve shared records or synchronize contributions.
