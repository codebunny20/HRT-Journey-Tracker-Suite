# Cycle Tracker (PySide6)

This app is implemented in a single script (`C-T.py`). It logs cycle/bleed entries to JSON on disk and provides a PySide6 UI for viewing, editing, and summarizing that history.

---

## `C-T.py` structure (what each part does)

## 1) Imports and UI toolkit
- Uses standard libs: `json`, `sys`, `dataclasses`, `datetime`, `pathlib`, `typing`.
- Uses PySide6 core UI types: `QApplication`, `QMainWindow`, dialogs, widgets, table, tooltips, shortcuts, and `QSettings` for user preferences.

---

## 2) Tag helpers (top-level utilities)

### `COMMON_TAGS`
A list of strings used to render “quick tag” buttons in the Add/Edit dialog:
```text
["cramps", "mood shift", "spotting", "fatigue", "no bleed", "breakthrough"]
```

### `_parse_tags(text: str) -> List[str]`
- Splits a comma-separated string into tags.
- Trims whitespace, drops empties.
- De-duplicates case-insensitively (so `Cramps` and `cramps` count as the same tag).

### `_tags_to_text(tags: List[str]) -> str`
- Converts a list back into a single comma-separated string for display.

---

## 3) Data model

### `CycleEntry` (`@dataclass`)
Represents one entry in the tracker.

Fields:
- `start_date: str` and `end_date: str` (stored as `YYYY-MM-DD`)
- `intensity: str` (`"none" | "light" | "medium" | "heavy"`)
- `notes: str`
- `tags: List[str]`

Methods:
- `start_as_date()` / `end_as_date()`
  - Convert the stored strings into `datetime.date` for calculations.
- `bleed_length_days()`
  - Inclusive day count: `(end - start) + 1`.

---

## 4) Persistence layer (local JSON)

### `CycleStorage`
Handles reading/writing entries.

- `__init__(path: Optional[str] = None)`
  - If `path` is not provided, it writes to a dedicated data folder next to the script:
    - `<script_dir>/data/cycle_entries.json`
  - Ensures the directory exists (`mkdir(..., exist_ok=True)`).

- `load() -> List[CycleEntry]`
  - Returns `[]` if the file doesn’t exist.
  - Returns `[]` on JSON decode errors / read errors.
  - Builds `CycleEntry` instances from JSON objects.
  - Skips malformed records missing required keys.
  - Sorts by `start_date` before returning.

- `save(entries: List[CycleEntry]) -> None`
  - Ensures the folder exists, then writes JSON with:
    - `indent=2`, `ensure_ascii=False`
  - Raises `OSError` upward; the GUI catches it and shows an error dialog.

On-disk JSON format:
- A list of dicts matching `CycleEntry` fields:
  - `start_date`, `end_date`, `intensity`, `notes`, `tags`.

---

## 5) Add/Edit dialog

### `CycleDialog(QDialog)`
Used for both “Add” and “Edit”.

UI elements:
- `QDateEdit` for start and end (`yyyy-MM-dd`, calendar popup)
- `QComboBox` for intensity (`none/light/medium/heavy`)
- `QPlainTextEdit` for notes
- `QLineEdit` for tags (comma-separated)
- Quick tag `QPushButton`s generated from `COMMON_TAGS`

Quick tag behavior:
- Clicking a tag button adds it to the tags field if not already present (case-insensitive check).

Editing behavior:
- When constructed with `existing=CycleEntry`, it pre-fills:
  - dates, intensity, notes, tags

### `get_entry() -> Optional[CycleEntry]`
- Only returns an entry if the dialog was accepted.
- Validates `end >= start`; otherwise shows `QMessageBox.warning(...)` and returns `None`.
- Returns a `CycleEntry` using:
  - formatted dates (`strftime("%Y-%m-%d")`)
  - trimmed notes
  - parsed tags via `_parse_tags(...)`

---

## 6) View/details dialog

### `CycleDetailsDialog(QDialog)`
Read-only display for a single entry.

What it shows:
- Start/End dates
- Bleed length (`CycleEntry.bleed_length_days()`)
- Intensity
- Tags (or `(none)`)
- Notes (or `(none)`), with newlines rendered as HTML `<br/>`

Implementation notes:
- Uses `QTextBrowser` to render a small HTML snippet.
- Has a Close button (`QDialogButtonBox.Close`).

---

