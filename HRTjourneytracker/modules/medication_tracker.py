from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
)


@dataclass
class MedRow:
    medication: str
    dosage: str
    notes: str = ""


@dataclass
class MedEntry:
    when: str  # ISO date YYYY-MM-DD
    meds: List[MedRow]


class _MedRowWidget(QWidget):
    """One medication row: dropdown + dosage + optional notes + remove."""
    def __init__(self, options: List[str], dosage_options: List[str], on_remove):
        super().__init__()
        self._on_remove = on_remove

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.med_combo = QComboBox()
        self.med_combo.setEditable(True)
        self.med_combo.addItems(options)

        self.dosage_combo = QComboBox()
        self.dosage_combo.setEditable(True)
        self.dosage_combo.addItems(dosage_options)
        self.dosage_combo.setInsertPolicy(QComboBox.InsertAtTop)
        self.dosage_combo.setPlaceholderText('Dosage (e.g., "2 mg")')

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Row notes (optional)")

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(lambda: self._on_remove(self))

        layout.addWidget(QLabel("Med"))
        layout.addWidget(self.med_combo, 2)
        layout.addWidget(QLabel("Dose"))
        layout.addWidget(self.dosage_combo, 1)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_input, 2)
        layout.addWidget(self.remove_btn)

    def to_row(self) -> Optional[MedRow]:
        medication = (self.med_combo.currentText() or "").strip()
        dosage = (self.dosage_combo.currentText() or "").strip()
        notes = (self.notes_input.text() or "").strip()
        if not medication:
            return None
        return MedRow(medication=medication, dosage=dosage, notes=notes)

    def set_from_row(self, row: MedRow) -> None:
        self.med_combo.setCurrentText(row.medication or "")
        self.dosage_combo.setCurrentText(row.dosage or "")
        self.notes_input.setText(row.notes or "")


