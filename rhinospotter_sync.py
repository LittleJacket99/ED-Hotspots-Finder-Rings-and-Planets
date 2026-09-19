import argparse
import hashlib
import importlib.util
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

USER_AGENT = "ED-Hotspots-Finder-Rings-and-Planets/1.0.2"

MAX_BATCH_SIZE = 200

LOCAL_APP_DATA = Path(
    os.environ.get("LOCALAPPDATA")
    or (Path.home() / "AppData" / "Local")
)

RHINOSPOTTER_ROOT = LOCAL_APP_DATA / "RhinoSpotter"

RHINOSPOTTER_PLUGIN_DIR = (
    LOCAL_APP_DATA
    / "EDMarketConnector"
    / "plugins"
    / "RhinoSpotter"
)

RS_API_PATH = RHINOSPOTTER_PLUGIN_DIR / "rs_api.py"

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


def _path_key(value):
    return os.path.normcase(os.path.abspath(str(Path(value).expanduser())))


def _is_default_data_path(path):
    return _path_key(path) == _path_key(RHINOSPOTTER_ROOT)


def _rs_api_candidates(source=None):
    """Return documented RhinoSpotter API locations to try, in priority order."""

    candidates = []
    if source is not None:
        path = Path(source).expanduser()
        if path.is_file() and path.name.casefold() == "rs_api.py":
            candidates.append(path)
        elif path.is_dir():
            candidates.append(path / "rs_api.py")

        # The Settings dialog historically passes the standard data root even
        # when Auto is selected. Treat that path as automatic discovery too.
        if _is_default_data_path(path):
            candidates.insert(0, RS_API_PATH)
    else:
        candidates.append(RS_API_PATH)

    unique = []
    seen = set()
    for candidate in candidates:
        key = _path_key(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _load_rs_api_module(api_path):
    """Load RhinoSpotter's documented external API without bundling it."""

    api_path = Path(api_path).expanduser()
    if not api_path.is_file():
        raise FileNotFoundError(f"RhinoSpotter API not found: {api_path}")

    plugin_dir = str(api_path.resolve().parent)
    added_path = plugin_dir not in sys.path
    if added_path:
        sys.path.insert(0, plugin_dir)

    try:
        spec = importlib.util.spec_from_file_location(
            "edhf_rhinospotter_rs_api",
            api_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load RhinoSpotter API: {api_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:
        raise RuntimeError(
            f"Could not import RhinoSpotter API {api_path}: {exc}"
        ) from exc
    finally:
        if added_path:
            try:
                sys.path.remove(plugin_dir)
            except ValueError:
                pass

    schema = getattr(module, "SCHEMA", None)
    if schema != 1:
        raise RuntimeError(
            "Unsupported RhinoSpotter API schema "
            f"{schema!r}. This version of ED Hotspots Finder supports SCHEMA 1."
        )
    return module


def _api_record(mark):
    """Map rs_api.bookmarks() outward keys to EDHF's stable internal names."""

    if not isinstance(mark, dict):
        return mark

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


def _body_key(record):
    system = clean_text(record.get("system"))
    body = clean_text(record.get("planet_name"))
    if not system or not body:
        return None
    return system.casefold(), body.casefold()


def _propagate_planet_radii(records):
    """Fill old missing radii from another bookmark on the same body.

    RhinoSpotter only began recording planet_radius in September 2026. A body's
    radius is stable, so one newer bookmark makes older bookmarks on that same
    (system, body) comparable without inventing a value.
    """

    known = {}
    for record in records:
        key = _body_key(record)
        radius = record.get("planet_radius") if isinstance(record, dict) else None
        if key is not None and radius not in (None, ""):
            known.setdefault(key, radius)

    inferred = 0
    missing = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("planet_radius") not in (None, ""):
            continue
        key = _body_key(record)
        radius = known.get(key) if key is not None else None
        if radius is not None:
            record["planet_radius"] = radius
            inferred += 1
        else:
            missing += 1
    return inferred, missing


def _prepare_records(items):
    """Validate raw records, propagate body radius where possible, normalize."""

    valid = []
    errors = 0
    for label, record in items:
        try:
            validate_record(record, label)
            valid.append(record)
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {label}: {exc}", file=sys.stderr)

    inferred, missing = _propagate_planet_radii(valid)
    deposits = [normalize_record(record) for record in valid]
    return deposits, errors, inferred, missing


def _load_rs_api(api_path):
    module = _load_rs_api_module(api_path)

    try:
        bookmarks = module.bookmarks()
    except Exception as exc:
        raise RuntimeError(f"RhinoSpotter API could not read bookmarks: {exc}") from exc

    if not isinstance(bookmarks, list):
        raise RuntimeError("RhinoSpotter API returned an unexpected bookmarks value.")

    items = []
    for index, mark in enumerate(bookmarks, start=1):
        bookmark_id = mark.get("id") if isinstance(mark, dict) else None
        label = f"rs_api bookmark #{bookmark_id or index}"
        items.append((label, _api_record(mark)))

    deposits, errors, inferred, missing = _prepare_records(items)

    try:
        api_version = str(module.version())
    except Exception:
        api_version = ""

    return {
        "records_found": len(bookmarks),
        "deposits": deposits,
        "read_errors": errors,
        "radius_inferred": inferred,
        "radius_missing": missing,
        "api_version": api_version,
        "api_schema": getattr(module, "SCHEMA", None),
    }


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
    """Resolve RhinoSpotter to its public API first, then legacy storage.

    RhinoSpotter 5.1+ exposes rs_api.py specifically so external applications do
    not depend on its private database schema. Direct SQLite/JSON access remains
    only as a compatibility fallback for older RhinoSpotter installations.

    Accepted explicit paths:
    - RhinoSpotter plugin folder containing rs_api.py
    - rs_api.py itself
    - historical RhinoSpotter data root/db/cards paths
    """

    for candidate in _rs_api_candidates(source):
        if candidate.is_file():
            return "rs_api", candidate

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

    if source is None:
        legacy_candidates.append(CARDS_DIR)

    seen = set()
    for candidate in legacy_candidates:
        key = _path_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_dir():
            return "legacy_json", candidate

    expected = (
        f"RhinoSpotter API: {RS_API_PATH}\n"
        f"SQLite fallback: {DATABASE_PATH}\n"
        f"Legacy cards folder: {CARDS_DIR}"
    )
    raise FileNotFoundError(
        "RhinoSpotter source not found.\n\n"
        f"Checked from: {path}\n\n{expected}"
    )

def _load_json_cards(cards_dir):
    files = sorted(Path(cards_dir).rglob("*.json"))
    items = []
    parse_errors = 0

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
            items.append((path, record))
        except Exception as exc:
            parse_errors += 1
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)

    deposits, errors, inferred, missing = _prepare_records(items)
    return files, deposits, parse_errors + errors, inferred, missing

def load_cards(cards_dir=CARDS_DIR):
    """Legacy JSON-card loader kept for backwards compatibility."""

    cards_dir = Path(cards_dir).expanduser()
    if not cards_dir.exists():
        raise FileNotFoundError(
            f"RhinoSpotter cards folder not found: {cards_dir}"
        )

    files, deposits, _errors, _inferred, _missing = _load_json_cards(cards_dir)
    return files, deposits


def _load_database(database_path):
    database_path = Path(database_path).expanduser()
    if not database_path.is_file():
        raise FileNotFoundError(
            f"RhinoSpotter database not found: {database_path}"
        )

    try:
        uri = database_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        with closing(connection) as conn:
            conn.execute("PRAGMA query_only = ON")
            rows = conn.execute(
                "SELECT id, data FROM bookmarks ORDER BY id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Could not read RhinoSpotter database {database_path}: {exc}"
        ) from exc

    items = []
    parse_errors = 0
    for bookmark_id, raw_data in rows:
        label = f"{database_path.name}: bookmark #{bookmark_id}"
        try:
            record = json.loads(raw_data)
        except Exception as exc:
            parse_errors += 1
            print(f"[ERROR] {label}: {exc}", file=sys.stderr)
            continue
        items.append((label, record))

    deposits, errors, inferred, missing = _prepare_records(items)
    return rows, deposits, parse_errors + errors, inferred, missing

def load_rhinospotter_records(source=None):
    """Load RhinoSpotter bookmarks through rs_api when available.

    Direct SQLite and legacy JSON readers are retained only for older installs.
    Missing planet radii are inherited from another bookmark on the same body
    when possible; otherwise the field remains absent/unknown rather than zero.
    """

    source_type, source_path = resolve_source(source)
    api_version = ""
    api_schema = None

    if source_type == "rs_api":
        loaded = _load_rs_api(source_path)
        deposits = loaded["deposits"]
        errors = loaded["read_errors"]
        records_found = loaded["records_found"]
        inferred = loaded["radius_inferred"]
        missing = loaded["radius_missing"]
        api_version = loaded["api_version"]
        api_schema = loaded["api_schema"]
    elif source_type == "sqlite":
        rows, deposits, errors, inferred, missing = _load_database(source_path)
        records_found = len(rows)
    else:
        files, deposits, errors, inferred, missing = _load_json_cards(source_path)
        records_found = len(files)

    return {
        "source_type": source_type,
        "source_path": source_path,
        "records_found": records_found,
        "records_valid": len(deposits),
        "read_errors": errors,
        "radius_inferred": inferred,
        "radius_missing": missing,
        "api_version": api_version,
        "api_schema": api_schema,
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
            "Optional RhinoSpotter plugin/API or legacy data path. "
            "By default rs_api is preferred, with SQLite/JSON fallback."
        ),
    )

    args = parser.parse_args()

    loaded = load_rhinospotter_records(args.source)
    deposits = loaded["deposits"]
    source_type = loaded["source_type"]
    source_path = loaded["source_path"]

    print()
    source_labels = {
        "rs_api": "RhinoSpotter API",
        "sqlite": "SQLite database (legacy fallback)",
        "legacy_json": "Legacy JSON cards",
    }
    print("Source type: " + source_labels.get(source_type, source_type))
    print(f"Source: {source_path}")
    if source_type == "rs_api":
        version = loaded.get("api_version") or "unknown"
        schema = loaded.get("api_schema")
        print(f"RhinoSpotter version: {version}")
        print(f"API schema: {schema}")
    print(f"Bookmarks found: {loaded['records_found']}")
    print(f"Valid records: {loaded['records_valid']}")
    print(f"Planet radii inferred from same body: {loaded['radius_inferred']}")
    print(f"Planet radii still unknown: {loaded['radius_missing']}")
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
