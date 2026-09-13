"""Validate local inputs before building the Windows release."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def validate():
    required = (
        "hotspots_finder_gui.py",
        "hotspots_engine.py",
        "HotspotsFinder.spec",
        "version_info.txt",
        "requirements.txt",
        "logo.png",
        "app.ico",
    )
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise ValueError("Missing build resources: " + ", ".join(missing))

    if not (ROOT / "logo.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("logo.png is not a PNG file")
    if not (ROOT / "app.ico").read_bytes().startswith(b"\x00\x00\x01\x00"):
        raise ValueError("app.ico is not a Windows icon")

    spec = (ROOT / "HotspotsFinder.spec").read_text(encoding="utf-8")
    for name in ("logo.png", "credentials.json", "app.ico", "version_info.txt"):
        if name not in spec:
            raise ValueError("Build specification does not reference " + name)

    credentials_path = ROOT / "credentials.json"
    if not credentials_path.is_file():
        raise ValueError(
            "credentials.json is missing. Put your Google OAuth Desktop app "
            "credentials next to build_windows.bat."
        )
    try:
        data = json.loads(credentials_path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("credentials.json is not valid JSON") from exc

    client = data.get("installed") if isinstance(data, dict) else None
    fields = ("client_id", "client_secret", "auth_uri", "token_uri")
    if not isinstance(client, dict) or any(
        not isinstance(client.get(key), str) or not client[key].strip()
        for key in fields
    ):
        raise ValueError(
            "credentials.json must contain a Google OAuth Desktop app "
            "client under the 'installed' key."
        )

    print("Build inputs valid: Desktop OAuth credentials and assets found.")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError) as exc:
        print("BUILD INPUT ERROR: " + str(exc), file=sys.stderr)
        sys.exit(1)
