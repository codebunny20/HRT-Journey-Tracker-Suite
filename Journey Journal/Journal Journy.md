# Journey Journal

A small, local-first journal for tracking day-to-day HRT-related experiences (mood, symptoms, emotional shifts, pain/discomfort, libido/arousal, and free-form notes). The goal is quick daily logging, easy review, and simple exporting—without needing an account or an internet connection.

---

## Key features

- **New entry form** with:
  - Date
  - Mood
  - Symptoms (single-select)
  - Emotional shifts
  - Pain / discomfort
  - Libido / arousal
  - Notes (free text)
- **Entries table** for browsing saved entries
- **View entries dialog**
  - Quick refresh from disk
  - View full entry
  - Details (raw JSON)
  - Delete selected entry
- **Export** to:
  - JSON (`.json`)
  - Plain text (`.txt`)
  - Markdown (`.md`)
- **Theme toggle**
  - View → Theme → Dark/Light (persists across launches)

---

## How to use

### Create a new entry
1. Open the app.
2. Go to the **New entry** tab.
3. Choose your **Date**.
4. Pick values for mood/symptoms/etc.
5. Write any extra details in **Notes**.
6. Click **Add Entry**.

Notes:
- The app avoids saving “empty” entries (you need notes and/or a mood selected).
- Only **one entry per date** is supported. If you save another entry for the same date, the app will prompt you to replace the existing one.

### Browse / delete entries
1. Go to the **Entries** tab.
2. Select one or more rows.
3. Click **Delete Selected** to remove them.

### View full entries (read-only)
1. Click **View entries** (in the Entries tab).
2. Double-click a row or press **View** to see the full entry text.

### Export your journal
1. Go to **Entries** tab.
2. Click **Export…**
3. Pick the format using the file dialog filter (JSON / Text / Markdown).
4. Save.

---

## Data storage

- Data is stored locally in a JSON array file:
  - `storage/j_j.json`
- The `storage` folder is created **next to the script or packaged executable**.

Each entry is stored roughly as:

- `entry_date`: `"YYYY-MM-DD"`
- `mood`: string
- `symptoms`: list of strings
- `emotional_shifts`: string
- `pain_discomfort`: string
- `libido_arousal`: string
- `notes`: string

---

## Privacy

This is **local-first**: your journal stays on your machine unless you export/share it.

---

## Troubleshooting

- If entries disappear, use **View entries → Refresh** (reloads from disk).
- If something fails to save/export, it’s typically a filesystem permission/path issue—try exporting to your Desktop.

---

## Roadmap

See: [Roadmap.md](./Roadmap.md)
