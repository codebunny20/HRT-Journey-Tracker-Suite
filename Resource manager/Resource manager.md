# Resource Manager (Link Manager)

A small desktop app (PySide6 / Qt) for saving, searching, and quickly opening useful links/resources. It’s designed to help you keep a curated list of URLs with titles, then open/copy/remove them in a couple clicks.

## What it does

- Save a **Title + URL** as a “resource”
- View resources in a list (title on the first line, URL on the second line)
- **Search/filter** the list by typing (matches title or URL)
- **Open** the selected link in your default browser
- **Copy** the selected link’s URL to the clipboard
- **Remove** a selected link (with confirmation)
- **Clear inputs** (title/url fields)
- **Clear all** saved links (with confirmation)
- Right‑click context menu on list items: **Open / Copy URL / Remove**
- Double‑click a list item to **Open**

## How to use

### Add a link
1. Type a **Title** (required)
2. Type a **URL** (required)
   - If you enter `example.com` it will be normalized to `https://example.com`
   - Only `http://` and `https://` URLs are accepted
3. Click **Add** (or press Enter in either input)

### Search
- Type into the **Search** box to filter results instantly.
- Search is case-insensitive and matches against both the title and URL.

### Open / Copy
- Select an item in the list
- Click:
  - **Open** to open it in your web browser
  - **Copy URL** to copy it to your clipboard
- You can also:
  - **Double-click** an item to open it
  - **Right-click** an item for the context menu

### Remove
- Select an item
- Click **Remove**
- Confirm the dialog to delete it

### Clear inputs / Clear all
- **Clear Inputs**: clears the Title/URL text boxes.
- **Clear All**: deletes every saved link (cannot be undone).

## Data/storage

The app uses a storage helper (`data.storage.LinkStorage`) to persist your saved links locally.

- Each stored entry is a small record with keys like:
  - `title`
  - `url`
- Links are loaded at startup and saved when you add/remove/clear.
- The exact storage location/filename is defined by `LinkStorage` (see `data/storage.py`).

## Requirements

- Python 3.x
- PySide6

Install dependencies (recommended inside a virtual environment):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -U pip
py -m pip install PySide6
```

## Run from source

From the `Resource manager` folder:

```powershell
py .\main.py
```

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
Build with console enabled so you can see error output:

```powershell
py -m PyInstaller --noconfirm --onefile --console --name "ResourceManager" .\main.py
```

### If imports under `data.*` fail when bundled
Try adding hidden imports:

```powershell
py -m PyInstaller --noconfirm --onefile --windowed --name "ResourceManager" --hidden-import data.ui_main --hidden-import data.storage .\main.py
```

## Notes / behavior

- URL validation is basic and intended to prevent obvious invalid inputs.
- Status text updates at the bottom after actions (added/removed/opened/copied, etc.).
- The list shows items using two lines for readability: title then URL.
