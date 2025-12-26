from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QFormLayout,
    QComboBox,
)


@dataclass
class JournalEntry:
    id: str
    created_at: str  # ISO datetime
    updated_at: str  # ISO datetime
    title: str
    tags: List[str]
    body_html: str


class Journal(QWidget):
    def __init__(self):
        super().__init__()

        self._safe_mode = False
        self._data_path = self._default_data_path()
        self._entries: List[JournalEntry] = []
        self._current_id: Optional[str] = None
        self._dirty = False

        # new: guards to stop selection/editor reload loops (caret resets)
        self._refreshing_list = False
        self._loading_editor = False
        self._saving = False

        self._load()

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Journal"))

        # Top controls
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search (title, tags, text)...")
        self.search_input.textChanged.connect(self._refresh_list)

        self.new_btn = QPushButton("New Entry")
        self.new_btn.clicked.connect(self._new_entry)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_entry)

        top.addWidget(self.search_input, 1)
        top.addWidget(self.new_btn)
        top.addWidget(self.delete_btn)
        root.addLayout(top)

        # Main split (simple manual layout)
        mid = QHBoxLayout()

        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.list.setFixedWidth(260)
        mid.addWidget(self.list)

        editor_col = QVBoxLayout()

        meta_box = QGroupBox("Entry")
        meta = QFormLayout(meta_box)
        self.title_input = QLineEdit()
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags (mood, topic, symptoms)...")

        # NEW: tags dropdown (adds selected tag into tags_input)
        self.tags_combo = QComboBox()
        self.tags_combo.setEditable(False)
        self.tags_combo.addItem("Add tag…", userData=None)
        self.tags_combo.addItems(
            [
                "mood",
                "energy",
                "sleep",
                "anxiety",
                "stress",
                "dysphoria",
                "euphoria",
                "libido",
                "appetite",
                "skin",
                "acne",
                "pain",
                "headache",
                "work",
                "family",
                "social",
            ]
        )
        self.tags_combo.currentIndexChanged.connect(self._on_tag_chosen)

        tags_row = QWidget()
        tags_row_l = QHBoxLayout(tags_row)
        tags_row_l.setContentsMargins(0, 0, 0, 0)
        tags_row_l.addWidget(self.tags_input, 1)
        tags_row_l.addWidget(self.tags_combo)

        meta.addRow("Title", self.title_input)
        meta.addRow("Tags", tags_row)
        editor_col.addWidget(meta_box)

        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Write your thoughts...")
        editor_col.addWidget(self.text_area, 1)

        bottom = QHBoxLayout()
        self.status_label = QLabel("")
        self.save_button = QPushButton("Save Now")
        self.save_button.clicked.connect(self._save_current)
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.save_button)
        editor_col.addLayout(bottom)

        mid.addLayout(editor_col, 1)
        root.addLayout(mid, 1)

        # Autosave
        self._autosave = QTimer(self)
        self._autosave.setInterval(1500)
        self._autosave.timeout.connect(self._autosave_tick)
        self._autosave.start()

        self.title_input.textChanged.connect(self._mark_dirty)
        self.tags_input.textChanged.connect(self._mark_dirty)
        self.text_area.textChanged.connect(self._mark_dirty)

        self._refresh_list()
        if self._entries:
            self._select_by_id(self._entries[0].id)
        else:
            self._new_entry()

    def set_safe_mode(self, enabled: bool):
        self._safe_mode = bool(enabled)
        self._apply_safe_mode_to_editor()
        self._refresh_list()

    def _apply_safe_mode_to_editor(self):
        blocked = self._safe_mode
        # Keep list visible, but hide actual content quickly
        self.text_area.setVisible(not blocked)
        self.title_input.setEchoMode(QLineEdit.Password if blocked else QLineEdit.Normal)
        self.tags_input.setEchoMode(QLineEdit.Password if blocked else QLineEdit.Normal)
        self.status_label.setText("Safe Mode enabled" if blocked else ("(unsaved)" if self._dirty else ""))

    def _default_data_path(self) -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "journal.json"

    def _load(self):
        if not self._data_path.exists():
            self._entries = []
            return
        try:
            raw = json.loads(self._data_path.read_text(encoding="utf-8"))
            self._entries = [JournalEntry(**item) for item in raw]
            self._entries.sort(key=lambda e: e.updated_at, reverse=True)
        except Exception:
            self._entries = []

    def _save_all(self):
        self._data_path.write_text(
            json.dumps([asdict(e) for e in self._entries], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _mark_dirty(self):
        # new: don't mark dirty due to programmatic loads
        if self._loading_editor or self._safe_mode:
            return
        self._dirty = True
        if not self._safe_mode:
            self.status_label.setText("(unsaved)")

    def _autosave_tick(self):
        if self._safe_mode:
            return
        if self._dirty and self._current_id:
            self._save_current()

    def _new_entry(self):
        now = datetime.now().isoformat(timespec="seconds")
        eid = f"j_{uuid.uuid4().hex[:12]}"
        entry = JournalEntry(
            id=eid,
            created_at=now,
            updated_at=now,
            title="",
            tags=[],
            body_html="",
        )
        self._entries.insert(0, entry)
        self._current_id = entry.id
        self._refresh_list()
        self._select_by_id(entry.id)
        self._dirty = True
        if not self._safe_mode:
            self._save_current()

    def _delete_entry(self):
        if not self._current_id:
            return
        self._entries = [e for e in self._entries if e.id != self._current_id]
        self._current_id = None
        self._save_all()
        self._refresh_list()
        if self._entries:
            self._select_by_id(self._entries[0].id)
        else:
            self._new_entry()

    def _on_select(self, current: QListWidgetItem, previous: QListWidgetItem):
        # new: ignore selection signals caused by list rebuild/selection restore
        if self._refreshing_list or self._loading_editor:
            return

        if previous is not None and self._dirty and not self._safe_mode:
            self._save_current()

        if current is None:
            return
        eid = current.data(Qt.UserRole)
        if isinstance(eid, str) and eid:
            self._load_into_editor(eid)

    def _select_by_id(self, eid: str):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole) == eid:
                self.list.setCurrentRow(i)
                return

    def _refresh_list(self):
        # new: preserve selection and avoid emitting selection changes while rebuilding
        selected_id = self._current_id
        self._refreshing_list = True
        try:
            q = (self.search_input.text() or "").strip().lower()

            def matches(e: JournalEntry) -> bool:
                if not q:
                    return True
                hay = " ".join([e.title, " ".join(e.tags), self._plain_preview(e.body_html)]).lower()
                return q in hay

            self.list.blockSignals(True)
            self.list.clear()
            for e in sorted(self._entries, key=lambda x: x.updated_at, reverse=True):
                if not matches(e):
                    continue

                if self._safe_mode:
                    title = "(hidden)"
                    subtitle = ""
                else:
                    title = (e.title or "").strip() or "(untitled)"
                    subtitle = ", ".join(e.tags) if e.tags else ""

                it = QListWidgetItem(f"{title}\n{subtitle}".rstrip())
                it.setData(Qt.UserRole, e.id)
                self.list.addItem(it)
            self.list.blockSignals(False)

            # restore selection WITHOUT triggering editor reload (signals are blocked above)
            if selected_id:
                for i in range(self.list.count()):
                    it = self.list.item(i)
                    if it.data(Qt.UserRole) == selected_id:
                        self.list.setCurrentRow(i)
                        break
        finally:
            self._refreshing_list = False

    def _plain_preview(self, html: str) -> str:
        # minimal: QTextEdit can render HTML; for search preview use crude stripping
        return (
            html.replace("<br>", " ")
            .replace("<br/>", " ")
            .replace("</p>", " ")
            .replace("&nbsp;", " ")
        )

    def _find(self, eid: str) -> Optional[JournalEntry]:
        for e in self._entries:
            if e.id == eid:
                return e
        return None

    def _load_into_editor(self, eid: str):
        self._current_id = eid
        e = self._find(eid)
        if not e:
            return

        # new: prevent _mark_dirty and other side effects while filling widgets
        self._loading_editor = True
        try:
            self.title_input.blockSignals(True)
            self.tags_input.blockSignals(True)
            self.text_area.blockSignals(True)

            self.title_input.setText(e.title)
            self.tags_input.setText(", ".join(e.tags))
            self.text_area.setHtml(e.body_html or "")

            self._dirty = False
        finally:
            self.title_input.blockSignals(False)
            self.tags_input.blockSignals(False)
            self.text_area.blockSignals(False)
            self._loading_editor = False

        self._apply_safe_mode_to_editor()

    def _save_current(self):
        if self._safe_mode or self._saving:
            return
        if not self._current_id:
            return
        e = self._find(self._current_id)
        if not e:
            return

        self._saving = True
        try:
            now = datetime.now().isoformat(timespec="seconds")
            e.title = self.title_input.text()
            e.tags = [t.strip() for t in (self.tags_input.text() or "").split(",") if t.strip()]
            e.body_html = self.text_area.toHtml()
            e.updated_at = now

            self._entries.sort(key=lambda x: x.updated_at, reverse=True)
            self._save_all()

            self._dirty = False
            self.status_label.setText(f"Saved {now}")

            # IMPORTANT: do NOT call _select_by_id() here (it can change selection -> reload editor -> caret reset)
            # Refresh list while preserving current selection.
            self._refresh_list()
        finally:
            self._saving = False

    def _on_tag_chosen(self, index: int):
        # ignore placeholder
        tag = self.tags_combo.currentText().strip()
        if index <= 0 or not tag:
            return

        # if safe mode, don't reveal/modify content
        if self._safe_mode:
            self.tags_combo.setCurrentIndex(0)
            return

        existing = [t.strip() for t in (self.tags_input.text() or "").split(",") if t.strip()]
        if tag not in existing:
            existing.append(tag)
            # will trigger _mark_dirty via textChanged (desired)
            self.tags_input.setText(", ".join(existing))

        # reset to placeholder
        self.tags_combo.setCurrentIndex(0)