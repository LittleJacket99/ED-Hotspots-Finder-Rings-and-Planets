# v7.11 — Windows release

A standalone Windows app for searching Elite Dangerous systems with Spansh and working with the results in Google Sheets.

- Mining hotspots and planets, including landability and volcanism where available.
- Manual system lists, Faction searches and Powerplay / Power State filters.
- Ring, mineral and planet filters, Only landables, Only pristine and Only positive results.
- Official spreadsheet template, editable reference tables and saved style / repair controls.
- Clean STOP cancellation without publishing a partial results table; Compact / Expand, progress and activity details.

## Windows downloads

Use the `.exe` directly or extract `ED-Hotspots-Landables-Finder-v7.11-Windows.zip`. The public Windows build embeds the application's Desktop OAuth client: no Python, PyInstaller or user-created OAuth client is needed. Each user authorizes their own Google account on first connection. `SHA256.txt` lists download checksums.

An EXE asset must actually be present before this is a ready-to-use Windows release. GitHub's Source code ZIP is for development.

The executable is unsigned. Windows SmartScreen may show an unknown-publisher warning. Token and configuration remain in `%APPDATA%\HotspotsFinder`, separately from the EXE.

## Validation

The v7.11 app was built and tested on Windows 11: spreadsheet connection, an 8-planet scan, and cancellation during a 361-system Powerplay search completed as expected. The public build workflow separately checks embedded resources, standalone GUI startup and the uploaded asset hashes. A new distribution OAuth client's audience and live authorization must also be checked by the maintainer.
