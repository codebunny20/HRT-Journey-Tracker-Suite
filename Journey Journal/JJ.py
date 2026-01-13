import sys
import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
import os

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QDateEdit, QComboBox, QCheckBox, QTextEdit,
    QPushButton, QTableView, QMessageBox, QGroupBox, QFileDialog,
    QScrollArea,
    QDialog, QDialogButtonBox, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QTabWidget,
)
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QHeaderView

# --- additions: theme + status animation ---
from PySide6.QtCore import QSettings, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect

APP_NAME = "Journey Journal"
ORG_NAME = "HRTJourneyTracker"
DATA_FILENAME = "j_j.json"
STORAGE_DIRNAME = "storage"  # match TrackMyHRT/main.py pattern

# --- additions: theme helpers ---
SETTINGS_THEME_KEY = "ui/theme"  # "dark" | "light"

DARK_STYLESHEET = """
QWidget { background: #121212; color: #eaeaea; }
QGroupBox { border: 1px solid #2a2a2a; margin-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit {
  background: #1e1e1e; border: 1px solid #2a2a2a; padding: 6px; border-radius: 4px;
}
QPushButton { background: #2b2b2b; border: 1px solid #3a3a3a; padding: 6px 10px; border-radius: 4px; }
QPushButton:hover { background: #333333; }
QTableView, QTableWidget { background: #141414; alternate-background-color: #171717; gridline-color: #2a2a2a; }
QHeaderView::section { background: #1b1b1b; border: 1px solid #2a2a2a; padding: 6px; }
QMenuBar, QMenu { background: #161616; color: #eaeaea; }
QMenu::item:selected { background: #2a2a2a; }
QStatusBar { background: #161616; }
"""

LIGHT_STYLESHEET = """
QWidget { background: #fafafa; color: #1b1b1b; }
QGroupBox { border: 1px solid #d7d7d7; margin-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit {
  background: #ffffff; border: 1px solid #cfcfcf; padding: 6px; border-radius: 4px;
}
QPushButton { background: #f0f0f0; border: 1px solid #cfcfcf; padding: 6px 10px; border-radius: 4px; }
QPushButton:hover { background: #e9e9e9; }
QTableView, QTableWidget { background: #ffffff; alternate-background-color: #f6f6f6; gridline-color: #dedede; }
QHeaderView::section { background: #f2f2f2; border: 1px solid #dedede; padding: 6px; }
QMenuBar, QMenu { background: #f7f7f7; color: #1b1b1b; }
QMenu::item:selected { background: #e9e9e9; }
QStatusBar { background: #f7f7f7; }
"""

def _load_theme() -> str:
    s = QSettings(ORG_NAME, APP_NAME)
    return str(s.value(SETTINGS_THEME_KEY, "dark")).lower()

def _save_theme(theme: str) -> None:
    s = QSettings(ORG_NAME, APP_NAME)
    s.setValue(SETTINGS_THEME_KEY, (theme or "dark").lower())

def _apply_theme(app: QApplication, theme: str) -> None:
    theme = (theme or "dark").lower()
    app.setStyleSheet(DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET)

