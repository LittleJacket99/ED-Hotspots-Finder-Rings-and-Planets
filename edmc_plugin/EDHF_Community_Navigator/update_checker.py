from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any


LATEST_RELEASE_API = (
    "https://api.github.com/repos/"
    "LittleJacket99/ED-Hotspots-Finder-Rings-and-Planets/releases/latest"
)
LATEST_RELEASE_PAGE = (
    "https://github.com/LittleJacket99/"
    "ED-Hotspots-Finder-Rings-and-Planets/releases/latest"
)


def _version_tuple(value: Any) -> tuple[int, int, int] | None:
    text = str(value or "").strip()
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def check_for_update(current_version: str, timeout: float = 4.0) -> dict[str, Any]:
    """Check the shared Finder + Companion GitHub release channel."""

    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Hotspots-Finder-Deposits-Companion/{current_version}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)

        latest_version = str(payload.get("tag_name") or "").strip()
        current_key = _version_tuple(current_version)
        latest_key = _version_tuple(latest_version)

        if current_key is None or latest_key is None:
            raise ValueError("GitHub returned an unsupported version tag")

        return {
            "ok": True,
            "update_available": latest_key > current_key,
            "current_version": str(current_version),
            "latest_version": latest_version.lstrip("vV"),
            "release_url": str(
                payload.get("html_url") or LATEST_RELEASE_PAGE
            ),
            "release_name": str(
                payload.get("name") or latest_version
            ),
        }

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ) as exc:
        return {
            "ok": False,
            "update_available": False,
            "current_version": str(current_version),
            "latest_version": "",
            "release_url": LATEST_RELEASE_PAGE,
            "error": str(exc),
        }
