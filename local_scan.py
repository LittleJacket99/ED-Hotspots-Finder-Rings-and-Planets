#!/usr/bin/env python3

"""Local scan pipeline for the v8 desktop UI.

This module contains no Google Sheets calls and uses the dedicated v8
Google-free Finder engine.
"""

import community_deposits
import finder_engine as engine
import system_filter_search


DISTANCE_HEADER = "Distance (LY)"


class LocalScanError(RuntimeError):
    pass


def normalize_config(config):
    config = dict(config or {})

    systems = engine.deduplicate([
        str(value).strip()
        for value in config.get("systems", [])
        if str(value).strip()
    ])

    reference_system = str(
        config.get("reference_system", "") or ""
    ).strip()

    max_distance_raw = str(
        config.get("max_distance_ly", "50") or ""
    ).strip()
    if not max_distance_raw:
        max_distance_raw = "50"

    max_distance_ly = 50.0
    if reference_system:
        try:
            max_distance_ly = float(max_distance_raw.replace(",", "."))
        except ValueError as exc:
            raise LocalScanError(
                "Max Distance (LY) must be a number."
            ) from exc

        if max_distance_ly <= 0:
            raise LocalScanError(
                "Max Distance (LY) must be greater than 0."
            )

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
        "reference_system": reference_system,
        "max_distance_ly": max_distance_ly,
        "only_positive_results": bool(
            config.get("only_positive_results", False)
        ),
        "community_deposits_enabled": bool(
            config.get("community_deposits_enabled", False)
        ),
    }

    return normalized


def _nothing_enabled(config):
    return (
        not config["hotspots_enabled"]
        and not config["planets_enabled"]
        and not config["community_deposits_enabled"]
    )


def _format_result_distance(value):
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def _add_distance_column(headers, rows, distances):
    """Insert Distance (LY) after System and populate visible system rows."""

    headers = list(headers or [])
    if DISTANCE_HEADER not in headers:
        try:
            system_index = headers.index("System")
        except ValueError:
            headers.append(DISTANCE_HEADER)
        else:
            headers.insert(system_index + 1, DISTANCE_HEADER)

    output_rows = []
    for source in rows or []:
        row = dict(source)
        system_name = str(row.get("System", "") or "").strip()
        if system_name:
            row[DISTANCE_HEADER] = _format_result_distance(
                distances.get(engine.norm(system_name), "")
            )
        else:
            # Compact Hotspots/Planets rows intentionally blank System on
            # repeated lines; keep Distance blank there as well.
            row[DISTANCE_HEADER] = ""
        output_rows.append(row)

    return headers, output_rows


