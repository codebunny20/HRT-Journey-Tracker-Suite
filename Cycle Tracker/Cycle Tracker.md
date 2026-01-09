# Cycle Tracker (`C-T.py`)

A PySide6 (Qt) desktop app to log cycle/bleed entries, view/edit/delete them in a table, and show simple summary stats (average cycle length, average bleed length, estimated next start). Includes Dark/Light theme via `QSettings`.

---

## Data storage (where + format)

- Stored in: `<script_dir>/data/cycle_entries.json` (created if missing)
- Format: **JSON array** (list) of entry objects.
- Persistence is handled by `CycleStorage`:
  - `load()` returns `[]` if missing or unreadable; skips malformed records; sorts by `start_date`.
  - `save()` writes formatted JSON (`indent=2`, `ensure_ascii=False`) and may raise `OSError` (GUI shows an error dialog).

---

## Entry schema (what gets saved)

```json
{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "intensity": "none",
  "notes": "...",
  "tags": ["cramps", "fatigue"]
}
```

Rules / validation:
- Add/Edit dialog enforces `end_date >= start_date`.
- Tags are parsed from comma-separated text:
  - whitespace-trimmed
  - empties removed
  - de-duplicated case-insensitively.

---

## UI: what the user does

### Main window
1. Review the **Summary** card (updates as entries change).
2. Use action buttons to manage entries:
   - **View** (details)
   - **Add**
   - **Edit**
   - **Delete**
   - **Reload**
3. Table shows:
   - Start, End, Bleed length, Intensity, Tags, Notes
   - Sorting is enabled; selection is full-row and single-select.
4. Optional: use the floating **Quick Add** (`+`) button (same as Add).

### Add/Edit entry dialog
1. Pick **Start** and **End** dates.
2. Choose **Intensity** (`none/light/medium/heavy`).
3. Enter **Notes**.
4. Enter **Tags** (comma-separated) or click quick-tag buttons (from `COMMON_TAGS`).
5. Save/accept:
   - If date range is invalid, it shows a warning and refuses.

### View/details dialog
- Read-only view of a single entry:
  - dates, bleed length, intensity, tags, notes.

---

## Key components (how it’s built)

### Data model
- `CycleEntry` dataclass:
  - `start_as_date()` / `end_as_date()`
  - `bleed_length_days()` (inclusive count)

### Sorting-safe selection (important)
Because the table can be sorted, each row stores the original entry index:
- `QTableWidgetItem.setData(Qt.UserRole, entry_index)`
- Selection resolves back to `self.entries` using `Qt.UserRole`.

### Summary calculations
- If fewer than 2 entries: shows “not enough entries”.
- Cycle lengths are computed from differences between consecutive start dates (positive-only).
- Average bleed length uses `bleed_length_days()`.
- Estimated next cycle start: `last_start + round(avg_cycle)`.

### Theme
- Stored in `QSettings` under `ui/theme` (`dark`/`light`).
- App-wide QSS via `DARK_QSS` / `LIGHT_QSS`.
- Guard fields prevent recursion/loops when applying theme (`self._applying_theme`, etc.).

### Hover tooltips
- Hover over table cells shows a tooltip including tags and notes (via `eventFilter` on `table.viewport()`).

---

## Shortcuts

- Enter/Return: View
- Ctrl+N: Add
- Ctrl+E: Edit
- Delete: Delete
- Ctrl+R: Reload
- Ctrl+Shift+N: Quick Add

---

## Run

- Run from source: `py .\C-T.py`
