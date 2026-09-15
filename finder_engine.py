#!/usr/bin/env python3

"""Google-free core engine for Hotspots & Landables Finder v8."""

import time

import requests


SPANSH_URL = "https://spansh.co.uk/api/bodies/search"
SPANSH_SYSTEMS_URL = "https://spansh.co.uk/api/systems/search"
USER_AGENT = "ED-Hotspots-Landables-Finder/8.0"

BATCH_SIZE = 25
PAGE_SIZE = 500
DELAY = 1.6
RETRIES = 3
REQUEST_TIMEOUT = 45

POWER_LIST = [
    "Aisling Duval",
    "Archon Delaine",
    "Arissa Lavigny-Duval",
    "Denton Patreus",
    "Edmund Mahon",
    "Felicia Winters",
    "Jerome Archer",
    "Li Yong-Rui",
    "Nakato Kaine",
    "Pranav Antal",
    "Yuri Grom",
    "Zemina Torval",
]


class ScanCancelled(RuntimeError):
    pass


def check_cancel(cancel_event=None):
    if cancel_event is not None and cancel_event.is_set():
        raise ScanCancelled("Scan cancelled by user.")


def cancellable_sleep(seconds, cancel_event=None):
    if not seconds:
        return
    if cancel_event is None:
        time.sleep(seconds)
        return
    if cancel_event.wait(seconds):
        raise ScanCancelled("Scan cancelled by user.")


def request_with_retries(method, url, cancel_event=None, **kwargs):
    last_error = None
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)

    for attempt in range(1, RETRIES + 1):
        check_cancel(cancel_event)
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except ScanCancelled:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= RETRIES:
                break
            print(
                f"Request failed ({attempt}/{RETRIES}): {exc}. Retrying..."
            )
            cancellable_sleep(min(2.0 * attempt, 5.0), cancel_event)

    raise RuntimeError(str(last_error) if last_error else "Request failed.")


def norm(value):
    return " ".join(str(value or "").strip().lower().split())


def norm_filter(value):
    value = norm(value)
    value = value.replace("-", " ")
    return " ".join(value.split())


def deduplicate(values):
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = norm(text)
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def value_matches_exact(value, expected):
    expected_key = norm(expected)
    if isinstance(value, (list, tuple, set)):
        return any(norm(item) == expected_key for item in value)
    return norm(value) == expected_key


