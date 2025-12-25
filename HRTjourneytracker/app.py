import sys
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QApplication,
	QComboBox,
	QDialog,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QMainWindow,
	QPlainTextEdit,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QTabWidget,
	QVBoxLayout,
	QWidget,
)

from modules.journal import add_entry, delete_entry, export_entry, list_entries, update_entry
from modules.medication_tracker import (
	delete_dose,
	export_dose,
	get_dose_options,
	get_medication_options,
	list_doses,
	log_dose,
	update_dose,
)


def _now_iso_local_seconds() -> str:
	return datetime.now().replace(microsecond=0).isoformat()


class LogsDialog(QDialog):
	def __init__(self, title: str, lines: list[str], parent: QWidget | None = None):
		super().__init__(parent)
		self.setWindowTitle(title)
		self.resize(720, 520)

		layout = QVBoxLayout(self)
		self.text = QPlainTextEdit(self)
		self.text.setReadOnly(True)
		self.text.setPlainText("\n".join(lines) if lines else "(no saved logs yet)")
		layout.addWidget(self.text)

		btn_close = QPushButton("Close", self)
		btn_close.clicked.connect(self.close)
		layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)


class MedicationTab(QWidget):
	def __init__(self, parent: QWidget | None = None):
		super().__init__(parent)

		root = QVBoxLayout(self)

		title = QLabel("Medication", self)
		title.setStyleSheet("font-weight: 600;")
		root.addWidget(title)

		# Pick row
		row1 = QGridLayout()
		row1.addWidget(QLabel("Med"), 0, 0)
		self.med_pick = QComboBox(self)
		self.med_pick.addItem("Select...")
		for opt in get_medication_options():
			self.med_pick.addItem(opt)
		row1.addWidget(self.med_pick, 0, 1)

		row1.addWidget(QLabel("Dose"), 0, 2)
		self.dose_pick = QComboBox(self)
		self.dose_pick.addItem("Select...")
		for opt in get_dose_options():
			self.dose_pick.addItem(opt)
		row1.addWidget(self.dose_pick, 0, 3)
		root.addLayout(row1)

		# Other row
		row2 = QGridLayout()
		row2.addWidget(QLabel("Other"), 0, 0)
		self.med_other = QLineEdit(self)
		self.med_other.setPlaceholderText("Medication name")
		self.med_other.setEnabled(False)
		row2.addWidget(self.med_other, 0, 1)

		row2.addWidget(QLabel("Other"), 0, 2)
		self.dose_other = QLineEdit(self)
		self.dose_other.setPlaceholderText("Dose (e.g., 2mg, 0.5 mL)")
		self.dose_other.setEnabled(False)
		row2.addWidget(self.dose_other, 0, 3)
		root.addLayout(row2)

		# Taken at row
		row3 = QHBoxLayout()
		row3.addWidget(QLabel("Taken at"))
		self.taken_at = QLineEdit(self)
		self.taken_at.setPlaceholderText("YYYY-MM-DDTHH:MM:SS (blank = now)")
		row3.addWidget(self.taken_at, stretch=1)
		btn_now = QPushButton("Now", self)
		btn_now.clicked.connect(self.set_taken_now)
		row3.addWidget(btn_now)
		root.addLayout(row3)

		# Actions
		actions = QHBoxLayout()
		btn_add = QPushButton("Log dose", self)
		btn_add.clicked.connect(self.on_log_dose)
		btn_view = QPushButton("View logs", self)
		btn_view.clicked.connect(self.open_logs)
		btn_refresh = QPushButton("Refresh", self)
		btn_refresh.clicked.connect(self.refresh)
		actions.addWidget(btn_add)
		actions.addWidget(btn_view)
		actions.addWidget(btn_refresh)
		root.addLayout(actions)

		self.status = QLabel("", self)
		root.addWidget(self.status)

		# Table
		self.table = QTableWidget(self)
		self.table.setColumnCount(3)
		self.table.setHorizontalHeaderLabels(["When", "Medication", "Dose"])
		self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.table.verticalHeader().setVisible(False)
		root.addWidget(self.table, stretch=1)

		self.med_pick.currentTextChanged.connect(self.on_med_pick_changed)
		self.dose_pick.currentTextChanged.connect(self.on_dose_pick_changed)

		self.refresh()

	def set_taken_now(self):
		self.taken_at.setText(_now_iso_local_seconds())

	def on_med_pick_changed(self, text: str):
		self.med_other.setEnabled(text == "Other...")

	def on_dose_pick_changed(self, text: str):
		self.dose_other.setEnabled(text == "Other...")

	def _get_med_name(self) -> str:
		text = self.med_pick.currentText().strip()
		if text == "Other...":
			return self.med_other.text().strip()
		if text == "Select...":
			return ""
		return text

	def _get_dose(self) -> str:
		text = self.dose_pick.currentText().strip()
		if text == "Other...":
			return self.dose_other.text().strip()
		if text == "Select...":
			return ""
		return text

	def on_log_dose(self):
		med_name = self._get_med_name()
		dose = self._get_dose()
		taken_at = self.taken_at.text().strip() or None

		if not med_name or not dose:
			self.status.setText("Medication and Dose are required.")
			return

		log_dose(med_name=med_name, dose=dose, taken_at=taken_at)
		self.status.setText("Saved.")

		self.med_pick.setCurrentText("Select...")
		self.med_other.clear()
		self.med_other.setEnabled(False)

		self.dose_pick.setCurrentText("Select...")
		self.dose_other.clear()
		self.dose_other.setEnabled(False)

		self.taken_at.clear()
		self.refresh()

	def refresh(self):
		rows = list(reversed(list_doses(limit=200)))
		self.table.setRowCount(len(rows))
		for i, row in enumerate(rows):
			self.table.setItem(i, 0, QTableWidgetItem(row.get("taken_at", "")))
			self.table.setItem(i, 1, QTableWidgetItem(row.get("med_name", "")))
			self.table.setItem(i, 2, QTableWidgetItem(row.get("dose", "")))
		self.table.resizeColumnsToContents()

	def open_logs(self):
		lines = [
			f"{row.get('taken_at','')} | {row.get('med_name','')} | {row.get('dose','')}"
			for row in reversed(list_doses(limit=500))
		]
		LogsDialog("Medication logs", lines, parent=self).exec()


