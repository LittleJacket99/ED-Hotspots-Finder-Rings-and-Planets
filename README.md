# ED Hotspots & Landables Finder

A Windows companion for **Elite Dangerous** that searches multiple star systems for mining hotspots and planets, using **Spansh** for data and **Google Sheets** for inputs and results.

Search a manual list of systems, find systems through a **Faction**, or select a **Powerplay** power and Power States. Filter ring types, minerals and planet types; show landability, volcanism and arrival distance; use **Only positive results** to keep matching hotspot and planet results.

[Download Windows release](https://github.com/LittleJacket99/ED-Hotspots-Landables-Finder/releases/latest) · [v7.11 release notes](RELEASE_NOTES.md)

## Quick Start

1. Download the Windows `.exe` or `ED-Hotspots-Landables-Finder-v7.11-Windows.zip` from **Releases**. Extract the ZIP if you choose it.
2. Run **ED Hotspots & Landables Finder.exe**.
3. Authorize Google when prompted on your first spreadsheet connection. In v7.11 this prompt appears when you connect a sheet in the next step, rather than immediately on launch.
4. Use **Open Template** to make a copy, then **Connect / Change Sheet** to paste its link. You can also connect your own spreadsheet directly.
5. In Google Sheets, enter systems in the Systems column, or use **Faction name** / **Power** and the Power State checkboxes to obtain systems automatically.
6. Enable Hotspots and/or Planets and set the filters in the sheet.
7. Click **SCAN** in the desktop app.
8. View, sort, filter and edit the results in Google Sheets.

## Installation

The normal installation is **GitHub Releases → download → run the EXE**. You need Windows, an Internet connection and a Google account with edit access to the spreadsheet. The v7.11 app has been tested on Windows 11.

**Python, PyInstaller and a personal Google OAuth client are not required to run the public Windows build.** The application client and required resources are embedded in the EXE. `SHA256.txt` provides checksums for the Windows downloads.

Choose the Windows assets, not GitHub's automatically generated **Source code** archives. A release without an `.exe` asset is not yet a ready-to-use Windows release.

GitHub may simplify the standalone download's filename. The ZIP keeps the application name **ED Hotspots & Landables Finder.exe**.

The EXE is currently unsigned, so Windows SmartScreen may show an unknown-publisher warning. Check that your download came from this repository's Releases page before deciding whether to run it.

## Search options

- **Hotspots:** choose ring types and minerals, with an optional Only pristine filter.
- **Planets:** choose planet types and/or Only landables; results include landability and volcanism when supplied by Spansh.
- **Systems:** enter a manual list, or supply a Faction name and/or a Powerplay power to search systems automatically.
- **Power States:** refine a selected Power; these checkboxes are ignored when Power is empty.
- **Only positive results:** keep `HOTSPOT_FOUND` and `PLANET_FOUND` rows in their respective tables.

Spansh is a community-data source. Missing or outdated records can affect results; no match is not proof that a system has no such body or hotspot.

## Why Google Sheets?

Google Sheets is an intentional part of the tool, not just an export destination. After scanning, you can use normal Sheets features: custom filters, sorting, formulas, formatting, new columns and tabs, copies of results, and your own analyses. This lets you add useful workflows without changing the desktop program.

Keep the functional input cells and output columns in their expected positions. A new scan rewrites the generated result tables; use separate tabs or copies for calculations and edits you want to retain independently of later scans.

## Official template and spreadsheet connection

The official **ED Hotspots & Landables Finder** template supplies the input controls, output layout and reference tables.

| Button | Purpose |
| --- | --- |
| **Open Template** | Opens Google's copy page for the official spreadsheet. Make your own copy, then connect it in the app. |
| **Connect / Change Sheet** | Connects a spreadsheet by its link and remembers it. Your own Google Spreadsheet is also supported. |
| **Open My Sheet** | Opens the currently connected spreadsheet in your browser. |

When connecting, the app copies a missing **Hotspots Finder** tab from the official template, with a local setup fallback if that copy fails. Missing **Minerals Table** and **Volcanism Table** tabs are also copied. Existing tabs are not replaced wholesale, and existing reference tables are left untouched. The main tab's functional structure can still be repaired by the app.

### Customization and maintenance

| Button | Purpose |
| --- | --- |
| **Repair Sheet** | Repairs the functional layout and restores formatting, reapplying your saved style when present. |
| **Restore Official Style** | Removes the saved personal style and restores the official appearance. |
| **Save Current Style** | Saves the supported formatting areas as your personal style profile in the spreadsheet. |

These controls let you personalize the sheet while keeping recovery tools available. Column widths and row heights remain managed by the app and are not part of the saved style profile.

**Minerals Table** and **Volcanism Table** are informational reference tabs you can consult and edit freely. The maintenance buttons do not repair or overwrite these tables.

## Scan controls

- **SCAN** starts a search with the current spreadsheet settings.
- **STOP** requests a clean cancellation. The current request may need to finish first; a cancelled scan does **not publish a partial results table**. STOP is disabled once final results writing begins.
- The **progress bar and percentage** track query batches, not estimated time remaining.
- **Show details** opens the activity log, useful for progress and errors.
- **Compact / Expand** switches between the full window and the small scan panel. Scan controls remain available in compact mode.

## Google authorization and privacy

The first spreadsheet connection opens your browser for Google sign-in and consent. Each user authorizes their own Google account; the public Windows build already includes the application's Desktop OAuth client.

v7.11 requests exactly this scope:

`https://www.googleapis.com/auth/spreadsheets`

Google describes it as permission to view, edit, create and delete your Google Sheets spreadsheets. **This authorization is broader than just the spreadsheet you connect**, even though the app uses the selected spreadsheet and official template for its workflow. It does not request the full Google Drive scope. See [Google's scope documentation](https://developers.google.com/workspace/sheets/api/scopes).

The app stores these plain JSON files locally, separately from the EXE:

- `%APPDATA%\HotspotsFinder\token.json` — Google authorization tokens.
- `%APPDATA%\HotspotsFinder\config.json` — the selected spreadsheet configuration.

Updating or moving the EXE does not delete these files. Keep them private and never post them in issues or commit them to GitHub. System searches go to Spansh; spreadsheet operations go to Google. You can revoke the app's authorization in your Google account settings.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Google sign-in or consent fails | Use the intended Google account and complete the browser flow. If Google blocks the application's audience or verification status, report it to the maintainer; you do not need to create an OAuth client. |
| Expired or revoked authorization | Close the app, remove only `%APPDATA%\HotspotsFinder\token.json`, then reconnect to authorize again. Keep `config.json` to retain the sheet selection. |
| Spreadsheet cannot be connected | Check the link and your Google account's edit access. Use **Connect / Change Sheet** again. |
| Main sheet structure is damaged | Use **Repair Sheet**. To reset the appearance as well, use **Restore Official Style**. |
| A reference tab is missing | Reconnect the spreadsheet to copy the missing reference tab from the template. |
| Scan fails or finds unexpected results | Open **Show details**, check filters and system names, and retry a small scan. Include the error text when reporting an issue, without tokens or personal configuration. |
| SmartScreen warning | An unsigned executable may show an unknown publisher. Confirm the download source and compare the checksum. |

## Build from source / Development

These steps are for developers and release maintainers, not normal Windows users.

1. Install **Python 3.10** on Windows with the `py` launcher.
2. Clone or download the repository.
3. Place a genuine Google **Desktop app** OAuth client JSON beside `build_windows.bat`, named `credentials.json`. Enable the Google Sheets API for that project.
4. Run **build_windows.bat**. It validates build inputs, installs requirements and PyInstaller, builds the one-file EXE, verifies its embedded resources, then packages the release.
5. Find the executable in `dist\ED Hotspots & Landables Finder.exe` and the Windows ZIP/checksums in `release\`.

For a public build, use the application's **distribution** client. Its Google OAuth audience, publishing status and any required verification must permit the intended users. The JSON is embedded during compilation and must not be committed or uploaded separately. Desktop application client data is recoverable from an EXE; each user's authorization tokens remain local. See [Google's installed-app OAuth guidance](https://developers.google.com/identity/protocols/oauth2/native-app).

Maintainers can use the **Build and publish Windows release** workflow with the repository secret `GOOGLE_DESKTOP_OAUTH_JSON`. See [Windows release setup](docs/WINDOWS_RELEASE.md). The workflow stops if the secret is absent; it never substitutes example credentials.

### How it works

| Component | Role |
| --- | --- |
| `hotspots_finder_gui.py` | Desktop GUI, scan controls and activity log |
| `hotspots_engine.py` | Filters, queries, spreadsheet connection and result processing |
| Spansh APIs | System and body data |
| Google Sheets API | Spreadsheet inputs, results, formatting and template copying |
| `HotspotsFinder.spec` / PyInstaller | One-file Windows build with application resources |
| `package_release.ps1` | Windows release ZIP and SHA-256 checksums |

The template's Apps Script reference is in `docs/HotspotsFinder_Template_AppsScript_v9.gs`; it is not bundled into the EXE. Version-specific changes and test results are recorded in [RELEASE_NOTES.md](RELEASE_NOTES.md).
