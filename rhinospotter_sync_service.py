#!/usr/bin/env python3

"""GUI-friendly wrapper around the already-tested RhinoSpotter sync logic."""

import json
import sys
from pathlib import Path

from rhinospotter_sync import (
    CARDS_DIR,
    MAX_BATCH_SIZE,
    chunks,
    normalize_record,
    send_batch,
    validate_record,
)


class RhinoSpotterSyncError(RuntimeError):
    pass


def _load_cards(cards_dir=None):
    """Load RhinoSpotter cards from the configured folder or default folder."""

    root = Path(cards_dir).expanduser() if cards_dir else CARDS_DIR
    if not root.exists():
        raise FileNotFoundError(f"RhinoSpotter folder not found: {root}")

    files = sorted(root.rglob("*.json"))
    deposits = []

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
            validate_record(record, path)
            deposits.append(normalize_record(record))
        except Exception as exc:
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)

    return root, files, deposits


def sync_cards(cards_dir=None):
    """Synchronise RhinoSpotter bookmarks and return a compact result summary.

    The actual record normalisation, report_id generation and HTTP payload are
    intentionally reused from rhinospotter_sync.py so GUI uploads remain fully
    compatible with the previously tested command-line sync.
    """

    root, files, deposits = _load_cards(cards_dir)

    summary = {
        "cards_dir": str(root),
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
