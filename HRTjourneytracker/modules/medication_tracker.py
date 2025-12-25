import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
DOSES_PATH = os.path.join(DATA_DIR, "doses.jsonl")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")

# Curated/common HRT-related meds (non-exhaustive). Used only for UI convenience.
# Keep names short so they fit well in a dropdown.
_HRT_MEDICATION_OPTIONS: List[str] = [
	# Estrogens
	"Estradiol (oral)",
	"Estradiol (sublingual)",
	"Estradiol (patch)",
	"Estradiol (gel)",
	"Estradiol valerate (IM/SC)",
	"Estradiol cypionate (IM/SC)",
	"Conjugated estrogens",
	"Ethinyl estradiol",
	# Anti-androgens / androgen blockers
	"Spironolactone",
	"Cyproterone acetate",
	"Bicalutamide",
	"Flutamide",
	"Finasteride",
	"Dutasteride",
	"GnRH agonist (leuprolide)",
	"GnRH agonist (goserelin)",
	"GnRH agonist (triptorelin)",
	"GnRH antagonist (degarelix)",
	# Progesterone / progestins (when used)
	"Progesterone (micronized)",
	"Medroxyprogesterone acetate",
	# Testosterone (for masculinizing therapy)
	"Testosterone cypionate (IM/SC)",
	"Testosterone enanthate (IM/SC)",
	"Testosterone undecanoate",
	"Testosterone gel",
	"Testosterone cream",
	"Testosterone patch",
	# Puberty blockers (common)
	"Histrelin implant",
	# Adjuncts sometimes used
	"Minoxidil (topical)",
	# Always include an escape hatch
	"Other...",
]


# Generic/common dose strings for quick entry (non-exhaustive; UI convenience only).
_DOSE_OPTIONS: List[str] = [
	"0.5 mg",
	"1 mg",
	"2 mg",
	"4 mg",
	"6 mg",
	"8 mg",
	"10 mg",
	"12.5 mg",
	"25 mg",
	"50 mg",
	"100 mg",
	"200 mg",
	"0.025 mg/day",
	"0.05 mg/day",
	"0.075 mg/day",
	"0.1 mg/day",
	"1 pump",
	"2 pumps",
	"3 pumps",
	"1 packet",
	"2 packets",
	"0.1 mL",
	"0.2 mL",
	"0.25 mL",
	"0.3 mL",
	"0.4 mL",
	"0.5 mL",
	"0.8 mL",
	"1 mL",
	"Other...",
]


def get_medication_options() -> List[str]:
	"""Return UI dropdown options."""
	return list(_HRT_MEDICATION_OPTIONS)


def get_dose_options() -> List[str]:
	"""Return UI dropdown options for dose."""
	return list(_DOSE_OPTIONS)


def _now_iso() -> str:
	return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _ensure_storage() -> None:
	os.makedirs(DATA_DIR, exist_ok=True)
	os.makedirs(EXPORTS_DIR, exist_ok=True)
	if not os.path.exists(DOSES_PATH):
		with open(DOSES_PATH, "w", encoding="utf-8") as _:
			pass


def log_dose(med_name: str, dose: str, taken_at: Optional[str] = None) -> None:
	_ensure_storage()
	row = {
		"id": uuid.uuid4().hex,
		"taken_at": taken_at or _now_iso(),
		"med_name": med_name,
		"dose": dose,
	}
	with open(DOSES_PATH, "a", encoding="utf-8") as f:
		f.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_doses(limit: int = 50) -> List[Dict[str, str]]:
	_ensure_storage()
	rows: List[Dict[str, str]] = []
	with open(DOSES_PATH, "r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			rows.append(json.loads(line))
	return rows[-limit:]


def _read_all() -> List[Dict[str, str]]:
	_ensure_storage()
	rows: List[Dict[str, str]] = []
	with open(DOSES_PATH, "r", encoding="utf-8") as f:
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
	with open(DOSES_PATH, "w", encoding="utf-8") as f:
		for row in rows:
			f.write(json.dumps(row, ensure_ascii=False) + "\n")


def get_dose(dose_id: str) -> Optional[Dict[str, str]]:
	for row in _read_all():
		if row.get("id") == dose_id:
			return row
	return None


def update_dose(dose_id: str, *, med_name: str, dose: str, taken_at: str) -> bool:
	rows = _read_all()
	updated = False
	for r in rows:
		if r.get("id") == dose_id:
			r["med_name"] = med_name
			r["dose"] = dose
			r["taken_at"] = taken_at
			updated = True
			break
	if updated:
		_write_all(rows)
	return updated


def delete_dose(dose_id: str) -> bool:
	rows = _read_all()
	new_rows = [r for r in rows if r.get("id") != dose_id]
	if len(new_rows) == len(rows):
		return False
	_write_all(new_rows)
	return True


def export_dose(dose_id: str) -> Optional[str]:
	row = get_dose(dose_id)
	if not row:
		return None
	_ensure_storage()
	path = os.path.join(EXPORTS_DIR, f"dose_{dose_id}.json")
	with open(path, "w", encoding="utf-8") as f:
		json.dump(row, f, ensure_ascii=False, indent=2)
	return path
