#!/usr/bin/env python3

"""GUI-friendly wrapper around the RhinoSpotter synchronization logic."""

import sqlite3
from contextlib import closing
from pathlib import Path

from rhinospotter_sync import (
    MAX_BATCH_SIZE,
    chunks,
    get_sync_state_entry,
    load_rhinospotter_records,
    record_fingerprint,
    record_state_key,
    resolve_source,
    save_sync_state_entry,
    send_batch,
)


class RhinoSpotterSyncError(RuntimeError):
    pass


def inspect_source(data_path=None):
    """Return the detected RhinoSpotter source and a lightweight summary."""

    source_type, source_path = resolve_source(data_path)

    if source_type == "rs_api":
        loaded = load_rhinospotter_records(data_path)
        return {
            "source_type": source_type,
            "source_path": str(source_path),
            "records_found": int(loaded["records_found"] or 0),
            "records_valid": int(loaded["records_valid"] or 0),
            "radius_inferred": int(loaded["radius_inferred"] or 0),
            "radius_missing": int(loaded["radius_missing"] or 0),
            "api_version": loaded.get("api_version", ""),
            "api_schema": loaded.get("api_schema"),
            "revision": loaded.get("revision"),
        }

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
    """Synchronize only new or changed RhinoSpotter bookmarks.

    Bookmarks are read locally, compared by stable identity and fingerprint,
    and only new/modified records are uploaded. RhinoSpotter revision() is
    retained as metadata but is not used as the sole skip condition because
    its aggregate value may remain unchanged after an edit to an arbitrary
    bookmark row. SQLite/JSON fallbacks use the same fingerprint filtering.
    """

    source_type, source_path = resolve_source(data_path)
    state = get_sync_state_entry(source_type, source_path)

    # RhinoSpotter 5.5.1 revision() can miss edits to arbitrary rows because
    # its current aggregate revision is not a complete content hash. Always
    # read the local bookmarks and let stable-id fingerprints decide what
    # needs uploading. This still avoids all Community Deposits/D1 work when
    # nothing changed.
    loaded = load_rhinospotter_records(data_path)
    deposits = loaded["deposits"]

    previous_fingerprints = state.get("fingerprints", {})
    if not isinstance(previous_fingerprints, dict):
        previous_fingerprints = {}

    current_fingerprints = {}
    records_to_send = []
    for deposit in deposits:
        key = record_state_key(deposit)
        fingerprint = record_fingerprint(deposit)
        current_fingerprints[key] = fingerprint
        if previous_fingerprints.get(key) != fingerprint:
            records_to_send.append(deposit)

    removed_local = len(
        set(previous_fingerprints)
        - set(current_fingerprints)
    )

    summary = {
        "source_type": loaded["source_type"],
        "source_path": str(loaded["source_path"]),
        "records_found": loaded["records_found"],
        "records_valid": loaded["records_valid"],
        "read_errors": loaded["read_errors"],
        "radius_inferred": loaded.get("radius_inferred", 0),
        "radius_missing": loaded.get("radius_missing", 0),
        "api_version": loaded.get("api_version", ""),
        "api_schema": loaded.get("api_schema"),
        "revision": loaded.get("revision"),
        "revision_unchanged": bool(
            state.get("complete")
            and state.get("revision") == loaded.get("revision")
        ),
        "records_sent": len(records_to_send),
        "local_unchanged": max(0, len(deposits) - len(records_to_send)),
        "removed_local": removed_local,
        "inserted": 0,
        "matched": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": loaded["read_errors"],
        "state_saved": False,
    }

    successful_keys = set()

    for batch in chunks(records_to_send, MAX_BATCH_SIZE):
        metadata_by_report = {
            str(record.get("report_id")): (
                record_state_key(record),
                record_fingerprint(record),
            )
            for record in batch
            if record.get("report_id")
        }

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
            elif action == "unchanged":
                summary["unchanged"] += 1

            report_id = str(item.get("report_id") or "")
            metadata_item = metadata_by_report.get(report_id)
            if metadata_item is not None:
                successful_keys.add(metadata_item[0])

    # Only mark the source revision complete after a clean, stable read and
    # successful server processing. If anything failed, retain successful
    # fingerprints but force a full comparison on the next Sync Bookmarks.
    complete = summary["errors"] == 0
    if source_type == "rs_api" and not loaded.get("revision_stable"):
        complete = False

    if summary["errors"] == 0:
        saved_fingerprints = current_fingerprints
    else:
        saved_fingerprints = dict(previous_fingerprints)
        for key in successful_keys:
            if key in current_fingerprints:
                saved_fingerprints[key] = current_fingerprints[key]

    state_entry = {
        "complete": complete,
        "revision": (
            loaded.get("revision")
            if complete and source_type == "rs_api"
            else None
        ),
        "records_found": loaded["records_found"],
        "records_valid": loaded["records_valid"],
        "radius_inferred": loaded.get("radius_inferred", 0),
        "radius_missing": loaded.get("radius_missing", 0),
        "fingerprints": saved_fingerprints,
    }

    try:
        save_sync_state_entry(
            source_type,
            source_path,
            state_entry,
        )
    except OSError as exc:
        summary["state_error"] = str(exc)
    else:
        summary["state_saved"] = True

    return summary


def sync_cards(cards_dir=None):
    """Backward-compatible name used by older GUI layers.

    Automatic discovery now prefers RhinoSpotter rs_api. Older SQLite and JSON
    sources remain available as compatibility fallbacks.
    """

    return sync_bookmarks(data_path=cards_dir)
