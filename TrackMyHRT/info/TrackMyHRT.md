# TrackMyHRT (`HRT.py`)

A small PySide6 (Qt) desktop app to log HRT entries: **date/time**, **medications**, optional **mood/energy/symptoms/libido** (multi-select), and **notes**.

---

## Data storage (where + format)

- Stored in: `storage/entries.json` (next to `HRT.py`, or next to the packaged `.exe` when frozen)
- Format: **JSON array** (list) of entry objects.
- Legacy: if `entries.json` is empty and `storage/entries.jsonl` exists, the app migrates JSONL → JSON and adds missing IDs.

---

## Entry schema (what gets saved)

```json
{
  "id": "uuidhex",
  "created_at": "YYYY-MM-DD HH:mm",
  "updated_at": "YYYY-MM-DD HH:mm",
  "timestamp_local": "YYYY-MM-DD HH:mm",
  "date": "YYYY-MM-DD",
  "time": "HH:mm",
  "medications": [
    { "name": "Estradiol", "dose": 2.0, "unit": "mg", "route": "Oral", "time": "08:00" }
  ],
  "mood": ["Calm"],
  "energy": ["Normal"],
  "symptoms": ["Headache"],
  "libido": ["Low"],
  "notes": "..."
}
```

Rules:
- Saving requires **at least one medication name**.
- `mood/energy/symptoms/libido` are saved as **lists of strings**.
- Viewer/export code tolerates older files where these might be a single string.

---

## UI: what the user does

### Main window
1. Set **Date/Time** (or click **Now** / **Pick date…**).
2. Add one or more **Medication** rows (Name/Dose/Unit/Route/Time).
3. Optionally select **Mood/Energy/Symptoms/Libido** and write **Notes**.
4. Click **Save entry** → app appends to `entries.json`.

### View entries dialog
- Shows saved entries (newest first)
- Actions: **View** (full text), **Details** (raw JSON), **Delete**, **Export…**

---

## Multi-select fields (Mood/Energy/Symptoms/Libido)

Implemented by `MultiSelectCombo`: a dropdown checklist that returns/sets values as a list of strings.

---

## Export

From **View entries → Export…**:
- `.jsonl` (one JSON object per line)
- `.json` (array)
- `.txt` (human-readable)
- `.md` (markdown)

---

# More detailed info and explanations
