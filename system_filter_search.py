#!/usr/bin/env python3

"""System-search helper for the v8 local GUI.

This keeps the new Reference System / Max Distance behaviour isolated while
v8 functionality is still being completed. It reuses finder_engine's Spansh
request/retry helpers and can be consolidated into the core engine later.
"""

import math

import finder_engine as engine


DEFAULT_MAX_DISTANCE_LY = 50.0
SYSTEM_NAME_LOOKUP_URL = "https://spansh.co.uk/api/systems/field_values/system_names"


def _format_distance(value):
    return f"{float(value):g}"


def search_systems_by_filters(
    faction_name,
    power_name,
    selected_power_states,
    *,
    reference_system="",
    max_distance_ly=DEFAULT_MAX_DISTANCE_LY,
    include_distances=False,
    cancel_event=None,
):
    faction_name = str(faction_name or "").strip()
    power_name = str(power_name or "").strip()
    reference_system = str(reference_system or "").strip()
    selected_power_states = [
        str(state).strip()
        for state in selected_power_states
        if str(state).strip()
    ]

    filters = {}
    if faction_name:
        filters["controlling_minor_faction"] = {"value": [faction_name]}
    if power_name:
        filters["power"] = {"value": [power_name]}
        if selected_power_states:
            filters["power_state"] = {"value": selected_power_states}

    # Current Spansh systems/search behaviour matches the approach used by
    # EliteMining: reference_system belongs at the top level, results are sorted
    # by distance, and the requested radius is applied client-side from the
    # returned `distance` field. Sending a `distance` filter together with
    # reference_system currently produces HTTP 400.
    if reference_system:
        try:
            max_distance_ly = float(max_distance_ly)
        except (TypeError, ValueError) as exc:
            raise ValueError("Max Distance (LY) must be a number.") from exc
        if max_distance_ly <= 0:
            raise ValueError("Max Distance (LY) must be greater than 0.")

    if not filters and not reference_system:
        return ([], {}) if include_distances else []

    print("Searching Spansh systems with filters:")
    if faction_name:
        print(f'  Controlling faction: "{faction_name}"')
    if power_name:
        print(f'  Power: "{power_name}"')
        print(
            "  Power states: "
            + (", ".join(selected_power_states) if selected_power_states else "ALL")
        )
    if reference_system:
        print(f'  Reference system: "{reference_system}"')
        print(f"  Max distance: {_format_distance(max_distance_ly)} LY")

    systems = []
    distances = {}
    seen = set()
    page = 0
    selected_state_keys = {engine.norm(state) for state in selected_power_states}

    while True:
        engine.check_cancel(cancel_event)
        payload = {
            "size": engine.PAGE_SIZE,
            "page": page,
        }
        if filters:
            payload["filters"] = filters

        if reference_system:
            payload["reference_system"] = reference_system
            payload["sort"] = [
                {
                    "distance": {
                        "direction": "asc",
                    }
                }
            ]

        response = engine.request_with_retries(
            "POST",
            engine.SPANSH_SYSTEMS_URL,
            cancel_event=cancel_event,
            json=payload,
            headers={
                "User-Agent": engine.USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        data = response.json()
        results = data.get("results", []) or []
        total = int(data.get("count", 0) or 0)
        reached_distance_limit = False

        for item in results:
            distance = None
            if reference_system:
                try:
                    distance = float(item.get("distance", ""))
                except (TypeError, ValueError):
                    # A reference search should always return distance. If a
                    # malformed row does not, it cannot be safely radius-filtered.
                    continue

                # Results are requested in ascending distance order, so once we
                # cross the radius there is no reason to request later pages.
                if distance > max_distance_ly:
                    reached_distance_limit = True
                    break

            if faction_name:
                if not engine.value_matches_exact(
                    item.get("controlling_minor_faction", ""), faction_name
                ):
                    continue

            if power_name:
                if not engine.value_matches_exact(item.get("power", []), power_name):
                    continue
                if selected_state_keys:
                    if engine.norm(item.get("power_state", "")) not in selected_state_keys:
                        continue

            system_name = str(
                item.get("name") or item.get("system_name") or ""
            ).strip()
            key = engine.norm(system_name)
            if not system_name or key in seen:
                continue

            seen.add(key)
            systems.append(system_name)

            if reference_system and distance is not None:
                distances[key] = distance

        if reached_distance_limit:
            break
        if not results or (page + 1) * engine.PAGE_SIZE >= total:
            break

        page += 1
        engine.cancellable_sleep(engine.DELAY, cancel_event)

    engine.check_cancel(cancel_event)

    if reference_system:
        systems.sort(
            key=lambda name: (
                distances.get(engine.norm(name), float("inf")),
                name.casefold(),
            )
        )
    else:
        systems.sort(key=str.casefold)

    print(f"Systems matching filters: {len(systems)}")

    if include_distances:
        return systems, distances
    return systems


def lookup_system_coordinates(system_name, *, cancel_event=None):
    """Return (x, y, z) for an exact system name using Spansh field values."""

    engine.check_cancel(cancel_event)
    system_name = str(system_name or "").strip()
    if not system_name:
        raise ValueError("Reference System is required.")

    response = engine.request_with_retries(
        "GET",
        SYSTEM_NAME_LOOKUP_URL,
        cancel_event=cancel_event,
        params={"q": system_name},
        headers={
            "User-Agent": engine.USER_AGENT,
            "Accept": "application/json",
        },
    )
    data = response.json()
    candidates = data.get("min_max", []) or []
    wanted = engine.norm(system_name)

    for item in candidates:
        if engine.norm(item.get("name", "")) != wanted:
            continue
        try:
            return (
                float(item["x"]),
                float(item["y"]),
                float(item["z"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f'Spansh returned invalid coordinates for "{system_name}".'
            ) from exc

    raise ValueError(f'System not found on Spansh: "{system_name}".')


def filter_systems_within_distance(
    reference_system,
    systems,
    *,
    max_distance_ly=DEFAULT_MAX_DISTANCE_LY,
    cancel_event=None,
):
    """Filter a small candidate set by true 3D distance from a reference.

    This is intended for Community Deposits: only systems which already have
    database rows are looked up, avoiding a galaxy-wide radius search.
    """

    reference_system = str(reference_system or "").strip()
    if not reference_system:
        return list(systems or []), {}

    try:
        max_distance_ly = float(max_distance_ly)
    except (TypeError, ValueError) as exc:
        raise ValueError("Max Distance (LY) must be a number.") from exc
    if max_distance_ly <= 0:
        raise ValueError("Max Distance (LY) must be greater than 0.")

    candidates = engine.deduplicate(systems or [])
    if not candidates:
        return [], {}

    print("Filtering database systems by distance:")
    print(f'  Reference system: "{reference_system}"')
    print(f"  Max distance: {_format_distance(max_distance_ly)} LY")
    print(f"  Candidate database systems: {len(candidates)}")

    ref_x, ref_y, ref_z = lookup_system_coordinates(
        reference_system,
        cancel_event=cancel_event,
    )

    kept = []
    distances = {}
    for system in candidates:
        engine.check_cancel(cancel_event)
        key = engine.norm(system)

        if key == engine.norm(reference_system):
            distance = 0.0
        else:
            try:
                x, y, z = lookup_system_coordinates(
                    system,
                    cancel_event=cancel_event,
                )
            except ValueError as exc:
                print(f"Skipping database system {system}: {exc}")
                continue

            distance = math.sqrt(
                (x - ref_x) ** 2
                + (y - ref_y) ** 2
                + (z - ref_z) ** 2
            )

        if distance <= max_distance_ly:
            kept.append(system)
            distances[key] = distance

    kept.sort(key=str.casefold)
    print(f"Database systems within distance: {len(kept)}")
    return kept, distances
