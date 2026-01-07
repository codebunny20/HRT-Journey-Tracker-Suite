# Journey Journal — Workflow (Folders + JJ.py)

## 1) Folder / file workflow (how the project is laid out)

### `Journey Journal/`
- Contains the Journey Journal application code.
- `JJ.py` is the entry point (run it to launch the PySide6 GUI).

### `Work Flows/`
- Contains human-readable documentation.
- This file explains how the app works end-to-end (UI → data → storage).

### `storage/` (created at runtime, next to `JJ.py` or next to the packaged `.exe`)
- Created automatically if missing.
- Holds the app’s data file:
  - `storage/j_j.json` — JSON array of journal entries.

> The storage location is computed in `JJ.py` by `_ensure_storage_ready()`.
> - Dev mode: `storage/` is created next to `JJ.py`.
> - Packaged/frozen mode: `storage/` is created next to the executable.

---

## 2) Data workflow (what happens to your entries)

### Data format
- The app stores entries in a single JSON file: `storage/j_j.json`.
- File content is a JSON array `[]` of objects shaped like `JournalEntry`:
  - `entry_date` (string `"yyyy-MM-dd"`)
  - `mood` (string)
  - `symptoms` (list of strings)
  - `emotional_shifts` (string)
  - `pain_discomfort` (string)
  - `libido_arousal` (string)
  - `notes` (string)

### Load on startup
1. App starts (`main()`).
2. Theme is loaded from QSettings and applied.
3. `HRTJournalWindow` is created.
4. `self.data_path = _default_data_file()` ensures `storage/j_j.json` exists.
5. `_load_data()` reads JSON and converts each object → `JournalEntry`.
6. Entries are sorted newest-first and shown in the table model.

### Save on “Add Entry”
1. User fills in the “New entry” tab and clicks **Add Entry**.
2. `add_entry()` builds a `JournalEntry`.
3. If an entry already exists for that date:
   - user is prompted to **Replace** it (1 entry per day behavior).
4. Entries are sorted newest-first.
5. `_save_data()` writes the whole array to a temp file `j_j.tmp` then replaces `j_j.json`.

### Delete from main table
1. User selects rows in the “Entries” tab table.
2. Click **Delete Selected**.
3. `delete_selected()` removes rows from the model, updates `self.entries`, and `_save_data()` persists.

### View / delete via “View entries” dialog
1. Click **View entries**.
2. Dialog loads entries from disk into its own table.
3. Actions:
   - **Refresh**: reloads `j_j.json`
   - **View**: shows a read-only full entry
   - **Details**: shows raw JSON for the selected entry
   - **Delete**: deletes selected entry by `entry_date`, then writes file back

> When the dialog closes, the main window replaces its entries with what the dialog loaded last (sync-from-disk).

---

## 3) UI workflow (tabs and actions)

### Tab: “New entry”
- Inputs: Date, Mood, Symptoms, Emotional shifts, Pain/Discomfort, Libido/Arousal, Notes.
- Primary action: **Add Entry**
  - Saves to `storage/j_j.json`
  - Clears certain fields afterwards

### Tab: “Entries”
- Table view of all entries (newest first).
- Actions:
  - **Export…**: export all entries as `.json`, `.txt`, or `.md`
  - **View entries**: opens advanced dialog with view/details/delete
  - **Delete Selected**: deletes selected rows from the main table

---

## 4) Export workflow

1. Click **Export…**
2. Choose a filename + format (filter controls default extension).
3. Export writes:
   - `.json`: array of dicts (same shape as storage)
   - `.txt`: a human-readable block per entry
   - `.md`: markdown headings per entry

---

## 5) Theme workflow (settings)

- Theme stored in QSettings under key `ui/theme` (values: `"dark"` or `"light"`).
- Menu: **View → Theme → Dark/Light**
- Changing theme:
  1. saves to QSettings
  2. applies stylesheet to entire app
  3. shows animated status message in the status bar
