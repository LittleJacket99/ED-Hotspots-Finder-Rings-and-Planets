# RhinoSpotter integration

**ED Hotspots Finder - Rings & Planets** includes optional integration with **[RhinoSpotter](https://github.com/Fumlop/EDRhinoSpotter)**, an independent EDMC plugin developed by **Fumlop** for Elite Dangerous surface mining.

RhinoSpotter and ED Hotspots Finder are separate projects with complementary roles.

## What RhinoSpotter does

RhinoSpotter helps commanders record planetary surface-mining locations while playing Elite Dangerous. Those local records can include information such as system, body, material, location and coordinates.

ED Hotspots Finder does not replace RhinoSpotter's in-game recording workflow.

## Why the integration exists

The purpose of the integration is to help build the shared **Community Deposits** database.

The intended workflow is:

**RhinoSpotter records a discovery → ED Hotspots Finder synchronizes it → Community Deposits makes it searchable across systems.**

This lets local discoveries made by individual commanders contribute to a larger shared dataset that can later be used during multi-system searches.

## Current synchronization workflow

Current RhinoSpotter releases store bookmarks in a SQLite database:

```text
%LOCALAPPDATA%\RhinoSpotter\db\rhinospotter.db
```

ED Hotspots Finder automatically detects this database from the standard RhinoSpotter data folder:

```text
%LOCALAPPDATA%\RhinoSpotter
```

The database is opened read-only. Older RhinoSpotter installations that still use JSON cards are also supported as a fallback.

A custom RhinoSpotter data folder can be selected in ED Hotspots Finder Settings.

When synchronization is started, compatible bookmarks are validated and prepared before being sent to the Community Deposits service.

The synchronization result reports the detected source, bookmark count, valid records, new deposits, matched reports, updated reports and errors.

## Using RhinoSpotter with ED Hotspots Finder

1. Install and use RhinoSpotter normally with EDMC.
2. Record planetary deposits while playing.
3. Open ED Hotspots Finder.
4. Configure the RhinoSpotter data folder in Settings if the standard location is not being used.
5. Run the RhinoSpotter synchronization workflow.
6. Use Community Deposits searches to retrieve shared reports alongside other system-search results.

## Project credit

RhinoSpotter is developed and maintained independently by **Fumlop**.

Project repository:

**https://github.com/Fumlop/EDRhinoSpotter**

ED Hotspots Finder does not bundle RhinoSpotter and does not claim ownership of the RhinoSpotter project or its code.

## Community Deposits

For more information about the shared database and how contributions are used, see [Community Deposits](COMMUNITY_DEPOSITS.md).