## 7) Main window

### Intensity color coding
- `INTENSITY_COLORS`: maps intensity to background/foreground colors.
- `_apply_intensity_style(item: QTableWidgetItem, intensity: str)`
  - Applies the colors to the *Intensity* cell using `QBrush(QColor(...))`.

### Theme constants / settings keys
- `ORG_NAME = "HRTJourneyTracker"`
- `APP_NAME = "Cycle Tracker"`
- `SETTINGS_THEME_KEY = "ui/theme"`: persisted theme value
- `THEME_DARK`, `THEME_LIGHT`
- `DARK_QSS`, `LIGHT_QSS`: app-wide Qt stylesheets

Theme functions:
- `_load_theme() -> str`
  - Reads `ui/theme` from `QSettings` (defaults to `"dark"`).
- `_apply_app_theme(theme: str, persist: bool = False) -> str`
  - Applies `DARK_QSS` or `LIGHT_QSS` to the `QApplication`.
  - If `persist=True`, writes it back into `QSettings`.

### `CycleTrackerWindow(QMainWindow)`
Top-level application UI.

Key state:
- `self.storage`: `CycleStorage`
- `self.entries`: list of `CycleEntry` loaded from disk
- Tooltip tracking: `self._last_tooltip_entry_idx`
- Theme guards: `self._applying_theme`, `self._last_theme_sig`, `self._theme`

Layout/components:
- Header labels (“Cycle Log”, subtitle)
- Summary card (`QFrame` with objectName `"SummaryCard"`) containing `self.summary_label`
- Actions row (buttons: View/Add/Edit/Delete/Reload)
- `QTableWidget` with 6 columns:
  - Start, End, Bleed length, Intensity, Tags, Notes
- Floating “Quick Add” button (`self.fab` with objectName `"QuickAddFab"`) positioned bottom-right

Table behavior:
- Sorting enabled.
- Full-row single selection.
- Read-only cells (`NoEditTriggers`).
- Column sizing uses `QHeaderView` resize modes, with Notes stretched.

### Sorting-safe selection (important detail)
Because sorting changes row order, the code stores the original entry index in each row:
- In `populate_table()`, each `QTableWidgetItem` gets:
  - `it.setData(Qt.UserRole, entry_index)`
- `get_selected_index()` reads `Qt.UserRole` from the selected row to find the correct entry in `self.entries`.

### Summary calculations (`update_summary()`)
- If fewer than 2 entries: displays a “not enough entries” message.
- Sorts entries by `start_as_date()`.
- Cycle length is computed from differences between consecutive *start* dates (positive-only).
- Average bleed length uses `bleed_length_days()`.
- Estimated next cycle start:
  - `last_start + round(avg_cycle)`.

### Actions and shortcuts
Actions call these methods:
- `on_view()`: opens `CycleDetailsDialog` for selected entry
- `on_add()`: opens `CycleDialog`, appends entry, sorts, saves, refreshes
- `on_edit()`: opens `CycleDialog(existing=...)`, replaces, sorts, saves, refreshes
- `on_delete()`: confirms, deletes, saves, refreshes
- `on_reload()`: reloads from JSON then refreshes
- `on_quick_add()`: same as add, triggered by the floating `+`

Shortcuts:
- Enter/Return: View
- Ctrl+N: Add
- Ctrl+E: Edit
- Delete: Delete
- Ctrl+R: Reload
- Ctrl+Shift+N: Quick Add

### Hover tooltips (`eventFilter`)
- Installed on `self.table.viewport()`.
- On mouse move:
  - finds the hovered cell, resolves the correct entry index via `Qt.UserRole`
  - shows `QToolTip` with:
    - `Tags: ...`
    - `Notes: ...` (or `Notes: (none)`)
- On leave: hides the tooltip.

### Theme application
- `changeEvent(PaletteChange)` triggers `apply_theme()`.
- `apply_theme()` prefers the stored theme (`self._theme` / `_load_theme()`).
- A recursion guard (`self._applying_theme`) prevents repeated `setStyleSheet` loops.

---

## 8) Program entry point

### `main()`
- Creates the `QApplication`.
- Sets org/app names for `QSettings`.
- Applies the saved theme (`_apply_app_theme(_load_theme())`).
- Creates `CycleStorage`, then `CycleTrackerWindow`, shows it.
- Starts the Qt event loop (`app.exec()`).

---