class JournalTab(QWidget):
	def __init__(self, parent: QWidget | None = None):
		super().__init__(parent)

		root = QVBoxLayout(self)

		title = QLabel("Journal", self)
		title.setStyleSheet("font-weight: 600;")
		root.addWidget(title)

		# Title + When row
		row1 = QGridLayout()
		row1.addWidget(QLabel("Title"), 0, 0)
		self.title = QLineEdit(self)
		row1.addWidget(self.title, 0, 1)

		row1.addWidget(QLabel("When"), 0, 2)
		self.created_at = QLineEdit(self)
		self.created_at.setPlaceholderText("YYYY-MM-DDTHH:MM:SS (blank = now)")
		row1.addWidget(self.created_at, 0, 3)
		root.addLayout(row1)

		# Helpers row
		row2 = QHBoxLayout()
		btn_now = QPushButton("Now", self)
		btn_now.clicked.connect(self.set_created_now)
		row2.addWidget(btn_now)

		self.search = QLineEdit(self)
		self.search.setPlaceholderText("Search title/body (optional)")
		self.search.textChanged.connect(self.refresh)
		row2.addWidget(self.search, stretch=1)

		btn_clear = QPushButton("Clear", self)
		btn_clear.clicked.connect(self.clear_form)
		row2.addWidget(btn_clear)
		root.addLayout(row2)

		# Body
		self.body = QPlainTextEdit(self)
		self.body.setPlaceholderText("Write your entry...")
		root.addWidget(self.body, stretch=1)

		# Actions
		actions = QHBoxLayout()
		btn_add = QPushButton("Save entry", self)
		btn_add.clicked.connect(self.on_add_entry)
		btn_view = QPushButton("View logs", self)
		btn_view.clicked.connect(self.open_logs)
		btn_refresh = QPushButton("Refresh", self)
		btn_refresh.clicked.connect(self.refresh)
		actions.addWidget(btn_add)
		actions.addWidget(btn_view)
		actions.addWidget(btn_refresh)
		root.addLayout(actions)

		self.status = QLabel("", self)
		root.addWidget(self.status)

		# Table (preview)
		self.table = QTableWidget(self)
		self.table.setColumnCount(2)
		self.table.setHorizontalHeaderLabels(["When | Title", "Body (preview)"])
		self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.table.verticalHeader().setVisible(False)
		root.addWidget(self.table, stretch=1)

		self.refresh()

	def set_created_now(self):
		self.created_at.setText(_now_iso_local_seconds())

	def clear_form(self):
		self.title.clear()
		self.created_at.clear()
		self.body.clear()
		self.status.clear()

	def on_add_entry(self):
		title = self.title.text().strip()
		body = self.body.toPlainText().strip()
		created_at = self.created_at.text().strip() or None

		if not title or not body:
			self.status.setText("Title and Body are required.")
			return

		add_entry(title=title, body=body, created_at=created_at)
		self.status.setText("Saved.")

		self.title.clear()
		self.body.clear()
		self.created_at.clear()
		self.refresh()

	def refresh(self):
		q = (self.search.text() or "").strip().lower()
		rows = list(reversed(list_entries(limit=500)))

		if q:
			def match(r: dict) -> bool:
				return q in (r.get("title", "").lower()) or q in (r.get("body", "").lower())
			rows = [r for r in rows if match(r)]

		rows = rows[:200]
		self.table.setRowCount(len(rows))

		for i, row in enumerate(rows):
			header = f"{row.get('created_at','')} | {row.get('title','')}"
			body = row.get("body", "")
			preview = (body[:260] + "…") if len(body) > 260 else body
			self.table.setItem(i, 0, QTableWidgetItem(header))
			self.table.setItem(i, 1, QTableWidgetItem(preview))

		self.table.resizeColumnsToContents()

	def open_logs(self):
		lines = [
			f"{row.get('created_at','')} | {row.get('title','')} - {row.get('body','')}"
			for row in reversed(list_entries(limit=200))
		]
		LogsDialog("Journal logs", lines, parent=self).exec()


