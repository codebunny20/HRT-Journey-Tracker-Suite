import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
JOURNAL_PATH = os.path.join(DATA_DIR, "journal.jsonl")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")


def _now_iso() -> str:
	return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _ensure_storage() -> None:
	os.makedirs(DATA_DIR, exist_ok=True)
	os.makedirs(EXPORTS_DIR, exist_ok=True)
	if not os.path.exists(JOURNAL_PATH):
		with open(JOURNAL_PATH, "w", encoding="utf-8") as _:
			pass


def add_entry(title: str, body: str, created_at: Optional[str] = None) -> None:
	_ensure_storage()
	row = {
		"id": uuid.uuid4().hex,
		"created_at": created_at or _now_iso(),
		"title": title,
		"body": body,
	}
	with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
		f.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_entries(limit: int = 50) -> List[Dict[str, str]]:
	_ensure_storage()
	rows: List[Dict[str, str]] = []
	with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			rows.append(json.loads(line))
	return rows[-limit:]


def _read_all() -> List[Dict[str, str]]:
	_ensure_storage()
	rows: List[Dict[str, str]] = []
	with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			obj = json.loads(line)
			# backfill id for legacy rows
			if "id" not in obj:
				obj["id"] = uuid.uuid4().hex
			rows.append(obj)
	return rows


def _write_all(rows: List[Dict[str, str]]) -> None:
	_ensure_storage()
	with open(JOURNAL_PATH, "w", encoding="utf-8") as f:
		for row in rows:
			f.write(json.dumps(row, ensure_ascii=False) + "\n")


def get_entry(entry_id: str) -> Optional[Dict[str, str]]:
	for row in _read_all():
		if row.get("id") == entry_id:
			return row
	return None


def update_entry(entry_id: str, *, title: str, body: str, created_at: str) -> bool:
	rows = _read_all()
	updated = False
	for r in rows:
		if r.get("id") == entry_id:
			r["title"] = title
			r["body"] = body
			r["created_at"] = created_at
			updated = True
			break
	if updated:
		_write_all(rows)
	return updated


def delete_entry(entry_id: str) -> bool:
	rows = _read_all()
	new_rows = [r for r in rows if r.get("id") != entry_id]
	if len(new_rows) == len(rows):
		return False
	_write_all(new_rows)
	return True


def export_entry(entry_id: str) -> Optional[str]:
	row = get_entry(entry_id)
	if not row:
		return None
	_ensure_storage()
	path = os.path.join(EXPORTS_DIR, f"journal_{entry_id}.json")
	with open(path, "w", encoding="utf-8") as f:
		json.dump(row, f, ensure_ascii=False, indent=2)
	return path
