# Journey Journal — How `JJ.py` works (detailed)

## Overview (what it is)
`JJ.py` is a **local, file-based desktop journal app** written with **PySide6 (Qt)**. It stores journal entries in a JSON file and provides a GUI to:

- create a new entry (date, mood, symptoms, categorical fields, notes)
- browse entries in a table (main window)
- open a “View entries” dialog for full entry viewing + multi-delete
- delete selected entries (from main table or dialog)
- export entries to **JSON**, **TXT**, or **Markdown**
- switch **dark/light theme** (remembered via `QSettings`)
- show status messages with a fade animation

---

## Files, constants, and storage locations

### Important constants
- `APP_NAME = "Journey Journal"`
- `ORG_NAME = "HRTJourneyTracker"`
- `DATA_FILENAME = "j_j.json"`
- `STORAGE_DIRNAME = "storage"`
- theme setting key: `SETTINGS_THEME_KEY = "ui/theme"` (`"dark"` or `"light"`)

### Where entries are stored
The JSON file is created/used at:

- `./storage/j_j.json` next to the script (dev run), **or**
- next to the packaged executable (if frozen, e.g., PyInstaller)

This logic is handled by:

- `_ensure_storage_ready()`
  - picks a base directory:
    - packaged: `Path(sys.executable).parent`
    - normal: `Path(__file__).parent`
  - ensures `storage/` exists
  - ensures `storage/j_j.json` exists (initializes it to `[]`)

Then:
- `DATA_FILE = _default_data_file()` (computed at import time)
- main window uses `self.data_path = _default_data_file()`

---

## Data format (what is saved)
Entries are stored as a **JSON array** (`[]`) of objects.

Each entry looks like:

```json
{
  "entry_date": "2026-01-12",
  "mood": "Good",
  "symptoms": ["Fatigue", "Headache"],
  "emotional_shifts": "None",
  "pain_discomfort": "Mild",
  "libido_arousal": "Normal",
  "notes": "..."
}
```

One important rule in this app:
- **only one entry per date** is intended (if you add a second for the same date, you’re prompted to replace).

---

## Main components (classes)

## 1) `JournalEntry` (dataclass)
This is the in-memory representation of one journal entry:

- fields:
  - `entry_date: str` (format `"yyyy-MM-dd"`)
  - `mood: str`
  - `symptoms: list`
  - `emotional_shifts: str`
  - `pain_discomfort: str`
  - `libido_arousal: str`
  - `notes: str`

Helper methods:
- `to_dict()` → `asdict(self)` so it can be JSON-serialized
- `from_dict(data)` → converts a dict into a `JournalEntry`, using defaults if keys are missing

---

## 2) `JournalTableModel` (`QAbstractTableModel`)
This is the **model** behind the main `QTableView` in the “Entries” tab.

### Why a model?
Qt’s Model/View pattern means:
- the view (`QTableView`) does not store data
- it asks its model (`JournalTableModel`) for row/column counts and values

Key parts:
- `HEADERS = [...]` (7 columns)
- `rowCount()` / `columnCount()` reflect `len(self.entries)` and number of headers
- `data(index, role)`:
  - `Qt.DisplayRole`: returns the visible cell text
  - `Qt.ToolTipRole`: shows full notes as a tooltip for the Notes column
- update helpers:
  - `add_entry(entry)` uses `beginInsertRows/endInsertRows`
  - `remove_rows(rows)` removes rows safely with `beginRemoveRows/endRemoveRows`
  - `replace_all(entries)` resets the model with `beginResetModel/endResetModel`

---

## 3) `ViewJournalEntriesDialog` (`QDialog`)
This is the “View entries” window opened from the main window.

It uses:
- a `QTableWidget` (not the model/view table model)
- it loads entries from disk on refresh, then manually fills table cells

Key behavior:
- `_load_entries()`
  - reads the JSON array from `self._data_path`
  - converts to `JournalEntry` list
  - sorts newest-first by `entry_date` string
- `_refresh()`
  - clears the table and populates it row-by-row
- selection helpers:
  - `_selected_indices()` returns selected row indices (multi-select)
  - `_selected_entry()` returns the first selected entry
