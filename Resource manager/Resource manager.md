# Resource Manager (`main.py`) — Link Manager

A small PySide6 (Qt) desktop app for saving, searching, and quickly opening useful links/resources. It stores **Title + URL** records locally, provides fast filtering, and supports open/copy/remove workflows.

---

## Data storage (where + format)

- Persisted via: `data.storage.LinkStorage`
- Format: a local on-disk store of “resource” records (each record includes at least `title` and `url`).
- Exact location/filename:
  - defined by `LinkStorage` (see `data/storage.py`).
- Saves occur after add/remove/clear operations; loads at startup.

---

## Entry schema (what gets saved)

```json
{
  "title": "Some resource",
  "url": "https://example.com"
}
```

Rules:
- **Title** is required.
- **URL** is required.
- URL normalization:
  - `example.com` becomes `https://example.com`
- Only `http://` and `https://` URLs are accepted (basic validation).

---

## UI: what the user does

### Main window
1. Enter **Title** and **URL**.
2. Click **Add** (or press Enter in either field).
3. Use **Search** to filter items instantly (case-insensitive; matches title or URL).
4. Select a list item and use:
   - **Open** (default browser)
   - **Copy URL** (clipboard)
   - **Remove** (with confirmation)
5. Optional conveniences:
   - Double-click an item to **Open**
   - Right-click a list item for context menu (**Open / Copy URL / Remove**)
   - **Clear Inputs** resets title/url fields
   - **Clear All** deletes everything (with confirmation)

List presentation:
- Two-line items for readability:
  - title on first line, URL on second line.

---

## Key components (how it’s built)

- Storage: `data.storage.LinkStorage` (load/save)
- Filtering: search box filters against both title and URL (case-insensitive)
- Actions update a status label after operations (added/removed/opened/copied)

---

## Run from source

From the `Resource manager` folder:

```powershell
py .\main.py
```

Requirements:
- Python 3.x
- PySide6

Install (recommended in a venv):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -U pip
py -m pip install PySide6
```

---

## Build as a Windows EXE (PyInstaller)

Install PyInstaller:

```powershell
py -m pip install pyinstaller
```

Build a GUI exe (no console window):

```powershell
py -m PyInstaller --noconfirm --onefile --windowed --name "ResourceManager" .\main.py
```

Output:
- `.\dist\ResourceManager.exe`

### If the EXE doesn’t start (debug build)
Use console mode to see errors:

```powershell
py -m PyInstaller --noconfirm --onefile --console --name "ResourceManager" .\main.py
```

### If imports under `data.*` fail when bundled
Add hidden imports:

```powershell
py -m PyInstaller --noconfirm --onefile --windowed --name "ResourceManager" --hidden-import data.ui_main --hidden-import data.storage .\main.py
```

### If Qt/PySide6 plugins are missing at runtime
- Build from an activated venv where PySide6 is installed.
- Upgrade tooling:

```powershell
py -m pip install -U pyinstaller PySide6
```

If needed, collect PySide6:

```powershell
py -m PyInstaller --noconfirm --onefile --windowed --name "ResourceManager" --collect-all PySide6 .\main.py
```

(Only use `--collect-all PySide6` if you hit plugin/runtime errors; it increases bundle size.)
