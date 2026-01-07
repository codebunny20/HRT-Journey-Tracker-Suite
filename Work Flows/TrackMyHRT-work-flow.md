# TrackMyHRT — Workflow (Folder + `HRT.py`)

## 1) TrackMyHRT folder workflow (as-used by the app)

From the provided files, the relevant parts are:

- `TrackMyHRT/HRT.py`
  - The main application script (PySide6 GUI).
  - Owns: UI, storage, migration, export, theme persistence.

- `TrackMyHRT/storage/`
  - Created automatically at runtime if missing.
  - Contains the data file(s):
    - `entries.json` (current canonical storage)
    - `entries.jsonl` (legacy; only read for one-time migration)

### 1.1 Where data is stored (runtime resolution)
`HRT.py` determines a base directory differently depending on how it is run:

- **Running from source (normal python):**
  - `base_dir = directory containing HRT.py`
  - Storage folder: `<base_dir>/storage/`
  - Data file: `<base_dir>/storage/entries.json`

- **Running as a packaged executable (frozen):**
  - `base_dir = directory containing the .exe`
  - Storage folder: `<base_dir>/storage/`
  - Data file: `<base_dir>/storage/entries.json`

This is implemented by `_ensure_storage_ready()` using:
- `getattr(sys, "frozen", False)` to detect “packaged/frozen”
- `sys.executable` vs `__file__`

---

## 2) `HRT.py` workflow (high-level responsibilities)

`HRT.py` is organized into these functional blocks:

1. **Imports + constants**
2. **Theme system (dark/light with `QSettings`)**
3. **Storage layer**
   - Ensure storage folder exists
   - Read/write JSON entries
   - One-time migration from JSONL
   - Ensure stable entry `id`s
   - Upsert/delete helpers
4. **UI components**
   - `MultiSelectCombo` (custom checklist dropdown)
   - `CalendarDialog`
   - `ViewEntriesDialog` (table view + export + delete + details)
   - `HelpDialog`
   - `MainWindow` (data entry form)
5. **Program entrypoint**
   - `main()` creates Qt app, applies theme, shows MainWindow

---

## 3) Storage + migration workflow

### 3.1 Canonical format
The app stores entries in **one JSON file**:

- Filename: `entries.json`
- Format: **JSON array** (list) of entry objects:
  ```json
  [
    { "id": "...", "timestamp_local": "...", "...": "..." },
    { "id": "...", "timestamp_local": "...", "...": "..." }
  ]
  ```

### 3.2 Legacy format (migration source)
Older versions wrote `entries.jsonl` (JSON Lines; one JSON object per line).
`HRT.py` will migrate only when:

- `entries.json` is missing/empty **and**
- `storage/entries.jsonl` exists and contains parseable objects

Migration behavior (`_migrate_jsonl_to_json_if_needed()`):
- Reads each non-empty line
- `json.loads(line)` per line; keeps dict objects
- Adds missing `id` fields via `_ensure_entry_ids()`
- Writes migrated list to `entries.json` (atomic write)

### 3.3 Ensuring entry IDs
`_ensure_entry_ids(entries)`:
- Ensures every entry dict has a non-empty `"id"`
- If missing, generates `uuid.uuid4().hex`
- Best-effort timestamps:
  - If `timestamp_local` exists and `created_at` missing → set `created_at`
  - If `timestamp_local` exists and `updated_at` missing → set `updated_at`

### 3.4 Read path
`_load_entries()`:
1. Run JSONL migration if needed
2. Read `entries.json` as list
3. Ensure all entries have `id` (and persist back if changed)
4. Sort entries newest-first by `timestamp_local` string (descending)

### 3.5 Write path
Write is done with atomic replace:

- `_write_entries_json_atomic(path, entries)`
  - writes to `entries.json.tmp`
  - `os.replace(tmp, path)` (atomic on Windows in most cases)

Saving a new entry in `MainWindow._save_entry()` currently does:
- `entries = _read_entries_json(path)`
- `entries.append(record)`
- `_write_entries_json_atomic(path, entries)`

Deletion:
- `_delete_entry_by_id(entry_id)` filters list and rewrites JSON.

There is also `_upsert_entry(updated)` available (insert-or-replace by id),
but the UI path shown uses append for new records.

---

## 4) Data model (entry schema)

Each saved entry is a dict with (current behavior):

- `id`: `uuid.uuid4().hex`
- `created_at`: `YYYY-MM-DD HH:mm` (same as timestamp at save)
- `updated_at`: `YYYY-MM-DD HH:mm` (same as timestamp at save)
- `timestamp_local`: `YYYY-MM-DD HH:mm` (derived from date/time widgets)
- `date`: `YYYY-MM-DD`
- `time`: `HH:mm`

- `medications`: list of medication dicts:
  - `name`: string
  - `dose`: float (parsed from user input; defaults to `0.0`)
  - `unit`: string
  - `route`: string
  - `time`: `HH:mm` (defaults to main time if blank)

- Multi-select fields (stored as **lists of strings**):
  - `mood`: `["Calm", "Happy"]` etc
  - `energy`: `["Tired"]` etc
  - `symptoms`: `["Headache", "Nausea"]` etc
  - `libido`: `["Normal"]` etc

- `notes`: string (trimmed with `rstrip()`)

Backward compatibility in the viewer/exporter:
- `ViewEntriesDialog._listish_to_text()` supports either a list or a single string
  (so older entries that stored `"mood": "Happy"` still display cleanly).

