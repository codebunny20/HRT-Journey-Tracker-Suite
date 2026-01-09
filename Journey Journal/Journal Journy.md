# Journey Journal (JJ.py) — Code Overview

This document explains what `JJ.py` does and how it is structured.

## What the app is
`JJ.py` is a PySide6 (Qt) desktop app named **Journey Journal**. It lets you:
- Create a daily journal entry (date, mood, symptoms, a few dropdown fields, notes)
- View entries in a table
- View full entry text in a dialog
- Delete entries (single or multiple)
- Export entries as **JSON**, **TXT**, or **Markdown**
- Toggle between **Dark** and **Light** themes (saved via `QSettings`)

---

## Key constants / configuration
Top-level constants define app identity and storage:
- `APP_NAME = "Journey Journal"`
- `ORG_NAME = "HRTJourneyTracker"`
- `DATA_FILENAME = "j_j.json"`
- `STORAGE_DIRNAME = "storage"`

Theme configuration:
- `SETTINGS_THEME_KEY = "ui/theme"` stores `"dark"` or `"light"` using `QSettings`
- `DARK_STYLESHEET` and `LIGHT_STYLESHEET` are Qt stylesheets applied to the whole app

---

## Theme helpers (QSettings + stylesheet)
Functions:
- `_load_theme()` reads the saved theme from `QSettings` (defaults to `"dark"`)
- `_save_theme(theme)` saves `"dark"`/`"light"` back to `QSettings`
- `_apply_theme(app, theme)` applies the corresponding stylesheet to the `QApplication`

Where theme toggling happens:
- In `HRTJournalWindow._init_menus()` the menu is created: **View → Theme → Dark/Light**
- In `HRTJournalWindow._set_theme()` the theme is saved + applied, and a status message is shown

---

## Storage location and initialization
The app stores data in a JSON file (a JSON **array** of entries).

Storage setup:
- `_ensure_storage_ready()` ensures a `storage/` folder exists next to:
  - the packaged executable when frozen (`sys.frozen`)
  - or next to `JJ.py` when running normally
- It ensures the file `storage/j_j.json` exists; if not, it writes `[]` to create an empty array.

The default data file path is:
- `_default_data_file()` → `_ensure_storage_ready()`
- `DATA_FILE` is initialized to that path.

---

## Data model (JournalEntry dataclass)
`JournalEntry` is a dataclass that represents one journal entry:

Fields:
- `entry_date: str` (stored as `"yyyy-MM-dd"`)
- `mood: str`
- `symptoms: list` (list of strings)
- `emotional_shifts: str`
- `pain_discomfort: str`
- `libido_arousal: str`
- `notes: str`

Conversion helpers:
- `to_dict()` returns a dict version (via `asdict`)
- `from_dict(data)` builds a `JournalEntry` from a dict and supplies defaults if keys are missing

Important design note:
- The app effectively enforces **one entry per date** (it prompts to replace if a date already exists).

---

## Table model (JournalTableModel)
`JournalTableModel` is a Qt `QAbstractTableModel` used by the main **Entries** table (`QTableView`).

- `HEADERS` defines 7 columns:
  1. Date
  2. Mood
  3. Symptoms
  4. Emotional shifts
  5. Pain / discomfort
  6. Libido / arousal
  7. Notes

Key behavior:
- `data()` returns display text for each cell
  - Symptoms are joined with `", "`
  - Notes are shown as a single-line preview (newlines replaced)
  - Full notes are exposed on hover via `Qt.ToolTipRole` for the Notes column
- `add_entry()`, `remove_rows(rows)`, and `replace_all(entries)` are convenience methods to update the model safely.

---

## View Entries dialog (ViewJournalEntriesDialog)
`ViewJournalEntriesDialog` is a modal dialog that loads entries from disk and shows them in a `QTableWidget`.

UI elements:
- A 7-column table mirroring the same headers
- Buttons: **Refresh**, **View**, **Details**, **Delete**, **Close**

Important methods:
- `_load_entries()` reads JSON from `self._data_path`, converts to `JournalEntry`, sorts newest-first
- `_refresh()` repopulates the table widget
- `_view_selected()` opens a modal dialog with an easy-to-read text layout of the entry
- `_show_details()` shows raw JSON for the entry via `json.dumps(..., indent=2)`
- `_delete_selected()` deletes selected rows:
  - Confirms with the user
  - Writes the updated list atomically using a `*.tmp` file then `replace()`