def run_local_scan(config, cancel_event=None):
    """Run the Finder logic and return data directly to the GUI."""

    engine.check_cancel(cancel_event)
    config = normalize_config(config)

    faction_name = config["faction_name"]
    power_name = config["power_name"]
    reference_system = config["reference_system"]
    max_distance_ly = config["max_distance_ly"]
    system_distances = {}

    selected_power_states = [
        state
        for state, enabled in config["power_states"].items()
        if enabled
    ]

    effective_power_states = selected_power_states if power_name else []

    if faction_name or power_name:
        systems, system_distances = system_filter_search.search_systems_by_filters(
            faction_name,
            power_name,
            effective_power_states,
            reference_system=reference_system,
            max_distance_ly=max_distance_ly,
            include_distances=True,
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
                "community_rows": [],
                "summary": {
                    "status": "NO_SYSTEMS_MATCHING_FILTERS",
                    "systems_found": 0,
                    "faction_name": faction_name,
                    "power_name": power_name,
                    "power_state_filters": effective_power_states,
                    "reference_system": reference_system,
                    "max_distance_ly": (
                        max_distance_ly if reference_system else None
                    ),
                    "hotspots_enabled": config["hotspots_enabled"],
                    "planets_enabled": config["planets_enabled"],
                    "community_deposits_enabled": config[
                        "community_deposits_enabled"
                    ],
                },
            }

        if _nothing_enabled(config):
            return {
                "status": "SYSTEM_LIST_UPDATED",
                "systems": systems,
                "hotspot_rows": [],
                "planet_rows": [],
                "community_rows": [],
                "summary": {
                    "status": "SYSTEM_LIST_UPDATED",
                    "systems_found": len(systems),
                    "faction_name": faction_name,
                    "power_name": power_name,
                    "power_state_filters": effective_power_states,
                    "reference_system": reference_system,
                    "max_distance_ly": (
                        max_distance_ly if reference_system else None
                    ),
                    "hotspots_enabled": False,
                    "planets_enabled": False,
                    "community_deposits_enabled": False,
                },
            }

    else:
        systems = config["systems"]

        if not systems:
            raise LocalScanError(
                "Add at least one system, or enter a Faction or Power."
            )

        if _nothing_enabled(config):
            return {
                "status": "NO_ACTION_SELECTED",
                "systems": systems,
                "hotspot_rows": [],
                "planet_rows": [],
                "community_rows": [],
                "summary": {
                    "status": "NO_ACTION_SELECTED",
                    "hotspots_enabled": False,
                    "planets_enabled": False,
                    "community_deposits_enabled": False,
                    "systems_found": len(systems),
                },
            }

    print(f"Systems loaded: {len(systems)}")
    print(f"Hotspots: {config['hotspots_enabled']}")
    print(f"Planets: {config['planets_enabled']}")
    print(f"Community Deposits: {config['community_deposits_enabled']}")
    if reference_system and (faction_name or power_name):
        print(
            f"Reference filter: {reference_system} / "
            f"{max_distance_ly:g} LY max"
        )

    bodies_by_system = {}
    unresolved = []

    if config["hotspots_enabled"] or config["planets_enabled"]:
        bodies_by_system, unresolved = engine.query_all_systems(
            systems,
            cancel_event=cancel_event,
        )
        engine.check_cancel(cancel_event)

    hotspot_filtered = []
    hotspot_clean = []
    planet_filtered = []
    planet_clean = []
    community_headers = []
    community_rows = []

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

        hotspot_clean = engine.clean_hotspot_rows(hotspot_filtered)

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

        planet_clean = engine.clean_planet_rows(planet_filtered)

    if config["community_deposits_enabled"]:
        community_headers, community_rows = (
            community_deposits.fetch_deposits_for_systems(
                systems,
                cancel_event=cancel_event,
            )
        )
        engine.check_cancel(cancel_event)

    hotspot_headers = list(engine.HOTSPOT_HEADERS)
    planet_headers = list(engine.PLANET_HEADERS)

    show_reference_distance = bool(
        reference_system and (faction_name or power_name)
    )
    if show_reference_distance:
        hotspot_headers, hotspot_clean = _add_distance_column(
            hotspot_headers,
            hotspot_clean,
            system_distances,
        )
        planet_headers, planet_clean = _add_distance_column(
            planet_headers,
            planet_clean,
            system_distances,
        )
        community_headers, community_rows = _add_distance_column(
            community_headers,
            community_rows,
            system_distances,
        )

    summary = engine.build_summary(
        config,
        hotspot_filtered,
        planet_filtered,
        unresolved,
    )
    summary["community_deposits_enabled"] = config[
        "community_deposits_enabled"
    ]
    summary["community_deposits_found"] = len(community_rows)
    summary["reference_system"] = reference_system
    summary["max_distance_ly"] = (
        max_distance_ly
        if reference_system and (faction_name or power_name)
        else None
    )

    return {
        "status": "COMPLETED",
        "systems": systems,
        "hotspot_headers": hotspot_headers,
        "hotspot_rows": hotspot_clean,
        "planet_headers": planet_headers,
        "planet_rows": planet_clean,
        "community_headers": community_headers,
        "community_rows": community_rows,
        "unresolved": unresolved,
        "summary": summary,
    }