---

## 5) UI workflow: Main window (creating entries)

`MainWindow` is the primary data entry UI.

### 5.1 Quick entry (date/time)
Controls:
- `QDateEdit` for date
- `QTimeEdit` for time
- `Now` button sets both to current local time
- `Pick date…` opens `CalendarDialog` for date selection

### 5.2 Medications table
Widget:
- `QTableWidget` with columns: `Name | Dose | Unit | Route | Time`

Row behavior:
- “Add medication” inserts a row with:
  - Name/Dose/Unit/Route are editable `QComboBox` fields (editable + suggestions)
  - Time is a table item defaulting to the main window time at row creation
- “Remove selected” deletes highlighted row(s)
  - If it deletes all rows, it auto-adds a fresh blank row

Collection behavior (`_collect_medications()`):
- Reads each row’s values
- Skips fully empty rows
- Parses dose with `_parse_dose()`:
  - accepts `,` or `.` decimal
  - extracts first numeric token with regex
  - raises validation error if no number found
- If med row time is blank, fills with main time
- Returns list of `MedicationRow` dataclass instances

Validation (`_validate_can_save()`):
- Requires **at least one medication name** (non-empty after stripping)
- If not met: save blocked with message

### 5.3 Mood / Energy / Symptoms / Libido / Notes
Widgets:
- `MultiSelectCombo` for Mood, Energy, Symptoms, Libido
  - behaves like a dropdown menu with multiple checkable items
  - stores selections as list-of-strings in JSON
- `QPlainTextEdit` notes field

Clear behavior (`_clear_form()`):
- Optionally keeps date/time (used after successful save)
- Clears all MultiSelectCombo selections
- Clears notes
- Resets medications table to one blank row

### 5.4 Save entry workflow
On “Save entry”:
1. Collect meds rows (may raise dose validation error)
2. Validate at least one medication name
3. Construct a timestamp from date/time widgets
4. Build record dict (schema above)
5. Read JSON array, append record, write atomically
6. Show status bar message + modal “Saved” dialog
7. Clear form but keep date/time

---

## 6) UI workflow: View/manage entries dialog

`ViewEntriesDialog` shows saved data and allows exporting and deletion.

### 6.1 Table view
- Columns: `Timestamp | Medications | Mood | Symptoms | Notes`
- Newest first (via `_load_entries()` sort)
- Double click a row opens full “Entry” view

Medication summary display:
- `_meds_summary()` formats each medication into a compact string:
  - `Name dose unit (route) @ time`
- Joined with `; ` for multiple meds

List-or-string display:
- Mood/Symptoms columns use `_listish_to_text()` to render either:
  - list → comma separated
  - string → as-is

### 6.2 Buttons
- **Refresh**: reload entries from disk
- **View**: opens a dialog showing a formatted full entry (plain text)
- **Details**: shows raw entry JSON (pretty-printed)
- **Delete**: deletes by `id` after confirmation
- **Export…**: writes all currently loaded entries to a chosen file

### 6.3 Export formats
Export uses the currently loaded entries in the dialog, not a fresh read unless you hit Refresh.

Supported extensions:
- `.jsonl`: emits one JSON object per line (even though storage is JSON array)
- `.json`: writes JSON array with indentation
- `.txt`: writes formatted text blocks per entry
- `.md`: writes Markdown with headings per entry

Formatting functions:
- `_format_entry_txt(entry)`
- `_format_entry_md(entry)`
- `_format_entry_plain_text(entry)` (used by View dialog)

These include: Mood, Energy, Symptoms, Libido, Notes, and medications list.

---

## 7) Theme workflow (dark/light)

Theme is persisted via `QSettings` under key:
- `ui/theme` with values `"dark"` or `"light"`

Where applied:
- At startup in `main()` before window creation
- In `MainWindow` constructor (reads settings and syncs menu actions)

User interaction:
- Menu: `View → Theme → Light/Dark`
- Selecting a theme:
  - updates app stylesheet
  - writes to settings
  - updates checkmarks via `_sync_theme_actions()`

---

## 8) “Open data folder” workflow (actually shows file path)
Menu: `File → Open data folder`

Current behavior:
- Shows a message box displaying the exact path to `entries.json`
- It does not open Explorer; it’s a “location hint” dialog.

---

## 9) Help workflow
Help button opens `HelpDialog` with quick instructions:
- date/time usage
- medications entry tips
- multi-select fields support
- saving requirements (must have medication name)
- viewing/export/deleting
- data location hint

---

## 10) End-to-end user flows (summary)

### Flow A — Add a new entry
1. Set Date/Time (or click Now / Pick date…)
2. Add one or more medication rows
3. (Optional) select Mood/Energy/Symptoms/Libido
4. (Optional) write Notes
5. Click Save entry
6. App appends a new object to `storage/entries.json`

### Flow B — Review and export history
1. Click View entries
2. Browse table (newest first)
3. Optional: View/double-click for full formatted entry
4. Optional: Export… choose `.json/.jsonl/.txt/.md`

### Flow C — Delete a mistaken entry
1. Click View entries
2. Select row
3. Click Delete
4. Confirmation dialog
5. Entry removed by id and file rewritten

### Flow D — Change theme
1. View → Theme → Light/Dark
2. Theme applied immediately and persisted via QSettings
