# TrackMyHRT

A lightweight, local-first **HRT journey tracker** for logging medication dosing and optional daily context (mood, symptoms, libido, notes). Built with **Python + PySide6 (Qt)**.

## What it does (overview)

TrackMyHRT lets you:
- Create a timestamped entry (date + time)
- Add one or more medication rows (name, dose, unit, route, time)
- Optionally record mood, symptoms, libido, and free-form notes
- Save entries locally to a simple **JSON Lines** file (`.jsonl`)
- Browse, view, and delete previously saved entries

All data is stored locally on your machine in the app’s `storage` folder.
The `storage` file will be created on your first entrie save.
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

### 3) Mood / Symptoms / Libido / Notes
All optional:
- **Mood**: editable dropdown (type or pick)
- **Symptoms**: editable dropdown (type or pick)
- **Libido**: editable dropdown (type or pick)
- **Notes**: free-form multi-line text

### 4) Saving
- **Save entry** appends a record to the data file as one JSON object per line (JSONL)
- Automatically stores:
  - `timestamp_local` (sortable string like `2025-12-29 14:05`)
  - `date` (`YYYY-MM-DD`)
  - `time` (`HH:mm`)
  - medications array
  - mood/symptoms/libido/notes

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

### 6) Help screen
The **Help** button opens an in-app help dialog that summarizes:
- Date/time usage
- Medication entry rules and dose parsing examples
- Saving requirements
- How the viewer works
- Data location hint

### 7) Data location
Data is stored in an app-local folder:

- `storage/entries.jsonl`

You can see the exact path via:
- Menu: **File → Open data folder** (shows the full entries file path)

> Note: This app currently *shows* you where the data file is; it does not automatically open the folder in your file explorer.

---

## Data format (JSON Lines)

Entries are stored as **JSON Lines (JSONL)**:
- One JSON object per line
- Easy to append, diff, and parse

### Schema (current)
Top-level fields:
- `timestamp_local` (string, `YYYY-MM-DD HH:mm`)
- `date` (string, `YYYY-MM-DD`)
- `time` (string, `HH:mm`)
- `medications` (array of objects)
- `mood` (string, optional)
- `symptoms` (string, optional)
- `libido` (string, optional)
- `notes` (string, optional)

Medication object fields:
- `name` (string)
- `dose` (number; `0.0` if omitted/blank)
- `unit` (string)
- `route` (string)
- `time` (string, `HH:mm`)

### Example record
```json
{
  "timestamp_local": "2025-12-29 14:05",
  "date": "2025-12-29",
  "time": "14:05",
  "medications": [
    { "name": "Estradiol", "dose": 2.0, "unit": "mg", "route": "Sublingual", "time": "14:05" },
    { "name": "Spironolactone", "dose": 50.0, "unit": "mg", "route": "Oral", "time": "09:00" }
  ],
  "mood": "Calm",
  "symptoms": "None",
  "libido": "Normal",
  "notes": "Felt steady today. No headache."
}
```

---

## Quick start (how to use)
1. Set **Date** and **Time** (or click **Now**).
2. In **Medications**, click **Add medication** if needed.
3. Fill at least one medication **Name** (required to save).
4. Optionally fill **Dose**, **Unit**, **Route**, **Time** per row.
5. Optionally add **Mood**, **Symptoms**, **Libido**, and **Notes**.
6. Click **Save entry**.
7. Click **View entries** to browse, inspect, or delete entries.

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
- Data file is append-only except when deleting an entry (rewrites the file without the deleted line).
