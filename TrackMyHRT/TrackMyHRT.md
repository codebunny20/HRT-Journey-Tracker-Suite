# TrackMyHRT

A lightweight, local-first **HRT journey tracker** for logging medication dosing and optional daily context (mood, energy, symptoms, libido, notes). Built with **Python + PySide6 (Qt)**.

## What it does (overview)

TrackMyHRT lets you:
- Create a timestamped entry (date + time)
- Add one or more medication rows (name, dose, unit, route, time)
- Optionally record mood/energy/symptoms/libido (multi-select) and free-form notes
- Save entries locally to a simple **JSON** file (JSON array)
- Browse, view, delete, and export previously saved entries

All data is stored locally on your machine in the app’s `storage` folder.
The storage file will be created on your first entry save.

---

## Current features

### 1) Quick entry (Date / Time)
- **Date** field (format `YYYY-MM-DD`)
- **Time** field (format `HH:mm`)
- **Pick date…** opens a calendar dialog for selecting a date
- **Now** sets date and time to the current moment

### 2) Medications table
Each entry can contain multiple medication rows with:
- **Name** (dropdown + editable text; includes common HRT meds and “Other”)
- **Dose** (dropdown + editable text)
  - Accepts numeric values and also tolerant input like: `2`, `2.0`, `2 mg`, `2,5` (comma becomes dot)
  - On save, the app extracts the first number it finds and stores it as a numeric JSON `dose`
- **Unit** (dropdown + editable text; examples: `mg`, `mcg`, `mL`, etc.)
- **Route** (dropdown + editable text; examples: Oral, Sublingual, Transdermal, Injection IM/SC, etc.)
- **Time** (text in `HH:mm`)
  - Defaults to the entry’s top-level time when you add the row
  - If left blank, it falls back to the entry time during save
- **Add medication** adds a new row
- **Remove selected** deletes highlighted row(s)
- Completely empty rows are ignored when saving

**Validation rule:** You must provide **at least one medication name** (across all rows) to save an entry.

### 3) Mood / Energy / Symptoms / Libido / Notes
All optional:
- **Mood**: multi-select dropdown
- **Energy**: multi-select dropdown
- **Symptoms**: multi-select dropdown
- **Libido**: multi-select dropdown
- **Notes**: free-form multi-line text

> Stored format: mood/energy/symptoms/libido are saved as JSON **arrays of strings** (lists).  
> The app still displays older saved entries that used strings.

### 4) Saving
- **Save entry** appends a record to the data file
- Automatically stores:
  - `id` (unique id)
  - `created_at`, `updated_at`
  - `timestamp_local` (sortable string like `2025-12-29 14:05`)
  - `date` (`YYYY-MM-DD`)
  - `time` (`HH:mm`)
  - medications array
  - mood/energy/symptoms/libido/notes

### 5) Viewing & managing entries
Open **View entries** to see a table of saved entries:
- Sorted **newest first** (`timestamp_local` descending)
- Table shows:
  - Timestamp
  - A compact “Medications” summary string
  - Mood
  - Symptoms
  - Notes (as a preview column)

Actions:
- **Double-click** a row or click **View** to open a full, readable view
- **Details** shows the raw JSON for the entry
- **Delete** permanently removes the selected entry (with confirmation)
- **Export…** exports all loaded entries to:
  - JSON Lines (`.jsonl`)
  - JSON (`.json`)
  - Text (`.txt`)
  - Markdown (`.md`)

### 6) Theme
- Menu: **View → Theme → Dark/Light**
- Theme choice is saved via app settings.

### 7) Help screen
The **Help** button opens an in-app help dialog that summarizes:
- Date/time usage
- Medication entry rules and dose parsing examples
- Saving requirements
- How the viewer works
- Data location hint

### 8) Data location
Data is stored in an app-local folder:

- `storage/entries.json`

Legacy support:
- If `storage/entries.json` is empty/missing and `storage/entries.jsonl` exists, the app will **migrate** JSONL → JSON automatically (one-time best-effort).

You can see the exact path via:
- Menu: **File → Open data folder** (shows the full entries file path)

> Note: This app currently *shows* you where the data file is; it does not automatically open the folder in your file explorer.

---

## Data format

### Current storage format (JSON array)
Entries are stored as a single JSON file containing an **array** of entry objects.

Top-level fields:
- `id` (string)
- `created_at` (string, `YYYY-MM-DD HH:mm`)
- `updated_at` (string, `YYYY-MM-DD HH:mm`)
- `timestamp_local` (string, `YYYY-MM-DD HH:mm`)
- `date` (string, `YYYY-MM-DD`)
- `time` (string, `HH:mm`)
- `medications` (array of objects)
- `mood` (array of strings, optional)
- `energy` (array of strings, optional)
- `symptoms` (array of strings, optional)
- `libido` (array of strings, optional)
- `notes` (string, optional)

Medication object fields:
- `name` (string)
- `dose` (number; `0.0` if omitted/blank)
- `unit` (string)
- `route` (string)
- `time` (string, `HH:mm`)

### Legacy format (JSON Lines)
Older versions used:
- `storage/entries.jsonl` (one JSON object per line)

This is still supported for migration.

---

## Quick start (how to use)
1. Set **Date** and **Time** (or click **Now**).
2. In **Medications**, click **Add medication** if needed.
3. Fill at least one medication **Name** (required to save).
4. Optionally fill **Dose**, **Unit**, **Route**, **Time** per row.
5. Optionally select **Mood/Energy/Symptoms/Libido** and add **Notes**.
6. Click **Save entry**.
7. Click **View entries** to browse, inspect, delete, or export entries.

---

## Launcher (workspace)

If you’re using the workspace **Launcher** app, TrackMyHRT should appear automatically as a launch button.

The Launcher discovers apps by scanning workspace subfolders and selecting an “entry script” using this priority:
1) `<FolderName>.py` (name match is tolerant of spaces/`_`/`-`)  
2) `main.py` / `app.py` / `run.py`  
3) if only one `*.py` exists at the folder root, it uses that

If TrackMyHRT does not appear:
- Ensure `TrackMyHRT/HRT.py` exists and is the intended entrypoint
- Ensure the folder is not named to collide with an excluded directory name (like `storage`, `assets`, `build`, etc.)
- Ensure PySide6 is installed in the Python environment the Launcher is using

---

## Notes / limitations (current)
- Local storage only (no cloud sync).
- Delete is permanent (no undo).
- Dose parsing stores the first numeric value found in the dose field.
- Storage is a single JSON file (`entries.json`) written atomically (temp file + replace).
- Export produces JSON/JSONL/TXT/MD files, but does not change your stored data file.
