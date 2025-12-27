# HRT Journey Tracker — Beta Release Notes (First Launch)

**Version:** Beta 0.1  
**Release date:** 12/26/2025

## Welcome
Thanks for trying the very first beta of **HRT Journey Tracker**. This early build focuses on the core experience (logging + viewing your history) and on collecting feedback to shape the next updates.

## What this beta is for
- Validate the core tracking flow end-to-end
- Catch bugs, crashes, and confusing UI
- Confirm the app is usable across devices/screen sizes

## What’s included (Beta 0.1)
- Basic personal tracking and organization tools
- Create and review entries over time
- Early UI/UX that will change based on feedback

## Known limitations (first launch)
- **UI polish:** spacing/labels may feel rough in places
- **Edge cases:** unusual date/time formats, very large histories, or rapid edits may expose issues
- **Breaking changes:** future betas may change how data is stored or displayed

## Support / Feedback
- Report issues: bunnycontact.me@gmail.com
- If you can, include:
  - App version (e.g., Beta 0.1)
  - Device + OS version
  - Steps to reproduce (numbered)
  - Expected result vs actual result
  - Screenshots/screen recording (if relevant)

**Bug report template (copy/paste):**
- Version:
- Device / OS:
- Steps:
- Expected:
- Actual:
- Attachments:

## Privacy / Data
- This app is intended for personal tracking.  
- **Assume entries may be stored on your device.** If you are testing on a shared device/account, avoid entering sensitive information.

# Features (current)

### App shell / navigation
- Sidebar navigation between:
  - **HRT Log**
  - **Journal**
  - **Resources**
  - **Settings**
- Applies a **QSS theme** (`assets/theme.qss`) on startup (dark by default).
- Global exception handler (`sys.excepthook`) that shows a dialog for unexpected crashes.

### Settings
- **Safe Mode (hide sensitive data)** toggle
- **“Hide Now”** button to quickly toggle Safe Mode
- Safe Mode currently affects:
  - **HRT Log**
  - **Journal**

### HRT Log (Medication Tracker)
- Add daily log entries with:
  - **Date**
  - **Multiple medications per day** (dynamic rows)
  - Per-medication fields:
    - Medication name (editable dropdown)
    - Dosage (editable dropdown)
    - Optional row notes
- Edit workflow:
  - **Edit selected history entry**
  - **Cancel edit**
  - Save changes back into the selected date entry
- History table shows:
  - Date
  - Medications
  - Dosages
  - Notes
- Filtering:
  - Date range **From / To**
  - Filter by a selected **Medication**
  - Clear filters
- Delete selected entry (with confirmation)
- Export:
  - Export filtered view to **.txt**
- Data storage:
  - Saves locally to `data/medication_log.json`
  - Includes a **migration** path for an older single-med schema to the new multi-med schema
- Safe Mode behavior:
  - Dosages masked
  - Notes replaced with “Hidden (Safe Mode)”

### Journal
- Create/edit/delete journal entries with:
  - Title
  - Comma-separated tags
  - Rich text body (stored as HTML from `QTextEdit`)
- Autosave:
  - Periodic autosave (every ~1.5s) when dirty
  - Manual **Save Now** button
- Search:
  - Search across title, tags, and body preview text
- Tag helper:
  - Dropdown list that inserts common tags into the tags field
- Safe Mode behavior:
  - Hides the body editor
  - Masks title/tags inputs (password echo)
  - List titles show “(hidden)”
- Data storage:
  - Saves locally to `data/journal.json`
  - Entries sorted by `updated_at`

### Resources (Links + notes)
- Save local resource items with:
  - Title (required)
  - URL (optional; supports http(s) and local file paths)
  - Category
  - Tags
  - Notes
- Browse UI:
  - Left list of saved resources
  - Right details pane (metadata + notes)
- Search + filters:
  - Search by title/tags/url/notes/category
  - Filter by category
- Actions:
  - Add / Edit / Delete resources
  - Open resource link (opens via OS)
  - Copy link to clipboard
  - Pin/unpin resources (pinned sorted first)
- Shortcuts/UX:
  - Double-click list item to open
  - Enter/Return to open
  - Delete key to delete
  - Ctrl+F focuses search
- Data storage:
  - Stored in `QSettings` under `resources_v1`
  - Categories auto-derived from stored resources

---

## Disclaimer
This app is for personal tracking and organization and does not provide medical advice. Always consult a qualified clinician for medical decisions.