- actions:
  - **View** / double click → `_view_selected()`
    - opens another dialog showing a formatted text view (full notes)
  - **Details** → `_show_details()`
    - shows `json.dumps(entry.to_dict(), indent=2)` in a message box
  - **Delete** → `_delete_selected()`
    - confirms deletion
    - deletes by date (since the app enforces one entry per date)
    - writes a temp file (`.tmp`) then replaces original file (`tmp.replace(...)`)

After the dialog is closed, the main window syncs its in-memory list from `dlg.entries()`.

---

## 4) `HRTJournalWindow` (`QMainWindow`)
This is the main app window. It builds:
- a status bar label with fade animation
- a menu (“View → Theme → Dark/Light”)
- a `QTabWidget` with:
  - Tab 1: “New entry” (form)
  - Tab 2: “Entries” (table + buttons)

### Tab 1: New entry form
Widgets:
- `QDateEdit` (defaults to `date.today()`; saves as `"yyyy-MM-dd"`)
- mood: `QComboBox` with `(none)` + values
- symptoms: **multi-select checkboxes** inside a `QGroupBox`
- emotional shifts / pain / libido: `QComboBox` each
- notes: `QTextEdit`
- “Clear symptoms” button unchecks all symptom checkboxes
- “Add Entry” button calls `add_entry()`

### Tab 2: Entries table
Widgets:
- buttons:
  - Export…
  - View entries
  - Delete Selected
- `QTableView` backed by `JournalTableModel`
- row selection enabled, multi-select enabled

---

## Persistence (loading/saving)

### Load: `_load_data()`
- reads JSON from `self.data_path`
- `self.entries = [JournalEntry.from_dict(e) for e in raw]`
- on error, sets empty list and shows warning

### Save: `_save_data()`
- writes JSON to a temp file: `something.tmp`
- then replaces the original file (safer than writing directly)

---

## Add entry logic (`add_entry()`)
1. Collect symptoms from checked checkboxes.
2. Read date as `"yyyy-MM-dd"`.
3. Convert mood `(none)` → empty string.
4. Read notes (trim whitespace).
5. Validate:
   - if mood AND notes are empty: warn and stop.
6. Build a `JournalEntry`.
7. De-duplicate by date:
   - if the same `entry_date` exists, prompt to replace.
8. Sort newest-first (`_sort_entries()`).
9. Update UI model (`self.model.replace_all(self.entries)`).
10. Save to disk (`_save_data()`).
11. Show animated status “Saved.”
12. Reset form controls.

---

## Delete logic (main table) (`delete_selected()`)
1. Get selected rows from `QTableView` selection model.
2. Confirm deletion.
3. Call `self.model.remove_rows(rows)`.
4. Sync `self.entries = self.model.entries`.
5. Save to disk.
6. Show animated status “Deleted.”

---

## Export logic (`export_entries()`)
1. Open save file dialog with filters:
   - JSON (*.json)
   - Text (*.txt)
   - Markdown (*.md)
2. If user didn’t type an extension, infer it from the chosen filter.
3. Write file based on extension:
   - `.json`: writes JSON array of `to_dict()`
   - `.md`: markdown export with one section per entry
   - otherwise: plain text export
4. Shows success or failure message.

There’s also a compatibility alias `export_json()` that simply calls `export_entries()`.

---

## Theme system (dark/light)
- `DARK_STYLESHEET` and `LIGHT_STYLESHEET` are Qt stylesheets.
- `QSettings(ORG_NAME, APP_NAME)` is used to persist the chosen theme.
- main window provides menu actions:
  - “Dark”, “Light”
- `_set_theme(theme)`:
  - saves to settings
  - applies stylesheet to the app
  - keeps checkmarks mutually exclusive
  - shows animated status “Theme: Dark/Light”

---

## Status bar animation
The status uses:
- `QGraphicsOpacityEffect` to allow opacity changes
- `QPropertyAnimation` to fade out then fade in new text

Method:
- `_set_status_text_animated(text, timeout_ms=2000)`
  - fades current text out
  - sets the new text
  - fades it in
  - optionally clears it after a timeout

---

## Startup sequence (`main()`)
1. Create `QApplication`.
2. Set org/app names (needed for QSettings).
3. Apply last theme (`_apply_theme(app, _load_theme())`).
4. Create `HRTJournalWindow` and show it.
5. Enter Qt event loop with `app.exec()`.
