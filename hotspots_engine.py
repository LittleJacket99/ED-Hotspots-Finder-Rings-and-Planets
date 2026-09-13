#!/usr/bin/env python3

import csv
import json
import base64
import gzip
import os
import re
import sys
import time
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SPANSH_URL = "https://spansh.co.uk/api/bodies/search"
SPANSH_SYSTEMS_URL = "https://spansh.co.uk/api/systems/search"
USER_AGENT = "Hotspots-Finder-Local/0.3"

BATCH_SIZE = 25
PAGE_SIZE = 500
DELAY = 1.6
RETRIES = 3


APP_NAME = "HotspotsFinder"
SHEET_NAME = "Hotspots Finder"
REFERENCE_SHEET_NAMES = (
    "Minerals Table",
    "Volcanism Table",
)
STYLE_SHEET_NAME = "_HF_STYLE"
MASTER_TEMPLATE_SPREADSHEET_ID = "1zxeZLf6Mo1g_ls4J4tWGx8OXPGfjmA9BWPgD8Cc0PFU"

POWER_LIST = [
    "Aisling Duval",
    "Archon Delaine",
    "Arissa Lavigny-Duval",
    "Denton Patreus",
    "Edmund Mahon",
    "Felicia Winters",
    "Jerome Archer",
    "Li Yong-Rui",
    "Nakato Kaine",
    "Pranav Antal",
    "Yuri Grom",
    "Zemina Torval",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

# ---------- COLORS ----------
DARK_BG = {"red": 67/255, "green": 67/255, "blue": 67/255}
DARK_HEADER = {"red": 38/255, "green": 38/255, "blue": 38/255}
INPUT_BG = {"red": 89/255, "green": 89/255, "blue": 89/255}
GRID = {"red": 85/255, "green": 85/255, "blue": 85/255}
LIGHT = {"red": 217/255, "green": 217/255, "blue": 217/255}
WHITE = {"red": 1, "green": 1, "blue": 1}
ORANGE = {"red": 1, "green": 165/255, "blue": 0}
GREEN = {"red": 90/255, "green": 205/255, "blue": 87/255}
RED = {"red": 1, "green": 42/255, "blue": 42/255}


def app_data_dir():
    root = os.environ.get("APPDATA")
    if root:
        path = Path(root) / APP_NAME
    else:
        path = Path.home() / f".{APP_NAME.lower()}"

    path.mkdir(parents=True, exist_ok=True)
    return path


APP_DIR = app_data_dir()
TOKEN_PATH = APP_DIR / "token.json"
CONFIG_PATH = APP_DIR / "config.json"


def resource_path(filename):
    """Return a bundled resource path in both script and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_dir = Path(__file__).resolve().parent
    return base_dir / filename


CREDENTIALS_PATH = resource_path("credentials.json")


def extract_spreadsheet_id(value):
    value = str(value).strip()

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    if match:
        return match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", value):
        return value

    raise ValueError("Invalid Google Sheet link or ID.")


def load_config():
    if not CONFIG_PATH.exists():
        return {}

    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(config):
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8"
    )


def get_credentials():
    creds = None

    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(TOKEN_PATH),
                SCOPES
            )
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                "\ncredentials.json is missing.\n"
                "For this prototype, a Google OAuth client of type "
                "'Desktop app' is required in the same folder as the script.\n"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            SCOPES
        )

        creds = flow.run_local_server(
            port=0,
            open_browser=True,
            authorization_prompt_message=(
                "\nYour browser will open to authorize Hotspots Finder.\n"
            ),
            success_message=(
                "Authorization completed. You can close this window."
            )
        )

        TOKEN_PATH.write_text(
            creds.to_json(),
            encoding="utf-8"
        )

    return creds


def get_spreadsheet_id():
    config = load_config()

    current = config.get("spreadsheet_id")
    if current:
        return current

    print()
    print("Paste the Google Sheet link:")
    value = input("> ").strip()

    spreadsheet_id = extract_spreadsheet_id(value)

    config["spreadsheet_id"] = spreadsheet_id
    save_config(config)

    return spreadsheet_id


def get_sheet_info(service, spreadsheet_id):
    metadata = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="properties.title,sheets.properties"
        )
        .execute()
    )

    title = metadata.get("properties", {}).get("title", "")
    sheets = metadata.get("sheets", [])

    return title, sheets


def get_master_sheet_id(
    service,
    sheet_title,
):
    """
    Resolve a tab in the official master spreadsheet by title instead
    of hard-coding its numeric sheetId.
    """
    _, sheets = get_sheet_info(
        service,
        MASTER_TEMPLATE_SPREADSHEET_ID,
    )

    for item in sheets:
        props = item.get(
            "properties",
            {},
        )

        if props.get("title") == sheet_title:
            return props["sheetId"]

    raise RuntimeError(
        f'The master template does not contain the "{sheet_title}" sheet.'
    )


def get_master_hotspots_sheet_id(
    service,
):
    """Backward-compatible resolver for the main app tab."""
    return get_master_sheet_id(
        service,
        SHEET_NAME,
    )


def copy_official_sheet(
    service,
    destination_spreadsheet_id,
    sheet_title,
):
    """
    Copy one official tab from the master spreadsheet into the user's
    spreadsheet and restore its exact source title.

    sheets.copyTo preserves native Google Sheets formatting, validation,
    dropdown option colours and other sheet-level properties.
    """
    source_sheet_id = get_master_sheet_id(
        service,
        sheet_title,
    )

    copied_props = (
        service
        .spreadsheets()
        .sheets()
        .copyTo(
            spreadsheetId=MASTER_TEMPLATE_SPREADSHEET_ID,
            sheetId=source_sheet_id,
            body={
                "destinationSpreadsheetId":
                    destination_spreadsheet_id
            },
        )
        .execute()
    )

    copied_sheet_id = copied_props["sheetId"]

    # copyTo chooses its own destination title (often "Copy of ...").
    # Rename by sheetId so localization does not matter.
    (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=destination_spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId":
                                    copied_sheet_id,
                                "title":
                                    sheet_title,
                            },
                            "fields":
                                "title",
                        }
                    }
                ]
            },
        )
        .execute()
    )

    return copied_sheet_id


def copy_official_hotspots_sheet(
    service,
    destination_spreadsheet_id,
):
    """Copy the official Hotspots Finder tab from the master."""
    return copy_official_sheet(
        service,
        destination_spreadsheet_id,
        SHEET_NAME,
    )


def ensure_reference_sheets(
    service,
    destination_spreadsheet_id,
):
    """
    Ensure the read-only-by-convention reference tabs exist in the
    connected spreadsheet. Existing tabs are never replaced or modified.

    Missing tabs are copied directly from the official master template.
    A failure to copy a reference tab is logged but does not block the
    main Hotspots Finder functionality.
    """
    _, sheets = get_sheet_info(
        service,
        destination_spreadsheet_id,
    )

    existing_titles = {
        item.get("properties", {}).get("title")
        for item in sheets
    }

    copied = []

    for sheet_title in REFERENCE_SHEET_NAMES:
        if sheet_title in existing_titles:
            print(f'{sheet_title} already present: no changes made.')
            continue

        print(
            f'{sheet_title} not found: '
            'copying it from the official template...'
        )

        try:
            copy_official_sheet(
                service,
                destination_spreadsheet_id,
                sheet_title,
            )
            copied.append(sheet_title)
            existing_titles.add(sheet_title)
            print(
                f'{sheet_title} copied from the master template.'
            )
        except Exception as exc:
            print(
                f'WARNING: could not copy {sheet_title}: {exc}'
            )

    return copied


def get_or_create_hotspots_sheet(
    service,
    spreadsheet_id,
):
    """
    Return:
        spreadsheet_title,
        hotspots_sheet_id,
        copied_from_master

    Existing Hotspots Finder tabs are never replaced.

    If the tab does not exist:
      1. try to copy the official master tab with sheets.copyTo;
      2. fall back to the legacy local sheet creation if copying fails.
    """
    title, sheets = get_sheet_info(
        service,
        spreadsheet_id,
    )

    for item in sheets:
        props = item.get(
            "properties",
            {},
        )

        if props.get("title") == SHEET_NAME:
            return (
                title,
                props["sheetId"],
                False,
            )

    print(
        "Hotspots Finder not found: "
        "copying it from the official template..."
    )

    try:
        copied_sheet_id = copy_official_hotspots_sheet(
            service,
            spreadsheet_id,
        )

        print(
            "Official sheet copied from the master template."
        )

        return (
            title,
            copied_sheet_id,
            True,
        )

    except Exception as exc:
        print(
            "Copy from the master template failed; "
            "using the local fallback setup."
        )
        print(
            f"copyTo details: {exc}"
        )

    response = (
        service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title":
                                    SHEET_NAME,
                                "gridProperties": {
                                    "rowCount":
                                        200,
                                    "columnCount":
                                        21,
                                },
                            }
                        }
                    }
                ]
            },
        )
        .execute()
    )

    props = (
        response["replies"][0]
        ["addSheet"]["properties"]
    )

    return (
        title,
        props["sheetId"],
        False,
    )


def get_value(service, spreadsheet_id, a1):
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=a1
        )
        .execute()
    )

    values = result.get("values", [])
    if not values or not values[0]:
        return ""
    return values[0][0]


def write_values(service, spreadsheet_id, range_name, values):
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": values}
        )
        .execute()
    )


def initialize_sheet(service, spreadsheet_id, sheet_id):
    print("Configuring the sheet automatically...")

    # Clear contents/formatting first, but only on this dedicated sheet.
    requests = [
        {
            "updateCells": {
                "range": {
                    "sheetId": sheet_id
                },
                "fields": "*"
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1,
                        "frozenColumnCount": 4,
                        "hideGridlines": True
                    }
                },
                "fields": (
                    "gridProperties.frozenRowCount,"
                    "gridProperties.frozenColumnCount,"
                    "gridProperties.hideGridlines"
                )
            }
        }
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    ).execute()

    # ----- Values -----
    labels = [
        ["Hotspots"],              # 1
        ["Icy"],                   # 2
        ["Metallic"],              # 3
        ["Metal Rich"],            # 4
        ["Rocky"],                 # 5
        ["Platinum"],              # 6
        ["Bromellite"],            # 7
        ["Monazite"],              # 8
        ["Only pristine"],         # 9
        [""],                      # 10
        ["Planets"],               # 11
        ["Only landables"],        # 12
        ["Icy"],                   # 13
        ["Metal Rich"],            # 14
        ["High Metal Content"],    # 15
        ["Rocky"],                 # 16
        ["Rocky Ice"],             # 17
        [""],                      # 18
        ["Faction name"],          # 19
        ["Power"],                 # 20
        ["Unoccupied"],            # 21
        ["Exploited"],             # 22
        ["Fortified"],             # 23
        ["Stronghold"],            # 24
        [""],                      # 25
        ["Only positive results"], # 26
        [""],                      # 27
        ["Status"],                # 28
    ]

    write_values(
        service,
        spreadsheet_id,
        f"'{SHEET_NAME}'!A1:A27",
        labels
    )

    write_values(
        service,
        spreadsheet_id,
        f"'{SHEET_NAME}'!C1:D2",
        [
            ["Systems", "Total: 0"],
            ["", "Notes Here"],
        ]
    )

    # Checkbox values
    for rng, values in [
        ("B1:B9", [[True]] + [[False] for _ in range(8)]),
        ("B11:B17", [[False] for _ in range(7)]),
        ("B21:B24", [[False] for _ in range(4)]),
        ("B26", [[False]]),
    ]:
        write_values(
            service,
            spreadsheet_id,
            f"'{SHEET_NAME}'!{rng}",
            values
        )

    # ----- Formatting / validations -----
    req = []

    # Whole sheet dark background / white Arial 11
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 200,
                "startColumnIndex": 0,
                "endColumnIndex": 21
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BG,
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "fontFamily": "Arial",
                        "fontSize": 11
                    },
                    "horizontalAlignment": "LEFT",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.textFormat,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.verticalAlignment"
            )
        }
    })

    # Uniform row height across the whole initial sheet.
    # Filters and result rows use the same size.
    req.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 200
            },
            "properties": {
                "pixelSize": 17
            },
            "fields": "pixelSize"
        }
    })

    # Column widths A:U.
    # Result columns are auto-resized after each run.
    widths = {
        0: 165,  # A
        1: 170,  # B
        2: 225,  # C systems
        3: 170,  # D notes
        4: 190,  # E
        5: 150,  # F
        6: 180,  # G
        7: 180,  # H
        8: 130,  # I
        9: 130,  # J
        10: 110, # K
        11: 160, # L
        12: 110, # M
        13: 28,  # N separator
        14: 190, # O
        15: 150, # P
        16: 180, # Q
        17: 150, # R
        18: 110, # S
        19: 170, # T - Volcanism
        20: 130, # U - LS Distance
    }

    for col, width in widths.items():
        req.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": col,
                    "endIndex": col + 1
                },
                "properties": {
                    "pixelSize": width
                },
                "fields": "pixelSize"
            }
        })

    # Section headers A:B
    section_rows = [0, 10, 18, 19, 27]  # 1,11,19,20,28
    for row in section_rows:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": DARK_HEADER,
                        "textFormat": {
                            "foregroundColor": WHITE,
                            "bold": True,
                            "fontFamily": "Arial",
                            "fontSize": 11
                        }
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.textFormat"
                )
            }
        })

    # Accent colors on labels
    for row, color in [
        (0, ORANGE),   # Hotspots
        (10, ORANGE),  # Planets
        (18, ORANGE),  # Faction
        (19, ORANGE),  # Power
        (27, ORANGE),  # Status
    ]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "foregroundColor": color,
                            "bold": True
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat"
            }
        })

    # Systems / Total headers C1:D1
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 2,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_HEADER,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "bold": True
                    }
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.textFormat"
            )
        }
    })

    # D1 total counter in white
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "bold": True
                    }
                }
            },
            "fields": "userEnteredFormat.textFormat"
        }
    })

    # Notes column D2:D
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 200,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BG,
                    "horizontalAlignment": "LEFT",
                    "wrapStrategy": "WRAP",
                    "textFormat": {
                        "foregroundColor": LIGHT,
                        "fontFamily": "Arial",
                        "fontSize": 11
                    }
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.wrapStrategy,"
                "userEnteredFormat.textFormat"
            )
        }
    })

    # Faction / Power input fields B19, B20
    for row in [18, 19]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": INPUT_BG,
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "foregroundColor": WHITE,
                            "bold": True
                        }
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.horizontalAlignment,"
                    "userEnteredFormat.textFormat"
                )
            }
        })

    # Power dropdown B20.
    req.append({
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 19,
                "endRowIndex": 20,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": power}
                        for power in POWER_LIST
                    ],
                },
                "strict": True,
                "showCustomUi": True,
            },
        }
    })

    # Checkbox validations
    checkbox_ranges = [
        (0, 9),    # B1:B9
        (10, 17),  # B11:B17
        (20, 24),  # B21:B24
        (25, 26),  # B26 Only positive results
    ]

    for start_row, end_row in checkbox_ranges:
        req.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2
                },
                "rule": {
                    "condition": {
                        "type": "BOOLEAN"
                    },
                    "strict": True,
                    "showCustomUi": True
                }
            }
        })

        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        })

    # Borders around filter blocks.
    border_style = {
        "style": "SOLID",
        "color": LIGHT
    }

    blocks = [
        (1, 5, False),   # A2:B5
        (5, 8, True),    # A6:B8
        (8, 9, True),    # A9:B9
        (11, 17, True),  # A12:B17
        (20, 24, True),  # A21:B24
        (25, 26, True),  # A26:B26
    ]

    for start_row, end_row, top in blocks:
        borders = {
            "left": border_style,
            "right": border_style,
            "bottom": border_style
        }

        if top:
            borders["top"] = border_style

        req.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2
                },
                **borders
            }
        })

    # Explicitly no border around A1:B1
    no_border = {"style": "NONE"}

    req.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": 2
            },
            "top": no_border,
            "bottom": no_border,
            "left": no_border,
            "right": no_border,
            "innerVertical": no_border
        }
    })

    # Results grid E:U, subtle.
    subtle = {
        "style": "SOLID",
        "color": GRID
    }

    req.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 200,
                "startColumnIndex": 4,
                "endColumnIndex": 21
            },
            "top": subtle,
            "bottom": subtle,
            "left": subtle,
            "right": subtle,
            "innerHorizontal": subtle,
            "innerVertical": subtle
        }
    })

    # N separator borders (both sides visible)
    req.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 200,
                "startColumnIndex": 13,
                "endColumnIndex": 14
            },
            "left": {
                "style": "SOLID_THICK",
                "color": LIGHT
            },
            "right": {
                "style": "SOLID_THICK",
                "color": LIGHT
            }
        }
    })

    # Status B28 base styling
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 27,
                "endRowIndex": 28,
                "startColumnIndex": 1,
                "endColumnIndex": 2
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BG,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "bold": True
                    }
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.textFormat"
            )
        }
    })

    # Conditional formatting for status B27
    for index, value, bg, fg in [
        (0, "RUNNING", ORANGE, DARK_HEADER),
        (1, "COMPLETED", GREEN, DARK_HEADER),
        (2, "ERROR", RED, WHITE),
    ]:
        req.append({
            "addConditionalFormatRule": {
                "index": index,
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 27,
                        "endRowIndex": 28,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [
                                {"userEnteredValue": value}
                            ]
                        },
                        "format": {
                            "backgroundColor": bg,
                            "textFormat": {
                                "foregroundColor": fg,
                                "bold": True
                            }
                        }
                    }
                }
            }
        })

    # Final font sizing:
    # whole sheet = 10 pt
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 200,
                "startColumnIndex": 0,
                "endColumnIndex": 21
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "fontSize": 10
                    }
                }
            },
            "fields": "userEnteredFormat.textFormat.fontSize"
        }
    })

    # Checkbox/input column B, rows 1:26 = 8 pt
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 26,
                "startColumnIndex": 1,
                "endColumnIndex": 2
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "fontSize": 8
                    }
                }
            },
            "fields": "userEnteredFormat.textFormat.fontSize"
        }
    })

    # Status result columns: body font size 8.
    # Headers F1 and P1 keep the normal 10 pt size.
    for status_col in [5, 15]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 200,
                    "startColumnIndex": status_col,
                    "endColumnIndex": status_col + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontSize": 8
                        }
                    }
                },
                "fields":
                    "userEnteredFormat.textFormat.fontSize"
            }
        })

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": req}
    ).execute()

    print("Hotspots Finder sheet configured.")


def ensure_sheet_setup(service, spreadsheet_id, sheet_id):
    marker = get_value(
        service,
        spreadsheet_id,
        f"'{SHEET_NAME}'!A1"
    )

    if str(marker).strip() == "Hotspots":
        print("Hotspots Finder is already configured.")
        return False

    initialize_sheet(
        service,
        spreadsheet_id,
        sheet_id
    )
    return True


def read_values(service, spreadsheet_id, range_name):
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        )
        .execute()
    )

    return result.get("values", [])


def write_value(service, spreadsheet_id, range_name, value):
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": [[value]]}
        )
        .execute()
    )


def cell(values, row, col):
    r = row - 1
    c = col - 1

    if r >= len(values):
        return ""

    if c >= len(values[r]):
        return ""

    return values[r][c]


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() == "TRUE"

# Active local Google Sheets connection.
SHEETS_SERVICE = None
SPREADSHEET_ID = None
HOTSPOTS_SHEET_ID = None


def init_local_google(ensure_references=False):
    """
    Connect to the user's Google account, remember the selected spreadsheet,
    and create/configure the Hotspots Finder sheet when needed.

    When ensure_references=True (used by Connect / Change Sheet), also copy
    any missing reference tabs from the official master template.
    """
    global SHEETS_SERVICE
    global SPREADSHEET_ID
    global HOTSPOTS_SHEET_ID

    creds = get_credentials()

    SHEETS_SERVICE = build(
        "sheets",
        "v4",
        credentials=creds,
        cache_discovery=False,
    )

    SPREADSHEET_ID = get_spreadsheet_id()

    (
        spreadsheet_title,
        HOTSPOTS_SHEET_ID,
        copied_from_master,
    ) = get_or_create_hotspots_sheet(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
    )

    created = ensure_sheet_setup(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        HOTSPOTS_SHEET_ID,
    )

    if ensure_references:
        # Reference tabs are copied only when missing. Existing user copies
        # are intentionally left untouched so they can be freely customized.
        ensure_reference_sheets(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
        )

    print(f"Spreadsheet: {spreadsheet_title}")
    print(f"Sheet:       {SHEET_NAME}")

    if copied_from_master:
        # Make the copied official appearance the initial saved style,
        # so Repair Sheet behaves exactly as before from this point on.
        save_current_style()

        print(
            "Official template copied and saved as the initial style."
        )

    elif created:
        print(
            "Hotspots Finder configured automatically."
        )


def require_google():
    if not SHEETS_SERVICE or not SPREADSHEET_ID:
        raise RuntimeError(
            "Google Sheets connection is not initialized."
        )


def get_hotspots_sheet_properties():
    """
    Return the current Hotspots Finder sheet properties.
    """
    require_google()

    metadata = (
        SHEETS_SERVICE
        .spreadsheets()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            fields="properties.title,sheets.properties",
        )
        .execute()
    )

    spreadsheet_title = (
        metadata
        .get("properties", {})
        .get("title", "")
    )

    for item in metadata.get("sheets", []):
        props = item.get("properties", {})

        if props.get("title") == SHEET_NAME:
            return spreadsheet_title, props

    raise RuntimeError(
        f'The "{SHEET_NAME}" sheet does not exist.'
    )


def ensure_sheet_capacity(
    required_rows=200,
    required_columns=20,
):
    """
    Grow the Hotspots Finder grid when a large result set needs more rows.
    Never shrinks the user's sheet.
    """
    require_google()

    _, props = get_hotspots_sheet_properties()

    grid = props.get(
        "gridProperties",
        {},
    )

    current_rows = int(
        grid.get("rowCount", 0)
        or 0
    )

    current_columns = int(
        grid.get("columnCount", 0)
        or 0
    )

    requests_to_send = []

    if current_rows < required_rows:
        requests_to_send.append({
            "appendDimension": {
                "sheetId": props["sheetId"],
                "dimension": "ROWS",
                "length":
                    required_rows
                    - current_rows,
            }
        })

    if current_columns < required_columns:
        requests_to_send.append({
            "appendDimension": {
                "sheetId": props["sheetId"],
                "dimension": "COLUMNS",
                "length":
                    required_columns
                    - current_columns,
            }
        })

    if requests_to_send:
        (
            SHEETS_SERVICE
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={
                    "requests":
                        requests_to_send
                },
            )
            .execute()
        )



def power_dropdown_validation_is_correct():
    """
    Return True when B20 already has the canonical Power dropdown:
    - ONE_OF_LIST
    - exact 12 Power names, in canonical order
    - strict validation
    - dropdown UI enabled

    If True, Repair Sheet does NOT recreate the validation rule.
    This intentionally preserves any visual customization attached
    to the existing Google Sheets dropdown.
    """
    require_google()

    try:
        response = (
            SHEETS_SERVICE
            .spreadsheets()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                ranges=[
                    f"'{SHEET_NAME}'!B20"
                ],
                includeGridData=True,
                fields=(
                    "sheets.data.rowData.values."
                    "dataValidation"
                ),
            )
            .execute()
        )

        sheets = response.get(
            "sheets",
            [],
        )

        if not sheets:
            return False

        data = sheets[0].get(
            "data",
            [],
        )

        if not data:
            return False

        row_data = data[0].get(
            "rowData",
            [],
        )

        if not row_data:
            return False

        values = row_data[0].get(
            "values",
            [],
        )

        if not values:
            return False

        rule = values[0].get(
            "dataValidation"
        )

        if not isinstance(rule, dict):
            return False

        condition = rule.get(
            "condition",
            {},
        )

        if (
            condition.get("type")
            != "ONE_OF_LIST"
        ):
            return False

        actual_values = [
            str(
                item.get(
                    "userEnteredValue",
                    "",
                )
            )
            for item in condition.get(
                "values",
                [],
            )
        ]

        return (
            actual_values == POWER_LIST
            and rule.get("strict") is True
            and rule.get("showCustomUi") is True
        )

    except Exception:
        # If inspection fails, Repair will safely rebuild the dropdown.
        return False


def power_dropdown_validation_request(
    sheet_id,
):
    return {
        "setDataValidation": {
            "range": {
                "sheetId":
                    sheet_id,
                "startRowIndex":
                    19,
                "endRowIndex":
                    20,
                "startColumnIndex":
                    1,
                "endColumnIndex":
                    2,
            },
            "rule": {
                "condition": {
                    "type":
                        "ONE_OF_LIST",
                    "values": [
                        {
                            "userEnteredValue":
                                power
                        }
                        for power
                        in POWER_LIST
                    ],
                },
                "strict":
                    True,
                "showCustomUi":
                    True,
            },
        }
    }



def repair_sheet_formatting():
    """
    Restore canonical Hotspots Finder structure/appearance without
    clearing user data.

    Supports migration from:
      - legacy 22-row layout
      - previous 27-row layout
      - current 28-row layout
    """
    require_google()

    spreadsheet_title, props = get_hotspots_sheet_properties()
    sheet_id = props["sheetId"]

    grid = props.get("gridProperties", {})
    row_count = max(int(grid.get("rowCount", 0) or 0), 200)
    column_count = max(int(grid.get("columnCount", 0) or 0), 21)

    ensure_sheet_capacity(row_count, column_count)

    current = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!A1:D28",
    )

    legacy_22 = (
        norm(cell(current, 14, 1)) == "faction name"
        and norm(cell(current, 16, 1)) == "power"
    )

    previous_27 = (
        norm(cell(current, 19, 1)) == "faction name"
        and norm(cell(current, 21, 1)) == "power"
    )

    if legacy_22:
        faction_name = str(cell(current, 14, 2) or "")
        power_name = str(cell(current, 16, 2) or "")
        power_values = [
            cell(current, 17, 2),
            cell(current, 18, 2),
            cell(current, 19, 2),
            cell(current, 20, 2),
        ]
        only_positive = False
        status_value = cell(current, 22, 2)

    elif previous_27:
        faction_name = str(cell(current, 19, 2) or "")
        power_name = str(cell(current, 21, 2) or "")
        power_values = [
            cell(current, 22, 2),
            cell(current, 23, 2),
            cell(current, 24, 2),
            cell(current, 25, 2),
        ]
        only_positive = to_bool(cell(current, 26, 2))
        status_value = cell(current, 27, 2)

    else:
        faction_name = str(cell(current, 19, 2) or "")
        power_name = str(cell(current, 20, 2) or "")
        power_values = [
            cell(current, 21, 2),
            cell(current, 22, 2),
            cell(current, 23, 2),
            cell(current, 24, 2),
        ]
        only_positive = to_bool(cell(current, 26, 2))
        status_value = cell(current, 28, 2)

    labels = [
        ["Hotspots"],
        ["Icy"],
        ["Metallic"],
        ["Metal Rich"],
        ["Rocky"],
        ["Platinum"],
        ["Bromellite"],
        ["Monazite"],
        ["Only pristine"],
        [""],
        ["Planets"],
        ["Only landables"],
        ["Icy"],
        ["Metal Rich"],
        ["High Metal Content"],
        ["Rocky"],
        ["Rocky Ice"],
        [""],
        ["Faction name"],
        ["Power"],
        ["Unoccupied"],
        ["Exploited"],
        ["Fortified"],
        ["Stronghold"],
        [""],
        ["Only positive results"],
        [""],
        ["Status"],
    ]

    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!A1:A28",
        labels,
    )

    if legacy_22 or previous_27:
        checkbox_prepare_requests = []

        for start_row, end_row in [
            (10, 17),
            (20, 24),
            (25, 26),
        ]:
            checkbox_prepare_requests.append({
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "rule": {
                        "condition": {"type": "BOOLEAN"},
                        "strict": True,
                        "showCustomUi": True,
                    },
                }
            })

        SHEETS_SERVICE.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": checkbox_prepare_requests},
        ).execute()

        SHEETS_SERVICE.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!B19:B28",
            body={},
        ).execute()

        write_values(SHEETS_SERVICE, SPREADSHEET_ID, f"'{SHEET_NAME}'!B19", [[faction_name]])
        write_values(SHEETS_SERVICE, SPREADSHEET_ID, f"'{SHEET_NAME}'!B20", [[power_name]])
        write_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!B21:B24",
            [[to_bool(v)] for v in power_values],
        )
        write_values(SHEETS_SERVICE, SPREADSHEET_ID, f"'{SHEET_NAME}'!B26", [[only_positive]])

        if status_value not in (None, ""):
            write_values(
                SHEETS_SERVICE,
                SPREADSHEET_ID,
                f"'{SHEET_NAME}'!B28",
                [[status_value]],
            )

    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!C1",
        [["Systems"]],
    )

    system_rows = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!C2:C",
    )

    systems = deduplicate([
        row[0]
        for row in system_rows
        if row and str(row[0]).strip()
    ])

    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!D1",
        [[f"Total: {len(systems)}"]],
    )

    note_rows = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!D2:D",
    )

    if not any(row and str(row[0]).strip() for row in note_rows):
        write_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!D2",
            [["Notes Here"]],
        )

    # --------------------------------------------------------
    # CHECKBOX VALUE SANITIZATION
    # --------------------------------------------------------
    # Google Sheets can keep an invalid value (for example 8 or 9)
    # even after checkbox validation is restored. Normalize every
    # checkbox cell before applying the final formatting:
    #   valid TRUE/FALSE -> preserved
    #   anything else    -> FALSE

    checkbox_value_ranges = [
        "B1:B9",
        "B11:B17",
        "B21:B24",
        "B26",
    ]

    for checkbox_range in checkbox_value_ranges:
        raw_values = read_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!{checkbox_range}",
        )

        normalized = []

        for row in raw_values:
            value = (
                row[0]
                if row
                else False
            )

            # Preserve actual booleans.
            if isinstance(value, bool):
                clean_value = value

            # Also accept literal TRUE/FALSE strings.
            elif isinstance(value, str):
                key = value.strip().lower()

                if key == "true":
                    clean_value = True
                elif key == "false":
                    clean_value = False
                else:
                    clean_value = False

            else:
                clean_value = False

            normalized.append(
                [clean_value]
            )

        # read_values may omit trailing empty rows; restore the full
        # expected checkbox range length.
        expected_lengths = {
            "B1:B9": 9,
            "B11:B17": 7,
            "B21:B24": 4,
            "B26": 1,
        }

        while (
            len(normalized)
            < expected_lengths[checkbox_range]
        ):
            normalized.append(
                [False]
            )

        write_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!{checkbox_range}",
            normalized,
        )

    # --------------------------------------------------------
    # POWER VALUE SANITIZATION
    # --------------------------------------------------------
    # B20 is a strict dropdown. Preserve blank, normalize a
    # case-insensitive valid value to the official spelling,
    # and clear anything outside the current Power list.

    power_rows = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!B20",
    )

    current_power = (
        str(power_rows[0][0]).strip()
        if power_rows
        and power_rows[0]
        and power_rows[0][0] is not None
        else ""
    )

    if current_power:
        power_lookup = {
            power.lower(): power
            for power in POWER_LIST
        }

        canonical_power = power_lookup.get(
            current_power.lower()
        )

        if canonical_power:
            write_values(
                SHEETS_SERVICE,
                SPREADSHEET_ID,
                f"'{SHEET_NAME}'!B20",
                [[canonical_power]],
            )
        else:
            (
                SHEETS_SERVICE
                .spreadsheets()
                .values()
                .clear(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"'{SHEET_NAME}'!B20",
                    body={},
                )
                .execute()
            )

    # --------------------------------------------------------
    # STATUS VALUE SANITIZATION
    # --------------------------------------------------------
    # Preserve only the official statuses.
    # Any manual/invalid value is cleared; the next Run will write
    # RUNNING / COMPLETED / ERROR normally.
    valid_statuses = {
        "RUNNING",
        "COMPLETED",
        "ERROR",
    }

    current_status = str(
        status_value or ""
    ).strip().upper()

    if current_status in valid_statuses:
        write_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!B28",
            [[current_status]],
        )
        status_value = current_status
    else:
        (
            SHEETS_SERVICE
            .spreadsheets()
            .values()
            .clear(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{SHEET_NAME}'!B28",
                body={},
            )
            .execute()
        )
        status_value = ""

    # --------------------------------------------------------
    # FORMAT REQUESTS
    # --------------------------------------------------------

    req = []

    req.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": 1,
                    "frozenColumnCount": 4,
                    "hideGridlines": True,
                },
            },
            "fields": (
                "gridProperties.frozenRowCount,"
                "gridProperties.frozenColumnCount,"
                "gridProperties.hideGridlines"
            ),
        }
    })

    # Base style over the full current grid.
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": row_count,
                "startColumnIndex": 0,
                "endColumnIndex": column_count,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BG,
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "fontFamily": "Arial",
                        "fontSize": 11,
                        "bold": False,
                    },
                    "horizontalAlignment": "LEFT",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.textFormat,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.verticalAlignment"
            ),
        }
    })

    # Uniform row height across the entire current sheet.
    # This keeps filters and all result rows visually consistent.
    req.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": row_count,
            },
            "properties": {
                "pixelSize": 17,
            },
            "fields": "pixelSize",
        }
    })

    widths = {
        0: 165,
        1: 170,
        2: 225,
        3: 170,
        4: 190,
        5: 150,
        6: 180,
        7: 180,
        8: 130,
        9: 130,
        10: 110,
        11: 160,
        12: 110,
        13: 28,
        14: 190,
        15: 150,
        16: 180,
        17: 150,
        18: 110,
        19: 170,
        20: 130,
    }

    for col, width in widths.items():
        req.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": col,
                    "endIndex": col + 1,
                },
                "properties": {
                    "pixelSize": width,
                },
                "fields": "pixelSize",
            }
        })

    for row in [0, 10, 18, 19, 27]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": DARK_HEADER,
                        "textFormat": {
                            "foregroundColor": WHITE,
                            "fontFamily": "Arial",
                            "fontSize": 11,
                            "bold": True,
                        },
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.textFormat"
                ),
            }
        })

    for row, color in [
        (0, ORANGE),
        (10, ORANGE),
        (18, ORANGE),
        (19, ORANGE),
        (27, ORANGE),
    ]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "foregroundColor": color,
                            "bold": True,
                        }
                    }
                },
                "fields":
                    "userEnteredFormat.textFormat",
            }
        })

    # C1:D1 headers.
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 2,
                "endColumnIndex": 4,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_HEADER,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "bold": True,
                    },
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.textFormat"
            ),
        }
    })

    # D1 total counter in white
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 3,
                "endColumnIndex": 4,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "bold": True,
                    },
                }
            },
            "fields":
                "userEnteredFormat.textFormat",
        }
    })

    # Systems body.
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": row_count,
                "startColumnIndex": 2,
                "endColumnIndex": 3,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BG,
                    "horizontalAlignment": "LEFT",
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "fontFamily": "Arial",
                        "fontSize": 11,
                        "bold": False,
                    },
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.textFormat"
            ),
        }
    })

    # Notes body D2:D. Values are preserved.
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": row_count,
                "startColumnIndex": 3,
                "endColumnIndex": 4,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BG,
                    "horizontalAlignment": "LEFT",
                    "wrapStrategy": "WRAP",
                    "textFormat": {
                        "foregroundColor": LIGHT,
                        "fontFamily": "Arial",
                        "fontSize": 11,
                        "bold": False,
                    },
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.wrapStrategy,"
                "userEnteredFormat.textFormat"
            ),
        }
    })

    # Faction / Power inputs B19, B20.
    for row in [18, 19]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": INPUT_BG,
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "foregroundColor": WHITE,
                            "bold": True,
                        },
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.horizontalAlignment,"
                    "userEnteredFormat.textFormat"
                ),
            }
        })

    # Power dropdown B20.
    # Preserve an already-correct dropdown instead of recreating it:
    # this keeps any user/template visual customization of the rule.
    if not power_dropdown_validation_is_correct():
        req.append(
            power_dropdown_validation_request(
                sheet_id
            )
        )

    for start_row, end_row in [
        (0, 9),
        (10, 17),
        (20, 24),
        (25, 26),  # B26 Only positive results
    ]:
        req.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2,
                },
                "rule": {
                    "condition": {
                        "type": "BOOLEAN",
                    },
                    "strict": True,
                    "showCustomUi": True,
                },
            }
        })

        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                    }
                },
                "fields":
                    "userEnteredFormat.horizontalAlignment",
            }
        })

    border_style = {
        "style": "SOLID",
        "color": LIGHT,
    }

    for start_row, end_row, top in [
        (1, 5, False),
        (5, 8, True),
        (8, 9, True),
        (11, 17, True),
        (20, 24, True),
        (25, 26, True),  # A26:B26
    ]:
        borders = {
            "left": border_style,
            "right": border_style,
            "bottom": border_style,
        }

        if top:
            borders["top"] = border_style

        req.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                **borders,
            }
        })

    no_border = {"style": "NONE"}

    req.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": 2,
            },
            "top": no_border,
            "bottom": no_border,
            "left": no_border,
            "right": no_border,
            "innerVertical": no_border,
        }
    })

    # Results header E:U.
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 4,
                "endColumnIndex": min(column_count, 21),
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_HEADER,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "bold": True,
                    },
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.textFormat"
            ),
        }
    })

    subtle = {
        "style": "SOLID",
        "color": GRID,
    }

    if row_count > 1:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": row_count,
                    "startColumnIndex": 4,
                    "endColumnIndex": min(column_count, 21),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": DARK_BG,
                        "horizontalAlignment": "LEFT",
                        "textFormat": {
                            "foregroundColor": WHITE,
                            "fontFamily": "Arial",
                            "fontSize": 11,
                            "bold": False,
                        },
                    }
                },
                "fields": (
                    "userEnteredFormat.backgroundColor,"
                    "userEnteredFormat.horizontalAlignment,"
                    "userEnteredFormat.textFormat"
                ),
            }
        })

        req.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": row_count,
                    "startColumnIndex": 4,
                    "endColumnIndex": min(column_count, 21),
                },
                "top": subtle,
                "bottom": subtle,
                "left": subtle,
                "right": subtle,
                "innerHorizontal": subtle,
                "innerVertical": subtle,
            }
        })

    # N separator borders (both sides visible)
    req.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": row_count,
                "startColumnIndex": 13,
                "endColumnIndex": 14,
            },
            "left": {
                "style": "SOLID_THICK",
                "color": LIGHT,
            },
            "right": {
                "style": "SOLID_THICK",
                "color": LIGHT,
            },
        }
    })

    # Status B28 style according to current value.
    status_key = str(
        status_value or ""
    ).strip().upper()

    status_bg = DARK_BG
    status_fg = WHITE

    if status_key == "RUNNING":
        status_bg = ORANGE
        status_fg = DARK_HEADER
    elif status_key == "COMPLETED":
        status_bg = GREEN
        status_fg = DARK_HEADER
    elif status_key == "ERROR":
        status_bg = RED
        status_fg = WHITE

    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 27,
                "endRowIndex": 28,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": status_bg,
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": status_fg,
                        "bold": True,
                    },
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.horizontalAlignment,"
                "userEnteredFormat.textFormat"
            ),
        }
    })

    # Final font sizing:
    # entire current sheet = 10 pt
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": row_count,
                "startColumnIndex": 0,
                "endColumnIndex": column_count,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "fontSize": 10,
                    }
                }
            },
            "fields":
                "userEnteredFormat.textFormat.fontSize",
        }
    })

    # Column B, rows 1:26 = 8 pt
    req.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 26,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "fontSize": 8,
                    }
                }
            },
            "fields":
                "userEnteredFormat.textFormat.fontSize",
        }
    })

    # Status result columns: body font size 8.
    # Headers F1 and P1 remain at the standard 10 pt.
    for status_col in [5, 15]:
        req.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": row_count,
                    "startColumnIndex": status_col,
                    "endColumnIndex": status_col + 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontSize": 8,
                        }
                    }
                },
                "fields":
                    "userEnteredFormat.textFormat.fontSize",
            }
        })

    # If this Sheet has a saved appearance, append its formatting
    # to the SAME batch request. The canonical structure is still
    # repaired first, but the user only sees the final custom style.
    saved_profile = load_saved_style()

    if saved_profile:
        req.extend(
            _build_saved_style_requests(
                saved_profile,
                sheet_id,
                row_count,
            )
        )

    (
        SHEETS_SERVICE
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": req},
        )
        .execute()
    )

    print(
        "Sheet structure and formatting repaired."
    )

    return spreadsheet_title



def norm(value):
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def norm_filter(value):
    return norm(value).replace("-", " ")


def deduplicate(values):
    seen = set()
    result = []

    for value in values:
        value = str(value or "").strip()

        if not value:
            continue

        key = norm(value)

        if key not in seen:
            seen.add(key)
            result.append(value)

    return result




def chunks(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


class ScanCancelled(Exception):
    """Raised when the desktop GUI requests a clean scan stop."""


def check_cancel(cancel_event=None):
    if cancel_event is not None and cancel_event.is_set():
        raise ScanCancelled("Scan cancelled by user.")


def cancellable_sleep(seconds, cancel_event=None):
    if cancel_event is None:
        time.sleep(seconds)
        return

    if cancel_event.wait(seconds):
        raise ScanCancelled("Scan cancelled by user.")


def request_with_retries(method, url, cancel_event=None, **kwargs):
    last_error = None

    for attempt in range(1, RETRIES + 1):
        check_cancel(cancel_event)

        try:
            response = requests.request(
                method,
                url,
                timeout=90,
                **kwargs,
            )

            response.raise_for_status()
            check_cancel(cancel_event)
            return response

        except ScanCancelled:
            raise

        except Exception as exc:
            last_error = exc

            if attempt < RETRIES:
                wait = 2 ** attempt

                print(
                    f"Request failed ({attempt}/{RETRIES}); "
                    f"retry in {wait}s: {exc}"
                )

                cancellable_sleep(wait, cancel_event)

    raise last_error




# ============================================================
# SHEET STYLE PROFILES
# ============================================================

STYLE_PROFILE_VERSION = 1


def _extract_format_matrix(a1_range, rows, cols):
    """
    Read only user-entered cell formatting from a range.
    Values are never included.
    """
    require_google()

    response = (
        SHEETS_SERVICE
        .spreadsheets()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            ranges=[
                f"'{SHEET_NAME}'!{a1_range}"
            ],
            includeGridData=True,
            fields=(
                "sheets.data.rowData.values."
                "userEnteredFormat"
            ),
        )
        .execute()
    )

    result = [
        [{} for _ in range(cols)]
        for _ in range(rows)
    ]

    sheets = response.get("sheets", [])

    if not sheets:
        return result

    data_blocks = sheets[0].get("data", [])

    if not data_blocks:
        return result

    row_data = data_blocks[0].get(
        "rowData",
        [],
    )

    for r in range(min(rows, len(row_data))):
        values = row_data[r].get(
            "values",
            [],
        )

        for c in range(
            min(cols, len(values))
        ):
            fmt = values[c].get(
                "userEnteredFormat",
                {},
            )

            result[r][c] = (
                fmt
                if isinstance(fmt, dict)
                else {}
            )

    return result


def _get_style_sheet_properties():
    require_google()

    metadata = (
        SHEETS_SERVICE
        .spreadsheets()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            fields="sheets.properties",
        )
        .execute()
    )

    for item in metadata.get("sheets", []):
        props = item.get(
            "properties",
            {},
        )

        if (
            props.get("title")
            == STYLE_SHEET_NAME
        ):
            return props

    return None


def _get_or_create_style_sheet():
    props = _get_style_sheet_properties()

    if props:
        grid = props.get(
            "gridProperties",
            {},
        )

        current_rows = int(
            grid.get("rowCount", 0)
            or 0
        )

        current_columns = int(
            grid.get("columnCount", 0)
            or 0
        )

        if (
            current_rows < 40
            or current_columns < 30
        ):
            (
                SHEETS_SERVICE
                .spreadsheets()
                .batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={
                        "requests": [
                            {
                                "updateSheetProperties": {
                                    "properties": {
                                        "sheetId":
                                            props["sheetId"],
                                        "gridProperties": {
                                            "rowCount":
                                                max(
                                                    current_rows,
                                                    40,
                                                ),
                                            "columnCount":
                                                max(
                                                    current_columns,
                                                    30,
                                                ),
                                        },
                                    },
                                    "fields": (
                                        "gridProperties."
                                        "rowCount,"
                                        "gridProperties."
                                        "columnCount"
                                    ),
                                }
                            }
                        ]
                    },
                )
                .execute()
            )

            props = _get_style_sheet_properties()

        if not props.get("hidden"):
            (
                SHEETS_SERVICE
                .spreadsheets()
                .batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={
                        "requests": [
                            {
                                "updateSheetProperties": {
                                    "properties": {
                                        "sheetId":
                                            props["sheetId"],
                                        "hidden": True,
                                    },
                                    "fields":
                                        "hidden",
                                }
                            }
                        ]
                    },
                )
                .execute()
            )

        return props

    response = (
        SHEETS_SERVICE
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title":
                                    STYLE_SHEET_NAME,
                                "hidden":
                                    True,
                                "gridProperties": {
                                    "rowCount":
                                        40,
                                    "columnCount":
                                        30,
                                },
                            }
                        }
                    }
                ]
            },
        )
        .execute()
    )

    return (
        response["replies"][0]
        ["addSheet"]["properties"]
    )


def _encode_style_profile(profile):
    raw = json.dumps(
        profile,
        separators=(",", ":"),
    ).encode("utf-8")

    compressed = gzip.compress(raw)

    return base64.b64encode(
        compressed
    ).decode("ascii")


def _decode_style_profile(payload):
    compressed = base64.b64decode(
        str(payload).encode("ascii")
    )

    raw = gzip.decompress(
        compressed
    )

    return json.loads(
        raw.decode("utf-8")
    )


def load_saved_style():
    """
    Return the saved style profile, or None if this Sheet uses
    the official appearance.
    """
    require_google()

    props = _get_style_sheet_properties()

    if not props:
        return None

    values = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{STYLE_SHEET_NAME}'!A1:B3",
    )

    if not values:
        return None

    lookup = {}

    for row in values:
        if (
            len(row) >= 2
            and str(row[0]).strip()
        ):
            lookup[
                str(row[0]).strip()
            ] = row[1]

    payload = lookup.get(
        "STYLE_DATA"
    )

    if not payload:
        return None

    try:
        profile = _decode_style_profile(
            payload
        )
    except Exception as exc:
        raise RuntimeError(
            "The saved style profile is corrupted."
        ) from exc

    if (
        profile.get("version")
        != STYLE_PROFILE_VERSION
    ):
        raise RuntimeError(
            "The saved style profile uses an "
            "unsupported version."
        )

    return profile


def _snapshot_format_templates():
    """
    Store real Google Sheets formatting templates inside _HF_STYLE.

    Layout in hidden sheet:
      D1:E29  <- A1:B29  filter/control panel + below-filter template
      G1:H2   <- C1:D2   Systems / Total / Notes templates
      J1:Z2   <- E1:U2   result headers + result-body templates

    PASTE_FORMAT copies formatting only — never user values.
    """
    require_google()

    style_props = _get_or_create_style_sheet()
    style_sheet_id = style_props["sheetId"]

    requests_to_send = [
        {
            "copyPaste": {
                "source": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "startRowIndex": 0,
                    "endRowIndex": 29,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "destination": {
                    "sheetId":
                        style_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 29,
                    "startColumnIndex": 3,
                    "endColumnIndex": 5,
                },
                "pasteType":
                    "PASTE_FORMAT",
                "pasteOrientation":
                    "NORMAL",
            }
        },
        {
            "copyPaste": {
                "source": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "startRowIndex": 0,
                    "endRowIndex": 2,
                    "startColumnIndex": 2,
                    "endColumnIndex": 4,
                },
                "destination": {
                    "sheetId":
                        style_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 2,
                    "startColumnIndex": 6,
                    "endColumnIndex": 8,
                },
                "pasteType":
                    "PASTE_FORMAT",
                "pasteOrientation":
                    "NORMAL",
            }
        },
        {
            "copyPaste": {
                "source": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "startRowIndex": 0,
                    "endRowIndex": 2,
                    "startColumnIndex": 4,
                    "endColumnIndex": 21,
                },
                "destination": {
                    "sheetId":
                        style_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 2,
                    "startColumnIndex": 9,
                    "endColumnIndex": 26,
                },
                "pasteType":
                    "PASTE_FORMAT",
                "pasteOrientation":
                    "NORMAL",
            }
        },
    ]

    (
        SHEETS_SERVICE
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests":
                    requests_to_send
            },
        )
        .execute()
    )

    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{STYLE_SHEET_NAME}'!A5:B5",
        [[
            "FORMAT_TEMPLATE_VERSION",
            1,
        ]],
    )


def save_current_style():
    """
    Capture the current visual style without saving any cell value,
    filter position or functional structure.

    Captured:
      A1:B28  -> control/filter panel
      C1:D2   -> Systems/Total + body templates
      E1:U2   -> result headers + body templates

    The style is stored compressed in the hidden _HF_STYLE sheet.
    """
    require_google()

    controls = _extract_format_matrix(
        "A1:B28",
        28,
        2,
    )

    systems = _extract_format_matrix(
        "C1:D2",
        2,
        2,
    )

    results = _extract_format_matrix(
        "E1:U2",
        2,
        17,
    )

    below_filters = _extract_format_matrix(
        "A29:B29",
        1,
        2,
    )

    # B28 is dynamic (RUNNING / COMPLETED / ERROR).
    # Do not override its status-dependent colors with a snapshot.
    controls[27][1] = {}

    profile = {
        "version":
            STYLE_PROFILE_VERSION,
        "controls":
            controls,
        "systems":
            systems,
        "results":
            results,
        "below_filters":
            below_filters,
    }

    payload = _encode_style_profile(
        profile
    )

    _get_or_create_style_sheet()

    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{STYLE_SHEET_NAME}'!A1:B3",
        [
            [
                "STYLE_VERSION",
                STYLE_PROFILE_VERSION,
            ],
            [
                "STYLE_DATA",
                payload,
            ],
            [
                "SOURCE_SHEET",
                SHEET_NAME,
            ],
        ],
    )

    _snapshot_format_templates()

    print(
        "Current sheet appearance saved as default style."
    )

    return True


def _append_format_request(
    requests_list,
    sheet_id,
    start_row,
    end_row,
    start_col,
    end_col,
    cell_format,
):
    if not cell_format:
        return

    requests_list.append({
        "repeatCell": {
            "range": {
                "sheetId":
                    sheet_id,
                "startRowIndex":
                    start_row,
                "endRowIndex":
                    end_row,
                "startColumnIndex":
                    start_col,
                "endColumnIndex":
                    end_col,
            },
            "cell": {
                "userEnteredFormat":
                    cell_format,
            },
            "fields":
                "userEnteredFormat",
        }
    })


def _build_saved_style_requests(
    profile,
    sheet_id,
    row_count,
):
    """
    Build formatting requests for the saved custom style.
    No API call is made here, so Repair Sheet can merge them into
    its own batchUpdate and avoid visible two-stage formatting.
    """
    requests_list = []

    # --------------------------------------------------------
    # A1:B28 exact visual appearance
    # --------------------------------------------------------

    controls = profile.get(
        "controls",
        [],
    )

    for r in range(
        min(28, len(controls))
    ):
        row = controls[r]

        for c in range(
            min(2, len(row))
        ):
            # B28 keeps dynamic status colors.
            if r == 27 and c == 1:
                continue

            _append_format_request(
                requests_list,
                sheet_id,
                r,
                r + 1,
                c,
                c + 1,
                row[c],
            )

    # --------------------------------------------------------
    # A29:B... template for area below filter panel
    # --------------------------------------------------------

    below_filters = profile.get(
        "below_filters",
        [],
    )

    if (
        row_count > 28
        and len(below_filters) >= 1
    ):
        row = below_filters[0]

        for c in range(
            min(2, len(row))
        ):
            _append_format_request(
                requests_list,
                sheet_id,
                28,
                row_count,
                c,
                c + 1,
                row[c],
            )

    # --------------------------------------------------------
    # C:D
    # C1 / D1 exact; C2 / D2 become templates for whole bodies
    # --------------------------------------------------------

    systems = profile.get(
        "systems",
        [],
    )

    if len(systems) >= 1:
        for c in range(
            min(2, len(systems[0]))
        ):
            _append_format_request(
                requests_list,
                sheet_id,
                0,
                1,
                2 + c,
                3 + c,
                systems[0][c],
            )

    if len(systems) >= 2:
        for c in range(
            min(2, len(systems[1]))
        ):
            _append_format_request(
                requests_list,
                sheet_id,
                1,
                row_count,
                2 + c,
                3 + c,
                systems[1][c],
            )

    # --------------------------------------------------------
    # E:U
    # Row 1 exact headers; row 2 templates for all result rows.
    # --------------------------------------------------------

    results = profile.get(
        "results",
        [],
    )

    if len(results) >= 1:
        for c in range(
            min(17, len(results[0]))
        ):
            _append_format_request(
                requests_list,
                sheet_id,
                0,
                1,
                4 + c,
                5 + c,
                results[0][c],
            )

    if len(results) >= 2:
        for c in range(
            min(17, len(results[1]))
        ):
            _append_format_request(
                requests_list,
                sheet_id,
                1,
                row_count,
                4 + c,
                5 + c,
                results[1][c],
            )

    return requests_list


def apply_saved_style():
    """
    Apply the saved appearance immediately.
    Returns True when a custom style was applied.
    """
    require_google()

    profile = load_saved_style()

    if not profile:
        return False

    _, props = get_hotspots_sheet_properties()

    sheet_id = props["sheetId"]

    grid = props.get(
        "gridProperties",
        {},
    )

    row_count = max(
        int(
            grid.get("rowCount", 0)
            or 0
        ),
        200,
    )

    requests_list = _build_saved_style_requests(
        profile,
        sheet_id,
        row_count,
    )

    if requests_list:
        (
            SHEETS_SERVICE
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={
                    "requests":
                        requests_list
                },
            )
            .execute()
        )

    print(
        "Saved custom appearance applied."
    )

    return True



def restore_official_style():
    """
    Remove the custom profile and immediately restore the official theme.
    Values and filters are preserved.
    """
    require_google()

    props = _get_style_sheet_properties()

    if props:
        (
            SHEETS_SERVICE
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={
                    "requests": [
                        {
                            "deleteSheet": {
                                "sheetId":
                                    props["sheetId"]
                            }
                        }
                    ]
                },
            )
            .execute()
        )

    repair_sheet_formatting()

    # Keep an official formatting template available for Apps Script.
    _get_or_create_style_sheet()
    _snapshot_format_templates()

    print(
        "Official Hotspots Finder appearance restored."
    )

    return True



# ============================================================
# GOOGLE SHEET STATUS
# ============================================================
# GOOGLE SHEET STATUS
# ============================================================

def update_finder_status(status):
    """
    Update Hotspots Finder!B28 through the Google Sheets API.
    Statuses: RUNNING / COMPLETED / ERROR
    """
    require_google()

    write_value(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!B28",
        status,
    )

    status_key = str(
        status or ""
    ).strip().upper()

    background = DARK_BG
    foreground = WHITE

    if status_key == "RUNNING":
        background = ORANGE
        foreground = DARK_HEADER
    elif status_key == "COMPLETED":
        background = GREEN
        foreground = DARK_HEADER
    elif status_key == "ERROR":
        background = RED
        foreground = WHITE

    (
        SHEETS_SERVICE
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId":
                                    HOTSPOTS_SHEET_ID,
                                "startRowIndex": 27,
                                "endRowIndex": 28,
                                "startColumnIndex": 1,
                                "endColumnIndex": 2,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor":
                                        background,
                                    "horizontalAlignment":
                                        "CENTER",
                                    "textFormat": {
                                        "foregroundColor":
                                            foreground,
                                        "bold": True,
                                    },
                                }
                            },
                            "fields": (
                                "userEnteredFormat."
                                "backgroundColor,"
                                "userEnteredFormat."
                                "horizontalAlignment,"
                                "userEnteredFormat."
                                "textFormat"
                            ),
                        }
                    }
                ]
            },
        )
        .execute()
    )


# ============================================================
# GOOGLE SHEET INPUT
# ============================================================
# GOOGLE SHEET INPUT
# ============================================================

def get_sheet_input():
    require_google()

    values = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!A1:D28",
    )

    system_rows = read_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!C2:C",
    )

    systems = deduplicate([
        row[0]
        for row in system_rows
        if row and str(row[0]).strip()
    ])

    # D1 contains the only visible counter.
    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!D1",
        [[f"Total: {len(systems)}"]],
    )

    hotspots_enabled = to_bool(
        cell(values, 1, 2)
    )

    planets_enabled = to_bool(
        cell(values, 11, 2)
    )

    ring_types = {
        "icy": to_bool(cell(values, 2, 2)),
        "metallic": to_bool(cell(values, 3, 2)),
        "metal rich": to_bool(cell(values, 4, 2)),
        "rocky": to_bool(cell(values, 5, 2)),
    }

    materials = {
        "platinum": to_bool(cell(values, 6, 2)),
        "bromellite": to_bool(cell(values, 7, 2)),
        "monazite": to_bool(cell(values, 8, 2)),
    }

    only_pristine = to_bool(
        cell(values, 9, 2)
    )

    only_landables = to_bool(
        cell(values, 12, 2)
    )

    planet_types = {
        "icy": to_bool(cell(values, 13, 2)),
        "metal rich": to_bool(cell(values, 14, 2)),
        "high metal content": to_bool(cell(values, 15, 2)),
        "rocky": to_bool(cell(values, 16, 2)),
        "rocky ice": to_bool(cell(values, 17, 2)),
    }

    faction_name = str(
        cell(values, 19, 2)
        or ""
    ).strip()

    power_name = str(
        cell(values, 20, 2)
        or ""
    ).strip()

    power_states = {
        "Unoccupied": to_bool(cell(values, 21, 2)),
        "Exploited": to_bool(cell(values, 22, 2)),
        "Fortified": to_bool(cell(values, 23, 2)),
        "Stronghold": to_bool(cell(values, 24, 2)),
    }

    only_positive_results = to_bool(
        cell(values, 26, 2)
    )

    if (
        not systems
        and not faction_name
        and not power_name
    ):
        raise RuntimeError(
            "No systems found in Hotspots Finder!C2:C, "
            "Faction name is empty and Power is empty."
        )

    return {
        "systems": systems,
        "hotspots_enabled": hotspots_enabled,
        "planets_enabled": planets_enabled,
        "ring_types": ring_types,
        "materials": materials,
        "only_pristine": only_pristine,
        "only_landables": only_landables,
        "planet_types": planet_types,
        "faction_name": faction_name,
        "power_name": power_name,
        "power_states": power_states,
        "only_positive_results":
            only_positive_results,
    }


# ============================================================
# SPANSH SYSTEM SEARCH - FACTION / POWER / POWER STATE
# ============================================================
# SPANSH SYSTEM SEARCH - FACTION / POWER / POWER STATE
# ============================================================

def value_matches_exact(value, expected):
    """
    Defensive exact-match helper.
    Spansh fields are normally strings, but this also supports
    list-like values for compatibility with older data.
    """
    expected_key = norm(expected)

    if isinstance(value, (list, tuple, set)):
        return any(
            norm(item) == expected_key
            for item in value
        )

    return norm(value) == expected_key


def search_systems_by_filters(
    faction_name,
    power_name,
    selected_power_states,
    cancel_event=None,
):
    """
    Search Spansh systems using any combination of:
      - controlling_minor_faction
      - power
      - power_state

    Power State is applied only when Power is set.
    """
    faction_name = str(
        faction_name or ""
    ).strip()

    power_name = str(
        power_name or ""
    ).strip()

    selected_power_states = [
        str(state).strip()
        for state in selected_power_states
        if str(state).strip()
    ]

    filters = {}

    if faction_name:
        filters[
            "controlling_minor_faction"
        ] = {
            "value": [faction_name]
        }

    if power_name:
        filters[
            "power"
        ] = {
            "value": [power_name]
        }

        if selected_power_states:
            filters[
                "power_state"
            ] = {
                "value":
                    selected_power_states
            }

    if not filters:
        return []

    print(
        "Searching Spansh systems with filters:"
    )

    if faction_name:
        print(
            f'  Controlling faction: "{faction_name}"'
        )

    if power_name:
        print(
            f'  Power: "{power_name}"'
        )

        print(
            "  Power states: "
            + (
                ", ".join(
                    selected_power_states
                )
                if selected_power_states
                else "ALL"
            )
        )

    systems = []
    seen = set()
    page = 0

    selected_state_keys = {
        norm(state)
        for state in selected_power_states
    }

    while True:
        check_cancel(cancel_event)

        payload = {
            "filters": filters,
            "size": PAGE_SIZE,
            "page": page,
        }

        response = request_with_retries(
            "POST",
            SPANSH_SYSTEMS_URL,
            cancel_event=cancel_event,
            json=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Accept":
                    "application/json",
                "Content-Type":
                    "application/json",
            },
        )

        data = response.json()

        results = (
            data.get("results", [])
            or []
        )

        total = int(
            data.get("count", 0)
            or 0
        )

        for item in results:

            # --------------------------------------------
            # Extra local exact-match validation
            # --------------------------------------------

            if faction_name:
                controlling = item.get(
                    "controlling_minor_faction",
                    "",
                )

                if not value_matches_exact(
                    controlling,
                    faction_name,
                ):
                    continue

            if power_name:
                system_power = item.get(
                    "power",
                    [],
                )

                if not value_matches_exact(
                    system_power,
                    power_name,
                ):
                    continue

                if selected_state_keys:
                    system_power_state = norm(
                        item.get(
                            "power_state",
                            "",
                        )
                    )

                    if (
                        system_power_state
                        not in selected_state_keys
                    ):
                        continue

            system_name = str(
                item.get("name")
                or item.get("system_name")
                or ""
            ).strip()

            if not system_name:
                continue

            key = norm(system_name)

            if key not in seen:
                seen.add(key)
                systems.append(
                    system_name
                )

        if (
            not results
            or
            (page + 1) * PAGE_SIZE
            >= total
        ):
            break

        page += 1
        cancellable_sleep(DELAY, cancel_event)

    check_cancel(cancel_event)

    systems.sort(
        key=lambda value:
            value.casefold()
    )

    print(
        f"Systems matching filters: "
        f"{len(systems)}"
    )

    return systems


def write_systems_to_sheet(systems):
    """
    Replace Hotspots Finder!C2:C and update D1.
    Column D from row 2 onward is reserved for user notes.
    """
    require_google()

    ensure_sheet_capacity(
        max(len(systems) + 1, 200),
        20,
    )

    (
        SHEETS_SERVICE
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!C2:C",
            body={},
        )
        .execute()
    )

    if systems:
        write_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!C2",
            [[system] for system in systems],
        )

    write_values(
        SHEETS_SERVICE,
        SPREADSHEET_ID,
        f"'{SHEET_NAME}'!D1",
        [[f"Total: {len(systems)}"]],
    )

    return {
        "status": "ok",
        "rows": len(systems),
    }


# ============================================================
# SPANSH
# ============================================================

def request_spansh_page(systems, page, cancel_event=None):
    payload = {
        "filters": {
            "system_name": {
                "value": systems
            }
        },
        "size": PAGE_SIZE,
        "page": page,
    }

    response = request_with_retries(
        "POST",
        SPANSH_URL,
        cancel_event=cancel_event,
        json=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    return response.json()


def fetch_batch(systems, cancel_event=None):
    bodies_by_system = {}
    page = 0

    while True:
        check_cancel(cancel_event)

        data = request_spansh_page(
            systems,
            page,
            cancel_event=cancel_event,
        )

        bodies = (
            data.get("results", [])
            or []
        )

        total = int(
            data.get("count", 0)
            or 0
        )

        for body in bodies:
            system_name = str(
                body.get("system_name", "")
                or ""
            ).strip()

            if not system_name:
                continue

            bodies_by_system.setdefault(
                norm(system_name),
                []
            ).append(body)

        if (
            not bodies
            or
            (page + 1) * PAGE_SIZE >= total
        ):
            break

        page += 1
        cancellable_sleep(DELAY, cancel_event)

    check_cancel(cancel_event)
    return bodies_by_system


def query_all_systems(systems, cancel_event=None):
    all_bodies = {}
    unresolved = []

    batches = list(
        chunks(
            systems,
            BATCH_SIZE,
        )
    )

    for batch_number, batch in enumerate(
        batches,
        1,
    ):
        check_cancel(cancel_event)

        print(
            f"[{batch_number}/{len(batches)}] "
            f"Querying {len(batch)} systems..."
        )

        try:
            result = fetch_batch(
                batch,
                cancel_event=cancel_event,
            )

            for key, bodies in result.items():
                all_bodies.setdefault(
                    key,
                    [],
                ).extend(bodies)

        except ScanCancelled:
            raise

        except Exception as exc:
            print(
                "Batch failed after retries: "
                f"{exc}"
            )

            print(
                "Falling back to "
                "one-system-at-a-time..."
            )

            for system in batch:
                try:
                    check_cancel(cancel_event)

                    result = fetch_batch(
                        [system],
                        cancel_event=cancel_event,
                    )

                    for key, bodies in result.items():
                        all_bodies.setdefault(
                            key,
                            [],
                        ).extend(bodies)

                except ScanCancelled:
                    raise

                except Exception as single_exc:
                    print(
                        f"UNRESOLVED: "
                        f"{system}: "
                        f"{single_exc}"
                    )

                    unresolved.append(
                        system
                    )

                cancellable_sleep(DELAY, cancel_event)

        if batch_number < len(batches):
            cancellable_sleep(DELAY, cancel_event)

    check_cancel(cancel_event)
    return all_bodies, unresolved


# ============================================================
# HOTSPOTS
# ============================================================

HOTSPOT_HEADERS = [
    "System",
    "Status",
    "Body",
    "Ring",
    "Ring Type",
    "Reserve Level",
    "LS Distance",
    "Material",
    "Hotspot Count",
]


def empty_hotspot_status(system, status):
    return {
        "System": system,
        "Status": status,
        "Body": "",
        "Ring": "",
        "Ring Type": "",
        "Reserve Level": "",
        "LS Distance": "",
        "Material": "",
        "Hotspot Count": "",
    }


def build_hotspot_rows(
    systems,
    bodies_by_system,
    unresolved,
):
    unresolved_keys = {
        norm(x)
        for x in unresolved
    }

    raw_rows = []

    for system in systems:
        key = norm(system)

        if key in unresolved_keys:
            raw_rows.append(
                empty_hotspot_status(
                    system,
                    "UNKNOWN_API_ERROR",
                )
            )
            continue

        bodies = bodies_by_system.get(
            key,
            [],
        )

        if not bodies:
            raw_rows.append(
                empty_hotspot_status(
                    system,
                    "SYSTEM_NOT_FOUND",
                )
            )
            continue

        has_ring = False

        for body in bodies:
            body_name = str(
                body.get("name", "")
                or ""
            ).strip()

            reserve = body.get(
                "reserve_level",
                "",
            )

            ls_distance = body.get(
                "distance_to_arrival",
                "",
            )

            rings = (
                body.get("rings", [])
                or []
            )

            for ring in rings:
                has_ring = True

                ring_name = str(
                    ring.get("name", "")
                    or ""
                ).strip()

                ring_type = ring.get(
                    "type",
                    "",
                )

                signals = (
                    ring.get("signals", [])
                    or []
                )

                if not signals:
                    raw_rows.append({
                        "System": system,
                        "Status": "NO_HOTSPOT / NOT SCANNED",
                        "Body": body_name,
                        "Ring": ring_name,
                        "Ring Type": ring_type,
                        "Reserve Level": reserve,
                        "LS Distance": ls_distance,
                        "Material": "",
                        "Hotspot Count": "",
                    })
                    continue

                valid_signal = False

                for signal in signals:
                    material = str(
                        signal.get("name", "")
                        or ""
                    ).strip()

                    if not material:
                        continue

                    valid_signal = True

                    raw_rows.append({
                        "System": system,
                        "Status": "HOTSPOT_FOUND",
                        "Body": body_name,
                        "Ring": ring_name,
                        "Ring Type": ring_type,
                        "Reserve Level": reserve,
                        "LS Distance": ls_distance,
                        "Material": material,
                        "Hotspot Count":
                            signal.get(
                                "count",
                                0,
                            ),
                    })

                if not valid_signal:
                    raw_rows.append({
                        "System": system,
                        "Status": "NO_HOTSPOT / NOT SCANNED",
                        "Body": body_name,
                        "Ring": ring_name,
                        "Ring Type": ring_type,
                        "Reserve Level": reserve,
                        "LS Distance": ls_distance,
                        "Material": "",
                        "Hotspot Count": "",
                    })

        if not has_ring:
            raw_rows.append(
                empty_hotspot_status(
                    system,
                    "NO_RINGS",
                )
            )

    return raw_rows


def filter_hotspot_rows(
    systems,
    raw_rows,
    ring_types,
    materials,
    only_pristine,
):
    selected_ring_types = {
        norm_filter(name)
        for name, enabled in ring_types.items()
        if enabled
    }

    selected_materials = {
        norm_filter(name)
        for name, enabled in materials.items()
        if enabled
    }

    system_level_statuses = {
        "UNKNOWN_API_ERROR",
        "SYSTEM_NOT_FOUND",
        "NO_RINGS",
    }

    rows_by_system = {
        norm(system): []
        for system in systems
    }

    for row in raw_rows:
        rows_by_system.setdefault(
            norm(row["System"]),
            [],
        ).append(row)

    filtered = []

    for system in systems:
        source_rows = rows_by_system.get(
            norm(system),
            [],
        )

        kept = []

        for row in source_rows:
            status = row["Status"]

            if status in system_level_statuses:
                kept.append(row)
                continue

            # Ring type filter.
            if selected_ring_types:
                if (
                    norm_filter(
                        row["Ring Type"]
                    )
                    not in selected_ring_types
                ):
                    continue

            # Reserve filter.
            if only_pristine:
                if norm_filter(
                    row["Reserve Level"]
                ) != "pristine":
                    continue

            # Material filter:
            # if one or more materials are selected, only actual
            # HOTSPOT_FOUND rows matching those materials survive.
            if selected_materials:
                if status != "HOTSPOT_FOUND":
                    continue

                if (
                    norm_filter(
                        row["Material"]
                    )
                    not in selected_materials
                ):
                    continue

            kept.append(row)

        if kept:
            filtered.extend(kept)
        else:
            filtered.append(
                empty_hotspot_status(
                    system,
                    "NO_MATCHING_HOTSPOTS",
                )
            )

    return filtered


def clean_hotspot_rows(raw_rows):
    clean_rows = []

    previous_system = None
    previous_ring_key = None

    for original in raw_rows:
        row = dict(original)

        system = row["System"]
        body = row["Body"]
        ring = row["Ring"]

        ring_key = (
            system,
            body,
            ring,
        )

        if system == previous_system:
            row["System"] = ""
        else:
            previous_system = system
            previous_ring_key = None

        if (
            ring
            and
            ring_key == previous_ring_key
        ):
            row["Status"] = ""
            row["Body"] = ""
            row["Ring"] = ""
            row["Ring Type"] = ""
            row["Reserve Level"] = ""
            row["LS Distance"] = ""

        elif ring:
            previous_ring_key = ring_key

        clean_rows.append(row)

    return clean_rows


# ============================================================
# PLANETS
# ============================================================

PLANET_HEADERS = [
    "System",
    "Status",
    "Body",
    "Planet Type",
    "Landable",
    "Volcanism",
    "LS Distance",
]


def empty_planet_status(system, status):
    return {
        "System": system,
        "Status": status,
        "Body": "",
        "Planet Type": "",
        "Landable": "",
        "Volcanism": "",
        "LS Distance": "",
    }


def build_planet_rows(
    systems,
    bodies_by_system,
    unresolved,
):
    unresolved_keys = {
        norm(x)
        for x in unresolved
    }

    raw_rows = []

    for system in systems:
        key = norm(system)

        if key in unresolved_keys:
            raw_rows.append(
                empty_planet_status(
                    system,
                    "UNKNOWN_API_ERROR",
                )
            )
            continue

        bodies = bodies_by_system.get(
            key,
            [],
        )

        if not bodies:
            raw_rows.append(
                empty_planet_status(
                    system,
                    "SYSTEM_NOT_FOUND",
                )
            )
            continue

        planets = []

        for body in bodies:
            body_type = norm(
                body.get("type", "")
            )

            if body_type != "planet":
                continue

            # Spansh Body Search uses "is_landable".
            # Keep "landable" as a fallback for compatibility.
            landable_value = body.get(
                "is_landable",
                body.get(
                    "landable",
                    None,
                ),
            )

            if landable_value is True:
                landable = "Yes"
            elif landable_value is False:
                landable = "No"
            else:
                landable = ""

            planets.append({
                "System": system,
                "Status": "PLANET_FOUND",
                "Body": str(
                    body.get("name", "")
                    or ""
                ).strip(),
                "Planet Type": str(
                    body.get("subtype", "")
                    or ""
                ).strip(),
                "Landable": landable,
                "Volcanism": str(
                    body.get("volcanism_type", "")
                    or ""
                ).strip(),
                "LS Distance":
                    body.get(
                        "distance_to_arrival",
                        "",
                    ),
            })

        if planets:
            raw_rows.extend(planets)
        else:
            raw_rows.append(
                empty_planet_status(
                    system,
                    "NO_PLANETS",
                )
            )

    return raw_rows


def planet_type_matches(value, selected_types):
    """
    Map Spansh planet subtype names to the compact UI categories.
    When no category is selected, every planet type is accepted.
    """
    active = {
        name
        for name, enabled
        in selected_types.items()
        if enabled
    }

    if not active:
        return True

    subtype = norm_filter(value)

    aliases = {
        "icy": {
            "icy body",
            "icy",
        },
        "metal rich": {
            "metal rich body",
            "metal rich",
        },
        "high metal content": {
            "high metal content world",
            "high metal content body",
            "high metal content",
        },
        "rocky": {
            "rocky body",
            "rocky",
        },
        "rocky ice": {
            "rocky ice world",
            "rocky ice body",
            "rocky ice",
        },
    }

    for category in active:
        accepted = aliases.get(
            category,
            {category},
        )

        if subtype in accepted:
            return True

    return False


def filter_planet_rows(
    systems,
    raw_rows,
    only_landables,
    selected_types,
):
    system_level_statuses = {
        "UNKNOWN_API_ERROR",
        "SYSTEM_NOT_FOUND",
        "NO_PLANETS",
    }

    rows_by_system = {
        norm(system): []
        for system in systems
    }

    for row in raw_rows:
        rows_by_system.setdefault(
            norm(row["System"]),
            [],
        ).append(row)

    filtered = []

    has_type_filters = any(
        selected_types.values()
    )

    for system in systems:
        source_rows = rows_by_system.get(
            norm(system),
            [],
        )

        kept = []
        system_status_rows = []

        for row in source_rows:
            if row["Status"] in system_level_statuses:
                system_status_rows.append(row)
                continue

            if row["Status"] != "PLANET_FOUND":
                continue

            if (
                only_landables
                and row["Landable"] != "Yes"
            ):
                continue

            if not planet_type_matches(
                row["Planet Type"],
                selected_types,
            ):
                continue

            kept.append(row)

        if kept:
            filtered.extend(kept)
            continue

        if system_status_rows:
            filtered.extend(system_status_rows)
            continue

        if only_landables and has_type_filters:
            status = "NO_MATCHING_LANDABLE_PLANETS"
        elif only_landables:
            status = "NO_LANDABLE_PLANETS"
        elif has_type_filters:
            status = "NO_MATCHING_PLANET_TYPES"
        else:
            status = "NO_PLANETS"

        filtered.append(
            empty_planet_status(
                system,
                status,
            )
        )

    return filtered



def clean_planet_rows(raw_rows):
    clean_rows = []

    previous_system = None

    for original in raw_rows:
        row = dict(original)

        system = row["System"]

        if system == previous_system:
            row["System"] = ""
            row["Status"] = ""
        else:
            previous_system = system

        clean_rows.append(row)

    return clean_rows


# ============================================================
# SHEET MATRIX
# ============================================================

def row_to_values(row, headers):
    return [
        row.get(header, "")
        for header in headers
    ]


def build_sheet_values(
    hotspots_enabled,
    planets_enabled,
    hotspot_rows,
    planet_rows,
):
    hotspot_block = []
    planet_block = []

    if hotspots_enabled:
        hotspot_block = [
            HOTSPOT_HEADERS
        ] + [
            row_to_values(
                row,
                HOTSPOT_HEADERS,
            )
            for row in hotspot_rows
        ]

    if planets_enabled:
        planet_block = [
            PLANET_HEADERS
        ] + [
            row_to_values(
                row,
                PLANET_HEADERS,
            )
            for row in planet_rows
        ]

    if (
        hotspots_enabled
        and planets_enabled
    ):
        height = max(
            len(hotspot_block),
            len(planet_block),
        )

        result = []

        for index in range(height):
            left = (
                hotspot_block[index]
                if index < len(hotspot_block)
                else [""] * len(
                    HOTSPOT_HEADERS
                )
            )

            right = (
                planet_block[index]
                if index < len(planet_block)
                else [""] * len(
                    PLANET_HEADERS
                )
            )

            # One empty separator column between blocks.
            result.append(
                left + [""] + right
            )

        return result

    if hotspots_enabled:
        return hotspot_block

    return planet_block


# ============================================================
# CSV
# ============================================================

def write_dict_csv(
    path,
    headers,
    rows,
):
    with Path(path).open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=headers,
        )

        writer.writeheader()
        writer.writerows(rows)


def write_matrix_csv(
    path,
    values,
):
    with Path(path).open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerows(values)


# ============================================================
# GOOGLE SHEET OUTPUT
# ============================================================

def auto_resize_result_columns():
    """
    Use Google Sheets' native column auto-resize, equivalent to
    manually double-clicking a column border, then add 2 px.

    Result areas:
      E:M
      O:U

    N stays a fixed separator.
    """
    require_google()

    # --------------------------------------------------------
    # 1) Native Google Sheets auto-resize
    # --------------------------------------------------------

    resize_requests = [
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "dimension":
                        "COLUMNS",
                    "startIndex": 4,   # E
                    "endIndex": 13,    # M inclusive
                }
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "dimension":
                        "COLUMNS",
                    "startIndex": 14,  # O
                    "endIndex": 21,    # U inclusive
                }
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "dimension":
                        "COLUMNS",
                    "startIndex": 13,  # N
                    "endIndex": 14,
                },
                "properties": {
                    "pixelSize": 28,
                },
                "fields":
                    "pixelSize",
            }
        },
    ]

    (
        SHEETS_SERVICE
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests":
                    resize_requests
            },
        )
        .execute()
    )

    # --------------------------------------------------------
    # 2) Read the actual native widths Google calculated
    # --------------------------------------------------------

    metadata = (
        SHEETS_SERVICE
        .spreadsheets()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            ranges=[
                f"'{SHEET_NAME}'!E:U"
            ],
            includeGridData=True,
            fields=(
                "sheets.data."
                "startColumn,"
                "sheets.data."
                "columnMetadata.pixelSize"
            ),
        )
        .execute()
    )

    sheets = metadata.get(
        "sheets",
        [],
    )

    if not sheets:
        return

    data_blocks = (
        sheets[0]
        .get(
            "data",
            [],
        )
    )

    if not data_blocks:
        return

    data = data_blocks[0]

    start_column = int(
        data.get(
            "startColumn",
            4,
        )
    )

    column_metadata = data.get(
        "columnMetadata",
        [],
    )

    # --------------------------------------------------------
    # 3) Add exactly 2 px to each result column
    # --------------------------------------------------------

    padding_requests = []

    result_columns = set(
        list(range(4, 13))
        + list(range(14, 21))
    )

    for offset, metadata_item in enumerate(
        column_metadata
    ):
        absolute_col = (
            start_column
            + offset
        )

        if absolute_col not in result_columns:
            continue

        pixel_size = metadata_item.get(
            "pixelSize"
        )

        if pixel_size is None:
            continue

        # All result columns use native width + 5 px.
        extra_padding = 5

        padding_requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId":
                        HOTSPOTS_SHEET_ID,
                    "dimension":
                        "COLUMNS",
                    "startIndex":
                        absolute_col,
                    "endIndex":
                        absolute_col + 1,
                },
                "properties": {
                    "pixelSize":
                        int(pixel_size)
                        + extra_padding,
                },
                "fields":
                    "pixelSize",
            }
        })

    if padding_requests:
        (
            SHEETS_SERVICE
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={
                    "requests":
                        padding_requests
                },
            )
            .execute()
        )



def write_sheet(values):
    require_google()

    ensure_sheet_capacity(
        max(len(values) + 5, 200),
        21,
    )

    # Clear only the result area. Filters, systems and notes remain untouched.
    (
        SHEETS_SERVICE
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!E:U",
            body={},
        )
        .execute()
    )

    if values:
        write_values(
            SHEETS_SERVICE,
            SPREADSHEET_ID,
            f"'{SHEET_NAME}'!E1",
            values,
        )

    auto_resize_result_columns()

    return {
        "status": "ok",
        "rows": max(len(values) - 1, 0),
    }


# ============================================================
# SUMMARY
# ============================================================

def build_summary(
    config,
    hotspot_rows,
    planet_rows,
    unresolved,
):
    hotspot_records = [
        row
        for row in hotspot_rows
        if row["Status"] == "HOTSPOT_FOUND"
    ]

    hotspot_total = sum(
        int(
            row["Hotspot Count"]
            or 0
        )
        for row in hotspot_records
    )

    planets_found = [
        row
        for row in planet_rows
        if row["Status"] == "PLANET_FOUND"
    ]

    selected_ring_types = [
        name
        for name, enabled
        in config["ring_types"].items()
        if enabled
    ]

    selected_materials = [
        name
        for name, enabled
        in config["materials"].items()
        if enabled
    ]

    selected_planet_types = [
        name
        for name, enabled
        in config.get(
            "planet_types",
            {},
        ).items()
        if enabled
    ]

    return {
        "systems_input":
            len(config["systems"]),

        "hotspots_enabled":
            config["hotspots_enabled"],

        "planets_enabled":
            config["planets_enabled"],

        "ring_type_filters":
            selected_ring_types,

        "material_filters":
            selected_materials,

        "only_pristine":
            config["only_pristine"],

        "only_landables":
            config["only_landables"],

        "planet_type_filters":
            selected_planet_types,

        "only_positive_results":
            config.get(
                "only_positive_results",
                False,
            ),

        "faction_name":
            config.get("faction_name", ""),

        "power_name":
            config.get("power_name", ""),

        "power_state_filters":
            [
                state
                for state, enabled
                in config.get(
                    "power_states",
                    {},
                ).items()
                if enabled
            ],

        "system_source":
            (
                "spansh_system_filters"
                if (
                    config.get("faction_name")
                    or config.get("power_name")
                )
                else "manual_list"
            ),

        "hotspot_material_records_after_filters":
            len(hotspot_records)
            if config["hotspots_enabled"]
            else 0,

        "hotspots_total_count_after_filters":
            hotspot_total
            if config["hotspots_enabled"]
            else 0,

        "planets_found_after_filters":
            len(planets_found)
            if config["planets_enabled"]
            else 0,

        "unresolved_system_queries":
            len(unresolved),

        "unresolved_systems":
            unresolved,
    }


def handle_no_systems_matching_filters(
    faction_name,
    power_name,
    selected_power_states,
    config,
):
    """
    Graceful non-error outcome when Spansh returns no systems.

    - Does NOT touch C2:C.
    - Replaces old results with a clear status.
    - Ends the workflow successfully.
    """
    states_text = (
        ", ".join(selected_power_states)
        if selected_power_states
        else ""
    )

    sheet_values = [
        [
            "Status",
            "Faction",
            "Power",
            "Power States",
        ],
        [
            "NO_SYSTEMS_MATCHING_FILTERS",
            faction_name,
            power_name,
            states_text,
        ],
    ]

    write_matrix_csv(
        "spansh_results.csv",
        sheet_values,
    )

    summary = {
        "status":
            "NO_SYSTEMS_MATCHING_FILTERS",
        "faction_name":
            faction_name,
        "power_name":
            power_name,
        "power_state_filters":
            selected_power_states,
        "system_source":
            "spansh_system_filters",
        "systems_found":
            0,
        "manual_system_list_preserved":
            True,
        "hotspots_enabled":
            config["hotspots_enabled"],
        "planets_enabled":
            config["planets_enabled"],
    }

    Path(
        "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print(
        "Writing NO_SYSTEMS_MATCHING_FILTERS "
        "to Google Sheet..."
    )

    result = write_sheet(
        sheet_values
    )

    print(
        "Sheet updated: "
        f"{result.get('rows', 0)} "
        "data rows."
    )


def handle_system_list_only(
    systems,
    faction_name,
    power_name,
    selected_power_states,
):
    """
    Hotspots OFF + Planets OFF:
    only update/report the system list.
    """
    states_text = (
        ", ".join(selected_power_states)
        if selected_power_states
        else "ALL"
    )

    sheet_values = [
        [
            "Status",
            "Systems",
            "Faction",
            "Power",
            "Power States",
        ],
        [
            "SYSTEM_LIST_UPDATED",
            len(systems),
            faction_name,
            power_name,
            (
                states_text
                if power_name
                else ""
            ),
        ],
    ]

    write_matrix_csv(
        "spansh_results.csv",
        sheet_values,
    )

    summary = {
        "status":
            "SYSTEM_LIST_UPDATED",
        "systems_found":
            len(systems),
        "faction_name":
            faction_name,
        "power_name":
            power_name,
        "power_state_filters":
            (
                selected_power_states
                if power_name
                else []
            ),
        "hotspots_enabled":
            False,
        "planets_enabled":
            False,
    }

    Path(
        "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print(
        "Writing system-list-only status "
        "to Google Sheet..."
    )

    write_sheet(
        sheet_values
    )


def handle_no_action_selected():
    """
    No Hotspots, no Planets, no Faction and no Power:
    preserve the current system list and show a friendly status.
    """
    sheet_values = [
        [
            "Status",
            "Message",
        ],
        [
            "NO_ACTION_SELECTED",
            (
                "Enable Hotspots or Planets, "
                "or enter a Faction name or Power."
            ),
        ],
    ]

    write_matrix_csv(
        "spansh_results.csv",
        sheet_values,
    )

    summary = {
        "status":
            "NO_ACTION_SELECTED",
        "hotspots_enabled":
            False,
        "planets_enabled":
            False,
        "manual_system_list_preserved":
            True,
    }

    Path(
        "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print(
        "Writing NO_ACTION_SELECTED "
        "to Google Sheet..."
    )

    write_sheet(
        sheet_values
    )


# ============================================================
# MAIN
# ============================================================

def main(cancel_event=None):
    check_cancel(cancel_event)

    config = get_sheet_input()

    faction_name = config.get(
        "faction_name",
        "",
    ).strip()

    power_name = config.get(
        "power_name",
        "",
    ).strip()

    selected_power_states = [
        state
        for state, enabled
        in config.get(
            "power_states",
            {},
        ).items()
        if enabled
    ]

    # Power State checkboxes are intentionally ignored
    # when Power itself is empty.
    effective_power_states = (
        selected_power_states
        if power_name
        else []
    )

    if faction_name or power_name:
        systems = (
            search_systems_by_filters(
                faction_name,
                power_name,
                effective_power_states,
                cancel_event=cancel_event,
            )
        )

        check_cancel(cancel_event)

        if not systems:
            handle_no_systems_matching_filters(
                faction_name,
                power_name,
                effective_power_states,
                config,
            )
            return

        # Keep the new system list staged in memory until the scan is
        # ready to commit. This way STOP cannot leave a half-finished
        # body-result update in the Sheet.
        config["systems"] = systems

        # If both result modes are disabled, the requested job is only
        # to populate the system list. Commit it after one final cancel check.
        if (
            not config["hotspots_enabled"]
            and not config["planets_enabled"]
        ):
            check_cancel(cancel_event)
            write_systems_to_sheet(systems)
            print(
                "System list in Google Sheet updated "
                "from Spansh system filters."
            )
            handle_system_list_only(
                systems,
                faction_name,
                power_name,
                effective_power_states,
            )
            return

    else:
        systems = config["systems"]

        print(
            "Faction name and Power empty: "
            "using manual system list."
        )

        # Nothing at all selected: do not query Spansh bodies.
        if (
            not config["hotspots_enabled"]
            and not config["planets_enabled"]
        ):
            handle_no_action_selected()
            return

    print(
        f"Systems loaded: {len(systems)}"
    )

    print(
        f"Hotspots: "
        f"{config['hotspots_enabled']}"
    )

    print(
        f"Planets: "
        f"{config['planets_enabled']}"
    )

    print(
        "Faction filter: "
        + (
            faction_name
            or "NONE"
        )
    )

    print(
        "Power filter: "
        + (
            power_name
            or "NONE"
        )
    )

    print(
        "Power State filters: "
        + (
            ", ".join(
                effective_power_states
            )
            if effective_power_states
            else "ALL / IGNORED"
        )
    )

    print(
        "Ring type filters: "
        + (
            ", ".join(
                name
                for name, enabled
                in config["ring_types"].items()
                if enabled
            )
            or "ALL"
        )
    )

    print(
        "Material filters: "
        + (
            ", ".join(
                name
                for name, enabled
                in config["materials"].items()
                if enabled
            )
            or "ALL"
        )
    )

    print(
        f"Only pristine: "
        f"{config['only_pristine']}"
    )

    print(
        f"Only landables: "
        f"{config['only_landables']}"
    )

    print(
        "Planet type filters: "
        + (
            ", ".join(
                name
                for name, enabled
                in config["planet_types"].items()
                if enabled
            )
            or "ALL"
        )
    )

    print(
        f"Only positive results: "
        f"{config['only_positive_results']}"
    )

    bodies_by_system, unresolved = (
        query_all_systems(
            systems,
            cancel_event=cancel_event,
        )
    )

    check_cancel(cancel_event)

    hotspot_filtered = []
    hotspot_clean = []

    planet_filtered = []
    planet_clean = []

    if config["hotspots_enabled"]:
        hotspot_raw = build_hotspot_rows(
            systems,
            bodies_by_system,
            unresolved,
        )

        hotspot_filtered = (
            filter_hotspot_rows(
                systems,
                hotspot_raw,
                config["ring_types"],
                config["materials"],
                config["only_pristine"],
            )
        )

        if config["only_positive_results"]:
            hotspot_filtered = [
                row
                for row in hotspot_filtered
                if row["Status"] == "HOTSPOT_FOUND"
            ]

        hotspot_clean = (
            clean_hotspot_rows(
                hotspot_filtered
            )
        )

        write_dict_csv(
            "spansh_hotspots.csv",
            HOTSPOT_HEADERS,
            hotspot_clean,
        )

    if config["planets_enabled"]:
        planet_raw = build_planet_rows(
            systems,
            bodies_by_system,
            unresolved,
        )

        planet_filtered = (
            filter_planet_rows(
                systems,
                planet_raw,
                config["only_landables"],
                config["planet_types"],
            )
        )

        if config["only_positive_results"]:
            planet_filtered = [
                row
                for row in planet_filtered
                if row["Status"] == "PLANET_FOUND"
            ]

        planet_clean = (
            clean_planet_rows(
                planet_filtered
            )
        )

        write_dict_csv(
            "spansh_planets.csv",
            PLANET_HEADERS,
            planet_clean,
        )

    sheet_values = build_sheet_values(
        config["hotspots_enabled"],
        config["planets_enabled"],
        hotspot_clean,
        planet_clean,
    )

    write_matrix_csv(
        "spansh_results.csv",
        sheet_values,
    )

    summary = build_summary(
        config,
        hotspot_filtered,
        planet_filtered,
        unresolved,
    )

    Path(
        "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    check_cancel(cancel_event)

    print()
    print(
        "Writing results "
        "to Google Sheet..."
    )

    # Commit begins here. Once this point is reached, finish both Sheet
    # writes atomically from the user's point of view instead of stopping
    # between the system list and the result tables.
    if faction_name or power_name:
        write_systems_to_sheet(systems)
        print(
            "System list in Google Sheet updated "
            "from Spansh system filters."
        )

    result = write_sheet(
        sheet_values
    )

    print(
        "Sheet updated: "
        f"{result.get('rows', 0)} "
        "data rows."
    )


if __name__ == "__main__":
    try:
        init_local_google()

        update_finder_status(
            "RUNNING"
        )

        main()

        update_finder_status(
            "COMPLETED"
        )

        print()
        print("Hotspots Finder completed successfully.")

    except Exception as exc:
        try:
            if SHEETS_SERVICE and SPREADSHEET_ID:
                update_finder_status(
                    "ERROR"
                )
        except Exception as status_error:
            print(
                "Could not update Sheet status to ERROR: "
                f"{status_error}"
            )

        print()
        print(f"ERROR: {exc}")
        raise