class MedicationTracker(QWidget):
    def __init__(self):
        super().__init__()

        self._safe_mode = False
        self._data_path = self._default_data_path()
        self._entries: List[MedEntry] = []
        self._load()

        self._med_options = [
            "Estradiol",
            "Spironolactone (blocker)",
            "Cyproterone acetate (blocker)",
            "Bicalutamide (blocker)",
            "Progesterone",
            "Estradiol injection",
            "Supplement",
        ]

        self._dosage_options = [
            "",
            "0.5 mg",
            "1 mg",
            "2 mg",
            "4 mg",
            "6 mg",
            "8 mg",
            "12.5 mg",
            "25 mg",
            "50 mg",
            "100 mg",
            "200 mg",
            "0.1 mL",
            "0.2 mL",
            "0.25 mL",
            "0.3 mL",
            "0.4 mL",
            "0.5 mL",
            "1 mL",
        ]

        self._editing_entry_when: Optional[str] = None  # ISO date string key for the entry being edited

        self._last_export_dir: Optional[Path] = None

        root = QVBoxLayout(self)
        root.addWidget(QLabel("HRT Log"))

        # ---- Daily log UI
        form_box = QGroupBox("Log an entry")
        form = QFormLayout(form_box)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        # Dynamic rows container
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)
        self._row_widgets: List[_MedRowWidget] = []

        rows_actions = QHBoxLayout()
        self.add_row_btn = QPushButton("Add another medication")
        self.add_row_btn.clicked.connect(self._add_row)
        rows_actions.addWidget(self.add_row_btn)
        rows_actions.addStretch(1)

        self.log_button = QPushButton("Log Entry")
        self.log_button.clicked.connect(self._on_log_entry)

        self.cancel_edit_btn = QPushButton("Cancel Edit")
        self.cancel_edit_btn.clicked.connect(self._cancel_edit_mode)
        self.cancel_edit_btn.setVisible(False)

        form.addRow("Date", self.date_edit)
        form.addRow("Medications", self.rows_container)
        form.addRow("", QWidget())  # spacer row for layout consistency
        form.addRow("", self.add_row_btn)
        form.addRow(self.log_button)
        form.addRow(self.cancel_edit_btn)

        root.addWidget(form_box)

        # Start with one row
        if not self._row_widgets:
            self._add_row()

        # ---- Filters
        filters_box = QGroupBox("Filters")
        filters = QHBoxLayout(filters_box)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addDays(-30))

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())

        self.med_filter = QComboBox()
        self.med_filter.addItem("All medications")
        self._refresh_med_filter_items()

        self.apply_filters_btn = QPushButton("Apply")
        self.apply_filters_btn.clicked.connect(self._refresh_table)

        self.clear_filters_btn = QPushButton("Clear")
        self.clear_filters_btn.clicked.connect(self._clear_filters)

        filters.addWidget(QLabel("From"))
        filters.addWidget(self.from_date)
        filters.addWidget(QLabel("To"))
        filters.addWidget(self.to_date)
        filters.addWidget(QLabel("Medication"))
        filters.addWidget(self.med_filter, 1)
        filters.addWidget(self.apply_filters_btn)
        filters.addWidget(self.clear_filters_btn)

        root.addWidget(filters_box)

        # ---- History view
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Medications", "Dosages", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        history_actions = QHBoxLayout()
        self.edit_selected_btn = QPushButton("Edit Selected")
        self.edit_selected_btn.clicked.connect(self._edit_selected)
        self.delete_selected_btn = QPushButton("Delete Selected")
        self.delete_selected_btn.clicked.connect(self._delete_selected)

        self.export_txt_btn = QPushButton("Export (.txt)")
        self.export_txt_btn.clicked.connect(self._export_txt)

        history_actions.addStretch(1)
        history_actions.addWidget(self.edit_selected_btn)
        history_actions.addWidget(self.delete_selected_btn)
        history_actions.addWidget(self.export_txt_btn)

        root.addWidget(QLabel("History"))
        root.addLayout(history_actions)
        root.addWidget(self.table, 1)

        self._refresh_table()

    def set_safe_mode(self, enabled: bool):
        self._safe_mode = bool(enabled)
        self._refresh_table()

    def _add_row(self):
        w = _MedRowWidget(self._med_options, self._dosage_options, on_remove=self._remove_row)
        self._row_widgets.append(w)
        self.rows_layout.addWidget(w)

    def _remove_row(self, w: _MedRowWidget):
        if w in self._row_widgets:
            self._row_widgets.remove(w)
        w.setParent(None)
        w.deleteLater()
        if not self._row_widgets:
            self._add_row()

    def _default_data_path(self) -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "medication_log.json"

    def _load(self):
        if not self._data_path.exists():
            self._entries = []
            return
        try:
            raw: List[Dict[str, Any]] = json.loads(self._data_path.read_text(encoding="utf-8"))
            self._entries = []
            for item in raw:
                # Migration: legacy schema had {when, medication, dosage, notes}
                if "meds" not in item and "medication" in item:
                    meds = [MedRow(medication=item.get("medication", ""), dosage=item.get("dosage", ""), notes=item.get("notes", ""))]
                    self._entries.append(MedEntry(when=item.get("when", ""), meds=meds))
                    continue

                meds_raw = item.get("meds", []) or []
                meds = [MedRow(**m) for m in meds_raw if isinstance(m, dict)]
                self._entries.append(MedEntry(when=item.get("when", ""), meds=meds))

            self._entries.sort(key=lambda e: e.when, reverse=True)
        except Exception:
            self._entries = []

    def _save(self):
        self._data_path.write_text(
            json.dumps(
                [{"when": e.when, "meds": [asdict(m) for m in e.meds]} for e in self._entries],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _set_edit_mode(self, enabled: bool) -> None:
        if enabled:
            self.log_button.setText("Save Changes")
            self.cancel_edit_btn.setVisible(True)
        else:
            self.log_button.setText("Log Entry")
            self.cancel_edit_btn.setVisible(False)
            self._editing_entry_when = None

    def _cancel_edit_mode(self) -> None:
        self._set_edit_mode(False)
        # Reset rows (keep one empty)
        for w in list(self._row_widgets):
            self._remove_row(w)
        self._add_row()

    def _selected_entry_when(self) -> Optional[str]:
        idx = self.table.currentRow()
        if idx < 0:
            return None
        item = self.table.item(idx, 0)
        return (item.text() if item else None) or None

    def _find_entry_index_by_when(self, when_iso: str) -> Optional[int]:
        # entries are stored by date; treat 'when' as the key
        for i, e in enumerate(self._entries):
            if e.when == when_iso:
                return i
        return None

    def _delete_selected(self) -> None:
        when = self._selected_entry_when()
        if not when:
            return

        res = QMessageBox.question(
            self,
            "Delete entry",
            f"Delete log entry for {when}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        idx = self._find_entry_index_by_when(when)
        if idx is None:
            return

        # If deleting the one currently being edited, exit edit mode.
        if self._editing_entry_when == when:
            self._set_edit_mode(False)

        del self._entries[idx]
        self._save()
        self._refresh_med_filter_items()
        self._refresh_table()

    def _edit_selected(self) -> None:
        when = self._selected_entry_when()
        if not when:
            return

        idx = self._find_entry_index_by_when(when)
        if idx is None:
            return

        e = self._entries[idx]
        try:
            d = datetime.fromisoformat(e.when).date()
        except ValueError:
            return

        # Load date + meds into the form
        self.date_edit.setDate(QDate(d.year, d.month, d.day))

        for w in list(self._row_widgets):
            self._remove_row(w)

        meds = e.meds or []
        if not meds:
            self._add_row()
        else:
            for m in meds:
                self._add_row()
                self._row_widgets[-1].set_from_row(m)

        self._editing_entry_when = e.when
        self._set_edit_mode(True)

    def _on_log_entry(self):
        when = self.date_edit.date().toPython()

        meds: List[MedRow] = []
        for w in self._row_widgets:
            row = w.to_row()
            if row:
                meds.append(row)

        if not meds:
            return

        new_entry = MedEntry(when=when.isoformat(), meds=meds)

        # EDIT mode: replace the existing entry
        if self._editing_entry_when:
            idx = self._find_entry_index_by_when(self._editing_entry_when)
            if idx is None:
                # fallback: if it vanished, just append
                self._entries.append(new_entry)
            else:
                self._entries[idx] = new_entry
            self._set_edit_mode(False)
        else:
            self._entries.append(new_entry)

        self._entries.sort(key=lambda e: e.when, reverse=True)
        self._save()

        # Reset rows (keep one empty)
        for w in list(self._row_widgets):
            self._remove_row(w)
        self._add_row()

        self._refresh_med_filter_items()
        self._refresh_table()

    def _clear_filters(self):
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.med_filter.setCurrentIndex(0)
        self._refresh_table()

    def _refresh_med_filter_items(self):
        current = self.med_filter.currentText() if hasattr(self, "med_filter") else None
        meds = sorted({m.medication for e in self._entries for m in (e.meds or []) if m.medication})
        if hasattr(self, "med_filter"):
            self.med_filter.blockSignals(True)
            self.med_filter.clear()
            self.med_filter.addItem("All medications")
            for m in meds:
                self.med_filter.addItem(m)
            if current:
                idx = self.med_filter.findText(current)
                if idx >= 0:
                    self.med_filter.setCurrentIndex(idx)
            self.med_filter.blockSignals(False)

    def _filtered_entries(self) -> List[MedEntry]:
        from_d: date = self.from_date.date().toPython()
        to_d: date = self.to_date.date().toPython()
        med = self.med_filter.currentText()
        use_med = med and med != "All medications"

        out: List[MedEntry] = []
        for e in self._entries:
            try:
                ed = datetime.fromisoformat(e.when).date()
            except ValueError:
                continue
            if ed < from_d or ed > to_d:
                continue
            if use_med:
                if not any((m.medication == med) for m in (e.meds or [])):
                    continue
            out.append(e)
        return out

    def _refresh_table(self):
        rows = self._filtered_entries()
        self.table.setRowCount(len(rows))

        for r, e in enumerate(rows):
            meds = e.meds or []
            med_names = ", ".join([m.medication for m in meds if m.medication])

            if self._safe_mode:
                dosages = "••••"
                notes = "Hidden (Safe Mode)"
            else:
                dosages = ", ".join([m.dosage for m in meds if m.dosage])
                notes = " | ".join([m.notes for m in meds if m.notes])

            self.table.setItem(r, 0, QTableWidgetItem(e.when))
            self.table.setItem(r, 1, QTableWidgetItem(med_names))
            self.table.setItem(r, 2, QTableWidgetItem(dosages))
            self.table.setItem(r, 3, QTableWidgetItem(notes))

        self.table.repaint()

    def _export_txt(self) -> None:
        rows = self._filtered_entries()
        if not rows:
            QMessageBox.information(self, "Export", "No entries to export for the current filters.")
            return

        default_name = f"medication_log_{date.today().isoformat()}.txt"
        start_dir = str(self._last_export_dir) if self._last_export_dir else ""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to .txt",
            str(Path(start_dir) / default_name) if start_dir else default_name,
            "Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return

        lines: List[str] = []
        lines.append("Medication Log Export")
        lines.append(f"Exported: {datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"Filters: from={self.from_date.date().toPython().isoformat()} to={self.to_date.date().toPython().isoformat()} med={self.med_filter.currentText()}")
        lines.append("")

        for e in rows:
            meds = e.meds or []
            lines.append(f"Date: {e.when}")
            if not meds:
                lines.append("  (no medications)")
                lines.append("")
                continue

            for m in meds:
                med_name = m.medication or ""
                if self._safe_mode:
                    dosage = "••••"
                    notes = "Hidden (Safe Mode)" if (m.notes or "") else ""
                else:
                    dosage = m.dosage or ""
                    notes = m.notes or ""

                line = f"  - {med_name}"
                if dosage:
                    line += f" | Dose: {dosage}"
                if notes:
                    line += f" | Notes: {notes}"
                lines.append(line)

            lines.append("")

        try:
            out_path = Path(path)
            out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            self._last_export_dir = out_path.parent
        except Exception as ex:
            QMessageBox.critical(self, "Export failed", f"Could not write file:\n{ex}")
            return

        QMessageBox.information(self, "Export", f"Exported {len(rows)} entr{'y' if len(rows)==1 else 'ies'} to:\n{path}")