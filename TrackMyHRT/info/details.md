# TrackMyHRT — `HRT.py` (what it does, how it works)

This is detailed breakdown of the TrackMyHRT tool/app project. This is app is a  (PySide6 / Qt) to log HRT-related entries. Each entry typically contains:

- **When it happened** (date + time, stored as a local timestamp string)
- **Medications** (0..N rows, each containing name/dose/unit/route/time)
- **Mood / energy / symptoms / libido** (multi-select lists)
- **Notes** (free text)

It also allows you to:
- view saved entries in a table
- open an entry in a readable “full view”
- see raw JSON details
- delete an entry
- export entries to JSONL / JSON / TXT / Markdown
- switch between dark/light themes

---

## 1) Data storage format and location

### Where data is stored
The app stores entries in:

- `./storage/entries.json` (relative to the script, or relative to the packaged exe if frozen)

This is computed by:

- `_ensure_storage_ready()`  
  - decides `base_dir`:
    - if packaged (`sys.frozen`): directory of the executable
    - else: directory of `HRT.py`
  - ensures `storage/` exists
  - ensures `entries.json` exists; if missing, it creates it containing `[]`

`_app_data_path()` simply returns that canonical path.

### JSON array format (current)
Entries are stored as a **single JSON array**:

```json
[
  { "id": "...", "timestamp_local": "YYYY-MM-DD HH:mm", "medications": [...], ... },
  { ... }
]
```

Write behavior:
- `_read_entries_json(path)` reads and returns a list, or `[]` on error.
- `_write_entries_json_atomic(path, entries)` writes with a `.tmp` file + `os.replace()` to reduce corruption risk.

### Legacy migration from JSONL (one-time)
Older versions used `entries.jsonl` (one JSON object per line). Migration logic:

- `LEGACY_JSONL_FILENAME = "entries.jsonl"`
- `_migrate_jsonl_to_json_if_needed()`:
  - if `entries.json` already has data, it does nothing
  - else, if legacy `entries.jsonl` exists:
    - reads each line
    - `json.loads(line)` per line
    - collects dict objects into a list
    - ensures each entry has an `id`
    - writes the list into `entries.json`

This is triggered by `_load_entries()`, so migration happens automatically once.

### Entry IDs
- Each entry is expected to have a stable `id` field (uuid hex).
- `_ensure_entry_ids(entries)` adds `id` to any dict missing it.

This enables deletion by ID (`_delete_entry_by_id(entry_id)`).

---

## 2) Theming (dark/light)

There are two Qt stylesheets:

- `DARK_STYLESHEET`
- `LIGHT_STYLESHEET`

Theme is persisted via Qt settings:

- `QSettings(org_name, APP_TITLE)`
- key: `ui/theme`

`_apply_app_theme(theme, settings, persist=True)`:
- normalizes theme string to `"dark"` or `"light"`
- applies stylesheet to `QApplication.instance()`
- optionally persists it to QSettings

The main window creates a `View → Theme` menu and syncs checkmarks via `_sync_theme_actions()`.

---

## 3) Custom multi-select control (checklist dropdown)

Qt `QComboBox` doesn’t natively do easy multi-select, so the app defines:

### `MultiSelectCombo(QToolButton)`
Core behavior:
- The widget looks like a button; clicking opens a menu.
- The menu contains checkable items implemented using `QWidgetAction` + a checkable `QToolButton`.
- Selected values are shown as button text (comma-separated).
- A placeholder appears when nothing is selected.

Important methods:
- `values()` → returns list of currently checked texts
- `set_values([...])` → programmatically set selections
- `eventFilter(...)` → prevents menu auto-closing during selection so you can check multiple items quickly

This same UX is used for:
- Mood
- Energy
- Symptoms
- Libido

---

## 4) Dialogs

### `CalendarDialog`
A small modal dialog containing a `QCalendarWidget` so the date picker experience is consistent (instead of the default popup).

Used by MainWindow’s “Pick date…” button.

### `ViewEntriesDialog`
This is the management screen for existing entries.

UI:
- `QTableWidget` with columns:
  1. Timestamp
  2. Medications (summarized)
  3. Mood
  4. Symptoms
  5. Notes

Features:
- `Refresh` reloads data from disk
- `View` (or double-click row) shows a full readable entry
- `Details` shows raw JSON in a message box
- `Delete` removes by `id` from `entries.json`
- `Export…` saves all currently loaded entries into a chosen format

