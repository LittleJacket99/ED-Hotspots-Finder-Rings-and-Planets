import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


API_URL = (
    "https://ed-alliance-community-deposits."
    "littlejacket99.workers.dev/v1/deposits/batch"
)

USER_AGENT = "ED-Hotspots-Landables-Finder/1.0"

MAX_BATCH_SIZE = 200

CARDS_DIR = (
    Path(os.environ["LOCALAPPDATA"])
    / "RhinoSpotter"
    / "cards"
)


def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def make_report_id(record):
    """
    Crea un ID stabile per il bookmark.

    NON usiamo:
    - amount
    - density
    - updated_at
    - depleted_at

    perché possono cambiare quando RhinoSpotter
    aggiorna lo stesso bookmark.
    """

    identity = {
        "commander": clean_text(
            record.get("commander")
        ),
        "system": clean_text(
            record.get("system")
        ),
        "planet_name": clean_text(
            record.get("planet_name")
        ),
        "location_index": record.get(
            "location_index"
        ),
        "latitude": record.get(
            "latitude"
        ),
        "longitude": record.get(
            "longitude"
        ),
        "commodity": clean_text(
            record.get("commodity")
        ),
        "marked_at": clean_text(
            record.get("marked_at")
        ),
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

        "commander": clean_text(
            record.get("commander")
        ),

        "system": clean_text(
            record.get("system")
        ),

        "system_address": record.get(
            "system_address"
        ),

        "planet_name": clean_text(
            record.get("planet_name")
        ),

        "body_id": record.get(
            "body_id"
        ),

        "location_index": record.get(
            "location_index"
        ),

        "latitude": record.get(
            "latitude"
        ),

        "longitude": record.get(
            "longitude"
        ),

        "planet_radius": record.get(
            "planet_radius"
        ),

        "commodity": clean_text(
            record.get("commodity")
        ),

        "rigs": record.get(
            "rigs"
        ),

        "amount": clean_text(
            record.get("amount")
        ),

        "density": clean_text(
            record.get("density")
        ),

        "heading": record.get(
            "heading"
        ),

        "marked_at": clean_text(
            record.get("marked_at")
        ),

        "updated_at": clean_text(
            record.get("updated_at")
        ),

        "depleted_at": clean_text(
            record.get("depleted_at")
        ),
    }

    # Non inviamo campi opzionali null.
    return {
        key: value
        for key, value in payload.items()
        if value is not None
    }


def validate_record(record, path):
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
            f"{path.name}: campi mancanti: "
            + ", ".join(missing)
        )


def load_cards():
    if not CARDS_DIR.exists():
        raise FileNotFoundError(
            f"Cartella RhinoSpotter non trovata: "
            f"{CARDS_DIR}"
        )

    files = sorted(
        CARDS_DIR.rglob("*.json")
    )

    deposits = []

    for path in files:
        try:
            with path.open(
                "r",
                encoding="utf-8"
            ) as handle:
                record = json.load(handle)

            validate_record(
                record,
                path
            )

            normalized = normalize_record(
                record
            )

            deposits.append(
                normalized
            )

        except Exception as exc:
            print(
                f"[ERRORE] {path}: {exc}",
                file=sys.stderr
            )

    return files, deposits


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
            "Content-Type":
                "application/json",

            "User-Agent":
                USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            return json.loads(
                response
                .read()
                .decode("utf-8")
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
    for start in range(
        0,
        len(items),
        size
    ):
        yield items[
            start:start + size
        ]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sincronizza i bookmark RhinoSpotter "
            "con ED Alliance Community Deposits."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Legge e prepara i dati "
            "senza inviarli al server."
        ),
    )

    args = parser.parse_args()

    files, deposits = load_cards()

    print()
    print(
        f"Cartella: {CARDS_DIR}"
    )
    print(
        f"File JSON trovati: {len(files)}"
    )
    print(
        f"Record validi: {len(deposits)}"
    )
    print()

    for index, deposit in enumerate(
        deposits,
        start=1
    ):
        print(
            f"[{index}] "
            f"{deposit.get('system')} | "
            f"{deposit.get('planet_name')} | "
            f"{deposit.get('commodity')} | "
            f"CMDR {deposit.get('commander', '-')}"
        )

        print(
            f"    report_id: "
            f"{deposit['report_id']}"
        )

        if deposit.get(
            "updated_at"
        ):
            print(
                f"    updated_at: "
                f"{deposit['updated_at']}"
            )

        if deposit.get(
            "depleted_at"
        ):
            print(
                f"    depleted_at: "
                f"{deposit['depleted_at']}"
            )

    print()

    if args.dry_run:
        print(
            "DRY RUN: nessun dato inviato."
        )
        return

    if not deposits:
        print(
            "Nessun record da sincronizzare."
        )
        return

    inserted = 0
    matched = 0
    updated = 0
    errors = 0

    for batch in chunks(
        deposits,
        MAX_BATCH_SIZE
    ):
        result = send_batch(
            batch
        )

        for item in result.get(
            "results",
            []
        ):
            if not item.get("ok"):
                errors += 1
                print(
                    "[ERRORE SERVER]",
                    item
                )
                continue

            action = item.get(
                "action"
            )

            if action == "inserted":
                inserted += 1

            elif (
                action
                == "matched_existing_deposit"
            ):
                matched += 1

            elif action == "updated_report":
                updated += 1

    print()
    print("Sincronizzazione completata.")
    print(
        f"Nuovi depositi: {inserted}"
    )
    print(
        f"Report associati a depositi esistenti: "
        f"{matched}"
    )
    print(
        f"Report aggiornati: {updated}"
    )
    print(
        f"Errori: {errors}"
    )


if __name__ == "__main__":
    main()