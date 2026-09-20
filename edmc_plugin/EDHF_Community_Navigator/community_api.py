from __future__ import annotations

from typing import Any

import requests


API_BASE = "https://ed-alliance-community-deposits.littlejacket99.workers.dev"
DEPOSITS_URL = f"{API_BASE}/v1/deposits"
BATCH_URL = f"{API_BASE}/v1/deposits/batch"
REQUEST_TIMEOUT = 20
MAX_BATCH_SIZE = 200
USER_AGENT = "Hotspots-Finder-Deposits-Companion/1.0.3"


class CommunityAPIError(RuntimeError):
    """Raised when the Community Deposits API cannot satisfy a request."""


def _response_json(response: requests.Response, *, context: str) -> dict[str, Any]:
    if response.status_code != 200:
        text = response.text.strip()
        if len(text) > 400:
            text = text[:400] + "..."
        raise CommunityAPIError(
            f"Community Deposits API returned HTTP {response.status_code} "
            f"for {context}: {text or 'no response body'}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CommunityAPIError(
            f"Community Deposits API returned invalid JSON for {context}."
        ) from exc

    if not isinstance(payload, dict):
        raise CommunityAPIError(
            f"Community Deposits API returned an unexpected response for {context}."
        )

    if payload.get("status") not in (None, "ok"):
        message = payload.get("error") or payload.get("message") or payload.get("status")
        raise CommunityAPIError(
            f"Community Deposits API error for {context}: {message}"
        )

    return payload


def fetch_system_deposits(system: str) -> list[dict[str, Any]]:
    system = str(system or "").strip()
    if not system:
        return []

    try:
        response = requests.get(
            DEPOSITS_URL,
            params={"system": system},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise CommunityAPIError(
            f"Community Deposits request failed for {system}: {exc}"
        ) from exc

    payload = _response_json(response, context=system)
    deposits = payload.get("deposits", [])
    if deposits is None:
        return []
    if not isinstance(deposits, list):
        raise CommunityAPIError(
            f"Community Deposits API returned invalid deposits data for {system}."
        )

    return [item for item in deposits if isinstance(item, dict)]


def send_deposit_batch(deposits: list[dict[str, Any]]) -> dict[str, Any]:
    if not deposits:
        return {"results": []}

    try:
        response = requests.post(
            BATCH_URL,
            json={"deposits": deposits},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise CommunityAPIError(
            f"Community Deposits batch upload failed: {exc}"
        ) from exc

    return _response_json(response, context="RhinoSpotter batch upload")


def chunks(items: list[dict[str, Any]], size: int = MAX_BATCH_SIZE):
    for start in range(0, len(items), size):
        yield items[start:start + size]