This dialog is used from the main window’s **Entries** tab via the **View entries** button.

After the dialog closes, the main window reloads/syncs entries from the dialog (`dlg.entries()`).

---

## Main window (HRTJournalWindow)
`HRTJournalWindow` is the primary `QMainWindow`. It builds the whole UI and wires up actions.

### Status bar animation (fade)
The status bar uses a `QLabel` with a `QGraphicsOpacityEffect`.
- `_set_status_text_animated(text, timeout_ms=2000)` fades the label out, updates text, then fades in.
- It also clears the text after `timeout_ms` using a `QTimer.singleShot`.

This is used for messages like:
- `"Saved."`, `"Deleted."`, `"Theme: Dark"`, etc.

### Tabs and layout
The central widget contains a `QTabWidget` with two tabs:

#### Tab 1: "New entry"
A scrollable form with:
- `QDateEdit` (defaults to today)
- `Mood` (`QComboBox`) includes `(none)` plus a small fixed set
- `Symptoms` is a group of **checkboxes** (multi-select) + a “Clear symptoms” button
- `Emotional shifts`, `Pain / discomfort`, `Libido / arousal` (`QComboBox` each)
- `Notes` (`QTextEdit`)
- Primary action button: **Add Entry** → calls `add_entry()`

#### Tab 2: "Entries"
Top button row:
- **Export…** → `export_entries()`
- **View entries** → `view_entries()` (opens `ViewJournalEntriesDialog`)
- **Delete Selected** → `delete_selected()`

Main table:
- `QTableView` using `JournalTableModel`
- Multi-row selection enabled
- Interactive column resizing; last column stretches

---

## Persistence (load/save)
Persistence is JSON file based.

- `_load_data()` reads `self.data_path` and converts each dict to `JournalEntry`
- `_save_data()` writes the full list back as JSON, using a `.tmp` file then replacing the original (helps prevent corruption)

---

## Add entry workflow (add_entry)
`add_entry()` collects values from the form:
- Symptoms are all checked checkboxes
- Date is serialized as `"yyyy-MM-dd"`
- Mood `(none)` is converted to empty string
- Notes are trimmed

Validation:
- If BOTH mood and notes are empty → warning; refuses to save (prevents empty rows).

Duplicate handling:
- `_find_entry_index_by_date(entry_date)` checks if a date already exists.
- If it does, the app prompts: **Replace it?**
  - Yes → replace current entry for that date
  - No → do nothing

Finally:
- Sort newest first
- Update model `replace_all()`
- Save to disk `_save_data()`
- Show status “Saved.”
- Reset form controls

---

## Delete in main table (delete_selected)
Deletes selected rows from the `QTableView`:
- Confirms with the user
- Calls `model.remove_rows(rows)`
- Saves updated entries to disk
- Shows status “Deleted.”

Note: This deletes by row index in the currently displayed model.

---

## Export (export_entries)
Export uses `QFileDialog.getSaveFileName` and supports:
- JSON (`.json`) → full structured list of dicts
- Markdown (`.md`) → human-readable export:
  - Header `# Journey Journal export`
  - Each entry is formatted by `_format_entry_md()`
- Text (`.txt`) → plain text blocks using `_format_entry_txt()`

If no file extension is provided, it infers one from the selected filter.

There is also `export_json()` which just calls `export_entries()` (compatibility alias).

---

## App entry point (main)
`main()`:
- Creates `QApplication`
- Sets org/app names (for QSettings)
- Applies saved theme
- Creates and shows `HRTJournalWindow`
- Runs the Qt event loop

The script runs `main()` when executed directly.

---

## Data file format
On disk: `storage/j_j.json` is a JSON array like:

```json
[
  {
    "entry_date": "2026-01-09",
    "mood": "Good",
    "symptoms": ["Fatigue"],
    "emotional_shifts": "More sensitive",
    "pain_discomfort": "Mild",
    "libido_arousal": "Normal",
    "notes": "..."
  }
]
```

Key characteristics:
- One entry per date is encouraged/enforced by replace prompt.
- Entries are frequently sorted newest-first in memory/UI.