Key helper logic:
- `_meds_summary(meds)` produces one-line medication summaries like:
  - `"Estradiol 2 mg (Oral) @ 09:00; Spironolactone 50 mg @ 21:00"`

Backward compatibility:
- `_listish_to_text(val)`:
  - if `val` is a list, joins with `", "`
  - if `val` is a string (older entries), returns it
This matters because newer code stores mood/symptoms/etc as arrays (lists).

Full-view formatting:
- `_format_entry_plain_text(entry)` produces a readable sectioned view.
Export formatting:
- `_format_entry_txt(entry)` plain text export format
- `_format_entry_md(entry)` markdown export format

Export behavior (`_export_entries()`):
- prompts for save location + file type filter
- writes:
  - `.jsonl` → each entry dumped on its own line
  - `.json` → the full list as a JSON array
  - `.txt` → concatenation of `_format_entry_txt`
  - `.md` → markdown document with entries as `##` sections

### `HelpDialog`
A static help text explaining:
- date/time entry
- medications table usage
- multi-select support
- saving and viewing/deleting
- where data is stored and how to find it

---

## 5) Main window layout and main workflow

### High level UI sections
`MainWindow` composes three main groups:

1. **Quick entry**
   - `QDateEdit` for date (with “Pick date…” custom calendar)
   - `QTimeEdit` for time (with “Now” button)

2. **Medications**
   - `QTableWidget` with 5 columns:
     - Name, Dose, Unit, Route, Time
   - “Add medication” adds a new row
   - “Remove selected” removes highlighted rows

3. **Mood, symptoms, notes**
   - Multi-select controls:
     - Mood
     - Energy
     - Symptoms
     - Libido
   - Notes text box

Bottom actions:
- View entries
- Help
- Clear
- Save entry

### Medication row entry
Each medication table row uses:
- Combo boxes for Name/Dose/Unit/Route (editable `QComboBox` so you can type custom values)
- Time stored in the last column as a `QTableWidgetItem`

Dose parsing:
- `_parse_dose(dose_text)`:
  - allows commas (`2,5` → `2.5`)
  - extracts first number via regex
  - converts to float
If dose is empty or unparsable, it becomes 0.0 or triggers validation error.

Collecting meds:
- `_collect_medications()` walks rows, reads each cell, skips completely empty rows, turns dose into float, and returns `List[MedicationRow]`.

Validation:
- `_validate_can_save(meds)` requires at least one medication with a non-empty name.

### Multi-select value storage
`_multiselect_values(widget)`:
- if widget is `MultiSelectCombo` → returns `widget.values()` (list of strings)
- if fallback `QComboBox` → splits by comma

Storage format used in new entries:
- `"mood": [ ... ]`
- `"energy": [ ... ]`
- `"symptoms": [ ... ]`
- `"libido": [ ... ]`

### Saving an entry
`_save_entry()` does:

1. Collect and validate medication rows.
2. Build a `datetime` from the chosen date/time.
3. Convert to a local timestamp string: `YYYY-MM-DD HH:mm`.
4. Build a record dict including:
   - `id` (uuid)
   - `created_at`, `updated_at`, `timestamp_local`
   - `date`, `time`
   - `medications` list of dict rows
   - mood/energy/symptoms/libido as lists
   - notes
5. Append the record to the JSON array on disk and atomically rewrite it.

After saving:
- status bar message (“Saved entry…”)
- popup confirmation showing the data path
- clears the form (optionally keeping date/time)

### Clearing the form
`_clear_form(keep_date_time=False)`:
- resets date/time (unless `keep_date_time=True`)
- clears all multi-select widgets
- clears notes
- resets meds table to exactly one initial row

### Viewing entries
`_view_entries()` opens `ViewEntriesDialog`, which loads entries sorted newest-first by `timestamp_local`.

### Menu options
- File → “Open data folder” doesn’t literally open Explorer; it shows a message box with the full path to entries.json.
- View → Theme → Dark/Light toggles stylesheet and persists setting.

---

## 6) Program entry point
`main()`:
- sets Qt organization/application names
- creates `QApplication`
- loads theme from `QSettings`
- creates and shows `MainWindow`

When running `HRT.py` directly (`__main__`), it calls `main()`.

---

## Practical mental model
- UI collects one “entry”
- entry becomes a JSON object with an `id` and timestamp
- all entries are stored as a JSON array in one file
- the viewer dialog reads that file, summarizes it into a table, and can export or delete items by `id`
