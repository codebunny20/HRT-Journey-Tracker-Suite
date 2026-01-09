# Journey Journal (`JJ.py`)

A small PySide6 (Qt) desktop app to create a **daily journal entry** (date, mood, symptoms, a few dropdown fields, notes), view entries in a table, delete (single/multiple), export, and toggle **Dark/Light** theme (persisted via `QSettings`).

---

## Data storage (where + format)

- Stored in: `storage/j_j.json`
  - Next to the packaged `.exe` when frozen, or next to `JJ.py` when running from source.
- Format: **JSON array** (list) of entry objects.
- Initialization:
  - `_ensure_storage_ready()` creates `storage/` and writes `[]` if the file doesn’t exist.
- Writes are **atomic-ish**:
  - `_save_data()` writes `*.tmp` then `replace()` to reduce corruption risk.

---

## Entry schema (what gets saved)

```json
{
  "entry_date": "YYYY-MM-DD",
  "mood": "Good",
  "symptoms": ["Fatigue"],
  "emotional_shifts": "More sensitive",
  "pain_discomfort": "Mild",
  "libido_arousal": "Normal",
  "notes": "..."
}
```

Rules / behavior:
- The app effectively enforces **one entry per date**:
  - If an entry already exists for the chosen date, it prompts to **replace** it.
- Validation:
  - If both **mood** and **notes** are empty, it refuses to save (prevents empty rows).

---

## UI: what the user does

### Main window
The UI is a `QMainWindow` with a `QTabWidget`:

#### Tab 1: “New entry”
1. Choose **Date**.
2. Pick **Mood** (or `(none)`).
3. Select any **Symptoms** (checkboxes; multi-select).
4. Optionally choose:
   - **Emotional shifts**
   - **Pain / discomfort**
   - **Libido / arousal**
5. Write **Notes**.
6. Click **Add Entry**.
   - If a same-date entry exists, confirm **Replace**.

#### Tab 2: “Entries”
- Uses a `QTableView` (multi-row selection).
- Buttons:
  - **Export…**
  - **View entries** (opens a dialog)
  - **Delete Selected** (deletes selected rows in the table)

### View entries dialog
A modal dialog that loads entries from disk and shows them in a `QTableWidget`.

Actions:
- **Refresh**
- **View** (formatted text)
- **Details** (raw JSON)
- **Delete**
- **Close**

---

## Key components (how it’s built)

### Data model
- `JournalEntry` dataclass with `to_dict()` / `from_dict(...)`.

### Table model
- `JournalTableModel(QAbstractTableModel)`
  - Notes column shows a one-line preview; full notes available via tooltip role.

### Theme
- Persisted via `QSettings` under `ui/theme` (`"dark"` or `"light"`).
- Applied app-wide with Qt stylesheets (`DARK_STYLESHEET`, `LIGHT_STYLESHEET`).
- Menu: **View → Theme → Dark/Light**.

### Status messages
- Status bar uses a `QLabel` + `QGraphicsOpacityEffect` fade animation for messages like “Saved.” / “Deleted.” / “Theme: Dark”.

---

## Export

From **Export…**:
- `.json` (full structured list)
- `.md` (human-readable export; uses `_format_entry_md()`)
- `.txt` (plain text blocks; uses `_format_entry_txt()`)

If no extension is provided, it infers one from the selected filter.
There is also `export_json()` as a compatibility alias.

---

## Run

- Run from source: `py .\JJ.py`

(If you bundle it, storage still resolves to a `storage/` folder next to the executable.)
