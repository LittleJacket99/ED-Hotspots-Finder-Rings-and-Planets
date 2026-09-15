#!/usr/bin/env python3

"""GUI-friendly wrapper around the already-tested RhinoSpotter sync logic."""

from rhinospotter_sync import (
    CARDS_DIR,
    MAX_BATCH_SIZE,
    chunks,
    load_cards,
    send_batch,
)


class RhinoSpotterSyncError(RuntimeError):
    pass


def sync_cards():
    """Synchronise RhinoSpotter bookmarks and return a compact result summary.

    The actual record normalisation, report_id generation and HTTP payload are
    intentionally reused from rhinospotter_sync.py so GUI uploads remain fully
    compatible with the previously tested command-line sync.
    """

    files, deposits = load_cards()

    summary = {
        "cards_dir": str(CARDS_DIR),
        "files_found": len(files),
        "records_valid": len(deposits),
        "inserted": 0,
        "matched": 0,
        "updated": 0,
        "errors": 0,
    }

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
