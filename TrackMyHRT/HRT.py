import json
import os
import sys
import re
import uuid  # <-- add
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QComboBox,
    QFileDialog,
)

from PySide6.QtCore import QSettings

# --- add: MultiSelectCombo support (same UX as symptoms) ---
from PySide6.QtCore import QEvent
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QToolButton, QMenu, QWidgetAction
# --- end add ---

APP_TITLE = "TrackMyHRT"
org_name = "HRT Journey Tracker"
DATA_FILENAME = "entries.json"  # <-- changed (was entries.jsonl)
LEGACY_JSONL_FILENAME = "entries.jsonl"  # <-- add
STORAGE_DIRNAME = "storage"

SETTINGS_THEME_KEY = "ui/theme"  # "dark" | "light"
THEME_DARK = "dark"
THEME_LIGHT = "light"

DARK_STYLESHEET = """
QWidget { background: #121212; color: #eaeaea; }
QGroupBox { border: 1px solid #2a2a2a; margin-top: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #eaeaea; }
QLineEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QComboBox, QTableWidget {
  background: #1b1b1b; color: #eaeaea; border: 1px solid #2a2a2a;
}
QHeaderView::section { background: #1b1b1b; color: #eaeaea; border: 1px solid #2a2a2a; padding: 4px; }
QPushButton { background: #232323; border: 1px solid #2f2f2f; padding: 6px 10px; }
QPushButton:hover { background: #2a2a2a; }
QPushButton:pressed { background: #1f1f1f; }
QMenuBar { background: #121212; }
QMenu { background: #1b1b1b; border: 1px solid #2a2a2a; }
QStatusBar { background: #121212; }
"""

LIGHT_STYLESHEET = """
QWidget { background: #f6f6f6; color: #111; }
QGroupBox { border: 1px solid #d0d0d0; margin-top: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #111; }
QLineEdit, QPlainTextEdit, QDateEdit, QTimeEdit, QComboBox, QTableWidget {
  background: #ffffff; color: #111; border: 1px solid #cfcfcf;
}
QHeaderView::section { background: #efefef; color: #111; border: 1px solid #d0d0d0; padding: 4px; }
QPushButton { background: #ffffff; border: 1px solid #cfcfcf; padding: 6px 10px; }
QPushButton:hover { background: #f0f0f0; }
QPushButton:pressed { background: #e6e6e6; }
QMenuBar { background: #f6f6f6; }
QMenu { background: #ffffff; border: 1px solid #cfcfcf; }
QStatusBar { background: #f6f6f6; }
"""

def _apply_app_theme(theme: str, settings: QSettings | None = None, persist: bool = True) -> str:
    t = (theme or "").strip().lower()
    if t not in (THEME_DARK, THEME_LIGHT):
        t = THEME_DARK
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(DARK_STYLESHEET if t == THEME_DARK else LIGHT_STYLESHEET)
    if persist and settings is not None:
        settings.setValue(SETTINGS_THEME_KEY, t)
    return t

@dataclass
class MedicationRow:
    name: str
    dose: float
    unit: str
    route: str
    time: str  # "HH:mm"

