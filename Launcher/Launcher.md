# HRT Journey Tracker — Launcher

A small PySide6 launcher that scans the workspace for sub-apps and shows a button for each one. Clicking a button starts that app using the same Python interpreter that ran the launcher.

## Requirements

- Python 3.10+ recommended
- `PySide6`

Install:

```bash
python -m pip install PySide6
```

> Tip: If you use a virtual environment, activate it first so the launcher and apps run under the same interpreter.

## Run

From the `Launcher` folder:

```bash
python Launcher.py
```

> Windows note: If `python` isn’t on PATH, try `py Launcher.py`.

## Features (new)

- Deterministic app discovery (stable “entry script” selection rules)
- Depth-2 fallback discovery (optional one-level-nested search when needed)
- Pre-flight syntax/import check via `python -m py_compile` before launching
- Recent activity per app (stored via `QSettings`)
- Keyboard shortcuts for refresh, theme toggle, workspace open, quit, and quick-launch

## How app discovery works

The launcher scans subfolders of the workspace root (the parent folder of `Launcher`).

For each subfolder, it tries to pick a *single* “entry script” in a deterministic way:

1. `<FolderName>.py` (ignores spaces/`_`/`-` differences)
2. `main.py`, `app.py`, then `run.py`
3. If there is exactly one `*.py` file in that folder root, it uses that

It ignores common non-app folders such as: `Launcher`, `.git`, `__pycache__`, `build`, `dist`, `storage`, `assets`, `.venv` / `venv`.

### Depth-2 fallback

If nothing is found directly inside `<AppFolder>/`, the launcher may look one level deeper and will accept a nested script only if it finds **exactly one** valid candidate across the nested folders.

> If multiple nested candidates are found, the app is skipped to avoid launching the wrong script.

## Shortcuts

- Refresh: `F5`
- Open Workspace Folder: `Alt+O`
- Quit: `Ctrl+Q`
- Toggle light theme: `Ctrl+L`
- Launch app: `Alt+<letter>` (auto-assigned per app button)

## Recent activity

The launcher stores “last opened” timestamps via `QSettings` and shows per-app recent activity.

## Troubleshooting

### “Missing dependency: PySide6”
Install it:

```bash
python -m pip install PySide6
```

### “Python could not compile this script”
The launcher runs `python -m py_compile <script>` before launching. Fix syntax/import-time errors in the target script, then refresh (`F5`).

Common causes:
- Missing dependency in the selected interpreter / venv
- Import-time side effects (code that runs at import and raises)
- Syntax errors

### App not showing up
- Ensure the app is in a subfolder under the workspace root.
- Ensure there is a clear entry script (`<FolderName>.py` or `main.py` etc.).
- Avoid placing the entry script under excluded folders like `storage/`, `dist/`, `.venv/`, etc.
- If the entry script is nested, ensure the app folder contains **only one** valid nested candidate (see “Depth-2 fallback”).
`````