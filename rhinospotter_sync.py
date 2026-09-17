import argparse
import hashlib
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path


API_URL = (
    "https://ed-alliance-community-deposits."
    "littlejacket99.workers.dev/v1/deposits/batch"
)

USER_AGENT = "ED-Hotspots-Finder-Rings-and-Planets/1.0.0"

MAX_BATCH_SIZE = 200

RHINOSPOTTER_ROOT = (
    Path(os.environ.get("LOCALAPPDATA") or Path.home())
    / "RhinoSpotter"
)

DATABASE_PATH = (
    RHINOSPOTTER_ROOT
    / "db"
    / "rhinospotter.db"
)

# RhinoSpotter 4.1 and older stored one JSON record per bookmark here.
# RhinoSpotter 4.2+ migrated those records into DATABASE_PATH.
CARDS_DIR = (
    RHINOSPOTTER_ROOT
    / "cards"
)


def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def make_report_id(record):
    """
    Create a stable ID for one RhinoSpotter bookmark.

    We intentionally do not use fields that can change when RhinoSpotter
    refreshes the same bookmark (amount, density, updated_at, depleted_at).
    """

    identity = {
        "commander": clean_text(record.get("commander")),
        "system": clean_text(record.get("system")),
        "planet_name": clean_text(record.get("planet_name")),
        "location_index": record.get("location_index"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "commodity": clean_text(record.get("commodity")),
        "marked_at": clean_text(record.get("marked_at")),
    }

    canonical = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    return f"rhino-{digest}"


def normalize_record(record):
    payload = {
        "report_id": make_report_id(record),
        "commander": clean_text(record.get("commander")),
        "system": clean_text(record.get("system")),
        "system_address": record.get("system_address"),
        "planet_name": clean_text(record.get("planet_name")),
        "body_id": record.get("body_id"),
        "location_index": record.get("location_index"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "planet_radius": record.get("planet_radius"),
        "commodity": clean_text(record.get("commodity")),
        "rigs": record.get("rigs"),
        "amount": clean_text(record.get("amount")),
        "density": clean_text(record.get("density")),
        "heading": record.get("heading"),
        "marked_at": clean_text(record.get("marked_at")),
        "updated_at": clean_text(record.get("updated_at")),
        "depleted_at": clean_text(record.get("depleted_at")),
    }

    # Do not send optional null fields.
    return {
        key: value
        for key, value in payload.items()
        if value is not None
    }


def _source_label(source):
    if isinstance(source, Path):
        return source.name
    return str(source)


def validate_record(record, source):
    if not isinstance(record, dict):
        raise ValueError(f"{_source_label(source)}: record is not a JSON object")

    required = [
        "system",
        "planet_name",
        "latitude",
        "longitude",
        "planet_radius",
        "commodity",
    ]

    missing = [
        field
        for field in required
        if record.get(field) is None
        or record.get(field) == ""
    ]

    if missing:
        raise ValueError(
            f"{_source_label(source)}: missing fields: "
            + ", ".join(missing)
        )


def _database_candidates(path):
    """Return likely RhinoSpotter database locations for a path."""

    path = Path(path).expanduser()
    candidates = []

    # A saved setting from the old integration often points directly to
    # ...\RhinoSpotter\cards. Prefer the sibling 4.2+ database when present.
    if path.name.casefold() == "cards":
        candidates.append(path.parent / "db" / "rhinospotter.db")

    if path.is_dir():
        candidates.extend(
            [
                path / "db" / "rhinospotter.db",
                path / "rhinospotter.db",
            ]
        )
    elif path.suffix.casefold() == ".db":
        candidates.append(path)

    # Keep order, drop duplicates.
    unique = []
    seen = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(str(candidate)))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_source(source=None):
    """Resolve a RhinoSpotter source to (kind, path).

    Current RhinoSpotter releases use SQLite. Legacy JSON cards remain
    supported as a fallback for older installs and migrated data folders.

    Accepted paths:
    - RhinoSpotter root folder
    - db folder
    - rhinospotter.db itself
    - legacy cards folder
    """

    path = Path(source).expanduser() if source else RHINOSPOTTER_ROOT

    for candidate in _database_candidates(path):
        if candidate.is_file():
            return "sqlite", candidate

    legacy_candidates = []
    if path.is_dir():
        legacy_candidates.append(path / "cards")
        legacy_candidates.append(path)
    elif path.name.casefold() == "cards" and path.is_dir():
        legacy_candidates.append(path)

    # When no explicit source is supplied, retain the old default fallback.
    if source is None:
        legacy_candidates.append(CARDS_DIR)

    seen = set()
    for candidate in legacy_candidates:
        key = os.path.normcase(os.path.abspath(str(candidate)))
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_dir():
            return "legacy_json", candidate

    expected = (
        f"SQLite database: {DATABASE_PATH}\n"
        f"Legacy cards folder: {CARDS_DIR}"
    )
    raise FileNotFoundError(
        "RhinoSpotter data source not found.\n\n"
        f"Checked from: {path}\n\n{expected}"
    )


def _load_json_cards(cards_dir):
    files = sorted(Path(cards_dir).rglob("*.json"))
    deposits = []
    errors = 0

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)

            validate_record(record, path)
            deposits.append(normalize_record(record))

        except Exception as exc:
            errors += 1
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)

    return files, deposits, errors