def _ensure_storage_ready() -> str:
    """
    Ensures ./storage exists next to this script (dev) or next to the packaged exe.
    Returns full path to entries.json.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    storage_dir = os.path.join(base_dir, STORAGE_DIRNAME)
    os.makedirs(storage_dir, exist_ok=True)

    path = os.path.join(storage_dir, DATA_FILENAME)
    if not os.path.exists(path):
        # create empty JSON array file
        with open(path, "w", encoding="utf-8") as f:
            f.write("[]")
    return path

def _app_data_path() -> str:
    # Centralize the canonical storage location (JSON array file).
    return _ensure_storage_ready()

def _legacy_jsonl_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, STORAGE_DIRNAME, LEGACY_JSONL_FILENAME)

def _read_entries_json(path: str) -> List[Dict[str, Any]]:
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, list) else []
    except Exception:
        return []

def _write_entries_json_atomic(path: str, entries: List[Dict[str, Any]]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _ensure_entry_ids(entries: List[Dict[str, Any]]) -> bool:
    """
    Ensures every entry has an 'id'. Returns True if any entries changed.
    """
    changed = False
    for e in entries:
        if isinstance(e, dict) and not str(e.get("id") or "").strip():
            e["id"] = uuid.uuid4().hex
            # best-effort timestamps
            ts = str(e.get("timestamp_local") or "").strip()
            if ts and not e.get("created_at"):
                e["created_at"] = ts
            if ts and not e.get("updated_at"):
                e["updated_at"] = ts
            changed = True
    return changed

def _migrate_jsonl_to_json_if_needed() -> None:
    """
    One-time migration:
    - If entries.json is empty (or missing) and legacy entries.jsonl exists with data,
      convert jsonl lines into a JSON array with ids.
    """
    json_path = _app_data_path()
    existing = _read_entries_json(json_path)
    if existing:
        return

    legacy = _legacy_jsonl_path()
    if not os.path.exists(legacy):
        return

    migrated: List[Dict[str, Any]] = []
    try:
        with open(legacy, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        migrated.append(obj)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return

    if not migrated:
        return

    _ensure_entry_ids(migrated)
    _write_entries_json_atomic(json_path, migrated)

def _load_entries() -> List[Dict[str, Any]]:
    _migrate_jsonl_to_json_if_needed()
    path = _app_data_path()
    entries = _read_entries_json(path)
    if _ensure_entry_ids(entries):
        # persist ids if we had to add them
        try:
            _write_entries_json_atomic(path, entries)
        except OSError:
            pass
    # newest-first
    entries.sort(key=lambda e: (e.get("timestamp_local") or ""), reverse=True)
    return entries

def _delete_entry_by_id(entry_id: str) -> bool:
    if not entry_id:
        return False
    path = _app_data_path()
    entries = _read_entries_json(path)
    before = len(entries)
    entries = [e for e in entries if str(e.get("id") or "") != entry_id]
    if len(entries) == before:
        return False
    _write_entries_json_atomic(path, entries)
    return True

def _upsert_entry(updated: Dict[str, Any]) -> None:
    """
    Insert if id not found; replace if id found.
    """
    path = _app_data_path()
    entries = _read_entries_json(path)

    entry_id = str(updated.get("id") or "").strip()
    if not entry_id:
        entry_id = uuid.uuid4().hex
        updated["id"] = entry_id

    replaced = False
    for i, e in enumerate(entries):
        if str(e.get("id") or "") == entry_id:
            entries[i] = updated
            replaced = True
            break
    if not replaced:
        entries.append(updated)

    _write_entries_json_atomic(path, entries)

# --- add: multi-select combo widget (checklist dropdown) ---
class MultiSelectCombo(QToolButton):
    def __init__(self, options: List[str], placeholder: str = "", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder or "Select…"
        self._menu = QMenu(self)
        self._model = QStandardItemModel(self)

        # allow clicking menu items without auto-closing
        self._menu.installEventFilter(self)

        for opt in options:
            if not opt:
                continue
            item = QStandardItem(opt)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setData(Qt.Unchecked, Qt.CheckStateRole)
            self._model.appendRow(item)

            act = QWidgetAction(self._menu)
            cb = QToolButton(self._menu)
            cb.setText(opt)
            cb.setToolButtonStyle(Qt.ToolButtonTextOnly)
            cb.setCheckable(True)
            cb.setChecked(False)
            cb.clicked.connect(lambda checked, it=item: self._toggle_item(it, checked))
            act.setDefaultWidget(cb)
            self._menu.addAction(act)

        self.setMenu(self._menu)
        self.setPopupMode(QToolButton.InstantPopup)
        self._sync_text()

    def eventFilter(self, obj, event):
        if obj is self._menu and event.type() in (QEvent.MouseButtonRelease, QEvent.MouseButtonPress):
            return True  # keep menu open while selecting multiple items
        return super().eventFilter(obj, event)

    def _toggle_item(self, item: QStandardItem, checked: bool):
        item.setData(Qt.Checked if checked else Qt.Unchecked, Qt.CheckStateRole)
        self._sync_text()

    def _sync_text(self):
        vals = self.values()
        self.setText(", ".join(vals) if vals else self._placeholder)

    def values(self) -> List[str]:
        out: List[str] = []
        for r in range(self._model.rowCount()):
            it = self._model.item(r)
            if it and it.checkState() == Qt.Checked:
                out.append(it.text())
        return out

    def set_values(self, values: List[str]):
        wanted = set((v or "").strip() for v in (values or []) if (v or "").strip())
        for r in range(self._model.rowCount()):
            it = self._model.item(r)
            if not it:
                continue
            it.setData(Qt.Checked if it.text() in wanted else Qt.Unchecked, Qt.CheckStateRole)
        for act in self._menu.actions():
            if isinstance(act, QWidgetAction):
                w = act.defaultWidget()
                if isinstance(w, QToolButton):
                    w.blockSignals(True)
                    w.setChecked(w.text() in wanted)
                    w.blockSignals(False)
        self._sync_text()
# --- end add ---

class CalendarDialog(QDialog):
    def __init__(self, initial_date: QDate, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick a date")
        self.setModal(True)

        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(initial_date)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.calendar)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_date(self) -> QDate:
        return self.calendar.selectedDate()

class ViewEntriesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View entries")
        self.setModal(True)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Medications", "Mood", "Symptoms", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Simple usability: double-click row to open full view
        self.table.doubleClicked.connect(self._view_selected)

        self.refresh_btn = QPushButton("Refresh", self)
        self.refresh_btn.clicked.connect(self._refresh)

        self.view_btn = QPushButton("View", self)
        self.view_btn.setToolTip("View the full selected entry")
        self.view_btn.clicked.connect(self._view_selected)

        self.details_btn = QPushButton("Details", self)
        self.details_btn.clicked.connect(self._show_details)

        self.delete_btn = QPushButton("Delete", self)
        self.delete_btn.setToolTip("Delete the selected entry")
        self.delete_btn.clicked.connect(self._delete_selected)

        self.export_btn = QPushButton("Export…", self)
        self.export_btn.setToolTip("Export all entries (JSONL/JSON/TXT/MD)")
        self.export_btn.clicked.connect(self._export_entries)

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.view_btn)
        btn_row.addWidget(self.details_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        self._entries: List[Dict[str, Any]] = []
        self._refresh()

    def _load_entries(self) -> List[Dict[str, Any]]:
        return _load_entries()

    def _meds_summary(self, meds: Any) -> str:
        if not isinstance(meds, list):
            return ""
        parts: List[str] = []
        for m in meds:
            if not isinstance(m, dict):
                continue
            name = (m.get("name") or "").strip()
            dose = m.get("dose")
            unit = (m.get("unit") or "").strip()
            route = (m.get("route") or "").strip()
            time = (m.get("time") or "").strip()

            s = name
            if dose not in (None, "", 0, 0.0):
                s = f"{s} {dose:g}"
            if unit:
                s = f"{s} {unit}"
            if route:
                s = f"{s} ({route})"
            if time:
                s = f"{s} @ {time}"
            s = s.strip()
            if s:
                parts.append(s)
        return "; ".join(parts)

    # --- add: list-or-string formatter (for backward compatibility) ---
    def _listish_to_text(self, val: Any) -> str:
        if isinstance(val, list):
            return ", ".join(str(x) for x in val if str(x).strip())
        return str(val or "").strip()
    # --- end add ---

    def _refresh(self):
        self._entries = self._load_entries()
        self.table.setRowCount(0)

        for entry in self._entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            ts = str(entry.get("timestamp_local") or "")
            meds = self._meds_summary(entry.get("medications"))
            mood = self._listish_to_text(entry.get("mood"))
            symptoms = self._listish_to_text(entry.get("symptoms"))
            notes = str(entry.get("notes") or "")

            for col, text in enumerate([ts, meds, mood, symptoms, notes]):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def _selected_entry(self) -> Dict[str, Any] | None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        r = sel[0].row()
        if r < 0 or r >= len(self._entries):
            return None
        return self._entries[r]

    def _delete_selected(self):
        entry = self._selected_entry()
        if not entry:
            return

        entry_id = str(entry.get("id") or "").strip()
        ts = str(entry.get("timestamp_local") or "")
        preview = ts or "(no timestamp)"

        ok = QMessageBox.question(
            self,
            "Delete entry?",
            f"Delete this entry?\n\n{preview}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ok != QMessageBox.Yes:
            return

        try:
            removed = _delete_entry_by_id(entry_id)
        except OSError as e:
            QMessageBox.critical(self, "Delete failed", f"Could not write:\n{_app_data_path()}\n\n{e}")
            return

        if not removed:
            QMessageBox.warning(self, "Not found", "Could not find the selected entry (it may have changed).")
            self._refresh()
            return

        QMessageBox.information(self, "Deleted", "Entry deleted.")
        self._refresh()

    def _show_details(self):
        entry = self._selected_entry()
        if not entry:
            return
        QMessageBox.information(self, "Entry details", json.dumps(entry, ensure_ascii=False, indent=2))

    def _format_entry_plain_text(self, entry: Dict[str, Any]) -> str:
        ts = str(entry.get("timestamp_local") or "").strip()
        date = str(entry.get("date") or "").strip()
        time = str(entry.get("time") or "").strip()

        # --- change: support list-or-string fields + include energy ---
        mood = self._listish_to_text(entry.get("mood"))
        energy = self._listish_to_text(entry.get("energy"))
        symptoms = self._listish_to_text(entry.get("symptoms"))
        libido = self._listish_to_text(entry.get("libido"))
        # --- end change ---

        notes = str(entry.get("notes") or "").rstrip()

        lines: List[str] = []
        lines.append("Entry")
        lines.append("=" * 40)
        if ts:
            lines.append(f"Timestamp: {ts}")
        if date:
            lines.append(f"Date:      {date}")
        if time:
            lines.append(f"Time:      {time}")
        lines.append("")

        lines.append("Medications")
        lines.append("-" * 40)
        meds = entry.get("medications")
        if isinstance(meds, list) and meds:
            for m in meds:
                if not isinstance(m, dict):
                    continue
                name = str(m.get("name") or "").strip()
                dose = m.get("dose")
                unit = str(m.get("unit") or "").strip()
                route = str(m.get("route") or "").strip()
                mt = str(m.get("time") or "").strip()

                parts: List[str] = []
                if name:
                    parts.append(name)
                if dose not in (None, "", 0, 0.0):
                    try:
                        parts.append(f"{float(dose):g}")
                    except Exception:
                        parts.append(str(dose))
                if unit:
                    parts.append(unit)
                if route:
                    parts.append(f"({route})")
                if mt:
                    parts.append(f"@ {mt}")

                line = " ".join(parts).strip()
                if line:
                    lines.append(f"- {line}")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("Mood / Symptoms")
        lines.append("-" * 40)
        lines.append(f"Mood:     {mood if mood else '(none)'}")
        lines.append(f"Energy:   {energy if energy else '(none)'}")
        lines.append(f"Symptoms: {symptoms if symptoms else '(none)'}")
        lines.append(f"Libido:   {libido if libido else '(none)'}")
        lines.append("")

        lines.append("Notes")
        lines.append("-" * 40)
        lines.append(notes if notes else "(none)")

        return "\n".join(lines)

    def _view_selected(self):
        entry = self._selected_entry()
        if not entry:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Entry")
        dlg.setModal(True)

        # Show a friendly, full readable view (scrollable + wrapped)
        text = QPlainTextEdit(dlg)
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        text.setPlainText(self._format_entry_plain_text(entry))

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dlg)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)

        layout = QVBoxLayout()
        layout.addWidget(text)
        layout.addWidget(buttons)
        dlg.setLayout(layout)

        dlg.resize(850, 600)
        dlg.exec()

    def _format_entry_txt(self, entry: Dict[str, Any]) -> str:
        ts = str(entry.get("timestamp_local") or "").strip()
        date = str(entry.get("date") or "").strip()
        time = str(entry.get("time") or "").strip()

        # --- change: support list-or-string fields + include energy ---
        mood = self._listish_to_text(entry.get("mood"))
        energy = self._listish_to_text(entry.get("energy"))
        symptoms = self._listish_to_text(entry.get("symptoms"))
        libido = self._listish_to_text(entry.get("libido"))
        # --- end change ---

        notes = str(entry.get("notes") or "").rstrip()

        meds_lines: List[str] = []
        meds = entry.get("medications")
        if isinstance(meds, list) and meds:
            for m in meds:
                if not isinstance(m, dict):
                    continue
                name = str(m.get("name") or "").strip()
                dose = m.get("dose")
                unit = str(m.get("unit") or "").strip()
                route = str(m.get("route") or "").strip()
                mt = str(m.get("time") or "").strip()

                parts: List[str] = []
                if name:
                    parts.append(name)
                if dose not in (None, "", 0, 0.0):
                    try:
                        parts.append(f"{float(dose):g}")
                    except Exception:
                        parts.append(str(dose))
                if unit:
                    parts.append(unit)
                if route:
                    parts.append(f"({route})")
                if mt:
                    parts.append(f"@ {mt}")
                line = " ".join(parts).strip()
                if line:
                    meds_lines.append(f"- {line}")

        if not meds_lines:
            meds_lines = ["- (none)"]

        parts = [
            "Entry",
            "=" * 40,
            f"Timestamp: {ts}" if ts else None,
            f"Date:      {date}" if date else None,
            f"Time:      {time}" if time else None,
            "",
            "Medications",
            "-" * 40,
            *meds_lines,
            "",
            "Mood / Symptoms",
            "-" * 40,
            f"Mood:     {mood if mood else '(none)'}",
            f"Energy:   {energy if energy else '(none)'}",
            f"Symptoms: {symptoms if symptoms else '(none)'}",
            f"Libido:   {libido if libido else '(none)'}",
            "",
            "Notes",
            "-" * 40,
            notes if notes else "(none)",
        ]
        return "\n".join([p for p in parts if p is not None])

    def _format_entry_md(self, entry: Dict[str, Any]) -> str:
        ts = str(entry.get("timestamp_local") or "").strip()
        date = str(entry.get("date") or "").strip() or (ts.split(" ")[0] if ts else "")

        # --- change: support list-or-string fields + include energy ---
        mood = self._listish_to_text(entry.get("mood"))
        energy = self._listish_to_text(entry.get("energy"))
        symptoms = self._listish_to_text(entry.get("symptoms"))
        libido = self._listish_to_text(entry.get("libido"))
        # --- end change ---

        notes = (str(entry.get("notes") or "")).rstrip() or "(none)"

        meds = entry.get("medications")
        meds_lines: List[str] = []
        if isinstance(meds, list) and meds:
            for m in meds:
                if not isinstance(m, dict):
                    continue
                name = str(m.get("name") or "").strip()
                dose = m.get("dose")
                unit = str(m.get("unit") or "").strip()
                route = str(m.get("route") or "").strip()
                mt = str(m.get("time") or "").strip()

                s = name
                if dose not in (None, "", 0, 0.0):
                    try:
                        s = f"{s} {float(dose):g}"
                    except Exception:
                        s = f"{s} {dose}"
                if unit:
                    s = f"{s} {unit}"
                if route:
                    s = f"{s} ({route})"
                if mt:
                    s = f"{s} @ {mt}"
                s = s.strip()
                if s:
                    meds_lines.append(f"- {s}")
        if not meds_lines:
            meds_lines = ["- (none)"]

        heading = date or (ts if ts else "Entry")
        return (
            f"## {heading}\n\n"
            + (f"- **Timestamp:** {ts}\n" if ts else "")
            + "- **Medications:**\n"
            + "\n".join(meds_lines)
            + "\n\n"
            + f"- **Mood:** {mood or '(none)'}\n"
            + f"- **Energy:** {energy or '(none)'}\n"
            + f"- **Symptoms:** {symptoms or '(none)'}\n"
            + f"- **Libido:** {libido or '(none)'}\n\n"
            + "### Notes\n\n"
            + f"{notes}\n"
        )

    def _export_entries(self):
        # Export whatever the dialog currently has loaded (refresh first if you want)
        src = _app_data_path()
        entries = list(self._entries or [])
        if not entries:
            QMessageBox.information(self, "Export", f"No entries to export.\n\nData file:\n{src}")
            return

        default_base = os.path.join(os.path.expanduser("~"), "trackmyhrt_export")
        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export entries",
            default_base,
            "JSON Lines (*.jsonl);;JSON (*.json);;Text (*.txt);;Markdown (*.md);;All files (*.*)",
        )
        if not path_str:
            return

        out_path = path_str
        root, ext = os.path.splitext(out_path)
        if ext == "":
            if selected_filter.startswith("JSON Lines"):
                out_path = root + ".jsonl"
            elif selected_filter.startswith("JSON"):
                out_path = root + ".json"
            elif selected_filter.startswith("Markdown"):
                out_path = root + ".md"
            else:
                out_path = root + ".txt"

        ext = os.path.splitext(out_path)[1].lower()

        try:
            if ext == ".jsonl":
                # Stored format is JSON array; generate JSONL export from entries.
                with open(out_path, "w", encoding="utf-8") as f:
                    for e in entries:
                        f.write(json.dumps(e, ensure_ascii=False) + "\n")
            elif ext == ".json":
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(entries, f, indent=2, ensure_ascii=False)
            elif ext == ".md":
                md = "# TrackMyHRT export\n\n" + "\n\n".join(self._format_entry_md(e) for e in entries) + "\n"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(md)
            else:
                txt = "\n\n".join(self._format_entry_txt(e) for e in entries) + "\n"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(txt)
        except OSError as e:
            QMessageBox.critical(self, "Export failed", f"Could not export:\n{e}")
            return

        QMessageBox.information(self, "Exported", f"Exported to:\n{out_path}")

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setModal(True)

        text = QPlainTextEdit(self)
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        text.setPlainText(
            "HRT Journey Tracker — Help\n"
            "\n"
            "Quick entry (Date/Time)\n"
            "- Use Date and Time to set when the entry happened.\n"
            "- Click “Pick date…” to choose from a calendar.\n"
            "- Click “Now” to set date/time to the current moment.\n"
            "\n"
            "Medications\n"
            "- Click “Add medication” to add a row.\n"
            "- Fill in Name, Dose, Unit, Route, and (optional) Time.\n"
            "- Dose accepts values like: 2, 2.0, 2 mg, 2,5 (comma works).\n"
            "- Empty rows are ignored.\n"
            "- Click “Remove selected” to delete highlighted row(s).\n"
            "\n"
            "Mood / Symptoms / Notes\n"
            "- Mood, Energy, Symptoms, and Libido support selecting multiple items.\n"
            "- Notes are optional; use for anything you want to remember.\n"
            "\n"
            "Saving\n"
            "- Click “Save entry” to append a new entry to the data file.\n"
            "- At least one medication Name is required to save.\n"
            "\n"
            "Viewing / Managing entries\n"
            "- Click “View entries” to see saved entries (newest first).\n"
            "- Double-click an entry (or click “View”) to open a full view.\n"
            "- Click “Details” to see raw JSON.\n"
            "- Click “Delete” to permanently remove the selected entry.\n"
            "\n"
            "Data location\n"
            "- Entries are stored in a JSON file in the app’s storage folder.\n"
            "- Use File → “Open data folder” to see the exact path.\n"
        )

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(text)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.resize(760, 520)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)

        self._settings = QSettings(org_name, APP_TITLE)
        self._theme = str(self._settings.value(SETTINGS_THEME_KEY, THEME_DARK) or THEME_DARK).lower()
        self._theme = _apply_app_theme(self._theme, self._settings, persist=False)

        root = QWidget(self)
        self.setCentralWidget(root)

        # Simple feedback line (low effort, helps UX)
        self.statusBar().showMessage("Ready")

        # Top: date/time controls
        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(False)  # uses our calendar dialog
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setToolTip("Entry date")

        self.time_edit = QTimeEdit(self)
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.setToolTip("Entry time")

        self.now_btn = QPushButton("Now", self)
        self.now_btn.setToolTip("Set date/time to current")
        self.now_btn.clicked.connect(self._set_now)

        self.pick_date_btn = QPushButton("Pick date…", self)
        self.pick_date_btn.setToolTip("Open calendar")
        self.pick_date_btn.clicked.connect(self._open_calendar)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addWidget(QLabel("Date:"))
        top_row.addWidget(self.date_edit)
        top_row.addWidget(self.pick_date_btn)
        top_row.addSpacing(12)
        top_row.addWidget(QLabel("Time:"))
        top_row.addWidget(self.time_edit)
        top_row.addWidget(self.now_btn)
        top_row.addStretch(1)

        dt_group = QGroupBox("Quick entry")
        dt_layout = QVBoxLayout()
        dt_layout.setContentsMargins(10, 10, 10, 10)
        dt_layout.addLayout(top_row)
        dt_group.setLayout(dt_layout)

        self.meds_table = QTableWidget(0, 5, self)
        self.meds_table.setHorizontalHeaderLabels(["Name", "Dose", "Unit", "Route", "Time"])
        self.meds_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4):
            self.meds_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.meds_table.verticalHeader().setVisible(False)
        self.meds_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.meds_table.setAlternatingRowColors(True)

        self.add_med_btn = QPushButton("Add medication", self)
        self.add_med_btn.clicked.connect(self._add_med_row)

        self.remove_med_btn = QPushButton("Remove selected", self)
        self.remove_med_btn.clicked.connect(self._remove_selected_rows)

        meds_btns = QHBoxLayout()
        meds_btns.setSpacing(8)
        meds_btns.addWidget(self.add_med_btn)
        meds_btns.addWidget(self.remove_med_btn)
        meds_btns.addStretch(1)

        meds_group = QGroupBox("Medications")
        meds_layout = QVBoxLayout()
        meds_layout.setContentsMargins(10, 10, 10, 10)
        meds_layout.setSpacing(8)
        meds_layout.addWidget(self.meds_table)
        meds_layout.addLayout(meds_btns)
        meds_group.setLayout(meds_layout)

        self.unit_options = ["", "mg", "mcg", "g", "mL", "IU", "patch", "pump", "tablet"]
        self.route_options = ["", "Oral", "Sublingual", "Transdermal", "Injection (IM)", "Injection (SC)", "Topical", "Other"]

        # --- change: move energetic/tired to energy; keep mood focused on mood ---
        self.mood_options = ["", "Calm", "Happy", "Anxious", "Irritable", "Low"]
        self.energy_options = ["", "Energetic", "Tired", "Normal", "Wired", "Exhausted"]
        self.symptom_options = ["", "None", "Headache", "Nausea", "Hot flashes", "Dizziness", "Breast tenderness", "Cramps"]
        self.libido_options = ["", "Very low", "Low", "Normal", "High", "Very high"]
        # --- end change ---

        self.med_name_options = [
            "",
            "Estradiol",
            "Estradiol valerate",
            "Estradiol cypionate",
            "Ethinyl estradiol",
            "Spironolactone",
            "Cyproterone acetate",
            "Bicalutamide",
            "Finasteride",
            "Dutasteride",
            "Progesterone",
            "Medroxyprogesterone",
            "GnRH agonist",
            "Other",
        ]

        self.dose_options = [
            "",
            "0.5", "1", "2", "4", "6", "8",
            "12.5", "25", "50", "100", "200",
            "0.1", "0.2", "0.3", "0.4",
        ]

        # --- change: make mood/energy/libido look/work like symptoms (MultiSelectCombo) ---
        self.mood_edit = MultiSelectCombo(
            [s for s in self.mood_options if s],
            placeholder="Select mood(s) (optional)",
            parent=self,
        )
        self.energy_edit = MultiSelectCombo(
            [s for s in self.energy_options if s],
            placeholder="Select energy (optional)",
            parent=self,
        )
        self.symptoms_edit = MultiSelectCombo(
            [s for s in self.symptom_options if s and s != "None"],
            placeholder="Select symptom(s) (optional)",
            parent=self,
        )
        self.libido_edit = MultiSelectCombo(
            [s for s in self.libido_options if s],
            placeholder="Select libido (optional)",
            parent=self,
        )
        # --- end change ---

        self.notes_edit = QPlainTextEdit(self)
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setTabChangesFocus(True)

        extras_group = QGroupBox("Mood, symptoms, notes")
        extras_form = QFormLayout()
        extras_form.setLabelAlignment(Qt.AlignRight)
        extras_form.setFormAlignment(Qt.AlignTop)
        extras_form.setHorizontalSpacing(12)
        extras_form.setVerticalSpacing(10)
        extras_form.addRow("Mood:", self.mood_edit)
        extras_form.addRow("Energy:", self.energy_edit)
        extras_form.addRow("Symptoms:", self.symptoms_edit)
        extras_form.addRow("Libido:", self.libido_edit)

        self.notes_edit.setMinimumHeight(120)
        extras_form.addRow("Notes:", self.notes_edit)
        extras_group.setLayout(extras_form)

        self.save_btn = QPushButton("Save entry", self)
        self.save_btn.clicked.connect(self._save_entry)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self._clear_form)

        self.view_entries_btn = QPushButton("View entries", self)
        self.view_entries_btn.clicked.connect(self._view_entries)

        self.help_btn = QPushButton("Help", self)
        self.help_btn.clicked.connect(self._show_help)

        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        save_row.addStretch(1)
        self.view_entries_btn.setMinimumWidth(130)
        self.help_btn.setMinimumWidth(90)
        self.save_btn.setMinimumWidth(120)
        save_row.addWidget(self.view_entries_btn)
        save_row.addWidget(self.help_btn)
        save_row.addWidget(self.clear_btn)
        save_row.addWidget(self.save_btn)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)
        main_layout.addWidget(dt_group)
        main_layout.addWidget(meds_group)
        main_layout.addWidget(extras_group)
        main_layout.addLayout(save_row)
        root.setLayout(main_layout)

        file_menu = self.menuBar().addMenu("&File")
        open_data_action = QAction("Open data folder", self)
        open_data_action.triggered.connect(self._open_data_folder_hint)
        file_menu.addAction(open_data_action)

        view_menu = self.menuBar().addMenu("&View")
        theme_menu = view_menu.addMenu("&Theme")

        self._theme_light_action = QAction("&Light", self)
        self._theme_light_action.setCheckable(True)
        self._theme_light_action.triggered.connect(lambda: self._set_theme(THEME_LIGHT))

        self._theme_dark_action = QAction("&Dark", self)
        self._theme_dark_action.setCheckable(True)
        self._theme_dark_action.triggered.connect(lambda: self._set_theme(THEME_DARK))

        theme_menu.addAction(self._theme_light_action)
        theme_menu.addAction(self._theme_dark_action)

        self._sync_theme_actions()

        self._add_med_row()
        self.meds_table.clearSelection()
        self.meds_table.setCurrentCell(-1, -1)

    def _set_theme(self, theme: str) -> None:
        self._theme = _apply_app_theme(theme, self._settings, persist=True)
        self._sync_theme_actions()

    def _sync_theme_actions(self) -> None:
        if not hasattr(self, "_theme_light_action"):
            return
        self._theme_light_action.blockSignals(True)
        self._theme_dark_action.blockSignals(True)
        self._theme_light_action.setChecked(self._theme == THEME_LIGHT)
        self._theme_dark_action.setChecked(self._theme == THEME_DARK)
        self._theme_light_action.blockSignals(False)
        self._theme_dark_action.blockSignals(False)

    def _open_data_folder_hint(self):
        QMessageBox.information(
            self,
            "Data location",
            f"Entries are saved to:\n{_app_data_path()}",
        )

    def _set_now(self):
        now = datetime.now()
        self.date_edit.setDate(QDate(now.year, now.month, now.day))
        self.time_edit.setTime(QTime(now.hour, now.minute))

    def _open_calendar(self):
        dlg = CalendarDialog(self.date_edit.date(), self)
        if dlg.exec() == QDialog.Accepted:
            self.date_edit.setDate(dlg.selected_date())

    def _make_combo(self, options: List[str], placeholder: str = "") -> QComboBox:
        cb = QComboBox(self)
        cb.setEditable(True)
        cb.addItems(options)
        if placeholder:
            cb.setPlaceholderText(placeholder)
        cb.setInsertPolicy(QComboBox.NoInsert)
        return cb

    def _combo_current_text(self, cb: QComboBox) -> str:
        return (cb.currentText() or "").strip()

    def _parse_dose(self, dose_text: str) -> float:
        s = (dose_text or "").strip()
        if not s:
            return 0.0
        s = s.replace(",", ".")
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if not m:
            raise ValueError(f"Invalid dose: '{dose_text}'")
        return float(m.group(0))

    def _add_med_row(self):
        row = self.meds_table.rowCount()
        self.meds_table.insertRow(row)

        name_cb = self._make_combo(self.med_name_options, placeholder="Medication")
        self.meds_table.setCellWidget(row, 0, name_cb)

        dose_cb = self._make_combo(self.dose_options, placeholder="Dose")
        self.meds_table.setCellWidget(row, 1, dose_cb)

        unit_cb = self._make_combo(self.unit_options, placeholder="Unit")
        self.meds_table.setCellWidget(row, 2, unit_cb)

        route_cb = self._make_combo(self.route_options, placeholder="Route")
        self.meds_table.setCellWidget(row, 3, route_cb)

        time_item = QTableWidgetItem(self.time_edit.time().toString("HH:mm"))
        time_item.setTextAlignment(Qt.AlignCenter)
        self.meds_table.setItem(row, 4, time_item)

        self.meds_table.setCurrentCell(row, 1)

    def _remove_selected_rows(self):
        selected = self.meds_table.selectionModel().selectedRows()
        for idx in sorted((s.row() for s in selected), reverse=True):
            self.meds_table.removeRow(idx)
        if self.meds_table.rowCount() == 0:
            self._add_med_row()

    def _collect_medications(self) -> List[MedicationRow]:
        meds: List[MedicationRow] = []
        for r in range(self.meds_table.rowCount()):
            name_widget = self.meds_table.cellWidget(r, 0)
            name = self._combo_current_text(name_widget) if isinstance(name_widget, QComboBox) else (
                (self.meds_table.item(r, 0).text() if self.meds_table.item(r, 0) else "").strip()
            )

            dose_widget = self.meds_table.cellWidget(r, 1)
            dose_raw = self._combo_current_text(dose_widget) if isinstance(dose_widget, QComboBox) else (
                (self.meds_table.item(r, 1).text() if self.meds_table.item(r, 1) else "").strip()
            )

            unit_widget = self.meds_table.cellWidget(r, 2)
            unit = self._combo_current_text(unit_widget) if isinstance(unit_widget, QComboBox) else (
                (self.meds_table.item(r, 2).text() if self.meds_table.item(r, 2) else "").strip()
            )

            route_widget = self.meds_table.cellWidget(r, 3)
            route = self._combo_current_text(route_widget) if isinstance(route_widget, QComboBox) else (
                (self.meds_table.item(r, 3).text() if self.meds_table.item(r, 3) else "").strip()
            )

            time_str = (self.meds_table.item(r, 4).text() if self.meds_table.item(r, 4) else "").strip()

            if not any([name, dose_raw, unit, route, time_str]):
                continue  # skip completely empty rows

            dose = 0.0
            if dose_raw:
                dose = self._parse_dose(dose_raw)

            if not time_str:
                time_str = self.time_edit.time().toString("HH:mm")

            meds.append(MedicationRow(name=name, dose=dose, unit=unit, route=route, time=time_str))
        return meds

    def _validate_can_save(self, meds: List[MedicationRow]) -> bool:
        return any(m.name.strip() for m in meds)

    # --- add: multi-select accessor (store as JSON lists) ---
    def _multiselect_values(self, w: Any) -> List[str]:
        if isinstance(w, MultiSelectCombo):
            return w.values()
        if isinstance(w, QComboBox):
            txt = self._combo_current_text(w)
            return [t.strip() for t in txt.split(",") if t.strip()] if txt else []
        return []
    # --- end add ---

    def _save_entry(self):
        try:
            meds = self._collect_medications()
        except ValueError as e:
            QMessageBox.warning(self, "Validation error", str(e))
            return

        if not self._validate_can_save(meds):
            QMessageBox.warning(self, "Missing medication name", "Please enter at least one medication name before saving.")
            return

        dt = datetime(
            self.date_edit.date().year(),
            self.date_edit.date().month(),
            self.date_edit.date().day(),
            self.time_edit.time().hour(),
            self.time_edit.time().minute(),
        )
        ts = dt.strftime("%Y-%m-%d %H:%M")

        record: Dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "created_at": ts,
            "updated_at": ts,
            "timestamp_local": ts,
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "time": self.time_edit.time().toString("HH:mm"),
            "medications": [
                {"name": m.name, "dose": m.dose, "unit": m.unit, "route": m.route, "time": m.time}
                for m in meds
                if any([m.name.strip(), m.dose, m.unit.strip(), m.route.strip(), m.time.strip()])
            ],
            # --- change: store as lists ---
            "mood": self._multiselect_values(self.mood_edit),
            "energy": self._multiselect_values(self.energy_edit),
            "symptoms": self._multiselect_values(self.symptoms_edit),
            "libido": self._multiselect_values(self.libido_edit),
            # --- end change ---
            "notes": self.notes_edit.toPlainText().rstrip(),
        }

        path = _app_data_path()
        try:
            entries = _read_entries_json(path)
            entries.append(record)
            _write_entries_json_atomic(path, entries)
        except OSError as e:
            QMessageBox.critical(self, "Save failed", f"Could not write to:\n{path}\n\n{e}")
            return

        self.statusBar().showMessage(f"Saved entry: {record.get('timestamp_local','')}", 4000)
        QMessageBox.information(self, "Saved", f"Entry saved to:\n{path}")
        self._clear_form(keep_date_time=True)

    def _clear_form(self, keep_date_time: bool = False):
        if not keep_date_time:
            self.date_edit.setDate(QDate.currentDate())
            self.time_edit.setTime(QTime.currentTime())

        # --- change: clear multi-selects like symptoms ---
        if isinstance(self.mood_edit, MultiSelectCombo):
            self.mood_edit.set_values([])
        if isinstance(self.energy_edit, MultiSelectCombo):
            self.energy_edit.set_values([])
        if isinstance(self.symptoms_edit, MultiSelectCombo):
            self.symptoms_edit.set_values([])
        if isinstance(self.libido_edit, MultiSelectCombo):
            self.libido_edit.set_values([])
        # --- end change ---

        self.notes_edit.clear()

        self.meds_table.setRowCount(0)
        self._add_med_row()
        self.meds_table.clearSelection()
        self.meds_table.setCurrentCell(-1, -1)

        self.statusBar().showMessage("Cleared form", 2500)

    def _view_entries(self):
        dlg = ViewEntriesDialog(self)
        dlg.resize(1000, 600)
        dlg.exec()

    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

def main():
    QApplication.setOrganizationName(org_name)
    QApplication.setApplicationName(APP_TITLE)

    app = QApplication(sys.argv)

    settings = QSettings(org_name, APP_TITLE)
    theme = str(settings.value(SETTINGS_THEME_KEY, THEME_DARK) or THEME_DARK).lower()
    _apply_app_theme(theme, settings, persist=False)

    win = MainWindow()
    win.resize(900, 650)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()