# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A set of Python scripts that pull data out of Autodesk Construction Cloud (ACC) through the Autodesk Platform Services (APS) REST APIs, flatten it to CSV, and upload the CSV back into a folder in the same ACC project's Docs. One script per data type (assets, submittals, submittal revisions, RFIs, issues, reviews), each looping over the projects listed in `config.py`.

There is no git repository, no `requirements.txt`, no build step, no linter and no test framework. Dependencies are `requests` and `pandas`, on Python 3.14.

## Commands

Everything must be run from the repository root: `token.json`, `logs/` and the `output/...` paths in `config.py` are all resolved relative to the current working directory, and imports like `from Modules.auth import ...` rely on the root being on `sys.path`.

```powershell
python main_data_connector.py       # Admin lookup CSVs -> Output/DataConnector/<project>/Extracted/
python main_assets.py
python main_submittals.py
python main_submittals_revision.py  # writes CSV only, no ACC upload
python main_rfi.py
python main_issues.py               # needs main_data_connector.py output first
python main_reviews.py              # uses main_data_connector.py output if present
```

`test_auth.py` and `test_admin_lookup.py` are manual smoke scripts, not pytest tests. Run them with `python test_auth.py`. Do not run `pytest` here: `test_auth.py` executes the OAuth flow at import time.

Every `main_*.py` makes live calls against production ACC projects and (except submittal revisions and the data connector) uploads a new file version to ACC. Running one is not a dry run.

## Architecture

Four layers, each `main_*.py` wiring one data type through them:

- `main_*.py` — entry point. Gets one access token, loops `PROJECTS`, skips projects whose `exports[<type>]` flag is falsy, calls the workflow.
- `Workflow/*_export.py` — orchestrates one project: fetch lookup maps, fetch records, call the CSV exporter, upload.
- `Services/*.py` — one module per APS endpoint family. Returns raw records or `{id: name}` lookup maps. Each module hand-rolls its own pagination and error handling.
- `Modules/` — shared infrastructure: `auth.py`, `logger.py`, `upload.py`, `csv_export.py`, `admin_lookup.py`.

### config.py drives everything

Each entry in `PROJECTS` has three dicts keyed by the same export-type names (`assets`, `submittals`, `submittal_revisions`, `issues`, `rfis`, `reviews`, `data_connector`):

- `exports` — on/off flag per type.
- `output_files` — local CSV path (for `data_connector`, a folder).
- `target_folders` — ACC folder URN the CSV is uploaded into.

Adding a project or enabling an export type means filling in all three. Workflows index these dicts directly (`project["output_files"]["issues"]`), so a missing key is a `KeyError`, not a skip. `urn:adsk.wipprod:fs.folder:co.CR211_ISSUE_FOLDER_ID` is a placeholder, not a real folder; it only appears under `data_connector`, which is never uploaded.

`config.py` also holds the APS client ID and secret in plain text, and `token.json` holds the live refresh token. Do not print, copy or commit either.

### Authentication

`Modules/auth.py` implements 3-legged OAuth. `get_access_token()` reads `token.json` and exchanges the refresh token; APS rotates refresh tokens, so the new one is written back on every call. If there is no token file or the refresh fails, it opens a browser and blocks on a one-shot HTTP server at `localhost:8080` waiting for the callback, so a first run (or a run after the refresh token has lapsed) needs an interactive user.

The token is fetched once per script run and passed down as a plain string. Nothing refreshes it mid-run.

### Project ID forms

`config.py` stores project IDs with the `b.` prefix. Which form an API wants varies:

- With `b.` prefix: Data Management (`Modules/upload.py`) and the Assets endpoints (`asset_api.py`, `categories.py`, `statues.py`, `custom_attributes.py`), which pass the ID through untouched.
- Without prefix: Submittals, RFIs, Issues, Reviews, Admin project users, Data Connector. Each of these service modules strips it with its own local `normalize_project_id` / `normalize_id`.

Pass the raw config value into service functions and let them normalize. A new service module needs to make this choice itself.

### Resolving IDs to names

Most of the code exists to turn opaque IDs into readable columns. There are two independent sources:

- `Services/project_users_api.get_project_users` — live call returning `{id: name}`, keyed by both the Autodesk ID and the project user ID. Used by submittals, RFIs and issues for user fields.
- `Modules/admin_lookup.AdminLookup` — offline, built from the `admin_*.csv` files that `main_data_connector.py` downloads. Issue assignees and watchers can be a user, a company or a role, and issues reference companies and roles by `company_oxygen_id` / `role_oxygen_id`, which only the Data Connector extract exposes. `resolve_assignee(id, type)` dispatches on `assignedToType`. Each record is registered under every identifier it has, so lookups work regardless of which ID form the API returned.

This makes the Data Connector run a prerequisite: `Workflow/issue_export.py` raises if `AdminLookup` cannot be built, while `Workflow/reviews_export.py` degrades to embedded names and raw IDs. The extract is a point-in-time snapshot, so names for users or companies added since the last `main_data_connector.py` run fall back to the raw ID.

`AdminLookup.find_csv_file` matches by substring over a recursive glob and takes the most recently modified hit, so `admin_users` also matches `admin_project_users.csv` and friends. Changing file names or adding lookups needs care here.

### CSV flattening

`Modules/csv_export.py` holds a `flatten_*` / `export_*_to_csv` pair per data type. The shared conventions:

- Iterate every key the API returned, so unknown fields pass through as columns rather than being dropped.
- Keep the raw ID column and add a readable sibling (`statusId` + `status`, `createdBy` + `createdByName`).
- Expand custom attributes into one column per attribute, named from the definition map, falling back to `custom_<id>`.
- Serialize remaining dicts and lists to a string.
- Write with `encoding="utf-8-sig"` so Excel opens them correctly.

Reviews are the exception: `flatten_review` lives in `Services/reviews_api.py` and `csv_export.py` imports it.

### Upload to ACC

`Modules/upload.upload_csv_to_acc` looks for an item with the same display name in the target folder, creates a storage object, does a single-part signed S3 upload, then creates either a new version of the existing item or a new item. Re-running an export therefore versions the existing file rather than duplicating it, and the output file's basename is the identity of the file in ACC.

### Rate limiting and pacing

- `UPLOAD_INTERVAL_SECONDS` (180) is slept between projects in the assets, submittals, RFI and issues scripts.
- Only `issues_api.py`, `rfi_api.py` and `reviews_api.get_review_workflow` retry on 429/5xx. The other service modules raise on the first non-200.
- Per-record fan-out calls are the slow part: one detail call per RFI (sequential), one workflow call per review (`max_workers=1` plus a 0.5 s sleep, deliberately throttled), one revisions call per submittal (`MAX_WORKERS = 5` threads).
- Data Connector jobs are asynchronous: create a one-time request for the `admin` service group, poll every 15 s for up to 30 minutes, then download and unzip.

### Logging

`Modules/logger.write_log` prints and appends to `logs/YYYYMMDD.log`. The assets, submittals, RFI and issues paths use it; the data connector, submittal revisions and most service modules use bare `print`, so their output is not in the log files.

## Things that look wrong but are load-bearing

- `Services/statues.py` is the asset statuses module. The filename is misspelled and imported under that name.
- `config.py` writes to `output/...` while the directory on disk is `Output/`. This works because Windows paths are case-insensitive.
- `Output/` and `logs/` contain real project data (names, emails, companies). `Output/DataConnector/*/Extracted/` is vendor-generated (schemas, HTML docs, SQL DDL) and gets overwritten on each run.
