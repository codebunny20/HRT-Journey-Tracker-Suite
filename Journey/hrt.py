from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QComboBox,
    QTextEdit, QDateEdit, QTimeEdit, QCheckBox,
    QSlider, QGroupBox, QFormLayout, QScrollArea,
    QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QDate, QTime
import sys
import json

from storage import save_entry, get_entry_by_date, upsert_entry, delete_entry_by_date
from storage import load_data


class HrtTrackerWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HRT Tracker")
        self.resize(1000, 700)

        # --- NEW: global styling + better defaults ---
        self.setStyleSheet("""
        QMainWindow { background: #0f172a; }
        QWidget { color: #e5e7eb; font-size: 13px; }
        QGroupBox {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 12px;
            margin-top: 12px;
            padding: 10px;
            background: rgba(255,255,255,0.03);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: #f3f4f6;
            font-weight: 600;
        }
        QTabWidget::pane {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 12px;
            background: rgba(255,255,255,0.02);
        }
        QTabBar::tab {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.10);
            padding: 8px 12px;
            margin-right: 6px;
            border-radius: 10px;
        }
        QTabBar::tab:selected { background: rgba(59,130,246,0.28); border-color: rgba(59,130,246,0.55); }
        QLineEdit, QComboBox, QDateEdit, QTimeEdit, QTextEdit {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 10px;
            padding: 8px;
            selection-background-color: rgba(59,130,246,0.55);
        }
        QTextEdit { line-height: 1.25; }
        QPushButton {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 10px;
            padding: 8px 12px;
        }
        QPushButton:hover { background: rgba(255,255,255,0.10); }
        QPushButton:pressed { background: rgba(255,255,255,0.14); }
        QPushButton[variant="primary"] { background: rgba(59,130,246,0.55); border-color: rgba(59,130,246,0.75); font-weight: 600; }
        QPushButton[variant="danger"]  { background: rgba(239,68,68,0.45); border-color: rgba(239,68,68,0.65); }
        QSlider::groove:horizontal {
            height: 8px; border-radius: 4px;
            background: rgba(255,255,255,0.10);
        }
        QSlider::sub-page:horizontal {
            background: rgba(59,130,246,0.55);
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            width: 18px; margin: -6px 0;
            border-radius: 9px;
            background: #e5e7eb;
            border: 2px solid rgba(15,23,42,0.9);
        }
        QListWidget {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 12px;
            padding: 6px;
        }
        QListWidget::item { padding: 8px; border-radius: 9px; }
        QListWidget::item:selected { background: rgba(59,130,246,0.26); }
        """)
        # --------------------------------------------

        # central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)     # NEW
        main_layout.setSpacing(10)                         # NEW

        # Tabs
        tabs = QTabWidget()
        self.tabs = tabs
        main_layout.addWidget(tabs)

        tabs.addTab(self._create_overview_tab(), "Overview")
        tabs.addTab(self._create_medication_tab(), "Medication")
        tabs.addTab(self._create_mood_tab(), "Mood")
        tabs.addTab(self._create_physical_tab(), "Physical")
        tabs.addTab(self._create_mental_social_tab(), "Mental & Social")
        tabs.addTab(self._create_notes_tab(), "Notes & Progress")
        tabs.addTab(self._create_entries_tab(), "Entries")

        # Bottom buttons
        button_row = QHBoxLayout()
        button_row.addStretch()
        self.delete_btn = QPushButton("Delete entry (by date)")
        save_btn = QPushButton("Save entry")
        clear_btn = QPushButton("Clear form")

        # NEW: visual intent
        self.delete_btn.setProperty("variant", "danger")
        save_btn.setProperty("variant", "primary")

        # NEW: shortcuts
        save_btn.setShortcut("Ctrl+S")
        clear_btn.setShortcut("Ctrl+R")
        self.delete_btn.setShortcut("Del")

        button_row.addWidget(self.delete_btn)
        button_row.addWidget(clear_btn)
        button_row.addWidget(save_btn)
        main_layout.addLayout(button_row)

        clear_btn.clicked.connect(self._clear_all)
        save_btn.clicked.connect(self._save_entry)
        self.delete_btn.clicked.connect(self._delete_entry_for_date)

        # Load existing entry whenever date changes
        self.date_edit.dateChanged.connect(self._load_entry_for_date)
        self._load_entry_for_date(self.date_edit.date())

        self._refresh_entries()

    # -------------------------
    # Overview tab
    # -------------------------
    def _create_overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)  # NEW
        layout.setSpacing(10)                      # NEW

        # Date/time row
        dt_layout = QHBoxLayout()
        dt_layout.setSpacing(10)  # NEW
        dt_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")  # NEW
        dt_layout.addWidget(self.date_edit)

        dt_layout.addWidget(QLabel("Time:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        dt_layout.addWidget(self.time_edit)

        dt_layout.addStretch()
        layout.addLayout(dt_layout)

        # Daily summary
        summary_group = QGroupBox("Daily summary (optional)")
        summary_layout = QFormLayout(summary_group)
        summary_layout.setLabelAlignment(Qt.AlignLeft)  # NEW
        summary_layout.setFormAlignment(Qt.AlignTop)    # NEW
        summary_layout.setHorizontalSpacing(14)         # NEW
        summary_layout.setVerticalSpacing(10)           # NEW

        self.energy_slider = self._create_labeled_slider()
        self.overall_mood_slider = self._create_labeled_slider()
        self.dysphoria_slider = self._create_labeled_slider()
        self.euphoria_slider = self._create_labeled_slider()

        summary_layout.addRow("Energy (0–10):", self.energy_slider)
        summary_layout.addRow("Overall mood (0–10):", self.overall_mood_slider)
        summary_layout.addRow("Dysphoria (0–10):", self.dysphoria_slider)
        summary_layout.addRow("Euphoria (0–10):", self.euphoria_slider)

        layout.addWidget(summary_group)
        layout.addStretch()

        return tab

    # -------------------------
    # Medication tab
    # -------------------------
    def _create_medication_tab(self) -> QWidget:
        tab = QWidget()
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(12, 12, 12, 12)  # NEW
        outer_layout.setSpacing(10)                      # NEW

        # Make scrollable for future expansion
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)

        med_group = QGroupBox("Medication tracking")
        form = QFormLayout(med_group)
        form.setHorizontalSpacing(14)  # NEW
        form.setVerticalSpacing(10)    # NEW

        self.med_type = QLineEdit()
        self.med_type.setPlaceholderText("e.g., Estradiol, Spiro, Progesterone")  # NEW
        self.med_route = QComboBox()
        self.med_route.addItems(["", "Oral", "Sublingual", "Injection", "Patch", "Gel", "Other"])

        self.med_dose = QLineEdit()
        self.med_dose.setPlaceholderText("e.g., 2 mg, 0.5 mL")

        self.med_taken_time = QTimeEdit()
        self.med_taken_time.setTime(QTime.currentTime())

        self.med_missed_checkbox = QCheckBox("Missed this dose")
        self.med_side_effects = QTextEdit()
        self.med_side_effects.setMinimumHeight(110)  # NEW
        self.med_side_effects.setPlaceholderText("Side effects, sensations, or notes after dose...")

        form.addRow("Medication name/type:", self.med_type)
        form.addRow("Route:", self.med_route)
        form.addRow("Dose:", self.med_dose)
        form.addRow("Dose time:", self.med_taken_time)
        form.addRow("", self.med_missed_checkbox)
        form.addRow("Immediate side effects / notes:", self.med_side_effects)

        layout.addWidget(med_group)
        layout.addStretch()
        outer_layout.addWidget(scroll)

        return tab

    # -------------------------
    # Mood tab
    # -------------------------
    def _create_mood_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)  # NEW
        layout.setSpacing(10)                      # NEW

        mood_group = QGroupBox("Mood & emotions")
        form = QFormLayout(mood_group)
        form.setHorizontalSpacing(14)  # NEW
        form.setVerticalSpacing(10)    # NEW

        self.mood_slider = self._create_labeled_slider()
        self.anxiety_slider = self._create_labeled_slider()
        self.irritability_slider = self._create_labeled_slider()
        self.stress_slider = self._create_labeled_slider()

        self.mood_notes = QTextEdit()
        self.mood_notes.setMinimumHeight(140)  # NEW
        self.mood_notes.setPlaceholderText(
            "Describe emotional patterns, triggers, and any notable events..."
        )

        form.addRow("Mood (0–10):", self.mood_slider)
        form.addRow("Anxiety (0–10):", self.anxiety_slider)
        form.addRow("Irritability (0–10):", self.irritability_slider)
        form.addRow("Stress (0–10):", self.stress_slider)
        form.addRow("Mood notes:", self.mood_notes)

        layout.addWidget(mood_group)
        layout.addStretch()

        return tab

    # -------------------------
    # Physical tab
    # -------------------------
    def _create_physical_tab(self) -> QWidget:
        tab = QWidget()
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(12, 12, 12, 12)  # NEW
        outer_layout.setSpacing(10)                      # NEW

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)

        # General physical group
        physical_group = QGroupBox("Physical sensations & changes")
        form = QFormLayout(physical_group)
        form.setHorizontalSpacing(14)  # NEW
        form.setVerticalSpacing(10)    # NEW

        self.energy_physical_slider = self._create_labeled_slider()
        self.sleep_quality_slider = self._create_labeled_slider()
        self.libido_slider = self._create_labeled_slider()

        self.skin_changes = QTextEdit()
        self.skin_changes.setPlaceholderText("Skin texture, dryness/oiliness, acne, etc...")

        self.body_hair_changes = QTextEdit()
        self.body_hair_changes.setPlaceholderText("Body hair density, texture, growth rate...")

        self.body_shape_changes = QTextEdit()
        self.body_shape_changes.setPlaceholderText("Fat distribution, muscle softness/firmness...")

        self.breast_chest_sensations = QTextEdit()
        self.breast_chest_sensations.setPlaceholderText("Tenderness, fullness, sensitivity...")

        self.general_physical_notes = QTextEdit()
        self.general_physical_notes.setPlaceholderText("Other sensations: headaches, digestion, pain, etc...")

        for te in [
            self.skin_changes, self.body_hair_changes, self.body_shape_changes,
            self.breast_chest_sensations, self.general_physical_notes
        ]:
            te.setMinimumHeight(110)  # NEW

        form.addRow("Energy (physical) 0–10:", self.energy_physical_slider)
        form.addRow("Sleep quality 0–10:", self.sleep_quality_slider)
        form.addRow("Libido 0–10:", self.libido_slider)
        form.addRow("Skin changes:", self.skin_changes)
        form.addRow("Body hair changes:", self.body_hair_changes)
        form.addRow("Body shape changes:", self.body_shape_changes)
        form.addRow("Breast/chest sensations:", self.breast_chest_sensations)
        form.addRow("Other physical notes:", self.general_physical_notes)

        layout.addWidget(physical_group)
        layout.addStretch()
        outer_layout.addWidget(scroll)

        return tab

    # -------------------------
    # Mental & Social tab
    # -------------------------
    def _create_mental_social_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)  # NEW
        layout.setSpacing(10)                      # NEW

        group = QGroupBox("Mental & social well-being")
        form = QFormLayout(group)
        form.setHorizontalSpacing(14)  # NEW
        form.setVerticalSpacing(10)    # NEW

        self.social_energy_slider = self._create_labeled_slider()
        self.body_image_slider = self._create_labeled_slider()

        self.dysphoria_context = QTextEdit()
        self.dysphoria_context.setPlaceholderText("Situations where dysphoria increased...")

        self.euphoria_context = QTextEdit()
        self.euphoria_context.setPlaceholderText("Gender euphoria moments, affirming experiences...")

        self.social_notes = QTextEdit()
        self.social_notes.setPlaceholderText("Social comfort, support, challenges, public experiences...")

        for te in [self.dysphoria_context, self.euphoria_context, self.social_notes]:
            te.setMinimumHeight(110)  # NEW

        form.addRow("Social energy 0–10:", self.social_energy_slider)
        form.addRow("Body image satisfaction 0–10:", self.body_image_slider)
        form.addRow("Dysphoria context:", self.dysphoria_context)
        form.addRow("Euphoria context:", self.euphoria_context)
        form.addRow("Social notes:", self.social_notes)

        layout.addWidget(group)
        layout.addStretch()

        return tab

    # -------------------------
    # Notes & Progress tab
    # -------------------------
    def _create_notes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)  # NEW
        layout.setSpacing(10)                      # NEW

        notes_group = QGroupBox("Notes, reflections, and milestones")
        v = QVBoxLayout(notes_group)

        self.general_notes = QTextEdit()
        self.general_notes.setMinimumHeight(260)  # NEW
        self.general_notes.setPlaceholderText(
            "Freeform journaling, milestones, comparisons to past entries, intentions for next days..."
        )

        v.addWidget(self.general_notes)
        layout.addWidget(notes_group)
        layout.addStretch()
        return tab

    # -------------------------
    # Entries tab
    # -------------------------
    def _create_entries_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)  # NEW
        layout.setSpacing(10)                      # NEW

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)  # NEW

        self.entries_refresh_btn = QPushButton("Refresh")
        self.entries_open_btn = QPushButton("Open in form")
        self.entries_delete_btn = QPushButton("Delete")
        self.entries_delete_btn.setProperty("variant", "danger")  # NEW

        # NEW: search/filter
        self.entries_search = QLineEdit()
        self.entries_search.setPlaceholderText("Search by date/time/medication…")
        self.entries_search.textChanged.connect(self._refresh_entries)

        self.entries_format_btn = QPushButton("View: Plain text")
        self.entries_format_btn.setCheckable(True)
        self.entries_format_btn.toggled.connect(self._toggle_entries_view_format)

        btn_row.addWidget(self.entries_refresh_btn)
        btn_row.addWidget(self.entries_open_btn)
        btn_row.addWidget(self.entries_delete_btn)
        btn_row.addWidget(self.entries_format_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(self.entries_search)  # NEW
        layout.addLayout(btn_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)  # NEW

        self.entries_list = QListWidget()
        self.entries_list.setMinimumWidth(320)  # NEW (more comfortable)
        splitter.addWidget(self.entries_list)

        self.entry_details = QTextEdit()
        self.entry_details.setReadOnly(True)
        self.entry_details.setPlaceholderText("Select an entry on the left to view full details.")
        splitter.addWidget(self.entry_details)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self.entries_refresh_btn.clicked.connect(self._refresh_entries)
        self.entries_list.currentItemChanged.connect(self._on_entries_selection_changed)
        self.entries_open_btn.clicked.connect(self._open_selected_entry_in_form)
        self.entries_delete_btn.clicked.connect(self._delete_selected_entry)

        self._entries_view_mode = "plain"
        return tab

    def _toggle_entries_view_format(self, checked: bool):
        # checked => JSON view
        self._entries_view_mode = "json" if checked else "plain"
        self.entries_format_btn.setText("View: JSON" if checked else "View: Plain text")
        # re-render selection
        self._on_entries_selection_changed(self.entries_list.currentItem(), None)

    def _format_entry_plain_text(self, entry: dict) -> str:
        def line(key: str, value) -> str:
            v = "" if value is None else str(value).strip()
            return f"{key}: {v}" if v else f"{key}:"

        def section(title: str) -> str:
            return f"\n== {title} ==\n"

        d = str(entry.get("date", "")).strip()
        t = str(entry.get("time", "")).strip()

        out = []
        out.append("HRT Tracker Entry")
        out.append("----------------")
        out.append(line("Date", d))
        out.append(line("Time", t))

        # Overview
        out.append(section("Overview"))
        out.append(line("Energy (0-10)", entry.get("energy", "")))
        out.append(line("Overall mood (0-10)", entry.get("overall_mood", "")))
        out.append(line("Dysphoria (0-10)", entry.get("dysphoria", "")))
        out.append(line("Euphoria (0-10)", entry.get("euphoria", "")))

        # Medication
        med = entry.get("medication") or {}
        out.append(section("Medication"))
        out.append(line("Type", med.get("type", "")))
        out.append(line("Route", med.get("route", "")))
        out.append(line("Dose", med.get("dose", "")))
        out.append(line("Time taken", med.get("time_taken", "")))
        out.append(line("Missed", "Yes" if med.get("missed", False) else "No"))
        se = str(med.get("side_effects", "")).strip()
        if se:
            out.append("\nSide effects / notes:\n" + se)

        # Mood
        mood = entry.get("mood_details") or {}
        out.append(section("Mood"))
        out.append(line("Mood (0-10)", mood.get("mood", "")))
        out.append(line("Anxiety (0-10)", mood.get("anxiety", "")))
        out.append(line("Irritability (0-10)", mood.get("irritability", "")))
        out.append(line("Stress (0-10)", mood.get("stress", "")))
        mn = str(mood.get("notes", "")).strip()
        if mn:
            out.append("\nMood notes:\n" + mn)

        # Physical
        phys = entry.get("physical") or {}
        out.append(section("Physical"))
        out.append(line("Energy (physical) (0-10)", phys.get("energy_physical", "")))
        out.append(line("Sleep quality (0-10)", phys.get("sleep_quality", "")))
        out.append(line("Libido (0-10)", phys.get("libido", "")))
        for label, k in [
            ("Skin changes", "skin"),
            ("Body hair changes", "body_hair"),
            ("Body shape changes", "body_shape"),
            ("Breast/chest sensations", "breast_chest"),
            ("Other physical notes", "other"),
        ]:
            v = str(phys.get(k, "")).strip()
            if v:
                out.append(f"\n{label}:\n{v}")

        # Mental & Social
        ms = entry.get("mental_social") or {}
        out.append(section("Mental & Social"))
        out.append(line("Social energy (0-10)", ms.get("social_energy", "")))
        out.append(line("Body image satisfaction (0-10)", ms.get("body_image", "")))
        for label, k in [
            ("Dysphoria context", "dysphoria_context"),
            ("Euphoria context", "euphoria_context"),
            ("Social notes", "social_notes"),
        ]:
            v = str(ms.get(k, "")).strip()
            if v:
                out.append(f"\n{label}:\n{v}")

        # Notes
        notes = str(entry.get("notes", "")).strip()
        if notes:
            out.append(section("Notes"))
            out.append(notes)

        # normalize
        text = "\n".join(out).strip() + "\n"
        return text

    def _on_entries_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            self.entry_details.clear()
            return

        entry = current.data(Qt.UserRole) or {}

        if getattr(self, "_entries_view_mode", "plain") == "json":
            try:
                pretty = json.dumps(entry, indent=4, ensure_ascii=False, sort_keys=True)
            except Exception:
                pretty = str(entry)
            self.entry_details.setPlainText(pretty)
            return

        # plain text view
        try:
            self.entry_details.setPlainText(self._format_entry_plain_text(entry))
        except Exception as ex:
            self.entry_details.setPlainText(f"Could not format entry:\n{ex}\n\nRaw:\n{entry}")

    def _refresh_entries(self):
        try:
            data = load_data()
        except Exception as ex:
            QMessageBox.warning(self, "Load failed", f"Could not load entries:\n{ex}")
            return

        data_sorted = sorted(data, key=lambda e: str(e.get("date", "")), reverse=True)

        # NEW: filter by search text
        query = ""
        if hasattr(self, "entries_search") and self.entries_search is not None:
            query = self.entries_search.text().strip().lower()

        self.entries_list.clear()
        self.entry_details.clear()

        for e in data_sorted:
            d = str(e.get("date", "")).strip()
            t = str(e.get("time", "")).strip()
            med = (e.get("medication") or {})
            med_type = str(med.get("type", "")).strip()

            label_parts = [p for p in [d, t] if p]
            label = "  ".join(label_parts)
            if med_type:
                label = f"{label}  -  {med_type}" if label else med_type
            if not label:
                label = "<unknown>"

            if query:
                hay = f"{label} {json.dumps(e, ensure_ascii=False)}".lower()
                if query not in hay:
                    continue

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, e)
            self.entries_list.addItem(item)

        if self.entries_list.count() == 0:
            self.entry_details.setPlainText("No entries found yet.")

    def _get_selected_entry(self) -> dict:
        item = self.entries_list.currentItem()
        return (item.data(Qt.UserRole) if item else None) or {}

    def _open_selected_entry_in_form(self):
        entry = self._get_selected_entry()
        iso = str(entry.get("date", "")).strip()
        if not iso:
            QMessageBox.information(self, "Open", "Select an entry first.")
            return

        qd = QDate.fromString(iso, "yyyy-MM-dd")
        if not qd.isValid():
            QMessageBox.warning(self, "Open", "Selected entry has an invalid date.")
            return

        self.date_edit.setDate(qd)
        self.tabs.setCurrentIndex(0)

    def _delete_selected_entry(self):
        entry = self._get_selected_entry()
        iso = str(entry.get("date", "")).strip()
        if not iso:
            QMessageBox.information(self, "Delete", "Select an entry first.")
            return

        qd = QDate.fromString(iso, "yyyy-MM-dd")
        if not qd.isValid():
            QMessageBox.warning(self, "Delete", "Selected entry has an invalid date.")
            return

        res = QMessageBox.question(
            self,
            "Delete entry",
            f"Delete entry for {iso}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        try:
            deleted = delete_entry_by_date(qd.toPython())
        except Exception as ex:
            QMessageBox.critical(self, "Delete failed", f"Could not delete entry:\n{ex}")
            return

        if deleted:
            self._refresh_entries()
            if self.date_edit.date().toString("yyyy-MM-dd") == iso:
                self._clear_all()
            QMessageBox.information(self, "Deleted", "Entry deleted.")
        else:
            QMessageBox.information(self, "Not found", "No entry exists for that date.")

    # -------------------------
    # Helpers
    # -------------------------
    def _create_labeled_slider(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)  # NEW
        layout.setSpacing(10)                  # NEW

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(10)
        slider.setTickInterval(1)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setValue(5)
        slider.setSingleStep(1)                # NEW
        slider.setPageStep(1)                  # NEW

        value_label = QLabel("5 / 10")         # NEW
        value_label.setFixedWidth(56)          # NEW
        value_label.setAlignment(Qt.AlignCenter)

        def update_label(val):
            value_label.setText(f"{val} / 10")  # NEW

        slider.valueChanged.connect(update_label)

        layout.addWidget(slider, 1)
        layout.addWidget(value_label, 0)

        container.slider = slider
        container.value_label = value_label
        return container

    def _clear_all(self):
        self.time_edit.setTime(QTime.currentTime())

        self.med_type.clear()
        self.med_dose.clear()

        self.med_route.setCurrentIndex(0)
        self.med_missed_checkbox.setChecked(False)

        self.med_side_effects.clear()
        self.mood_notes.clear()
        self.skin_changes.clear()
        self.body_hair_changes.clear()
        self.body_shape_changes.clear()
        self.breast_chest_sensations.clear()
        self.general_physical_notes.clear()
        self.dysphoria_context.clear()
        self.euphoria_context.clear()
        self.social_notes.clear()
        self.general_notes.clear()

        for s in [
            self.energy_slider, self.overall_mood_slider, self.dysphoria_slider, self.euphoria_slider,
            self.mood_slider, self.anxiety_slider, self.irritability_slider, self.stress_slider,
            self.energy_physical_slider, self.sleep_quality_slider, self.libido_slider,
            self.social_energy_slider, self.body_image_slider,
        ]:
            s.slider.setValue(5)

    def _load_entry_for_date(self, qdate: QDate):
        entry = get_entry_by_date(qdate.toPython())
        if not entry:
            return

        try:
            t = (entry.get("time") or "").strip()
            if t:
                parsed = QTime.fromString(t, "HH:mm")
                if parsed.isValid():
                    self.time_edit.setTime(parsed)

            self.energy_slider.slider.setValue(int(entry.get("energy", 5)))
            self.overall_mood_slider.slider.setValue(int(entry.get("overall_mood", 5)))
            self.dysphoria_slider.slider.setValue(int(entry.get("dysphoria", 5)))
            self.euphoria_slider.slider.setValue(int(entry.get("euphoria", 5)))

            med = entry.get("medication") or {}
            self.med_type.setText(str(med.get("type", "")))
            route = str(med.get("route", ""))
            idx = self.med_route.findText(route)
            self.med_route.setCurrentIndex(idx if idx >= 0 else 0)
            self.med_dose.setText(str(med.get("dose", "")))

            mt = str(med.get("time_taken", "")).strip()
            if mt:
                parsed = QTime.fromString(mt, "HH:mm")
                if parsed.isValid():
                    self.med_taken_time.setTime(parsed)

            self.med_missed_checkbox.setChecked(bool(med.get("missed", False)))
            self.med_side_effects.setPlainText(str(med.get("side_effects", "")))

            mood = entry.get("mood_details") or {}
            self.mood_slider.slider.setValue(int(mood.get("mood", 5)))
            self.anxiety_slider.slider.setValue(int(mood.get("anxiety", 5)))
            self.irritability_slider.slider.setValue(int(mood.get("irritability", 5)))
            self.stress_slider.slider.setValue(int(mood.get("stress", 5)))
            self.mood_notes.setPlainText(str(mood.get("notes", "")))

            phys = entry.get("physical") or {}
            self.energy_physical_slider.slider.setValue(int(phys.get("energy_physical", 5)))
            self.sleep_quality_slider.slider.setValue(int(phys.get("sleep_quality", 5)))
            self.libido_slider.slider.setValue(int(phys.get("libido", 5)))
            self.skin_changes.setPlainText(str(phys.get("skin", "")))
            self.body_hair_changes.setPlainText(str(phys.get("body_hair", "")))
            self.body_shape_changes.setPlainText(str(phys.get("body_shape", "")))
            self.breast_chest_sensations.setPlainText(str(phys.get("breast_chest", "")))
            self.general_physical_notes.setPlainText(str(phys.get("other", "")))

            ms = entry.get("mental_social") or {}
            self.social_energy_slider.slider.setValue(int(ms.get("social_energy", 5)))
            self.body_image_slider.slider.setValue(int(ms.get("body_image", 5)))
            self.dysphoria_context.setPlainText(str(ms.get("dysphoria_context", "")))
            self.euphoria_context.setPlainText(str(ms.get("euphoria_context", "")))
            self.social_notes.setPlainText(str(ms.get("social_notes", "")))

            self.general_notes.setPlainText(str(entry.get("notes", "")))
        except Exception as ex:
            QMessageBox.warning(self, "Load failed", f"Could not load entry for this date:\n{ex}")

    def _save_entry(self):
        entry = {
            "date": self.date_edit.date().toPython().isoformat(),
            "time": self.time_edit.time().toString("HH:mm"),

            "energy": self.energy_slider.slider.value(),
            "overall_mood": self.overall_mood_slider.slider.value(),
            "dysphoria": self.dysphoria_slider.slider.value(),
            "euphoria": self.euphoria_slider.slider.value(),

            "medication": {
                "type": self.med_type.text(),
                "route": self.med_route.currentText(),
                "dose": self.med_dose.text(),
                "time_taken": self.med_taken_time.time().toString("HH:mm"),
                "missed": self.med_missed_checkbox.isChecked(),
                "side_effects": self.med_side_effects.toPlainText(),
            },

            "mood_details": {
                "mood": self.mood_slider.slider.value(),
                "anxiety": self.anxiety_slider.slider.value(),
                "irritability": self.irritability_slider.slider.value(),
                "stress": self.stress_slider.slider.value(),
                "notes": self.mood_notes.toPlainText(),
            },

            "physical": {
                "energy_physical": self.energy_physical_slider.slider.value(),
                "sleep_quality": self.sleep_quality_slider.slider.value(),
                "libido": self.libido_slider.slider.value(),
                "skin": self.skin_changes.toPlainText(),
                "body_hair": self.body_hair_changes.toPlainText(),
                "body_shape": self.body_shape_changes.toPlainText(),
                "breast_chest": self.breast_chest_sensations.toPlainText(),
                "other": self.general_physical_notes.toPlainText(),
            },

            "mental_social": {
                "social_energy": self.social_energy_slider.slider.value(),
                "body_image": self.body_image_slider.slider.value(),
                "dysphoria_context": self.dysphoria_context.toPlainText(),
                "euphoria_context": self.euphoria_context.toPlainText(),
                "social_notes": self.social_notes.toPlainText(),
            },

            "notes": self.general_notes.toPlainText(),
        }

        try:
            updated = upsert_entry(entry)
        except Exception as ex:
            QMessageBox.critical(self, "Save failed", f"Could not save entry:\n{ex}")
            return

        QMessageBox.information(
            self,
            "Saved",
            "Entry updated for this date." if updated else "Entry saved for this date.",
        )
        self._refresh_entries()

    def _delete_entry_for_date(self):
        d = self.date_edit.date().toPython()
        res = QMessageBox.question(
            self,
            "Delete entry",
            f"Delete entry for {d.isoformat()}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        try:
            deleted = delete_entry_by_date(d)
        except Exception as ex:
            QMessageBox.critical(self, "Delete failed", f"Could not delete entry:\n{ex}")
            return

        if deleted:
            QMessageBox.information(self, "Deleted", "Entry deleted.")
            self._clear_all()
            self._refresh_entries()
        else:
            QMessageBox.information(self, "Not found", "No entry exists for this date.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HrtTrackerWindow()
    window.show()
    sys.exit(app.exec())