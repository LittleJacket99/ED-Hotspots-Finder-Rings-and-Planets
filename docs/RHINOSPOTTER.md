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

In the current ED Hotspots Finder release, the RhinoSpotter synchronization workflow reads compatible local JSON card records from the configured cards directory.

The default path is:

```text
%LOCALAPPDATA%\RhinoSpotter\cards
```

A custom cards directory can be selected in ED Hotspots Finder Settings.

When synchronization is started, compatible records are validated and prepared before being sent to the Community Deposits service.

The synchronization result reports how many records were added, matched with an existing deposit, updated or rejected because of an error.

## Using RhinoSpotter with ED Hotspots Finder

1. Install and use RhinoSpotter normally with EDMC.
2. Record planetary deposits while playing.
3. Open ED Hotspots Finder.
4. Configure the RhinoSpotter cards path in Settings if the default path is not being used.
5. Run the RhinoSpotter synchronization workflow.
6. Use Community Deposits searches to retrieve shared reports alongside other system-search results.

## Project credit

RhinoSpotter is developed and maintained independently by **Fumlop**.

Project repository:

**https://github.com/Fumlop/EDRhinoSpotter**

ED Hotspots Finder does not bundle RhinoSpotter and does not claim ownership of the RhinoSpotter project or its code.

## Community Deposits

For more information about the shared database and how contributions are used, see [Community Deposits](COMMUNITY_DEPOSITS.md).
