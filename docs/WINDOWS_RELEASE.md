# Public Windows release setup

This is a **maintainer-only** procedure. Users download the Windows assets and authorize their own Google accounts; they do not create OAuth clients.

## Required real OAuth client

1. In Google Cloud, select the project for **ED Hotspots & Landables Finder** and enable the Google Sheets API.
2. Select or create an OAuth client of type **Desktop app**, intended for distribution with this application. Download its JSON. It must have an `installed` section, not a service-account key or a Web application client.
3. Check the OAuth audience and publishing/verification status. Public users must be allowed to authorize the app. A Testing audience limited to test users is not a general public rollout. The `spreadsheets` scope is sensitive; follow Google's applicable verification requirements. The JSON alone does not prove this project configuration.
4. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
5. Name the secret **GOOGLE_DESKTOP_OAUTH_JSON** and paste the complete downloaded JSON as its value. Do not add the JSON to the repository, an issue, a release asset or a screenshot.
6. Open **Actions → Build and publish Windows release → Run workflow**, using `main`.

[Repository Actions secrets](https://github.com/LittleJacket99/ED-Hotspots-Landables-Finder/settings/secrets/actions) · [Windows build workflow](https://github.com/LittleJacket99/ED-Hotspots-Landables-Finder/actions/workflows/release-windows.yml)

## What the workflow does

- Stops if the distribution secret is missing; validates genuine Desktop-client structure without printing the values.
- Compiles the v7.11 GUI and engine on Windows with Python 3.10 and PyInstaller.
- Checks the embedded `credentials.json` and `logo.png` against the build inputs, the icon/version resources and the Windows x64 executable format.
- Rejects any embedded `token.json` or `config.json`.
- Opens the actual GUI from a temporary directory, without sidecar credentials and with clean AppData. This checks startup; it does not perform an unattended Google sign-in.
- Packages the EXE, user README, release notes and checksums.
- Uploads `ED Hotspots & Landables Finder.exe`, `ED-Hotspots-Landables-Finder-v7.11-Windows.zip` and `SHA256.txt`; downloads them again and verifies their hashes.
- Handles GitHub's download-filename normalization and records the actual names in the external checksum file; the ZIP retains the exact application filename.
- Replaces the known source-only `v7.11` tag with the verified build commit and publishes the corrected release. A failed upload leaves a draft rather than a public incomplete Windows release.
- Removes the temporary credentials JSON from the runner after the build.

The OAuth client is deliberately embedded in the EXE. This is a distribution client, not an end-user token; native applications cannot keep their client data confidential. Token and configuration storage remain `%APPDATA%\HotspotsFinder` on each user's PC.

## Completion check

A green workflow alone does not establish Google's audience configuration. Download the published Windows ZIP on a clean Windows profile, launch the EXE with no Python or separate credentials file, authorize an intended Google account, connect a spreadsheet and run a small scan. Confirm local `token.json` and `config.json` appear under `%APPDATA%\HotspotsFinder`.

The app's earlier Windows test confirmed scanning and STOP. The distribution client still requires this real authorization check; no test credentials or fake successful sign-ins may substitute for it.

Google references: [Sheets scopes](https://developers.google.com/workspace/sheets/api/scopes), [Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app).
