#!/usr/bin/env python3

"""Client helpers for the ED Alliance Community Deposits API."""

import json

import requests


API_BASE = "https://ed-alliance-community-deposits.littlejacket99.workers.dev"
DEPOSITS_URL = f"{API_BASE}/v1/deposits"
USER_AGENT = "ED-Hotspots-Landables-Finder/8.0"
REQUEST_TIMEOUT = 20


class CommunityDepositsError(RuntimeError):
    pass


def _check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        # Imported lazily so this module stays independent and easy to reuse.
        from finder_engine import ScanCancelled

        raise ScanCancelled("Scan cancelled by user.")


def _display_header(raw_key):
    aliases = {
        "id": "ID",
        "deposit_id": "Deposit ID",
        "system": "System",
        "system_name": "System",
        "star_system": "System",
        "body": "Body",
        "body_name": "Body",
        "commodity": "Commodity",
        "material": "Commodity",
        "latitude": "Latitude",
        "lat": "Latitude",
        "longitude": "Longitude",
        "lon": "Longitude",
        "lng": "Longitude",
        "planet_radius": "Planet Radius",
        "body_radius": "Planet Radius",
        "radius": "Planet Radius",
        "report_count": "Reports",
        "reports_count": "Reports",
        "reports": "Reports",
        "created_at": "Created",
        "updated_at": "Updated",
        "last_reported_at": "Last Reported",
        "last_seen_at": "Last Seen",
    }
    if raw_key in aliases:
        return aliases[raw_key]
    return str(raw_key).replace("_", " ").strip().title()


def _cell_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _normalise_rows(raw_rows, requested_system=None):
    """Convert API deposit objects to rows suitable for a Treeview.

    The API remains the source of truth. Unknown future scalar fields are kept
    automatically instead of being discarded, so the GUI is resilient to
    backend additions.
    """

    rows = []
    header_order = []

    preferred = (
        "id",
        "deposit_id",
        "system",
        "system_name",
        "star_system",
        "body",
        "body_name",
        "commodity",
        "material",
        "latitude",
        "lat",
        "longitude",
        "lon",
        "lng",
        "planet_radius",
        "body_radius",
        "radius",
        "report_count",
        "reports_count",
        "reports",
        "created_at",
        "updated_at",
        "last_reported_at",
        "last_seen_at",
    )

    raw_keys = []
    seen_raw = set()
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        for key in item.keys():
            if key not in seen_raw:
                seen_raw.add(key)
                raw_keys.append(key)

    ordered_raw = [key for key in preferred if key in seen_raw]
    ordered_raw.extend(key for key in raw_keys if key not in ordered_raw)

    # Collapse aliases that map to the same display name. Prefer the first
    # populated alias in ordered_raw for each row.
    display_groups = []
    group_index = {}
    for raw_key in ordered_raw:
        header = _display_header(raw_key)
        if header not in group_index:
            group_index[header] = len(display_groups)
            display_groups.append((header, [raw_key]))
        else:
            display_groups[group_index[header]][1].append(raw_key)

    headers = [header for header, _keys in display_groups]

    if not headers:
        headers = [
            "System",
            "Body",
            "Commodity",
            "Latitude",
            "Longitude",
            "Reports",
            "Updated",
        ]

    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        row = {}
        for header, keys in display_groups:
            value = ""
            for key in keys:
                candidate = item.get(key)
                if candidate not in (None, ""):
                    value = _cell_value(candidate)
                    break
            row[header] = value

        if "System" in headers and not row.get("System") and requested_system:
            row["System"] = requested_system

        rows.append(row)

    return headers, rows


def fetch_system_deposits(system, *, session=None, cancel_event=None):
    _check_cancel(cancel_event)

    system = str(system or "").strip()
    if not system:
        return [], []

    client = session or requests.Session()
    try:
        response = client.get(
            DEPOSITS_URL,
            params={"system": system},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise CommunityDepositsError(
            f"Community Deposits request failed for {system}: {exc}"
        ) from exc

    _check_cancel(cancel_event)

    if response.status_code != 200:
        text = response.text.strip()
        if len(text) > 300:
            text = text[:300] + "..."
        raise CommunityDepositsError(
            f"Community Deposits API returned HTTP {response.status_code} "
            f"for {system}: {text or 'no response body'}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CommunityDepositsError(
            f"Community Deposits API returned invalid JSON for {system}."
        ) from exc

    if not isinstance(payload, dict):
        raise CommunityDepositsError(
            f"Community Deposits API returned an unexpected response for {system}."
        )

    if payload.get("status") not in (None, "ok"):
        message = payload.get("error") or payload.get("message") or payload.get("status")
        raise CommunityDepositsError(
            f"Community Deposits API error for {system}: {message}"
        )

    deposits = payload.get("deposits", [])
    if deposits is None:
        deposits = []
    if not isinstance(deposits, list):
        raise CommunityDepositsError(
            f"Community Deposits API returned invalid deposits data for {system}."
        )

    return _normalise_rows(deposits, requested_system=system)


def fetch_deposits_for_systems(systems, *, cancel_event=None):
    """Fetch Community Deposits for each selected system."""

    all_rows = []
    all_headers = []
    seen_headers = set()

    with requests.Session() as session:
        for system in systems:
            _check_cancel(cancel_event)
            headers, rows = fetch_system_deposits(
                system,
                session=session,
                cancel_event=cancel_event,
            )

            for header in headers:
                if header not in seen_headers:
                    seen_headers.add(header)
                    all_headers.append(header)
            all_rows.extend(rows)

    if not all_headers:
        all_headers = [
            "System",
            "Body",
            "Commodity",
            "Latitude",
            "Longitude",
            "Reports",
            "Updated",
        ]

    # Rows fetched from different systems may expose slightly different API
    # fields. Ensure every row has every final column.
    for row in all_rows:
        for header in all_headers:
            row.setdefault(header, "")

    return all_headers, all_rows
