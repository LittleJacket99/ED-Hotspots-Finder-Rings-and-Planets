#!/usr/bin/env python3

"""GUI-friendly wrapper around the RhinoSpotter synchronization logic."""

import sqlite3
from contextlib import closing
from pathlib import Path

from rhinospotter_sync import (
    MAX_BATCH_SIZE,
    chunks,
    load_rhinospotter_records,
    resolve_source,
    send_batch,
)


class RhinoSpotterSyncError(RuntimeError):
    pass


def inspect_source(data_path=None):
    """Return the detected RhinoSpotter source and a lightweight record count."""

    source_type, source_path = resolve_source(data_path)

    if source_type == "sqlite":
        try:
            uri = Path(source_path).resolve().as_uri() + "?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=5.0)
            with closing(connection) as conn:
                records_found = conn.execute(
                    "SELECT COUNT(*) FROM bookmarks"
                ).fetchone()[0]
        except sqlite3.Error as exc:
            raise RhinoSpotterSyncError(
                f"Could not inspect RhinoSpotter database {source_path}: {exc}"
            ) from exc
    else:
        records_found = sum(1 for _ in Path(source_path).rglob("*.json"))

    return {
        "source_type": source_type,
        "source_path": str(source_path),
        "records_found": int(records_found or 0),
    }


def sync_bookmarks(data_path=None):
    """Synchronize RhinoSpotter bookmarks and return a compact summary.

    RhinoSpotter 4.2+ stores bookmarks in SQLite. Older JSON-card folders are
    still accepted as a fallback. Record normalization, stable report IDs and
    HTTP payload handling remain shared with the command-line sync module.
    """

    loaded = load_rhinospotter_records(data_path)
    deposits = loaded["deposits"]

    summary = {
        "source_type": loaded["source_type"],
        "source_path": str(loaded["source_path"]),
        "records_found": loaded["records_found"],
        "records_valid": loaded["records_valid"],
        "read_errors": loaded["read_errors"],
        "inserted": 0,
        "matched": 0,
        "updated": 0,
        "errors": loaded["read_errors"],
    }

    # Compatibility for the current v1.0.0 GUI summary. The presentation layer
    # will be updated separately to use records_found/source_type directly.
    summary["files_found"] = loaded["records_found"]

    if not deposits:
        return summary

    for batch in chunks(deposits, MAX_BATCH_SIZE):
        result = send_batch(batch)

        if not isinstance(result, dict):
            raise RhinoSpotterSyncError(
                "Community Deposits server returned an unexpected response."
            )

        results = result.get("results", [])
        if not isinstance(results, list):
            raise RhinoSpotterSyncError(
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


def sync_cards(cards_dir=None):
    """Backward-compatible name used by the current GUI.

    A path that still points to the historical ``cards`` directory will now
    automatically prefer the sibling SQLite database when RhinoSpotter 4.2+
    is installed.
    """

    return sync_bookmarks(data_path=cards_dir)