def _ensure_storage_ready() -> Path:
    """
    Ensures ./storage exists next to this script (dev) or next to the packaged exe.
    Returns full path to j_j.json.
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent

    storage_dir = base_dir / STORAGE_DIRNAME
    storage_dir.mkdir(parents=True, exist_ok=True)

    path = storage_dir / DATA_FILENAME
    if not path.exists():
        path.write_text("[]", encoding="utf-8")  # JJ uses a JSON array (not jsonl)
    return path

def _default_data_file() -> Path:
    return _ensure_storage_ready()

DATA_FILE = _default_data_file()

# -----------------------------
# Data model
# -----------------------------

@dataclass
class JournalEntry:
    entry_date: str
    mood: str
    symptoms: list
    emotional_shifts: str
    pain_discomfort: str
    libido_arousal: str
    notes: str

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return JournalEntry(
            entry_date=data.get("entry_date", ""),
            mood=data.get("mood", ""),
            symptoms=data.get("symptoms", []),
            emotional_shifts=data.get("emotional_shifts", "None"),
            pain_discomfort=data.get("pain_discomfort", "None"),
            libido_arousal=data.get("libido_arousal", "None"),
            notes=data.get("notes", ""),
        )

# -----------------------------
# Table model
# -----------------------------

class JournalTableModel(QAbstractTableModel):
    HEADERS = ["Date", "Mood", "Symptoms", "Emotional shifts", "Pain / discomfort", "Libido / arousal", "Notes"]

    def __init__(self, entries):
        super().__init__()
        self.entries = entries

    def rowCount(self, parent=None):
        return len(self.entries)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        entry = self.entries[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return entry.entry_date
            elif col == 1:
                return entry.mood
            elif col == 2:
                return ", ".join(entry.symptoms)
            elif col == 3:
                return entry.emotional_shifts
            elif col == 4:
                return entry.pain_discomfort
            elif col == 5:
                return entry.libido_arousal
            elif col == 6:
                return entry.notes.replace("\n", " ").strip()

        if role == Qt.ToolTipRole:
            if col == 6 and entry.notes:
                return entry.notes

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def add_entry(self, entry):
        self.beginInsertRows(QModelIndex(), len(self.entries), len(self.entries))
        self.entries.append(entry)
        self.endInsertRows()

    def remove_rows(self, rows: list[int]):
        if not rows:
            return
        for r in sorted(set(rows), reverse=True):
            if 0 <= r < len(self.entries):
                self.beginRemoveRows(QModelIndex(), r, r)
                self.entries.pop(r)
                self.endRemoveRows()

    def replace_all(self, entries):
        self.beginResetModel()
        self.entries = entries
        self.endResetModel()

# -----------------------------
# View Entries Dialog
# -----------------------------

class ViewJournalEntriesDialog(QDialog):
    def __init__(self, data_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View entries")
        self.setModal(True)

        self._data_path = data_path
        self._entries: list[JournalEntry] = []

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(JournalTableModel.HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in (1, 2, 3, 4, 5):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)  # allow multi-row delete
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
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

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.view_btn)
        btn_row.addWidget(self.details_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        self._refresh()

    def entries(self) -> list[JournalEntry]:
        return self._entries

    def _load_entries(self) -> list[JournalEntry]:
        try:
            if not self._data_path.exists():
                return []
            raw = json.loads(self._data_path.read_text(encoding="utf-8") or "[]")
            entries = [JournalEntry.from_dict(e) for e in (raw if isinstance(raw, list) else [])]
            entries.sort(key=lambda e: e.entry_date, reverse=True)
            return entries
        except Exception:
            return []

    def _refresh(self):
        self._entries = self._load_entries()
        self.table.setRowCount(0)

        for entry in self._entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            cells = [
                entry.entry_date,
                entry.mood,
                ", ".join(entry.symptoms),
                entry.emotional_shifts,
                entry.pain_discomfort,
                entry.libido_arousal,
                entry.notes.replace("\n", " ").strip(),
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(str(text or ""))
                if col == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def _selected_indices(self) -> list[int]:
        sel = self.table.selectionModel().selectedRows()
        rows = sorted({i.row() for i in sel if i and i.row() >= 0})
        return [r for r in rows if r < len(self._entries)]

    def _selected_index(self) -> int:
        rows = self._selected_indices()
        return rows[0] if rows else -1

    def _selected_entry(self) -> JournalEntry | None:
        i = self._selected_index()
        return self._entries[i] if i != -1 else None

    def _show_details(self):
        entry = self._selected_entry()
        if not entry:
            return
        QMessageBox.information(self, "Entry details", json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))

    def _view_selected(self):
        entry = self._selected_entry()
        if not entry:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Entry — {entry.entry_date}")
        dlg.setModal(True)

        text = QPlainTextEdit(dlg)
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        parts = [
            "Entry",
            "=" * 40,
            f"Date: {entry.entry_date}",
            "",
            f"Mood: {entry.mood or '(none)'}",
            f"Symptoms: {', '.join(entry.symptoms) if entry.symptoms else '(none)'}",
            f"Emotional shifts: {entry.emotional_shifts or '(none)'}",
            f"Pain / discomfort: {entry.pain_discomfort or '(none)'}",
            f"Libido / arousal: {entry.libido_arousal or '(none)'}",
            "",
            "Notes",
            "-" * 40,
            entry.notes or "(none)",
        ]
        text.setPlainText("\n".join(parts))

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dlg)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)

        layout = QVBoxLayout()
        layout.addWidget(text)
        layout.addWidget(buttons)
        dlg.setLayout(layout)
        dlg.resize(850, 600)
        dlg.exec()

    def _delete_selected(self):
        rows = self._selected_indices()
        if not rows:
            return

        to_delete = [self._entries[r] for r in rows]
        msg = "Delete the selected entr{}?\n\n{}\n\nThis cannot be undone.".format(
            "y" if len(to_delete) == 1 else "ies",
            "\n".join(e.entry_date for e in to_delete[:12]) + ("" if len(to_delete) <= 12 else "\n…"),
        )
        ok = QMessageBox.question(
            self,
            "Delete entry?",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ok != QMessageBox.Yes:
            return

        delete_dates = {e.entry_date for e in to_delete}  # JJ enforces one entry per date
        new_entries = [e for e in self._entries if e.entry_date not in delete_dates]
        if len(new_entries) == len(self._entries):
            QMessageBox.warning(self, "Not found", "Could not find the selected entry (it may have changed).")
            self._refresh()
            return

        try:
            tmp = self._data_path.with_suffix(".tmp")
            tmp.write_text(json.dumps([e.to_dict() for e in new_entries], ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._data_path)
        except Exception as e:
            QMessageBox.critical(self, "Delete failed", f"Could not write:\n{self._data_path}\n\n{e}")
            return

        QMessageBox.information(self, "Deleted", f"Deleted {len(delete_dates)} entr{('y' if len(delete_dates)==1 else 'ies')}.")
        self._refresh()

# -----------------------------
# Main Window
# -----------------------------

class HRTJournalWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)

        # --- status label with fade animation ---
        sb = self.statusBar()
        self._status_label = QLabel("")
        self._status_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self._status_fx = QGraphicsOpacityEffect(self._status_label)
        self._status_label.setGraphicsEffect(self._status_fx)
        self._status_fx.setOpacity(1.0)
        sb.addPermanentWidget(self._status_label, 1)

        self._status_anim = QPropertyAnimation(self._status_fx, b"opacity", self)
        self._status_anim.setDuration(180)
        self._status_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._pending_status_text = ""

        app = QApplication.instance()
        if app:
            app.setOrganizationName(ORG_NAME)
            app.setApplicationName(APP_NAME)
            _apply_theme(app, _load_theme())

        # --- menu: View -> Theme ---
        self._init_menus()

        self.data_path = _default_data_file()

        self.entries = []
        self._load_data()

        self.model = JournalTableModel(self.entries)

        main = QWidget()
        main_layout = QVBoxLayout(main)

        tabs = QTabWidget()
        main_layout.addWidget(tabs, 1)  # stretch

        # -----------------------------
        # Tab 1: New entry
        # -----------------------------
        entry_tab = QWidget()
        entry_layout = QVBoxLayout(entry_tab)

        # --- Entry Form ---
        form_group = QGroupBox("New Journal Entry")
        form_group.setMinimumWidth(420)  # side panel shouldn't collapse too much
        form_layout = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(date.today())
        self.date_edit.setCalendarPopup(True)

        self.mood_combo = QComboBox()
        self.mood_combo.addItem("(none)")  # allow empty mood, matches README behavior
        self.mood_combo.addItems(["Great", "Good", "Okay", "Low", "Rough"])

        # Replace single-select symptoms combobox w/ multi-select checkboxes
        self.symptoms_group = QGroupBox()
        self.symptoms_group.setFlat(True)
        symptoms_layout = QVBoxLayout(self.symptoms_group)
        symptoms_layout.setContentsMargins(0, 0, 0, 0)

        self._symptom_checks: list[QCheckBox] = []
        for label in [
            "Mood swings",
            "Cramps",
            "Fatigue",
            "Breast tenderness",
            "Headache",
        ]:
            cb = QCheckBox(label)
            self._symptom_checks.append(cb)
            symptoms_layout.addWidget(cb)
        symptoms_layout.addStretch(1)

        self.symptoms_clear_btn = QPushButton("Clear symptoms")
        self.symptoms_clear_btn.setAutoDefault(False)
        self.symptoms_clear_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self._symptom_checks])
        symptoms_layout.addWidget(self.symptoms_clear_btn)

        self.emotional_combo = QComboBox()
        self.emotional_combo.addItems([
            "None",
            "More sensitive",
            "More irritable",
            "More stable/calm",
            "Easier to cry",
            "Anxious",
            "Euphoric",
        ])

        self.pain_combo = QComboBox()
        self.pain_combo.addItems([
            "None",
            "Mild",
            "Moderate",
            "Strong",
            "Cramps",
            "Headache",
            "Muscle/joint aches",
        ])

        self.libido_combo = QComboBox()
        self.libido_combo.addItems([
            "None",
            "Low",
            "Normal",
            "High",
        ])

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Write anything you want to...")

        form_layout.addRow("Date:", self.date_edit)
        form_layout.addRow("Mood:", self.mood_combo)
        form_layout.addRow("Symptoms:", self.symptoms_group)
        form_layout.addRow("Emotional shifts:", self.emotional_combo)
        form_layout.addRow("Pain / discomfort:", self.pain_combo)
        form_layout.addRow("Libido / arousal:", self.libido_combo)
        form_layout.addRow("Notes:", self.notes_edit)
        form_group.setLayout(form_layout)

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QScrollArea.NoFrame)
        form_scroll.setWidget(form_group)
        entry_layout.addWidget(form_scroll, 1)  # stretch

        entry_btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Add Entry")
        self.save_btn.clicked.connect(self.add_entry)

        entry_btn_row.addStretch()
        entry_btn_row.addWidget(self.save_btn)
        entry_layout.addLayout(entry_btn_row, 0)

        tabs.addTab(entry_tab, "New entry")

        # -----------------------------
        # Tab 2: Entries
        # -----------------------------
        entries_tab = QWidget()
        entries_layout = QVBoxLayout(entries_tab)

        btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)

        self.export_btn = QPushButton("Export…")
        self.export_btn.clicked.connect(self.export_entries)

        self.view_entries_btn = QPushButton("View entries")
        self.view_entries_btn.clicked.connect(self.view_entries)

        btn_layout.addStretch()
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.view_entries_btn)
        btn_layout.addWidget(self.delete_btn)
        entries_layout.addLayout(btn_layout)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        # slightly more responsive than always ResizeToContents
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(140)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.setWordWrap(False)
        entries_layout.addWidget(self.table, 1)  # stretch

        tabs.addTab(entries_tab, "Entries")

        # -----------------------------
        # Tab 3: Voice journal
        # -----------------------------
        voice_tab = QWidget()
        voice_layout = QVBoxLayout(voice_tab)

        voice_layout.addWidget(QLabel("Voice journal tab (coming soon)."))
        voice_layout.addStretch(1)

        tabs.addTab(voice_tab, "Voice journal")

        self.setCentralWidget(main)
        self.resize(950, 700)

        # Sort once on startup (newest first)
        self._sort_entries()
        self.model.replace_all(self.entries)

        # Start on "New entry" tab
        tabs.setCurrentIndex(0)

    # --- additions: menus ---
    def _init_menus(self):
        view_menu = self.menuBar().addMenu("View")
        theme_menu = view_menu.addMenu("Theme")

        self._theme_dark_action = QAction("Dark", self, checkable=True)
        self._theme_light_action = QAction("Light", self, checkable=True)

        theme_menu.addAction(self._theme_dark_action)
        theme_menu.addAction(self._theme_light_action)

        cur = _load_theme()
        self._theme_dark_action.setChecked(cur == "dark")
        self._theme_light_action.setChecked(cur == "light")

        self._theme_dark_action.triggered.connect(lambda: self._set_theme("dark"))
        self._theme_light_action.triggered.connect(lambda: self._set_theme("light"))

    def _set_theme(self, theme: str):
        theme = (theme or "dark").lower()
        _save_theme(theme)
        app = QApplication.instance()
        if app:
            _apply_theme(app, theme)

        # keep actions mutually exclusive without QActionGroup
        self._theme_dark_action.blockSignals(True)
        self._theme_light_action.blockSignals(True)
        self._theme_dark_action.setChecked(theme == "dark")
        self._theme_light_action.setChecked(theme == "light")
        self._theme_dark_action.blockSignals(False)
        self._theme_light_action.blockSignals(False)

        self._set_status_text_animated(f"Theme: {theme.capitalize()}")

    # --- additions: animated status ---
    def _set_status_text_animated(self, text: str, timeout_ms: int = 2000):
        from PySide6.QtCore import QTimer

        self._pending_status_text = text

        def _fade_in():
            self._status_label.setText(self._pending_status_text)
            self._status_anim.stop()
            self._status_anim.setStartValue(0.0)
            self._status_anim.setEndValue(1.0)
            self._status_anim.start()

        # avoid stacking signals
        try:
            self._status_anim.finished.disconnect()
        except Exception:
            pass

        self._status_anim.stop()
        self._status_anim.setStartValue(float(self._status_fx.opacity()))
        self._status_anim.setEndValue(0.0)
        self._status_anim.finished.connect(_fade_in)
        self._status_anim.start()

        if timeout_ms and timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda: self._status_label.setText(""))

    # -----------------------------
    # Persistence
    # -----------------------------

    def _load_data(self):
        try:
            if not self.data_path.exists():
                self.entries = []
                return
            with self.data_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            self.entries = [JournalEntry.from_dict(e) for e in raw]
        except Exception as e:
            self.entries = []
            QMessageBox.warning(self, "Load failed", f"Could not load journal data:\n{e}")

    def _save_data(self):
        try:
            tmp = self.data_path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2, ensure_ascii=False)
            tmp.replace(self.data_path)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not save journal data:\n{e}")

    # -----------------------------
    # Add / Delete / Export
    # -----------------------------

    def _sort_entries(self):
        # entry_date is "yyyy-MM-dd" so string sort works
        self.entries.sort(key=lambda e: e.entry_date, reverse=True)

    def _find_entry_index_by_date(self, entry_date: str) -> int:
        for i, e in enumerate(self.entries):
            if e.entry_date == entry_date:
                return i
        return -1

    def add_entry(self):
        symptoms = [cb.text() for cb in self._symptom_checks if cb.isChecked()]

        entry_date = self.date_edit.date().toString("yyyy-MM-dd")
        mood = self.mood_combo.currentText()
        if mood == "(none)":
            mood = ""

        notes = self.notes_edit.toPlainText().strip()

        # Basic validation (avoid saving empty rows)
        if not mood and not notes:
            QMessageBox.warning(self, "Missing info", "Add notes and/or select a mood before saving.")
            return

        entry = JournalEntry(
            entry_date=entry_date,
            mood=mood,
            symptoms=symptoms,
            emotional_shifts=self.emotional_combo.currentText(),
            pain_discomfort=self.pain_combo.currentText(),
            libido_arousal=self.libido_combo.currentText(),
            notes=notes,
        )

        # Prevent duplicates for the same date (offer replace)
        existing_idx = self._find_entry_index_by_date(entry.entry_date)
        if existing_idx != -1:
            if QMessageBox.question(
                self,
                "Entry exists",
                f"An entry already exists for {entry.entry_date}.\nReplace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
            self.entries[existing_idx] = entry
        else:
            self.entries.append(entry)

        self._sort_entries()
        self.model.replace_all(self.entries)
        self._save_data()

        self._set_status_text_animated("Saved.", 2000)

        # reset form
        for cb in self._symptom_checks:
            cb.setChecked(False)
        self.emotional_combo.setCurrentIndex(0)
        self.pain_combo.setCurrentIndex(0)
        self.libido_combo.setCurrentIndex(0)
        self.notes_edit.clear()
        self.mood_combo.setCurrentIndex(0)

    def delete_selected(self):
        sel = self.table.selectionModel()
        if not sel or not sel.hasSelection():
            return
        rows = [i.row() for i in sel.selectedRows()]
        if not rows:
            return
        if QMessageBox.question(self, "Delete", f"Delete {len(rows)} selected entr{('y' if len(rows)==1 else 'ies')}?") != QMessageBox.StandardButton.Yes:
            return

        self.model.remove_rows(rows)
        self.entries = self.model.entries  # keep reference consistent
        self._save_data()
        self._set_status_text_animated("Deleted.", 2000)

    def _format_entry_txt(self, e: JournalEntry) -> str:
        parts = [
            f"Date: {e.entry_date}",
            f"Mood: {e.mood or '(none)'}",
            f"Symptoms: {', '.join(e.symptoms) if e.symptoms else '(none)'}",
            f"Emotional shifts: {e.emotional_shifts or '(none)'}",
            f"Pain / discomfort: {e.pain_discomfort or '(none)'}",
            f"Libido / arousal: {e.libido_arousal or '(none)'}",
            "Notes:",
            (e.notes or "(none)").rstrip(),
        ]
        return "\n".join(parts)

    def _format_entry_md(self, e: JournalEntry) -> str:
        notes = (e.notes or "(none)").rstrip()
        return (
            f"## {e.entry_date}\n\n"
            f"- **Mood:** {e.mood or '(none)'}\n"
            f"- **Symptoms:** {', '.join(e.symptoms) if e.symptoms else '(none)'}\n"
            f"- **Emotional shifts:** {e.emotional_shifts or '(none)'}\n"
            f"- **Pain / discomfort:** {e.pain_discomfort or '(none)'}\n"
            f"- **Libido / arousal:** {e.libido_arousal or '(none)'}\n\n"
            f"### Notes\n\n"
            f"{notes}\n"
        )

    def export_entries(self):
        # Pick filename + format using filter
        default_base = Path.home() / "hrt_journal_export"
        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Journal",
            str(default_base),
            "JSON (*.json);;Text (*.txt);;Markdown (*.md);;All files (*.*)",
        )
        if not path_str:
            return

        path = Path(path_str)

        # If user didn't specify an extension, infer from chosen filter
        if path.suffix == "":
            if selected_filter.startswith("JSON"):
                path = path.with_suffix(".json")
            elif selected_filter.startswith("Text"):
                path = path.with_suffix(".txt")
            elif selected_filter.startswith("Markdown"):
                path = path.with_suffix(".md")
            else:
                path = path.with_suffix(".txt")

        ext = path.suffix.lower()

        try:
            if ext == ".json":
                path.write_text(
                    json.dumps([e.to_dict() for e in self.entries], indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            elif ext == ".md":
                md = "# Journey Journal export\n\n" + "\n\n".join(self._format_entry_md(e) for e in self.entries) + "\n"
                path.write_text(md, encoding="utf-8")
            else:  # .txt or anything else
                txt = "\n\n".join(self._format_entry_txt(e) for e in self.entries) + "\n"
                path.write_text(txt, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", f"Could not export:\n{e}")
            return

        QMessageBox.information(self, "Exported", f"Exported to:\n{path}")

    # (Optionally keep the old name as a compatibility alias if referenced elsewhere.)
    def export_json(self):
        self.export_entries()

    def view_entries(self):
        dlg = ViewJournalEntriesDialog(self.data_path, self)
        dlg.resize(1000, 600)
        dlg.exec()

        # sync main table with whatever is on disk now
        self.entries = dlg.entries()
        self._sort_entries()
        self.model.replace_all(self.entries)

# -----------------------------
# Run app
# -----------------------------

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    _apply_theme(app, _load_theme())

    window = HRTJournalWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()