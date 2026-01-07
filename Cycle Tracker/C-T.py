import json
import sys
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QDate, QSize, QEvent
from PySide6.QtGui import QAction, QShortcut, QKeySequence, QColor, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QToolTip,
    QTextBrowser,
)


COMMON_TAGS = ["cramps", "mood shift", "spotting", "fatigue", "no bleed", "breakthrough"]

def _parse_tags(text: str) -> List[str]:
    parts = [p.strip() for p in (text or "").split(",")]
    seen = set()
    out: List[str] = []
    for p in parts:
        if not p:
            continue
        k = p.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out

def _tags_to_text(tags: List[str]) -> str:
    return ", ".join(tags or [])


# -----------------------------
# Data model and persistence
# -----------------------------


@dataclass
class CycleEntry:
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    intensity: str   # "none", "light", "medium", "heavy"
    notes: str
    tags: List[str] = field(default_factory=list)

    def start_as_date(self) -> date:
        return datetime.strptime(self.start_date, "%Y-%m-%d").date()

    def end_as_date(self) -> date:
        return datetime.strptime(self.end_date, "%Y-%m-%d").date()

    def bleed_length_days(self) -> int:
        return (self.end_as_date() - self.start_as_date()).days + 1


class CycleStorage:
    def __init__(self, path: Optional[str] = None) -> None:
        if path is None:
            # Save alongside the app in a dedicated data folder
            base_dir = Path(__file__).resolve().parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.path = data_dir / "cycle_entries.json"
        else:
            self.path = Path(path)
            # Ensure parent folder exists for custom paths too
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[CycleEntry]:
        # Ensure folder exists even if user deletes it between runs
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        entries: List[CycleEntry] = []
        for item in raw:
            try:
                entries.append(
                    CycleEntry(
                        start_date=item["start_date"],
                        end_date=item["end_date"],
                        intensity=item.get("intensity", "none"),
                        notes=item.get("notes", ""),
                        tags=list(item.get("tags", [])) if isinstance(item.get("tags", []), list) else [],
                    )
                )
            except KeyError:
                # Skip malformed entry
                continue
        # sort by start_date
        entries.sort(key=lambda e: e.start_date)
        return entries

    def save(self, entries: List[CycleEntry]) -> None:
        # Ensure folder exists before writing
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in entries]
        try:
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            # We surface error in the GUI instead of silently failing
            raise e


# ---------------------------------------------------------
# Improved Add/Edit Dialog
# ---------------------------------------------------------

