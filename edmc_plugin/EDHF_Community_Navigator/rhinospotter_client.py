from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from EDHF_Community_Navigator.community_api import chunks, send_deposit_batch


SUPPORTED_SCHEMA = 1


class RhinoSpotterError(RuntimeError):
    """Raised when RhinoSpotter cannot be read or synchronized."""


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def resolve_rs_api(plugin_dir: str | Path) -> Path:
    plugin_dir = Path(plugin_dir).resolve()
    path = plugin_dir.parent / "RhinoSpotter" / "rs_api.py"
    if not path.is_file():
        raise RhinoSpotterError(
            "RhinoSpotter rs_api.py was not found. "
            "Install/update RhinoSpotter in EDMarketConnector and restart EDMC."
        )
    return path


def _load_rs_api(path: Path) -> ModuleType:
    plugin_path = str(path.parent)
    added_path = plugin_path not in sys.path
    if added_path:
        sys.path.insert(0, plugin_path)

    try:
        spec = importlib.util.spec_from_file_location(
            "edhf_community_navigator_rs_api",
            path,
        )
        if spec is None or spec.loader is None:
            raise RhinoSpotterError(f"Could not load RhinoSpotter API: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except RhinoSpotterError:
        raise
    except Exception as exc:
        raise RhinoSpotterError(
            f"Could not import RhinoSpotter API {path}: {exc}"
        ) from exc
    finally:
        if added_path:
            try:
                sys.path.remove(plugin_path)
            except ValueError:
                pass

    schema = getattr(module, "SCHEMA", None)
    if schema != SUPPORTED_SCHEMA:
        raise RhinoSpotterError(
            f"Unsupported RhinoSpotter API schema {schema!r}; "
            f"expected schema {SUPPORTED_SCHEMA}."
        )

    return module


def _report_id(record: dict[str, Any]) -> str:
    identity = {
        "commander": _clean_text(record.get("commander")),
        "system": _clean_text(record.get("system")),
        "planet_name": _clean_text(record.get("planet_name")),
        "location_index": record.get("location_index"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "commodity": _clean_text(record.get("commodity")),
        "marked_at": _clean_text(record.get("marked_at")),
    }

    canonical = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"rhino-{digest}"


def _api_record(mark: dict[str, Any]) -> dict[str, Any]:
    return {
        "commander": mark.get("commander"),
        "system": mark.get("system"),
        "planet_name": mark.get("body"),
        "location_index": mark.get("location"),
        "latitude": mark.get("latitude"),
        "longitude": mark.get("longitude"),
        "planet_radius": mark.get("planet_radius"),
        "commodity": mark.get("material"),
        "rigs": mark.get("rigs"),
        "amount": mark.get("amount"),
        "density": mark.get("density"),
        "heading": mark.get("heading"),
        "marked_at": mark.get("marked_at"),
        "depleted_at": mark.get("depleted_at"),
    }


def _body_key(record: dict[str, Any]) -> tuple[str, str] | None:
    system = _clean_text(record.get("system"))
    body = _clean_text(record.get("planet_name"))
    if not system or not body:
        return None
    return system.casefold(), body.casefold()


def _propagate_planet_radii(records: list[dict[str, Any]]) -> tuple[int, int]:
    known: dict[tuple[str, str], Any] = {}
    for record in records:
        key = _body_key(record)
        radius = record.get("planet_radius")
        if key is not None and radius not in (None, ""):
            known.setdefault(key, radius)

    inferred = 0
    missing = 0
    for record in records:
        if record.get("planet_radius") not in (None, ""):
            continue
        key = _body_key(record)
        radius = known.get(key) if key is not None else None
        if radius is None:
            missing += 1
        else:
            record["planet_radius"] = radius
            inferred += 1

    return inferred, missing


def _normalise_record(record: dict[str, Any]) -> dict[str, Any]:
    required = ("system", "planet_name", "latitude", "longitude", "commodity")
    missing = [
        key for key in required
        if record.get(key) is None or record.get(key) == ""
    ]
    if missing:
        raise RhinoSpotterError(
            "RhinoSpotter bookmark is missing required fields: "
            + ", ".join(missing)
        )

    payload = {
        "report_id": _report_id(record),
        "commander": _clean_text(record.get("commander")),
        "system": _clean_text(record.get("system")),
        "planet_name": _clean_text(record.get("planet_name")),
        "location_index": record.get("location_index"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "planet_radius": record.get("planet_radius"),
        "commodity": _clean_text(record.get("commodity")),
        "rigs": record.get("rigs"),
        "amount": _clean_text(record.get("amount")),
        "density": _clean_text(record.get("density")),
        "heading": record.get("heading"),
        "marked_at": _clean_text(record.get("marked_at")),
        "depleted_at": _clean_text(record.get("depleted_at")),
    }

    return {key: value for key, value in payload.items() if value is not None}


def load_bookmarks(plugin_dir: str | Path) -> dict[str, Any]:
    path = resolve_rs_api(plugin_dir)
    module = _load_rs_api(path)

    try:
        bookmarks = module.bookmarks()
    except Exception as exc:
        raise RhinoSpotterError(
            f"RhinoSpotter API could not read bookmarks: {exc}"
        ) from exc

    if not isinstance(bookmarks, list):
        raise RhinoSpotterError(
            "RhinoSpotter API returned an unexpected bookmarks value."
        )

    raw_records = [
        _api_record(mark)
        for mark in bookmarks
        if isinstance(mark, dict)
    ]
    inferred, missing_radius = _propagate_planet_radii(raw_records)

    records: list[dict[str, Any]] = []
    errors = 0
    for record in raw_records:
        try:
            records.append(_normalise_record(record))
        except RhinoSpotterError:
            errors += 1

    try:
        api_version = str(module.version())
    except Exception:
        api_version = ""

    return {
        "records_found": len(bookmarks),
        "records_valid": len(records),
        "read_errors": errors,
        "radius_inferred": inferred,
        "radius_missing": missing_radius,
        "api_version": api_version,
        "api_schema": getattr(module, "SCHEMA", None),
        "records": records,
    }


def sync_bookmarks(plugin_dir: str | Path) -> dict[str, Any]:
    loaded = load_bookmarks(plugin_dir)
    records = loaded["records"]

    summary = {
        "records_found": loaded["records_found"],
        "records_valid": loaded["records_valid"],
        "read_errors": loaded["read_errors"],
        "radius_inferred": loaded["radius_inferred"],
        "radius_missing": loaded["radius_missing"],
        "api_version": loaded["api_version"],
        "api_schema": loaded["api_schema"],
        "inserted": 0,
        "matched": 0,
        "updated": 0,
        "errors": loaded["read_errors"],
    }

    for batch in chunks(records):
        result = send_deposit_batch(batch)
        results = result.get("results", [])
        if not isinstance(results, list):
            raise RhinoSpotterError(
                "Community Deposits server returned invalid batch results."
            )

        for item in results:
            if not isinstance(item, dict) or not item.get("ok"):
                summary["errors"] += 1
                continue

            action = item.get("action")
            if action == "inserted":
                summary["inserted"] += 1
            elif action == "matched_existing_deposit":
                summary["matched"] += 1
            elif action == "updated_report":
                summary["updated"] += 1

    return summary
