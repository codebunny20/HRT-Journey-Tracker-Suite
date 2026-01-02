# Journey Journal — Roadmap

This roadmap tracks planned improvements for the Journey Journal app. Items are grouped by timeframe and scoped to the current desktop, local-first direction.

---

## Near-term (next iterations)

- **Multi-select symptoms**
  - Replace single symptom dropdown with multi-select (checkbox list or tag-style picker).
- **Search + filter**
  - Date range filter
  - Mood / symptom filters
  - Text search across notes
- **Sorting controls**
  - Clickable header sorting (date/mood/etc.)
  - Default: newest first
- **Edit entry flow**
  - Edit selected entry directly (instead of “replace by date” only)
  - Preserve date uniqueness constraint (optional setting later)
- **Quick stats**
  - Simple counts over time (mood distribution, symptom frequency)
  - “Last 30 days” summary

---

## Medium-term

- **Tags**
  - User-defined tags per entry
  - Filter by tag
- **Configurable dropdown lists**
  - Customize mood/symptom/emotional shift options in settings
- **Backups**
  - Automatic rotating backups in `storage/backup/`
  - “Restore from backup” UI
- **Data resilience**
  - File-locking / safer writes
  - Corruption detection + recovery prompts

---

## Longer-term / optional

- **Encryption at rest**
  - Password-protected journal file (opt-in)
- **Import tools**
  - Import from prior exports (JSON/Markdown)
- **Reporting**
  - Printable summary export (PDF via export pipeline)
- **Attachments**
  - Optional photos/documents stored locally and linked to an entry

---
## Notes / non-goals (for now)

- No cloud sync or accounts by default (keep it local-first).
- No medical guidance features; app remains a journaling/tracking tool.
