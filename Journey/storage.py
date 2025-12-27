import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

# Store data under: <project>/Journey/storage/hrt_data.json
DEFAULT_FILE = os.path.join(os.path.dirname(__file__), "storage", "hrt_data.json")


def _resolve_path(file_path: str) -> str:
    """Return an absolute, normalized path."""
    return os.path.abspath(os.path.normpath(file_path))


def load_data(file_path: str = DEFAULT_FILE) -> List[Dict[str, Any]]:
    """Load all entries from JSON. Returns a list."""
    file_path = _resolve_path(file_path)
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # Corrupted/unreadable file fallback
        return []


def _write_data(data: List[Dict[str, Any]], file_path: str = DEFAULT_FILE) -> None:
    file_path = _resolve_path(file_path)
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


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