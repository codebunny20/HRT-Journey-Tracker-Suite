# Resource Manager (Link Manager) — Workflow

## Purpose
A small desktop app (PySide6/Qt) for saving, searching, opening, copying, and deleting useful links. Links are persisted locally via `LinkStorage`.

---

## Folder/Module Structure (high level)
- `Resource manager/main.py`
  - Application entrypoint.
  - Wires UI events (buttons, search box, list interactions) to behavior.
  - Uses `LinkStorage` for persistence.
- `data/ui_main.py`
  - Defines `LinkManagerUI` (Qt widgets: inputs, buttons, list, status label, etc.).
  - Exposes widget references used by `main.py` (e.g., `add_btn`, `list_widget`, `status_label`).
- `data/storage.py`
  - Defines `LinkStorage`:
    - Holds `self.data` as a list of link objects like: `{ "title": str, "url": str }`.
    - Handles load/save (persistence) and mutations (`add_link`, `remove_link`).

> Note: Exact on-disk storage format/location is determined by `LinkStorage` in `data/storage.py`.

---

## Runtime Workflow (what happens when you run it)

### 1) Startup
1. `main.py` creates a `QApplication`.
2. `LinkManagerApp()` is instantiated (subclass of `LinkManagerUI`).
3. `LinkManagerApp.__init__`:
   - Creates `self.storage = LinkStorage()`.
   - Calls `refresh_list()` to render saved links.
   - Connects UI signals to methods (Add/Remove/Open/Copy/Clear/Search).
4. Window is shown; Qt event loop starts.

### 2) Load + Render
- `LinkStorage()` loads existing saved links into `self.storage.data`.
- `refresh_list()`:
  - Reads current search query from `search_input`.
  - Clears the list widget.
  - Iterates through `self.storage.data` and filters by query (matches title or URL).
  - Creates visual list items with:
    - Display text: `"{title}\n{url}"`
    - Hidden payload (`Qt.UserRole`): `{ index, title, url }`
  - Updates the status label with counts.

### 3) User Operations (UI → behavior)

#### A) Add link
Trigger:
- Click **Add** or press Enter in title/url inputs.
Flow:
1. Read `title_input` and `url_input`.
2. Normalize URL:
   - If missing scheme, prefix `https://`.
3. Validate:
   - Title not empty
   - URL not empty
   - URL parses as `http`/`https`
4. `self.storage.add_link(title, url)`
5. `refresh_list()` to reflect change
6. Clear inputs + status message.

#### B) Search/filter
Trigger:
- Typing in `search_input`.
Flow:
- `refresh_list()` runs on each change and filters in-memory list display (does not delete/modify stored data).

#### C) Open link
Trigger:
- Select an item + click **Open**
- Double-click an item
- Context menu → Open
Flow:
1. Resolve selected list item payload.
2. Extract URL from payload.
3. `QDesktopServices.openUrl(QUrl(url))` opens default browser.
4. Status message.

#### D) Copy URL
Trigger:
- Select item + click **Copy URL**
- Context menu → Copy URL
Flow:
1. Resolve selected payload.
2. Clipboard set to the URL.
3. Status message.

#### E) Remove link
Trigger:
- Select item + click **Remove**
- Context menu → Remove
Flow:
1. Resolve selected payload, get stored index.
2. Confirm via dialog.
3. `self.storage.remove_link(index)`
4. `refresh_list()`
5. Status message.

#### F) Clear inputs
Trigger:
- Click **Clear Inputs**
Flow:
- Clears title/url input fields, focuses title field, status message.

#### G) Clear all links
Trigger:
- Click **Clear All**
Flow:
1. If no data: status “Nothing to clear.”
2. Confirm destructive action.
3. `self.storage.data = []`
4. `self.storage.save()`
5. `refresh_list()` + status message.

---

## Data Flow Summary
- Source of truth: `self.storage.data` (list of dicts).
- UI list is regenerated from storage on every `refresh_list()`.
- Selected UI item carries `{index,title,url}` as `Qt.UserRole` data:
  - Used to map UI selection back to storage record.

---

## Error/Edge Handling
- No selection → warning dialog for open/copy/remove.
- Invalid URL or missing fields → warning dialog and focus returned to correct input.
- “Clear all” is guarded by confirmation dialog.

---

## How to Run (typical)
1. Ensure Python + dependencies installed (`PySide6`).
2. Run:
   - `python main.py`
3. Use the UI to add/search/open/copy/remove links; links persist via `LinkStorage`.

---

## Suggested Future Enhancements (optional)
- Edit link (update title/URL).
- Sort links (alphabetical, recently added).
- Tagging/categories.
- Export/import links (JSON/CSV).
