import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

# NEW
import tempfile
import time
import uuid
from datetime import datetime

# Store data under: <project>/Journey/storage/hrt_data.json
DEFAULT_FILE = os.path.join(os.path.dirname(__file__), "storage", "hrt_data.json")

# NEW: draft + lock
DRAFT_FILE = os.path.join(os.path.dirname(__file__), "storage", "hrt_draft.json")
LOCK_FILE = os.path.join(os.path.dirname(__file__), "storage", ".hrt_data.lock")


def _resolve_path(file_path: str) -> str:
    """Return an absolute, normalized path."""
    return os.path.abspath(os.path.normpath(file_path))


def _acquire_lock(lock_path: str, timeout_s: float = 2.0) -> None:
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError:
            if (time.time() - start) >= timeout_s:
                # best-effort: continue without lock rather than deadlocking UI
                return
            time.sleep(0.05)


def _release_lock(lock_path: str) -> None:
    try:
        os.remove(lock_path)
    except OSError:
        pass


def load_data(file_path: str = DEFAULT_FILE) -> List[Dict[str, Any]]:
    """Load all entries from JSON. Returns a list."""
    file_path = _resolve_path(file_path)
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            # NEW: light schema upgrade (id/timestamps)
            now = datetime.now().isoformat(timespec="seconds")
            changed = False
            for e in data:
                if isinstance(e, dict):
                    if not e.get("id"):
                        e["id"] = str(uuid.uuid4())
                        changed = True
                    if not e.get("created_at"):
                        e["created_at"] = e.get("updated_at") or now
                        changed = True
                    if not e.get("updated_at"):
                        e["updated_at"] = now
                        changed = True
            if changed:
                _write_data(data, file_path)
            return data
    except (json.JSONDecodeError, OSError):
        return []


def _write_data(data: List[Dict[str, Any]], file_path: str = DEFAULT_FILE) -> None:
    file_path = _resolve_path(file_path)
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    _acquire_lock(LOCK_FILE)
    try:
        # NEW: atomic write
        dir_name = os.path.dirname(file_path) or "."
        fd, tmp_path = tempfile.mkstemp(prefix="hrt_", suffix=".tmp", dir=dir_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, file_path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
    finally:
        _release_lock(LOCK_FILE)


def get_entry_by_date(target_date: date, file_path: str = DEFAULT_FILE) -> Optional[Dict[str, Any]]:
    """Return the entry for a specific date if it exists."""
    iso = target_date.isoformat()
    for entry in load_data(file_path):
        if entry.get("date") == iso:
            return entry
    return None


def save_entry(entry: Dict[str, Any], file_path: str = DEFAULT_FILE) -> None:
    """Append a new entry to the JSON file (no dedupe)."""
    data = load_data(file_path)
    data.append(entry)
    _write_data(data, file_path)


def upsert_entry(entry: Dict[str, Any], file_path: str = DEFAULT_FILE) -> bool:
    """
    Insert or replace by entry["date"].
    Returns True if updated, False if inserted.
    """
    iso = (entry.get("date") or "").strip()
    if not iso:
        raise ValueError("entry must include a non-empty 'date' field (YYYY-MM-DD)")

    data = load_data(file_path)
    for i, existing in enumerate(data):
        if existing.get("date") == iso:
            data[i] = entry
            _write_data(data, file_path)
            return True

    data.append(entry)
    _write_data(data, file_path)
    return False


def delete_entry_by_date(target_date: date, file_path: str = DEFAULT_FILE) -> bool:
    """Delete an entry by date. Returns True if deleted."""
    iso = target_date.isoformat()
    data = load_data(file_path)
    new_data = [e for e in data if e.get("date") != iso]
    if len(new_data) == len(data):
        return False
    _write_data(new_data, file_path)
    return True


# NEW: draft persistence (autosave)
def save_draft(entry: Dict[str, Any], file_path: str = DRAFT_FILE) -> None:
    file_path = _resolve_path(file_path)
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)


def load_draft(file_path: str = DRAFT_FILE) -> Optional[Dict[str, Any]]:
    file_path = _resolve_path(file_path)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return raw if isinstance(raw, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def clear_draft(file_path: str = DRAFT_FILE) -> None:
    file_path = _resolve_path(file_path)
    try:
        os.remove(file_path)
    except OSError:
        pass