def load_cards(cards_dir=CARDS_DIR):
    """Legacy JSON-card loader kept for backwards compatibility."""

    cards_dir = Path(cards_dir).expanduser()
    if not cards_dir.exists():
        raise FileNotFoundError(
            f"RhinoSpotter cards folder not found: {cards_dir}"
        )

    files, deposits, _errors = _load_json_cards(cards_dir)
    return files, deposits


def _load_database(database_path):
    database_path = Path(database_path).expanduser()
    if not database_path.is_file():
        raise FileNotFoundError(
            f"RhinoSpotter database not found: {database_path}"
        )

    try:
        connection = sqlite3.connect(str(database_path), timeout=5.0)
        with closing(connection) as conn:
            # We only read RhinoSpotter's database. query_only also protects
            # against accidental writes if this module changes later.
            conn.execute("PRAGMA query_only = ON")
            rows = conn.execute(
                "SELECT id, data FROM bookmarks ORDER BY id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Could not read RhinoSpotter database {database_path}: {exc}"
        ) from exc

    deposits = []
    errors = 0

    for bookmark_id, raw_data in rows:
        label = f"{database_path.name}: bookmark #{bookmark_id}"
        try:
            record = json.loads(raw_data)
            validate_record(record, label)
            deposits.append(normalize_record(record))
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {label}: {exc}", file=sys.stderr)

    return rows, deposits, errors


def load_rhinospotter_records(source=None):
    """Load current SQLite bookmarks or legacy JSON cards.

    Returns metadata plus normalized Community Deposits payload records.
    """

    source_type, source_path = resolve_source(source)

    if source_type == "sqlite":
        rows, deposits, errors = _load_database(source_path)
        records_found = len(rows)
    else:
        files, deposits, errors = _load_json_cards(source_path)
        records_found = len(files)

    return {
        "source_type": source_type,
        "source_path": source_path,
        "records_found": records_found,
        "records_valid": len(deposits),
        "read_errors": errors,
        "deposits": deposits,
    }


def send_batch(deposits):
    payload = {
        "deposits": deposits
    }

    data = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"HTTP {exc.code}: {body}"
        ) from exc


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize RhinoSpotter bookmarks with "
            "ED Alliance Community Deposits."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and prepare records without sending them to the server.",
    )

    parser.add_argument(
        "--source",
        help=(
            "Optional RhinoSpotter root/db/cards path. "
            "By default the current SQLite database is detected automatically."
        ),
    )

    args = parser.parse_args()

    loaded = load_rhinospotter_records(args.source)
    deposits = loaded["deposits"]
    source_type = loaded["source_type"]
    source_path = loaded["source_path"]

    print()
    print(
        "Source type: "
        + ("SQLite database" if source_type == "sqlite" else "Legacy JSON cards")
    )
    print(f"Source: {source_path}")
    print(f"Bookmarks found: {loaded['records_found']}")
    print(f"Valid records: {loaded['records_valid']}")
    print(f"Read errors: {loaded['read_errors']}")
    print()

    for index, deposit in enumerate(deposits, start=1):
        print(
            f"[{index}] "
            f"{deposit.get('system')} | "
            f"{deposit.get('planet_name')} | "
            f"{deposit.get('commodity')} | "
            f"CMDR {deposit.get('commander', '-')}"
        )

        print(f"    report_id: {deposit['report_id']}")

        if deposit.get("updated_at"):
            print(f"    updated_at: {deposit['updated_at']}")

        if deposit.get("depleted_at"):
            print(f"    depleted_at: {deposit['depleted_at']}")

    print()

    if args.dry_run:
        print("DRY RUN: no data sent.")
        return

    if not deposits:
        print("No records to synchronize.")
        return

    inserted = 0
    matched = 0
    updated = 0
    errors = loaded["read_errors"]

    for batch in chunks(deposits, MAX_BATCH_SIZE):
        result = send_batch(batch)

        for item in result.get("results", []):
            if not item.get("ok"):
                errors += 1
                print("[SERVER ERROR]", item)
                continue

            action = item.get("action")

            if action == "inserted":
                inserted += 1
            elif action == "matched_existing_deposit":
                matched += 1
            elif action == "updated_report":
                updated += 1

    print()
    print("Synchronization completed.")
    print(f"New deposits: {inserted}")
    print(f"Reports matched to existing deposits: {matched}")
    print(f"Updated reports: {updated}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
