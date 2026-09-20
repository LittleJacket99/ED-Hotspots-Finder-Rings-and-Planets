from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any


RELEASES_API = (
    "https://api.github.com/repos/"
    "LittleJacket99/ED-Hotspots-Finder-Rings-and-Planets/releases?per_page=30"
)
RELEASES_PAGE = (
    "https://github.com/LittleJacket99/"
    "ED-Hotspots-Finder-Rings-and-Planets/releases"
)
TAG_PREFIX = "companion-v"


def _version_tuple(value: Any) -> tuple[int, int, int] | None:
    text = str(value or "").strip()
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def check_for_update(current_version: str, timeout: float = 4.0) -> dict[str, Any]:
    """Return the latest public Companion release, ignoring Finder releases."""

    request = urllib.request.Request(
        RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Hotspots-Finder-Deposits-Companion/{current_version}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)

        if not isinstance(payload, list):
            raise ValueError("GitHub returned an unexpected releases response")

        latest_release = None
        latest_key = None

        for release in payload:
            if not isinstance(release, dict):
                continue
            if release.get("draft") or release.get("prerelease"):
                continue

            tag = str(release.get("tag_name") or "").strip()
            if not tag.casefold().startswith(TAG_PREFIX):
                continue

            version_text = tag[len(TAG_PREFIX):]
            version_key = _version_tuple(version_text)
            if version_key is None:
                continue

            if latest_key is None or version_key > latest_key:
                latest_key = version_key
                latest_release = release

        current_key = _version_tuple(current_version)
        if current_key is None:
            raise ValueError("Installed Companion version is unsupported")

        if latest_release is None or latest_key is None:
            return {
                "ok": True,
                "update_available": False,
                "current_version": str(current_version),
                "latest_version": "",
                "release_url": RELEASES_PAGE,
            }

        tag = str(latest_release.get("tag_name") or "").strip()
        latest_version = tag[len(TAG_PREFIX):]

        return {
            "ok": True,
            "update_available": latest_key > current_key,
            "current_version": str(current_version),
            "latest_version": latest_version,
            "release_tag": tag,
            "release_url": str(
                latest_release.get("html_url") or RELEASES_PAGE
            ),
            "release_name": str(
                latest_release.get("name") or tag
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
            "release_url": RELEASES_PAGE,
            "error": str(exc),
        }
