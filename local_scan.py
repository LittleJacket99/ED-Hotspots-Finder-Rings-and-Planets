#!/usr/bin/env python3

"""Local scan pipeline for the v8 desktop UI.

This module contains no Google Sheets calls and uses the dedicated v8
Google-free Finder engine.
"""

import finder_engine as engine


class LocalScanError(RuntimeError):
    pass


def normalize_config(config):
    config = dict(config or {})

    systems = engine.deduplicate([
        str(value).strip()
        for value in config.get("systems", [])
        if str(value).strip()
    ])

    normalized = {
        "systems": systems,
        "hotspots_enabled": bool(config.get("hotspots_enabled", False)),
        "planets_enabled": bool(config.get("planets_enabled", False)),
        "ring_types": {
            "icy": False,
            "metallic": False,
            "metal rich": False,
            "rocky": False,
            **dict(config.get("ring_types", {})),
        },
        "materials": {
            "platinum": False,
            "bromellite": False,
            "monazite": False,
            **dict(config.get("materials", {})),
        },
        "only_pristine": bool(config.get("only_pristine", False)),
        "only_landables": bool(config.get("only_landables", False)),
        "planet_types": {
            "icy": False,
            "metal rich": False,
            "high metal content": False,
            "rocky": False,
            "rocky ice": False,
            **dict(config.get("planet_types", {})),
        },
        "faction_name": str(config.get("faction_name", "") or "").strip(),
        "power_name": str(config.get("power_name", "") or "").strip(),
        "power_states": {
            "Unoccupied": False,
            "Exploited": False,
            "Fortified": False,
            "Stronghold": False,
            **dict(config.get("power_states", {})),
        },
        "only_positive_results": bool(
            config.get("only_positive_results", False)
        ),
        "community_deposits_enabled": bool(
            config.get("community_deposits_enabled", False)
        ),
    }

    return normalized


def run_local_scan(config, cancel_event=None):
    """Run the Finder logic and return data directly to the GUI."""

    engine.check_cancel(cancel_event)
    config = normalize_config(config)

    faction_name = config["faction_name"]
    power_name = config["power_name"]

    selected_power_states = [
        state
        for state, enabled in config["power_states"].items()
        if enabled
    ]

    effective_power_states = (
        selected_power_states if power_name else []
    )

    if faction_name or power_name:
        systems = engine.search_systems_by_filters(
            faction_name,
            power_name,
            effective_power_states,
            cancel_event=cancel_event,
        )

        engine.check_cancel(cancel_event)
        config["systems"] = systems

        if not systems:
            return {
                "status": "NO_SYSTEMS_MATCHING_FILTERS",
                "systems": [],
                "hotspot_rows": [],
                "planet_rows": [],
                "summary": {
                    "status": "NO_SYSTEMS_MATCHING_FILTERS",
                    "systems_found": 0,
                    "faction_name": faction_name,
                    "power_name": power_name,
                    "power_state_filters": effective_power_states,
                    "hotspots_enabled": config["hotspots_enabled"],
                    "planets_enabled": config["planets_enabled"],
                },
            }

        if (
            not config["hotspots_enabled"]
            and not config["planets_enabled"]
        ):
            return {
                "status": "SYSTEM_LIST_UPDATED",
                "systems": systems,
                "hotspot_rows": [],
                "planet_rows": [],
                "summary": {
                    "status": "SYSTEM_LIST_UPDATED",
                    "systems_found": len(systems),
                    "faction_name": faction_name,
                    "power_name": power_name,
                    "power_state_filters": effective_power_states,
                    "hotspots_enabled": False,
                    "planets_enabled": False,
                },
            }

    else:
        systems = config["systems"]

        if not systems:
            raise LocalScanError(
                "Add at least one system, or enter a Faction or Power."
            )

        if (
            not config["hotspots_enabled"]
            and not config["planets_enabled"]
        ):
            return {
                "status": "NO_ACTION_SELECTED",
                "systems": systems,
                "hotspot_rows": [],
                "planet_rows": [],
                "summary": {
                    "status": "NO_ACTION_SELECTED",
                    "hotspots_enabled": False,
                    "planets_enabled": False,
                    "systems_found": len(systems),
                },
            }

    print(f"Systems loaded: {len(systems)}")
    print(f"Hotspots: {config['hotspots_enabled']}")
    print(f"Planets: {config['planets_enabled']}")

    bodies_by_system, unresolved = engine.query_all_systems(
        systems,
        cancel_event=cancel_event,
    )

    engine.check_cancel(cancel_event)

    hotspot_filtered = []
    hotspot_clean = []
    planet_filtered = []
    planet_clean = []

    if config["hotspots_enabled"]:
        hotspot_raw = engine.build_hotspot_rows(
            systems,
            bodies_by_system,
            unresolved,
        )

        hotspot_filtered = engine.filter_hotspot_rows(
            systems,
            hotspot_raw,
            config["ring_types"],
            config["materials"],
            config["only_pristine"],
        )

        if config["only_positive_results"]:
            hotspot_filtered = [
                row
                for row in hotspot_filtered
                if row["Status"] == "HOTSPOT_FOUND"
            ]

        hotspot_clean = engine.clean_hotspot_rows(
            hotspot_filtered
        )

    if config["planets_enabled"]:
        planet_raw = engine.build_planet_rows(
            systems,
            bodies_by_system,
            unresolved,
        )

        planet_filtered = engine.filter_planet_rows(
            systems,
            planet_raw,
            config["only_landables"],
            config["planet_types"],
        )

        if config["only_positive_results"]:
            planet_filtered = [
                row
                for row in planet_filtered
                if row["Status"] == "PLANET_FOUND"
            ]

        planet_clean = engine.clean_planet_rows(
            planet_filtered
        )

    summary = engine.build_summary(
        config,
        hotspot_filtered,
        planet_filtered,
        unresolved,
    )

    return {
        "status": "COMPLETED",
        "systems": systems,
        "hotspot_headers": list(engine.HOTSPOT_HEADERS),
        "hotspot_rows": hotspot_clean,
        "planet_headers": list(engine.PLANET_HEADERS),
        "planet_rows": planet_clean,
        "unresolved": unresolved,
        "summary": summary,
    }
