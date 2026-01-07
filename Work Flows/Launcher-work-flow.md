# Work Flows Folder — Operating Workflow (Launcher)

## Purpose
This folder defines the standard procedures for using and maintaining the **HRT Journey tracker**. Use these workflows to ensure entries, reviews, exports, and backups are done consistently.

---

## Folder Map (What belongs here)
Use this section as the “table of contents” for the Work Flows folder.

- **Launcher-work-flow.md** (this file)  
  Entry point: the end-to-end workflow and how the other workflow docs fit together.

- *(Add/keep other workflow docs here as they exist in your folder, e.g.)*  
  - `Daily-check-in-work-flow.md` — steps for daily logging  
  - `Weekly-review-work-flow.md` — weekly review + trend checks  
  - `Data-maintenance-work-flow.md` — fixing/normalizing entries, deduping, edits  
  - `Export-and-backup-work-flow.md` — exporting data and storing backups  
  - `Troubleshooting-work-flow.md` — common issues and recovery steps

> If a workflow doesn’t exist yet, keep the name here as a placeholder so the folder stays navigable.

---

## Conventions (apply to all workflows)
- **Date format:** `YYYY-MM-DD` for entries, filenames, and exports.
- **Single source of truth:** make edits in the tracker first; regenerate exports from it (not the other way around).
- **Minimal manual edits:** avoid freeform changes that could break consistency; prefer structured fields.
- **Backups:** before major edits (bulk changes, imports, schema changes), create a backup/export.

---

## End-to-End Workflow (Recommended Routine)

### 1) Launch / Start a Session
1. Open the **HRT Journey tracker** from its main location.
2. Confirm you’re editing the **latest** version (no duplicate copies open).
3. Optional: skim last entry to maintain continuity (symptoms, dosage notes, side effects).

**Exit criteria:** tracker is open; you know whether you’re doing a daily entry, review, or maintenance task.

---

### 2) Daily Check-In (Typical)
Use this when you’re adding new observations for the day.

1. Create a new daily entry for `YYYY-MM-DD` (or confirm it doesn’t already exist).
2. Fill in the minimal core fields consistently (example categories):
   - Medication / dosage
   - Physical symptoms
   - Mood / energy / sleep
   - Notes (short, objective)
3. Sanity check:
   - No missing date
   - Units consistent (mg, mL, etc.)
   - No duplicate entry for the same date

**Exit criteria:** today’s record exists and is complete enough to be useful later.

---

### 3) Weekly Review (Once per week)
Use this to summarize and find trends.

1. Pick the review window (e.g., last 7 days).
2. Spot-check for:
   - Missing days
   - Outliers (unusual symptoms, doses, measurements)
   - Emerging trends (sleep, mood stability, side effects)
3. Write a short weekly summary (bullet points).
4. Flag anything needing follow-up (questions for clinician, dosage discussion topics).

**Exit criteria:** you have a weekly summary + a short list of follow-ups.

---

### 4) Data Maintenance (As needed)
Use when something is inconsistent or needs correction.

1. Decide scope:
   - Single entry fix (typo, wrong unit)
   - Batch fix (rename a tag/category, normalize measurement units)
2. Before bulk edits: export a backup snapshot.
3. Apply the change.
4. Verify:
   - Historical entries still readable
   - No broken formulas/relationships (if applicable)

**Exit criteria:** data is consistent; no unintended changes.

---

### 5) Export & Backup (Recommended monthly + before risky edits)
1. Export your tracker data (use `YYYY-MM-DD` in file names).
2. Store in a dedicated backup location (preferably outside the working folder).
3. Confirm export opens correctly.

**Exit criteria:** you can restore from the backup/export if needed.

---

## Quick Checklists

### Daily (2–5 minutes)
- [ ] Entry exists for today
- [ ] Core fields filled
- [ ] Units consistent
- [ ] Short note added (if anything notable)

### Weekly (10–20 minutes)
- [ ] No missing days
- [ ] Trends noted
- [ ] Questions/follow-ups captured

### Before Bulk Changes
- [ ] Export/backup created
- [ ] Change applied
- [ ] Verify key views/metrics still correct

---

## Troubleshooting (Pointers)
- **Duplicate entries:** keep one; merge notes; delete/mark duplicates.
- **Wrong date:** correct to `YYYY-MM-DD`; verify ordering.
- **Inconsistent units/tags:** normalize using the same spelling/units everywhere.
- **Accidental edits:** revert using latest backup/export.

---

## How to Extend This Folder
When you add a new workflow file:
1. Create the file in this folder with a clear name.
2. Add it to the **Folder Map** section above.
3. Keep each workflow structured as:
   - Purpose
   - When to use
   - Steps
   - Exit criteria
   - Checklist (optional)