class ManageLogsTab(QWidget):
	def __init__(self, *, on_refresh_med=None, on_refresh_journal=None, parent: QWidget | None = None):
		super().__init__(parent)
		self._on_refresh_med = on_refresh_med
		self._on_refresh_journal = on_refresh_journal

		self._selected_id: str | None = None
		self._selected_kind: str = "Medication"
		self._items: list[dict] = []

		root = QVBoxLayout(self)

		title = QLabel("Manage Logs", self)
		title.setStyleSheet("font-weight: 600;")
		root.addWidget(title)

		# Top controls
		top = QHBoxLayout()
		top.addWidget(QLabel("Type"))
		self.kind = QComboBox(self)
		self.kind.addItems(["Medication", "Journal"])
		self.kind.currentTextChanged.connect(self.on_kind_changed)
		top.addWidget(self.kind)

		self.search = QLineEdit(self)
		self.search.setPlaceholderText("Search… (optional)")
		self.search.textChanged.connect(self.reload)
		top.addWidget(self.search, stretch=1)

		btn_reload = QPushButton("Reload", self)
		btn_reload.clicked.connect(self.reload)
		top.addWidget(btn_reload)
		root.addLayout(top)

		# Items table
		self.items_table = QTableWidget(self)
		self.items_table.setColumnCount(2)
		self.items_table.setHorizontalHeaderLabels(["ID", "Summary"])
		self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.items_table.verticalHeader().setVisible(False)
		self.items_table.itemSelectionChanged.connect(self.on_table_selection_changed)
		root.addWidget(self.items_table, stretch=1)

		# Editor
		editor = QGridLayout()
		editor.addWidget(QLabel("ID"), 0, 0)
		self.id_lbl = QLabel("(none)", self)
		editor.addWidget(self.id_lbl, 0, 1)

		editor.addWidget(QLabel("When"), 1, 0)
		self.when = QLineEdit(self)
		self.when.setPlaceholderText("YYYY-MM-DDTHH:MM:SS")
		editor.addWidget(self.when, 1, 1)

		self.a_label = QLabel("Medication", self)
		editor.addWidget(self.a_label, 2, 0)
		self.a = QLineEdit(self)
		editor.addWidget(self.a, 2, 1)

		self.b_label = QLabel("Dose", self)
		editor.addWidget(self.b_label, 3, 0)
		self.b = QPlainTextEdit(self)
		self.b.setFixedHeight(90)
		editor.addWidget(self.b, 3, 1)

		root.addLayout(editor)

		# Editor helpers
		helpers = QHBoxLayout()
		btn_now = QPushButton("Now", self)
		btn_now.clicked.connect(self.when_set_now)
		btn_clear_sel = QPushButton("Clear selection", self)
		btn_clear_sel.clicked.connect(self.clear_selection)
		helpers.addWidget(btn_now)
		helpers.addWidget(btn_clear_sel)
		helpers.addStretch(1)
		root.addLayout(helpers)

		# Actions
		actions = QHBoxLayout()
		btn_save = QPushButton("Save", self)
		btn_save.clicked.connect(self.save_selected)
		btn_delete = QPushButton("Delete", self)
		btn_delete.clicked.connect(self.delete_selected)
		btn_export = QPushButton("Export", self)
		btn_export.clicked.connect(self.export_selected)
		actions.addWidget(btn_save)
		actions.addWidget(btn_delete)
		actions.addWidget(btn_export)
		root.addLayout(actions)

		self.status = QLabel("", self)
		root.addWidget(self.status)

		self._sync_editor_labels()
		self.reload()

	def when_set_now(self):
		self.when.setText(_now_iso_local_seconds())

	def clear_selection(self):
		self._selected_id = None
		self.items_table.clearSelection()
		self._clear_editor()
		self.status.setText("Cleared.")

	def on_kind_changed(self, text: str):
		self._selected_kind = text
		self._selected_id = None
		self._clear_editor()
		self._sync_editor_labels()
		self.reload()

	def _sync_editor_labels(self):
		if self._selected_kind == "Medication":
			self.a_label.setText("Medication")
			self.b_label.setText("Dose")
			self.a.setPlaceholderText("Medication name")
			self.b.setPlaceholderText("Dose")
		else:
			self.a_label.setText("Title")
			self.b_label.setText("Body")
			self.a.setPlaceholderText("Title")
			self.b.setPlaceholderText("Body")

	def _clear_editor(self):
		self.id_lbl.setText("(none)")
		self.when.clear()
		self.a.clear()
		self.b.clear()

	def _matches_search(self, item: dict) -> bool:
		q = (self.search.text() or "").strip().lower()
		if not q:
			return True
		if self._selected_kind == "Medication":
			s = f"{item.get('taken_at','')} {item.get('med_name','')} {item.get('dose','')}".lower()
		else:
			s = f"{item.get('created_at','')} {item.get('title','')} {item.get('body','')}".lower()
		return q in s

	def reload(self):
		self.status.setText("")
		self._selected_id = None
		self._clear_editor()

		if self._selected_kind == "Medication":
			items = list(reversed(list_doses(limit=1000)))
			self._items = [x for x in items if self._matches_search(x)]
			self.items_table.setRowCount(len(self._items))
			for i, item in enumerate(self._items):
				item_id = item.get("id", "")
				line = f"{item.get('taken_at','')} | {item.get('med_name','')} | {item.get('dose','')}"
				self.items_table.setItem(i, 0, QTableWidgetItem(item_id))
				self.items_table.setItem(i, 1, QTableWidgetItem(line))
		else:
			items = list(reversed(list_entries(limit=1000)))
			self._items = [x for x in items if self._matches_search(x)]
			self.items_table.setRowCount(len(self._items))
			for i, item in enumerate(self._items):
				item_id = item.get("id", "")
				when = item.get("created_at", "")
				title = item.get("title", "")
				line = f"{when} | {title}"
				self.items_table.setItem(i, 0, QTableWidgetItem(item_id))
				self.items_table.setItem(i, 1, QTableWidgetItem(line))

		self.items_table.resizeColumnsToContents()

	def on_table_selection_changed(self):
		# BUGFIX: selectedItems()[0] may be a cell from column 1 ("Summary"), and
		# item(row, 0) can be None transiently depending on selection state.
		# Use currentRow() and always read the ID from column 0.
		row = self.items_table.currentRow()
		if row < 0:
			return
		item_id_item = self.items_table.item(row, 0)
		if not item_id_item:
			return
		self.select_item(item_id_item.text())

	def select_item(self, item_id: str):
		self._selected_id = item_id
		self.id_lbl.setText(item_id or "(missing id)")

		item = next((x for x in self._items if x.get("id") == item_id), None)
		if not item:
			self.status.setText("Item not found (try Reload).")
			return

		if self._selected_kind == "Medication":
			self.when.setText(item.get("taken_at", ""))
			self.a.setText(item.get("med_name", ""))
			self.b.setPlainText(item.get("dose", ""))
		else:
			self.when.setText(item.get("created_at", ""))
			self.a.setText(item.get("title", ""))
			self.b.setPlainText(item.get("body", ""))

		self.status.setText("Loaded.")

	def save_selected(self):
		if not self._selected_id:
			self.status.setText("Select an item first.")
			return

		when = self.when.text().strip()
		a = self.a.text().strip()
		b = self.b.toPlainText().strip()

		if not when or not a or not b:
			self.status.setText("All fields are required.")
			return

		if self._selected_kind == "Medication":
			ok = update_dose(self._selected_id, med_name=a, dose=b, taken_at=when)
		else:
			ok = update_entry(self._selected_id, title=a, body=b, created_at=when)

		self.status.setText("Saved." if ok else "Save failed.")
		self.reload()
		if ok:
			self._refresh_other_tabs()

	def delete_selected(self):
		if not self._selected_id:
			self.status.setText("Select an item first.")
			return

		if self._selected_kind == "Medication":
			ok = delete_dose(self._selected_id)
		else:
			ok = delete_entry(self._selected_id)

		self.status.setText("Deleted." if ok else "Delete failed.")
		self._selected_id = None
		self._clear_editor()
		self.reload()
		if ok:
			self._refresh_other_tabs()

	def export_selected(self):
		if not self._selected_id:
			self.status.setText("Select an item first.")
			return

		if self._selected_kind == "Medication":
			path = export_dose(self._selected_id)
		else:
			path = export_entry(self._selected_id)

		self.status.setText(f"Exported to: {path}" if path else "Export failed.")

	def _refresh_other_tabs(self):
		if self._on_refresh_med:
			self._on_refresh_med()
		if self._on_refresh_journal:
			self._on_refresh_journal()


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("HRT Journey Tracker")
		self.resize(980, 720)

		tabs = QTabWidget(self)
		self.setCentralWidget(tabs)

		self.med_tab = MedicationTab(self)
		self.journal_tab = JournalTab(self)
		self.manage_tab = ManageLogsTab(
			on_refresh_med=self.med_tab.refresh,
			on_refresh_journal=self.journal_tab.refresh,
			parent=self,
		)

		tabs.addTab(self.med_tab, "Medication")
		tabs.addTab(self.journal_tab, "Journal")
		tabs.addTab(self.manage_tab, "Manage Logs")


def main() -> int:
	app = QApplication(sys.argv)
	win = MainWindow()
	win.show()
	return app.exec()


if __name__ == "__main__":
	raise SystemExit(main())