class CycleDialog(QDialog):
    def __init__(self, parent=None, existing=None):
        super().__init__(parent)
        self.setWindowTitle("Cycle Entry")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setSpacing(12)

        self.start_edit = QDateEdit(calendarPopup=True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_edit.setDate(QDate.currentDate())

        self.end_edit = QDateEdit(calendarPopup=True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_edit.setDate(QDate.currentDate())

        self.intensity_box = QComboBox()
        self.intensity_box.addItems(["none", "light", "medium", "heavy"])

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes…")
        self.notes_edit.setFixedHeight(80)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("comma-separated (e.g. cramps, fatigue)")
        tags_picker = QWidget()
        tags_picker_layout = QHBoxLayout(tags_picker)
        tags_picker_layout.setContentsMargins(0, 0, 0, 0)
        tags_picker_layout.setSpacing(6)

        def add_tag(tag: str):
            current = _parse_tags(self.tags_edit.text())
            if tag.casefold() not in {t.casefold() for t in current}:
                current.append(tag)
            self.tags_edit.setText(_tags_to_text(current))

        for tag in COMMON_TAGS:
            b = QPushButton(tag)
            b.setProperty("tag", tag)
            b.setMaximumHeight(26)
            b.clicked.connect(lambda _=False, t=tag: add_tag(t))
            tags_picker_layout.addWidget(b)
        tags_picker_layout.addStretch(1)

        form.addRow("Start date:", self.start_edit)
        form.addRow("End date:", self.end_edit)
        form.addRow("Bleed intensity:", self.intensity_box)
        form.addRow("Notes:", self.notes_edit)
        form.addRow("Tags:", self.tags_edit)
        form.addRow("", tags_picker)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if existing:
            s = existing.start_as_date()
            e = existing.end_as_date()
            self.start_edit.setDate(QDate(s.year, s.month, s.day))
            self.end_edit.setDate(QDate(e.year, e.month, e.day))
            self.intensity_box.setCurrentText(existing.intensity)
            self.notes_edit.setPlainText(existing.notes)
            self.tags_edit.setText(_tags_to_text(getattr(existing, "tags", [])))

    def get_entry(self):
        if self.result() != QDialog.Accepted:
            return None

        start = self.start_edit.date().toPython()
        end = self.end_edit.date().toPython()

        if end < start:
            QMessageBox.warning(self, "Invalid dates", "End date cannot be before start date.")
            return None

        return CycleEntry(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            intensity=self.intensity_box.currentText(),
            notes=self.notes_edit.toPlainText().strip(),
            tags=_parse_tags(self.tags_edit.text()),
        )


# ---------------------------------------------------------
# Read-only Entry Details Dialog
# ---------------------------------------------------------

class CycleDetailsDialog(QDialog):
    def __init__(self, entry: CycleEntry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Entry Details")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Entry Details")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        info = QFrame()
        info.setFrameShape(QFrame.StyledPanel)
        info.setStyleSheet("QFrame { border-radius: 10px; padding: 12px; }")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)

        start = entry.start_date
        end = entry.end_date
        intensity = entry.intensity
        bleed_len = entry.bleed_length_days()
        tags = _tags_to_text(getattr(entry, "tags", [])) or "(none)"
        notes = (entry.notes or "").strip() or "(none)"

        details = QTextBrowser()
        details.setOpenExternalLinks(False)
        details.setReadOnly(True)
        details.setFrameShape(QFrame.NoFrame)
        details.setStyleSheet("QTextBrowser { background: transparent; }")
        details.setHtml(
            "<div style='font-size: 13px;'>"
            f"<b>Start:</b> {start}<br/>"
            f"<b>End:</b> {end}<br/>"
            f"<b>Bleed length:</b> {bleed_len} day(s)<br/>"
            f"<b>Intensity:</b> {intensity}<br/>"
            f"<b>Tags:</b> {tags}<br/><br/>"
            f"<b>Notes:</b><br/>{notes.replace('\\n', '<br/>')}"
            "</div>"
        )

        info_layout.addWidget(details)
        layout.addWidget(info)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


# ---------------------------------------------------------
# Improved Main Window
# ---------------------------------------------------------

INTENSITY_COLORS = {
    "none":   {"bg": "#D9D9D9", "fg": "#2B2B2B"},  # soft grey
    "light":  {"bg": "#CFE9FF", "fg": "#102A43"},  # pastel blue
    "medium": {"bg": "#E2D6FF", "fg": "#2D1B4E"},  # pastel purple
    "heavy":  {"bg": "#FFD6E7", "fg": "#4A1230"},  # pastel pink
}

def _apply_intensity_style(item: QTableWidgetItem, intensity: str) -> None:
    palette = INTENSITY_COLORS.get((intensity or "").strip().lower())
    if not palette:
        return
    item.setBackground(QBrush(QColor(palette["bg"])))
    item.setForeground(QBrush(QColor(palette["fg"])))

class CycleTrackerWindow(QMainWindow):
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.entries = self.storage.load()

        # guard flags for theming recursion
        self._applying_theme = False
        self._last_theme_sig = None

        self.setWindowTitle("Cycle Log")
        self.resize(900, 600)

        # ---------------- Header ----------------
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 10)

        title = QLabel("Cycle Log")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel("Track cycle patterns over time")
        subtitle.setStyleSheet("font-size: 14px; color: #666;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        # ---------------- Summary Card ----------------
        self.summary_card = QFrame()
        self.summary_card.setFrameShape(QFrame.StyledPanel)
        self.summary_card.setObjectName("SummaryCard")  # set BEFORE apply_theme/QSS
        self.summary_card.setStyleSheet("QFrame { border-radius: 10px; padding: 12px; }")

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 14px;")
        card_layout = QVBoxLayout(self.summary_card)
        card_layout.addWidget(self.summary_label)

        # ---------------- Table ----------------
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Start", "End", "Bleed length", "Intensity", "Tags", "Notes"])
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        # predictable selection/editing behavior
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # nicer sizing + wrapping notes
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)

        self.table.setStyleSheet("QTableWidget { font-size: 14px; }")

        # Hover tooltip support
        self._last_tooltip_entry_idx = None
        self.table.viewport().setMouseTracking(True)
        self.table.viewport().installEventFilter(self)

        # ---------------- Toolbar ----------------
        toolbar = QToolBar("Actions")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        view_action = QAction("View", self)
        add_action = QAction("Add", self)
        edit_action = QAction("Edit", self)
        delete_action = QAction("Delete", self)
        reload_action = QAction("Reload", self)

        toolbar.addAction(view_action)
        toolbar.addSeparator()
        toolbar.addAction(add_action)
        toolbar.addAction(edit_action)
        toolbar.addAction(delete_action)
        toolbar.addSeparator()
        toolbar.addAction(reload_action)

        view_action.triggered.connect(self.on_view)
        add_action.triggered.connect(self.on_add)
        edit_action.triggered.connect(self.on_edit)
        delete_action.triggered.connect(self.on_delete)
        reload_action.triggered.connect(self.on_reload)

        # convenient buttons row (layout improvement)
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(8)

        view_btn = QPushButton("View")
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Delete")
        reload_btn = QPushButton("Reload")

        view_btn.clicked.connect(self.on_view)
        add_btn.clicked.connect(self.on_add)
        edit_btn.clicked.connect(self.on_edit)
        del_btn.clicked.connect(self.on_delete)
        reload_btn.clicked.connect(self.on_reload)

        btn_row_layout.addWidget(view_btn)
        btn_row_layout.addWidget(add_btn)
        btn_row_layout.addWidget(edit_btn)
        btn_row_layout.addWidget(del_btn)
        btn_row_layout.addStretch(1)
        btn_row_layout.addWidget(reload_btn)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Return"), self, activated=self.on_view)
        QShortcut(QKeySequence("Enter"), self, activated=self.on_view)
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, activated=self.on_quick_add)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.on_add)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.on_edit)
        QShortcut(QKeySequence("Delete"), self, activated=self.on_delete)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.on_reload)

        # double click edits
        self.table.itemDoubleClicked.connect(lambda *_: self.on_edit())

        # ---------------- Layout ----------------
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(header)
        layout.addWidget(self.summary_card)
        layout.addWidget(btn_row)
        layout.addWidget(self.table)

        self.setCentralWidget(central)

        # Floating quick-add "+" button (bottom-right)
        self.fab = QPushButton("+", self)
        self.fab.setObjectName("QuickAddFab")
        self.fab.setToolTip("Quick Add")
        self.fab.setFixedSize(44, 44)
        self.fab.clicked.connect(self.on_quick_add)
        self.fab.raise_()
        self._position_fab()

        # Apply theme styling based on current palette (system/dark/light)
        self.apply_theme()

        self.refresh_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_fab()

    def _position_fab(self):
        if not hasattr(self, "fab"):
            return
        margin = 20
        x = self.width() - self.fab.width() - margin
        y = self.height() - self.fab.height() - margin
        self.fab.move(x, y)

    # ---------------- UI Logic ----------------

    def refresh_ui(self):
        self.populate_table()
        self.update_summary()

    def populate_table(self):
        # keep sorting from moving rows while we rebuild
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for entry_index, entry in enumerate(self.entries):
            row = self.table.rowCount()
            self.table.insertRow(row)

            start_item = QTableWidgetItem(entry.start_date)
            end_item = QTableWidgetItem(entry.end_date)
            len_item = QTableWidgetItem(str(entry.bleed_length_days()))
            intensity_item = QTableWidgetItem(entry.intensity)
            _apply_intensity_style(intensity_item, entry.intensity)
            tags_item = QTableWidgetItem(_tags_to_text(getattr(entry, "tags", [])))
            notes_item = QTableWidgetItem(entry.notes)

            # IMPORTANT: row index != entry index once user sorts.
            # Store the real entry index on every row.
            for it in (start_item, end_item, len_item, intensity_item, tags_item, notes_item):
                it.setData(Qt.UserRole, entry_index)

            self.table.setItem(row, 0, start_item)
            self.table.setItem(row, 1, end_item)
            self.table.setItem(row, 2, len_item)
            self.table.setItem(row, 3, intensity_item)
            self.table.setItem(row, 4, tags_item)
            self.table.setItem(row, 5, notes_item)

        self.table.setSortingEnabled(True)
        self.table.resizeRowsToContents()

    def get_selected_index(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        idx = item.data(Qt.UserRole)
        return int(idx) if idx is not None else None

    def update_summary(self):
        if len(self.entries) < 2:
            self.summary_label.setText("Not enough entries to estimate cycle patterns yet.")
            return

        entries = sorted(self.entries, key=lambda e: e.start_as_date())
        intervals = [
            (b.start_as_date() - a.start_as_date()).days
            for a, b in zip(entries[:-1], entries[1:])
            if (b.start_as_date() - a.start_as_date()).days > 0
        ]

        bleed_lengths = [e.bleed_length_days() for e in entries]
        avg_bleed = sum(bleed_lengths) / len(bleed_lengths) if bleed_lengths else 0

        if not intervals:
            self.summary_label.setText(
                f"Average bleed length: {avg_bleed:.1f} days\n"
                f"Estimated next cycle: unavailable (need more distinct start dates)"
            )
            return

        avg_cycle = sum(intervals) / len(intervals)
        next_start_ord = entries[-1].start_as_date().toordinal() + int(round(avg_cycle))
        next_start_date = date.fromordinal(next_start_ord).strftime("%Y-%m-%d")

        self.summary_label.setText(
            f"Average cycle length: {avg_cycle:.1f} days\n"
            f"Average bleed length: {avg_bleed:.1f} days\n"
            f"Estimated next cycle: {next_start_date}"
        )

    # ---------------- Actions ----------------

    def on_quick_add(self):
        # CycleDialog already defaults start/end to today; this is a low-friction entry point.
        dialog = CycleDialog(self)
        if dialog.exec():
            entry = dialog.get_entry()
            if entry:
                self.entries.append(entry)
                self.entries.sort(key=lambda e: e.start_date)
                try:
                    self.storage.save(self.entries)
                except OSError as e:
                    QMessageBox.critical(self, "Save failed", f"Could not save data:\n{e}")
                self.refresh_ui()

    def on_add(self):
        dialog = CycleDialog(self)
        if dialog.exec():
            entry = dialog.get_entry()
            if entry:
                self.entries.append(entry)
                self.entries.sort(key=lambda e: e.start_date)
                try:
                    self.storage.save(self.entries)
                except OSError as e:
                    QMessageBox.critical(self, "Save failed", f"Could not save data:\n{e}")
                self.refresh_ui()

    def on_edit(self):
        idx = self.get_selected_index()
        if idx is None:
            QMessageBox.information(self, "No selection", "Select an entry to edit.")
            return

        dialog = CycleDialog(self, existing=self.entries[idx])
        if dialog.exec():
            entry = dialog.get_entry()
            if entry:
                self.entries[idx] = entry
                self.entries.sort(key=lambda e: e.start_date)
                try:
                    self.storage.save(self.entries)
                except OSError as e:
                    QMessageBox.critical(self, "Save failed", f"Could not save data:\n{e}")
                self.refresh_ui()

    def on_delete(self):
        idx = self.get_selected_index()
        if idx is None:
            QMessageBox.information(self, "No selection", "Select an entry to delete.")
            return

        if QMessageBox.question(self, "Delete", "Delete this entry?") == QMessageBox.Yes:
            del self.entries[idx]
            try:
                self.storage.save(self.entries)
            except OSError as e:
                QMessageBox.critical(self, "Save failed", f"Could not save data:\n{e}")
            self.refresh_ui()

    def on_reload(self):
        self.entries = self.storage.load()
        self.refresh_ui()

    def on_view(self):
        idx = self.get_selected_index()
        if idx is None:
            QMessageBox.information(self, "No selection", "Select an entry to view.")
            return
        CycleDetailsDialog(self.entries[idx], self).exec()

    def changeEvent(self, event):
        # Re-apply when palette/theme changes at runtime
        if event.type() == QEvent.PaletteChange:
            self.apply_theme()
        super().changeEvent(event)

    def apply_theme(self):
        # prevent recursion (setStyleSheet can trigger PaletteChange)
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            pal = self.palette()
            window_bg = pal.window().color()

            # heuristic: darker background => dark mode
            is_dark = window_bg.lightness() < 128

            # keep a small signature; if unchanged, don't restyle
            theme_sig = (is_dark, window_bg.name())
            if self._last_theme_sig == theme_sig:
                return
            self._last_theme_sig = theme_sig

            if is_dark:
                header_bg = "#2b2f36"
                header_fg = "#f2f2f2"
                card_bg = "#1f232a"
                card_border = "#3a3f48"
                alt_row = "#20252c"
                grid = "#3a3f48"
            else:
                header_bg = "#e8eef7"
                header_fg = "#111111"
                card_bg = "#f7faff"
                card_border = "#d0d7e2"
                alt_row = "#fafcff"
                grid = "#d0d7e2"

            # Avoid global QWidget { color: ... } (can break palette/disabled colors)
            self.setStyleSheet(f"""
                QFrame#SummaryCard {{
                    background: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 10px;
                    padding: 12px;
                }}

                QTableWidget {{
                    background: {window_bg.name()};
                    gridline-color: {grid};
                    alternate-background-color: {alt_row};
                }}

                QHeaderView::section {{
                    background: {header_bg};
                    color: {header_fg};
                    padding: 6px;
                    font-weight: 600;
                    border: 0px;
                }}

                QToolBar {{
                    background: transparent;
                    border: 0px;
                }}

                QPushButton {{
                    padding: 6px 10px;
                }}

                QPushButton#QuickAddFab {{
                    border-radius: 22px;
                    font-size: 22px;
                    font-weight: 700;
                    padding: 0px;
                }}
            """)
        finally:
            self._applying_theme = False

    def eventFilter(self, obj, event):
        if obj == self.table.viewport():
            if event.type() == QEvent.MouseMove:
                pos = event.position().toPoint()  # Qt6
                item = self.table.itemAt(pos)
                if item is None:
                    if self._last_tooltip_entry_idx is not None:
                        QToolTip.hideText()
                        self._last_tooltip_entry_idx = None
                    return False

                idx = item.data(Qt.UserRole)
                entry_idx = int(idx) if idx is not None else None
                if entry_idx is None or entry_idx < 0 or entry_idx >= len(self.entries):
                    return False

                if self._last_tooltip_entry_idx != entry_idx:
                    entry = self.entries[entry_idx]
                    notes = (entry.notes or "").strip()
                    tags = _tags_to_text(getattr(entry, "tags", []))
                    if notes or tags:
                        text = ""
                        if tags:
                            text += f"Tags: {tags}\n"
                        text += f"Notes: {notes}" if notes else "Notes: (none)"
                        QToolTip.showText(event.globalPosition().toPoint(), text, self.table)
                    else:
                        QToolTip.hideText()
                    self._last_tooltip_entry_idx = entry_idx

            elif event.type() in (QEvent.Leave, QEvent.HoverLeave):
                QToolTip.hideText()
                self._last_tooltip_entry_idx = None

        return super().eventFilter(obj, event)


# -----------------------------
# Entry point
# -----------------------------


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("HRT Journey Cycle Tracker")

    storage = CycleStorage()
    window = CycleTrackerWindow(storage)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()