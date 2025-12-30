# TrackMyHRT — Roadmap

## Phase 0 — Baseline (now)
- [x] Quick entry: date/time + “Now” + calendar picker
- [x] Medications table with dropdowns and dose parsing
- [x] Save entries to JSONL in an app-local storage folder
- [x] View entries (table), view full entry text, view raw JSON, delete entry
- [x] Basic Help dialog + “Open data folder” hint

## Phase 1 — Data quality + small UX wins
- [ ] Add input validation hints in the UI (highlight bad dose cell, missing name, etc.)
- [ ] Make medication “Time” column a time editor widget (instead of plain cell text)
- [ ] Add keyboard shortcuts (Save, View entries, Add/Remove row)
- [ ] Persist window size/position (QSettings)
- [ ] Add “Edit entry” flow (open selected entry, allow changes, save back)

## Phase 2 — Search, filtering, and overview
- [ ] Filters in View Entries (date range, medication name, route)
- [ ] Full-text search across notes/symptoms/mood
- [ ] Summary view (last 7/30 days; counts by medication; adherence hints)
- [ ] “Today” quick filter + jump-to-date

## Phase 3 — Export / import / backup
- [ ] Export to CSV and/or JSON (single file)
- [ ] Import from CSV/JSON with conflict handling
- [ ] One-click backup (copy JSONL with timestamp)
- [ ] Optional autosave backup rotation

## Phase 4 — Privacy and safety features
- [ ] Optional app passcode / OS keychain integration (if desired)
- [ ] “Redact” mode for sharing screenshots (hide notes, hide timestamps)
- [ ] Clear “this is not medical advice” disclaimer in Help/About
- [ ] Data integrity: detect malformed lines and offer repair/cleanup tool

## Phase 5 — Packaging + maintenance
- [ ] PyInstaller build script (one-folder + one-file builds)
- [ ] Add version + About dialog (app version, data path, build date)
- [ ] Basic automated checks (formatting + minimal unit tests for parsing / IO)
- [ ] CI workflow (lint + build artifact)

## Nice-to-haves (later)
- [ ] Charts (dose over time, mood over time) with opt-in metrics
- [ ] Custom lists for dropdown options (user-editable presets)
- [ ] Multi-profile support (separate storage per profile)
- [ ] Optional reminders/notifications (platform dependent)
