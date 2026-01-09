# HRT Journey Tracker

Ive made this small collection of **PySide6 (Qt) desktop apps** to help track different parts of an HRT journey (logging, journaling, cycle tracking, resources, and voice/pitch practice). Each app is self-contained, stores data locally, and includes a documented workflow.

Once all apps are functional and cohesive I plan to bundle and biuld an all in one app including everything in this project. I also would like to make a secure web version.

## What’s included (at a glance)
- **TrackMyHRT**: medication + symptom tracking with exports
- **Journey Journal**: daily journaling with themes, table view, and exports
- **Cycle Tracker**: cycle/bleed logging with summary stats and an estimated next start date
- **Resource Manager**: save/search/open useful links (title + URL)
- **Voice Trainer (prototype)**: record/load audio and estimate pitch (Hz)

## Quick start (from source)
> Each app can be run on its own.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -U pip
py -m pip install PySide6
```

Then run an app (examples):

```powershell
py .\HRT.py
py .\JJ.py
py .\C-T.py
```

> Some apps have extra dependencies (see the app’s `.md` doc, especially Voice Trainer).

## Apps included

### TrackMyHRT (`HRT.py`)
Log HRT entries with **date/time**, one or more **medications** (name/dose/unit/route/time), optional **mood/energy/symptoms/libido** (multi-select), and **notes**.

Notable behavior/features:
- Saving requires **at least one medication name**
- Built-in viewer: **View / Details (raw JSON) / Delete / Export**
- Export formats: `.jsonl`, `.json`, `.txt`, `.md`
- Supports migrating older **JSONL → JSON** storage if detected

- Data storage: `storage/entries.json` (next to `HRT.py` or bundled `.exe`)
- Run: `py .\HRT.py`
- Details: [TrackMyHRT/TrackMyHRT.md](TrackMyHRT/TrackMyHRT.md)

### Journey Journal (`JJ.py`)
Create a **daily journal entry** (date, mood, symptoms, a few dropdown fields, notes), browse entries in a table, delete single/multiple, export (`.json/.md/.txt`), and toggle **Dark/Light** theme (persisted via `QSettings`).

Notable behavior/features:
- Enforces **one entry per date** (prompts to replace)
- Refuses to save fully empty entries (prevents blank rows)
- Exports to: `.json`, `.md` (formatted), `.txt` (plain blocks)
- Includes a “view entries” dialog with **Refresh / View / Details / Delete**
- Theme menu: **View → Theme → Dark/Light**

- Data storage: `storage/j_j.json`
- Run: `py .\JJ.py`
- Details: [Journey Journal/Journal Journy.md](Journey%20Journal/Journal%20Journy.md)

### Cycle Tracker (`C-T.py`)
Log cycle/bleed entries, view/edit/delete them in a sortable table, and see summary stats: **average cycle length**, **average bleed length**, and an **estimated next start**. Includes Dark/Light theme via `QSettings`, plus hover tooltips for tags/notes.

Notable behavior/features:
- Add/Edit validates that **end date >= start date**
- Tags are comma-separated and are trimmed + de-duplicated
- Sorting-safe row selection (stores an index in `Qt.UserRole`)
- Summary shows “not enough entries” until there are at least 2 cycles

- Data storage: `data/cycle_entries.json` (next to the script)
- Run: `py .\C-T.py`
- Details: [Cycle Tracker/Cycle Tracker.md](Cycle%20Tracker/Cycle%20Tracker.md)

### Resource Manager (`main.py`) — Link Manager
Save and manage useful **Title + URL** resources with fast search/filtering and quick actions: open in browser, copy URL, remove, clear all.

Notable behavior/features:
- Instant filtering matches **title or URL** (case-insensitive)
- Normalizes URLs (e.g. `example.com` → `https://example.com`)
- Accepts only `http://` and `https://`
- Context menu + double-click open

- Data storage: handled by `data.storage.LinkStorage` (see app docs)
- Run (from `Resource manager` folder): `py .\main.py`
- Details: [Resource manager/Resource manager.md](Resource%20manager/Resource%20manager.md)

### Voice Trainer — Prototype (`V-T.py`)
Record a short mono clip (or load an audio file), estimate pitch using **aubio YIN**, and display an **average pitch (median) in Hz**. Uses a worker thread for recording so the UI stays responsive.

Notable behavior/features:
- Can analyze either `last_recording.wav` or any chosen file
- Filters pitch values to a human-voice range (~50–500 Hz) and ignores silence
- Designed as a prototype for future integration

- Data storage: uses a working file `last_recording.wav` next to the script (no entries DB)
- Run: `py .\V-T.py`
- Details: [Voice-Trainer/Voice Trainer.md](Voice%20Trainer/Voice%20Trainer.md)

## Project direction (planned)
- **Combine** these tools into one cohesive “all-in-one” desktop app once the individual apps stabilize
- Explore a **secure web version** later (after the desktop workflow and data model are solid)

## Notes
- These are desktop GUI apps built with **PySide6**; each app’s markdown file documents behavior, storage, and UI flows.
- If you bundle into an `.exe` (PyInstaller), storage paths are described per-app in the linked docs.
