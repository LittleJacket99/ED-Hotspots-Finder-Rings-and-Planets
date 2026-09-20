# RhinoSpotter integration

**ED Hotspots Finder - Rings & Planets** and the **Hotspots Finder EDMC Plugin** integrate with **[RhinoSpotter](https://github.com/Fumlop/EDRhinoSpotter)**, an independent EDMC plugin developed by **Fumlop** for Elite Dangerous surface mining.

RhinoSpotter and this project are separate projects with complementary roles.

## What RhinoSpotter does

RhinoSpotter helps commanders record planetary surface-mining locations while playing Elite Dangerous.

Compatible bookmarks can include information such as:

- system and body;
- RhinoSpotter Location;
- material;
- Rigs;
- Amount;
- Density;
- latitude and longitude;
- heading;
- planet radius and other available body metadata;
- depletion information.

ED Hotspots Finder and the EDMC Plugin do not replace RhinoSpotter's in-game recording workflow. They use compatible RhinoSpotter bookmarks as a contribution source for **Community Deposits**.

## Why the integration exists

The purpose of the integration is to help build the shared Community Deposits database.

The intended workflow is:

**RhinoSpotter records a discovery → Finder or EDMC Plugin synchronizes it → Community Deposits makes it searchable**

This lets local discoveries made by individual commanders contribute to a larger shared dataset.

## RhinoSpotter 5.1+ external API

Current RhinoSpotter releases expose a documented external API through:

```text
%LOCALAPPDATA%\EDMarketConnector\plugins\RhinoSpotter\rs_api.py
```

The integration uses `rs_api.bookmarks()` and currently supports RhinoSpotter API `SCHEMA = 1`.

Using the documented API avoids depending on RhinoSpotter's private storage implementation.

## ED Hotspots Finder behavior

The desktop Finder automatically prefers `rs_api.py` when it is available.

For older RhinoSpotter installations, the Finder retains compatibility fallbacks for:

- the local SQLite bookmark database, opened read-only;
- legacy JSON card folders.

A custom RhinoSpotter source can be selected in Finder Settings. The Settings status can show the detected source, RhinoSpotter API version when applicable, and bookmark count.

When synchronization is started, compatible bookmarks are validated and prepared before being sent to Community Deposits.

The completion summary reports values such as:

- bookmarks found;
- valid records;
- new deposits;
- reports matched to existing deposits;
- updated reports;
- unchanged reports;
- errors.

## EDMC Plugin behavior

The **Hotspots Finder EDMC Plugin** intentionally uses RhinoSpotter 5.1+ `rs_api.py` only.

Use **Sync Bookmarks** inside EDMC to send compatible bookmarks to Community Deposits.

RhinoSpotter is not required for the plugin's Community Deposits lookup or navigation features. If RhinoSpotter is missing or too old, only bookmark synchronization is unavailable.

## Stable report identity

The integration generates a stable `report_id` from fields that identify the bookmark/deposit rather than mutable state.

Fields such as **Rigs**, **Amount**, **Density**, `updated_at` and depletion timestamps are not used to deliberately create a new report identity when the same bookmark is edited.

This allows the same RhinoSpotter bookmark to update its existing Community Deposits report instead of creating a duplicate.

## Mutable deposit data

Current Community Deposits behavior treats these RhinoSpotter changes as meaningful updates:

- **Rigs**;
- **Amount**;
- depletion state.

**Density** remains stable after the Community Deposit is created.

Re-synchronizing the same values again returns `unchanged` and does not intentionally refresh the visible **Updated** timestamp.

## Location

RhinoSpotter's bookmark `location` value is mapped to Community Deposits `location_index`.

It is displayed as **Location** in both Finder and EDMC Plugin results, and it is also shown in the EDMC navigation HUD.

## Using RhinoSpotter with the Finder

1. Install RhinoSpotter 5.1+ as an EDMC plugin.
2. Record planetary deposits while playing.
3. Open ED Hotspots Finder.
4. Verify the detected RhinoSpotter source in Settings.
5. Run the synchronization workflow.
6. Search Community Deposits together with other Finder results.

## Using RhinoSpotter with the EDMC Plugin

1. Install RhinoSpotter 5.1+ and the Hotspots Finder EDMC Plugin.
2. Record bookmarks normally in RhinoSpotter.
3. Press **Sync Bookmarks** in Hotspots Finder Deposits Companion.
4. Use **Scan System** / **Open Deposits** to inspect Community Deposits for the current system.
5. Select a deposit and press **Start Tracking** when navigation is useful.

## Project credit

RhinoSpotter is developed and maintained independently by **Fumlop**.

Project repository:

**https://github.com/Fumlop/EDRhinoSpotter**

RhinoSpotter is not bundled with this project, and this project does not claim ownership of RhinoSpotter or its code.

## Community Deposits

For more information about the shared database and how contributions are used, see [Community Deposits](COMMUNITY_DEPOSITS.md).