def search_systems_by_filters(
    faction_name,
    power_name,
    selected_power_states,
    cancel_event=None,
):
    faction_name = str(faction_name or "").strip()
    power_name = str(power_name or "").strip()
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

    if not filters:
        return []

    print("Searching Spansh systems with filters:")
    if faction_name:
        print(f'  Controlling faction: "{faction_name}"')
    if power_name:
        print(f'  Power: "{power_name}"')
        print(
            "  Power states: "
            + (", ".join(selected_power_states) if selected_power_states else "ALL")
        )

    systems = []
    seen = set()
    page = 0
    selected_state_keys = {norm(state) for state in selected_power_states}

    while True:
        check_cancel(cancel_event)
        payload = {"filters": filters, "size": PAGE_SIZE, "page": page}
        response = request_with_retries(
            "POST",
            SPANSH_SYSTEMS_URL,
            cancel_event=cancel_event,
            json=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        data = response.json()
        results = data.get("results", []) or []
        total = int(data.get("count", 0) or 0)

        for item in results:
            if faction_name:
                if not value_matches_exact(
                    item.get("controlling_minor_faction", ""), faction_name
                ):
                    continue

            if power_name:
                if not value_matches_exact(item.get("power", []), power_name):
                    continue
                if selected_state_keys:
                    if norm(item.get("power_state", "")) not in selected_state_keys:
                        continue

            system_name = str(
                item.get("name") or item.get("system_name") or ""
            ).strip()
            key = norm(system_name)
            if system_name and key not in seen:
                seen.add(key)
                systems.append(system_name)

        if not results or (page + 1) * PAGE_SIZE >= total:
            break

        page += 1
        cancellable_sleep(DELAY, cancel_event)

    check_cancel(cancel_event)
    systems.sort(key=str.casefold)
    print(f"Systems matching filters: {len(systems)}")
    return systems


def request_spansh_page(systems, page, cancel_event=None):
    payload = {
        "filters": {"system_name": {"value": systems}},
        "size": PAGE_SIZE,
        "page": page,
    }
    response = request_with_retries(
        "POST",
        SPANSH_URL,
        cancel_event=cancel_event,
        json=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    return response.json()


def fetch_batch(systems, cancel_event=None):
    bodies_by_system = {}
    page = 0

    while True:
        check_cancel(cancel_event)
        data = request_spansh_page(systems, page, cancel_event=cancel_event)
        bodies = data.get("results", []) or []
        total = int(data.get("count", 0) or 0)

        for body in bodies:
            system_name = str(body.get("system_name", "") or "").strip()
            if not system_name:
                continue
            bodies_by_system.setdefault(norm(system_name), []).append(body)

        if not bodies or (page + 1) * PAGE_SIZE >= total:
            break

        page += 1
        cancellable_sleep(DELAY, cancel_event)

    check_cancel(cancel_event)
    return bodies_by_system


def query_all_systems(systems, cancel_event=None):
    all_bodies = {}
    unresolved = []
    batches = list(chunks(systems, BATCH_SIZE))

    for batch_number, batch in enumerate(batches, 1):
        check_cancel(cancel_event)
        print(f"[{batch_number}/{len(batches)}] Querying {len(batch)} systems...")

        try:
            result = fetch_batch(batch, cancel_event=cancel_event)
            for key, bodies in result.items():
                all_bodies.setdefault(key, []).extend(bodies)
        except ScanCancelled:
            raise
        except Exception as exc:
            print(f"Batch failed after retries: {exc}")
            print("Falling back to one-system-at-a-time...")

            for system in batch:
                try:
                    check_cancel(cancel_event)
                    result = fetch_batch([system], cancel_event=cancel_event)
                    for key, bodies in result.items():
                        all_bodies.setdefault(key, []).extend(bodies)
                except ScanCancelled:
                    raise
                except Exception as single_exc:
                    print(f"UNRESOLVED: {system}: {single_exc}")
                    unresolved.append(system)
                cancellable_sleep(DELAY, cancel_event)

        if batch_number < len(batches):
            cancellable_sleep(DELAY, cancel_event)

    check_cancel(cancel_event)
    return all_bodies, unresolved


HOTSPOT_HEADERS = [
    "System",
    "Status",
    "Body",
    "Ring",
    "Ring Type",
    "Reserve Level",
    "LS Distance",
    "Material",
    "Hotspot Count",
]


def empty_hotspot_status(system, status):
    return {
        "System": system,
        "Status": status,
        "Body": "",
        "Ring": "",
        "Ring Type": "",
        "Reserve Level": "",
        "LS Distance": "",
        "Material": "",
        "Hotspot Count": "",
    }


def build_hotspot_rows(systems, bodies_by_system, unresolved):
    unresolved_keys = {norm(x) for x in unresolved}
    raw_rows = []

    for system in systems:
        key = norm(system)
        if key in unresolved_keys:
            raw_rows.append(empty_hotspot_status(system, "UNKNOWN_API_ERROR"))
            continue

        bodies = bodies_by_system.get(key, [])
        if not bodies:
            raw_rows.append(empty_hotspot_status(system, "SYSTEM_NOT_FOUND"))
            continue

        has_ring = False
        for body in bodies:
            body_name = str(body.get("name", "") or "").strip()
            reserve = body.get("reserve_level", "")
            ls_distance = body.get("distance_to_arrival", "")

            for ring in body.get("rings", []) or []:
                has_ring = True
                ring_name = str(ring.get("name", "") or "").strip()
                ring_type = ring.get("type", "")
                signals = ring.get("signals", []) or []

                if not signals:
                    raw_rows.append({
                        "System": system,
                        "Status": "NO_HOTSPOT / NOT SCANNED",
                        "Body": body_name,
                        "Ring": ring_name,
                        "Ring Type": ring_type,
                        "Reserve Level": reserve,
                        "LS Distance": ls_distance,
                        "Material": "",
                        "Hotspot Count": "",
                    })
                    continue

                valid_signal = False
                for signal in signals:
                    material = str(signal.get("name", "") or "").strip()
                    if not material:
                        continue
                    valid_signal = True
                    raw_rows.append({
                        "System": system,
                        "Status": "HOTSPOT_FOUND",
                        "Body": body_name,
                        "Ring": ring_name,
                        "Ring Type": ring_type,
                        "Reserve Level": reserve,
                        "LS Distance": ls_distance,
                        "Material": material,
                        "Hotspot Count": signal.get("count", 0),
                    })

                if not valid_signal:
                    raw_rows.append({
                        "System": system,
                        "Status": "NO_HOTSPOT / NOT SCANNED",
                        "Body": body_name,
                        "Ring": ring_name,
                        "Ring Type": ring_type,
                        "Reserve Level": reserve,
                        "LS Distance": ls_distance,
                        "Material": "",
                        "Hotspot Count": "",
                    })

        if not has_ring:
            raw_rows.append(empty_hotspot_status(system, "NO_RINGS"))

    return raw_rows


def filter_hotspot_rows(systems, raw_rows, ring_types, materials, only_pristine):
    selected_ring_types = {
        norm_filter(name) for name, enabled in ring_types.items() if enabled
    }
    selected_materials = {
        norm_filter(name) for name, enabled in materials.items() if enabled
    }
    system_level_statuses = {"UNKNOWN_API_ERROR", "SYSTEM_NOT_FOUND", "NO_RINGS"}
    rows_by_system = {norm(system): [] for system in systems}

    for row in raw_rows:
        rows_by_system.setdefault(norm(row["System"]), []).append(row)

    filtered = []
    for system in systems:
        source_rows = rows_by_system.get(norm(system), [])
        kept = []

        for row in source_rows:
            status = row["Status"]
            if status in system_level_statuses:
                kept.append(row)
                continue

            if selected_ring_types:
                if norm_filter(row["Ring Type"]) not in selected_ring_types:
                    continue

            if only_pristine and norm_filter(row["Reserve Level"]) != "pristine":
                continue

            if selected_materials:
                if status != "HOTSPOT_FOUND":
                    continue
                if norm_filter(row["Material"]) not in selected_materials:
                    continue

            kept.append(row)

        if kept:
            filtered.extend(kept)
        else:
            filtered.append(empty_hotspot_status(system, "NO_MATCHING_HOTSPOTS"))

    return filtered


def clean_hotspot_rows(raw_rows):
    clean_rows = []
    previous_system = None
    previous_ring_key = None

    for original in raw_rows:
        row = dict(original)
        system = row["System"]
        body = row["Body"]
        ring = row["Ring"]
        ring_key = (system, body, ring)

        if system == previous_system:
            row["System"] = ""
        else:
            previous_system = system
            previous_ring_key = None

        if ring and ring_key == previous_ring_key:
            row["Status"] = ""
            row["Body"] = ""
            row["Ring"] = ""
            row["Ring Type"] = ""
            row["Reserve Level"] = ""
            row["LS Distance"] = ""
        elif ring:
            previous_ring_key = ring_key

        clean_rows.append(row)

    return clean_rows


PLANET_HEADERS = [
    "System",
    "Status",
    "Body",
    "Planet Type",
    "Landable",
    "Volcanism",
    "LS Distance",
]


def empty_planet_status(system, status):
    return {
        "System": system,
        "Status": status,
        "Body": "",
        "Planet Type": "",
        "Landable": "",
        "Volcanism": "",
        "LS Distance": "",
    }


def build_planet_rows(systems, bodies_by_system, unresolved):
    unresolved_keys = {norm(x) for x in unresolved}
    raw_rows = []

    for system in systems:
        key = norm(system)
        if key in unresolved_keys:
            raw_rows.append(empty_planet_status(system, "UNKNOWN_API_ERROR"))
            continue

        bodies = bodies_by_system.get(key, [])
        if not bodies:
            raw_rows.append(empty_planet_status(system, "SYSTEM_NOT_FOUND"))
            continue

        planets = []
        for body in bodies:
            if norm(body.get("type", "")) != "planet":
                continue

            landable_value = body.get("is_landable", body.get("landable", None))
            if landable_value is True:
                landable = "Yes"
            elif landable_value is False:
                landable = "No"
            else:
                landable = ""

            planets.append({
                "System": system,
                "Status": "PLANET_FOUND",
                "Body": str(body.get("name", "") or "").strip(),
                "Planet Type": str(body.get("subtype", "") or "").strip(),
                "Landable": landable,
                "Volcanism": str(body.get("volcanism_type", "") or "").strip(),
                "LS Distance": body.get("distance_to_arrival", ""),
            })

        if planets:
            raw_rows.extend(planets)
        else:
            raw_rows.append(empty_planet_status(system, "NO_PLANETS"))

    return raw_rows


def planet_type_matches(value, selected_types):
    active = {name for name, enabled in selected_types.items() if enabled}
    if not active:
        return True

    subtype = norm_filter(value)
    aliases = {
        "icy": {"icy body", "icy"},
        "metal rich": {"metal rich body", "metal rich"},
        "high metal content": {
            "high metal content world",
            "high metal content body",
            "high metal content",
        },
        "rocky": {"rocky body", "rocky"},
        "rocky ice": {"rocky ice world", "rocky ice body", "rocky ice"},
    }

    for category in active:
        if subtype in aliases.get(category, {category}):
            return True
    return False


def filter_planet_rows(systems, raw_rows, only_landables, selected_types):
    system_level_statuses = {"UNKNOWN_API_ERROR", "SYSTEM_NOT_FOUND", "NO_PLANETS"}
    rows_by_system = {norm(system): [] for system in systems}

    for row in raw_rows:
        rows_by_system.setdefault(norm(row["System"]), []).append(row)

    filtered = []
    has_type_filters = any(selected_types.values())

    for system in systems:
        source_rows = rows_by_system.get(norm(system), [])
        kept = []
        system_status_rows = []

        for row in source_rows:
            if row["Status"] in system_level_statuses:
                system_status_rows.append(row)
                continue
            if row["Status"] != "PLANET_FOUND":
                continue
            if only_landables and row["Landable"] != "Yes":
                continue
            if not planet_type_matches(row["Planet Type"], selected_types):
                continue
            kept.append(row)

        if kept:
            filtered.extend(kept)
            continue
        if system_status_rows:
            filtered.extend(system_status_rows)
            continue

        if only_landables and has_type_filters:
            status = "NO_MATCHING_LANDABLE_PLANETS"
        elif only_landables:
            status = "NO_LANDABLE_PLANETS"
        elif has_type_filters:
            status = "NO_MATCHING_PLANET_TYPES"
        else:
            status = "NO_PLANETS"

        filtered.append(empty_planet_status(system, status))

    return filtered


def clean_planet_rows(raw_rows):
    clean_rows = []
    previous_system = None

    for original in raw_rows:
        row = dict(original)
        system = row["System"]
        if system == previous_system:
            row["System"] = ""
            row["Status"] = ""
        else:
            previous_system = system
        clean_rows.append(row)

    return clean_rows


def build_summary(config, hotspot_rows, planet_rows, unresolved):
    hotspot_records = [
        row for row in hotspot_rows if row.get("Status") == "HOTSPOT_FOUND"
    ]
    planet_records = [
        row for row in planet_rows if row.get("Status") == "PLANET_FOUND"
    ]

    hotspot_total = 0
    for row in hotspot_records:
        try:
            hotspot_total += int(row.get("Hotspot Count", 0) or 0)
        except (TypeError, ValueError):
            pass

    return {
        "status": "COMPLETED",
        "systems": len(config.get("systems", [])),
        "hotspots_enabled": config.get("hotspots_enabled", False),
        "planets_enabled": config.get("planets_enabled", False),
        "hotspot_material_records_after_filters": len(hotspot_records),
        "hotspots_total_count_after_filters": hotspot_total,
        "planets_found_after_filters": len(planet_records),
        "unresolved_system_queries": len(unresolved),
        "unresolved_systems": list(unresolved),
    }
