#!/usr/bin/env python3

"""Client helpers for the ED Alliance Community Deposits API."""

import json

import requests


API_BASE = "https://ed-alliance-community-deposits.littlejacket99.workers.dev"
DEPOSITS_URL = f"{API_BASE}/v1/deposits"
USER_AGENT = "ED-Hotspots-Finder-Rings-and-Planets/1.0.3"
REQUEST_TIMEOUT = 20

COMMUNITY_HEADERS = [
    "System",
    "Body",
    "Location",
    "Commodity",
    "Rigs",
    "Amount",
    "Density",
    "Latitude",
    "Longitude",
    "Reports",
    "Updated",
]


class CommunityDepositsError(RuntimeError):
    pass


def _check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        from finder_engine import ScanCancelled

        raise ScanCancelled("Scan cancelled by user.")


def _cell_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _first_value(item, keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return _cell_value(value)
    return default


def _normalise_rows(raw_rows, requested_system=None):
    """Return only user-facing Community Deposits columns."""

    rows = []

    for item in raw_rows:
        if not isinstance(item, dict):
            continue

        row = {
            "System": _first_value(
                item,
                ("system", "system_name", "star_system"),
                requested_system or "",
            ),
            "Body": _first_value(
                item,
                ("body", "body_name", "planet_name"),
            ),
            "Location": _first_value(
                item,
                ("location_index", "location"),
            ),
            "Commodity": _first_value(
                item,
                ("commodity", "material"),
            ),
            "Rigs": _first_value(item, ("rigs",)),
            "Amount": _first_value(item, ("amount",)),
            "Density": _first_value(item, ("density",)),
            "Latitude": _first_value(item, ("latitude", "lat")),
            "Longitude": _first_value(item, ("longitude", "lon", "lng")),
            "Reports": _first_value(
                item,
                ("report_count", "reports_count", "reports"),
            ),
            "Updated": _first_value(
                item,
                ("updated_at", "last_reported_at", "last_seen_at"),
            ),
        }
        rows.append(row)

    return list(COMMUNITY_HEADERS), rows


def _validate_payload(response, *, context):
    if response.status_code != 200:
        text = response.text.strip()
        if len(text) > 300:
            text = text[:300] + "..."
        raise CommunityDepositsError(
            f"Community Deposits API returned HTTP {response.status_code} "
            f"for {context}: {text or 'no response body'}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CommunityDepositsError(
            f"Community Deposits API returned invalid JSON for {context}."
        ) from exc

    if not isinstance(payload, dict):
        raise CommunityDepositsError(
            f"Community Deposits API returned an unexpected response for {context}."
        )

    if payload.get("status") not in (None, "ok"):
        message = payload.get("error") or payload.get("message") or payload.get("status")
        raise CommunityDepositsError(
            f"Community Deposits API error for {context}: {message}"
        )

    deposits = payload.get("deposits", [])
    if deposits is None:
        deposits = []
    if not isinstance(deposits, list):
        raise CommunityDepositsError(
            f"Community Deposits API returned invalid deposits data for {context}."
        )

    return deposits


def fetch_all_deposits(*, cancel_event=None):
    """Fetch every Community Deposit currently exposed by the API."""

    _check_cancel(cancel_event)

    try:
        response = requests.get(
            DEPOSITS_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise CommunityDepositsError(
            f"Community Deposits request failed: {exc}"
        ) from exc

    _check_cancel(cancel_event)
    deposits = _validate_payload(response, context="all deposits")
    return _normalise_rows(deposits)


def fetch_system_deposits(system, *, session=None, cancel_event=None):
    _check_cancel(cancel_event)

    system = str(system or "").strip()
    if not system:
        return list(COMMUNITY_HEADERS), []

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
    deposits = _validate_payload(response, context=system)
    return _normalise_rows(deposits, requested_system=system)


def fetch_deposits_for_systems(systems, *, cancel_event=None):
    """Fetch Community Deposits for each selected system."""

    all_rows = []

    with requests.Session() as session:
        for system in systems:
            _check_cancel(cancel_event)
            _headers, rows = fetch_system_deposits(
                system,
                session=session,
                cancel_event=cancel_event,
            )
            all_rows.extend(rows)

    return list(COMMUNITY_HEADERS), all_rows
