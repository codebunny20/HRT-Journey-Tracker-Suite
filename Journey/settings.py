"""
Settings logic for Journey tracker application.

This module is intentionally UI-agnostic. It stores user preferences in a small JSON file.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Any, Dict


APP_DIR = Path(__file__).resolve().parent

# NEW: store settings in a dedicated folder
SETTINGS_DIR = APP_DIR / "settings"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"

# NEW: legacy path (from earlier versions)
LEGACY_SETTINGS_PATH = APP_DIR / "settings.json"


@dataclass(frozen=True)
class AppSettings:
    window_title: str = "HRT Tracker"
    window_width: int = 1000
    window_height: int = 700

    # UI defaults
    default_slider_value: int = 5
    entries_default_view: str = "plain"  # "plain" | "json"
    default_tab_index: int = 0

    # Theme colors (simple hex, e.g. "#0f172a")
    theme_accent: str = "#3b82f6"
    theme_bg: str = "#0f172a"
    theme_text: str = "#e5e7eb"
    theme_muted_text: str = "#f3f4f6"
    theme_surface: str = "rgba(255,255,255,0.03)"
    theme_surface_2: str = "rgba(255,255,255,0.06)"
    theme_border: str = "rgba(255,255,255,0.10)"

    # Styling: keep as a string so hrt.py can directly apply it
    stylesheet: str = ""

    # NEW: safety/UX
    autosave_seconds: int = 30
    confirm_on_delete: bool = True
    confirm_on_exit_with_unsaved: bool = True

    # NEW: optional override for storage location (empty => default in storage.py)
    storage_file_path: str = ""


def _ensure_settings_dir() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _migrate_legacy_settings_if_needed() -> None:
    """
    If an old settings.json exists next to settings.py, move it into settings/settings.json.
    """
    _ensure_settings_dir()
    try:
        if LEGACY_SETTINGS_PATH.exists() and not SETTINGS_PATH.exists():
            LEGACY_SETTINGS_PATH.replace(SETTINGS_PATH)
    except Exception:
        # best-effort migration only
        pass


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _clamp_int(value: Any, fallback: int, *, min_value: int | None = None, max_value: int | None = None) -> int:
    v = _coerce_int(value, fallback)
    if min_value is not None:
        v = max(min_value, v)
    if max_value is not None:
        v = min(max_value, v)
    return v


def _merge_defaults(defaults: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(defaults)
    for k, v in (user or {}).items():
        out[k] = v
    return out


def _coerce_str(value: Any, fallback: str) -> str:
    try:
        s = str(value)
        return s if s is not None else fallback
    except Exception:
        return fallback


def _looks_like_hex_color(s: str) -> bool:
    s = (s or "").strip()
    if len(s) not in (4, 7) or not s.startswith("#"):
        return False
    try:
        int(s[1:], 16)
        return True
    except Exception:
        return False


def _coerce_color(value: Any, fallback: str, *, allow_rgba: bool = True) -> str:
    s = _coerce_str(value, fallback).strip()
    if allow_rgba and s.lower().startswith("rgba("):
        return s
    if _looks_like_hex_color(s):
        return s
    return fallback


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return fallback


def load_settings() -> AppSettings:
    defaults = asdict(AppSettings())

    _migrate_legacy_settings_if_needed()
    _ensure_settings_dir()

    if not SETTINGS_PATH.exists():
        return AppSettings()

    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        merged = _merge_defaults(defaults, raw)

        # basic validation/coercion
        merged["window_width"] = _clamp_int(merged.get("window_width"), defaults["window_width"], min_value=600, max_value=4000)
        merged["window_height"] = _clamp_int(merged.get("window_height"), defaults["window_height"], min_value=400, max_value=3000)
        merged["default_slider_value"] = _clamp_int(
            merged.get("default_slider_value"), defaults["default_slider_value"], min_value=0, max_value=10
        )
        merged["default_tab_index"] = _clamp_int(merged.get("default_tab_index"), defaults["default_tab_index"], min_value=0, max_value=50)

        view = str(merged.get("entries_default_view", defaults["entries_default_view"])).lower().strip()
        merged["entries_default_view"] = view if view in ("plain", "json") else defaults["entries_default_view"]

        # NEW
        merged["autosave_seconds"] = _clamp_int(merged.get("autosave_seconds"), defaults["autosave_seconds"], min_value=5, max_value=600)
        merged["confirm_on_delete"] = _coerce_bool(merged.get("confirm_on_delete"), defaults["confirm_on_delete"])
        merged["confirm_on_exit_with_unsaved"] = _coerce_bool(
            merged.get("confirm_on_exit_with_unsaved"), defaults["confirm_on_exit_with_unsaved"]
        )
        merged["storage_file_path"] = _coerce_str(merged.get("storage_file_path"), defaults["storage_file_path"]).strip()

        # theme validation
        merged["theme_accent"] = _coerce_color(merged.get("theme_accent"), defaults["theme_accent"], allow_rgba=False)
        merged["theme_bg"] = _coerce_color(merged.get("theme_bg"), defaults["theme_bg"], allow_rgba=False)
        merged["theme_text"] = _coerce_color(merged.get("theme_text"), defaults["theme_text"], allow_rgba=False)
        merged["theme_muted_text"] = _coerce_color(merged.get("theme_muted_text"), defaults["theme_muted_text"], allow_rgba=False)

        merged["theme_surface"] = _coerce_color(merged.get("theme_surface"), defaults["theme_surface"], allow_rgba=True)
        merged["theme_surface_2"] = _coerce_color(merged.get("theme_surface_2"), defaults["theme_surface_2"], allow_rgba=True)
        merged["theme_border"] = _coerce_color(merged.get("theme_border"), defaults["theme_border"], allow_rgba=True)

        return AppSettings(**merged)
    except Exception:
        # If settings are corrupted, fall back to defaults (don’t crash the app)
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    _migrate_legacy_settings_if_needed()
    _ensure_settings_dir()

    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# Simple cache so you can call get_settings() often without rereading disk
_settings_cache: AppSettings | None = None


def get_settings(force_reload: bool = False) -> AppSettings:
    global _settings_cache
    if _settings_cache is None or force_reload:
        _settings_cache = load_settings()
    return _settings_cache


def update_settings(**changes: Any) -> AppSettings:
    """
    Merge changes into existing settings, persist to disk, update cache, and return new settings.
    """
    current = asdict(get_settings())
    current.update(changes)
    new_settings = AppSettings(**current)
    save_settings(new_settings)

    global _settings_cache
    _settings_cache = new_settings
    return new_settings

