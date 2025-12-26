import sys
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QListWidget,
    QStackedWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QFrame,
    QLineEdit,
    QComboBox,
    QTextBrowser,
    QSplitter,
    QGroupBox,
    QFormLayout,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
)
import json
import traceback
import re
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QPlainTextEdit

from modules.medication_tracker import MedicationTracker
from modules.journal import Journal

# --- new: small helpers to prevent fatal UI crashes ---
def _show_unhandled_exception(parent: QWidget | None, exc_type, exc, tb):
    details = "".join(traceback.format_exception(exc_type, exc, tb))
    # Avoid recursive failures if UI isn't ready.
    try:
        QMessageBox.critical(parent, "Unexpected error", "An unexpected error occurred.\n\nDetails:\n" + details[-4000:])
    except Exception:
        print(details, file=sys.stderr)

def _normalize_url(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    # If user pastes a windows path, make it file:///
    if re.match(r"^[A-Za-z]:[\\/]", s):
        return QUrl.fromLocalFile(s).toString()
    # If missing scheme but looks like a domain, assume https.
    if "://" not in s and re.match(r"^[\w\.-]+\.[A-Za-z]{2,}(/.*)?$", s):
        return "https://" + s
    return s


class ResourcesPage(QWidget):
    def __init__(self):
        super().__init__()

        self._settings = QSettings("HRTJourneyTracker", "HRTJourneyTracker")
        self._resources = self._load_resources()
        self._current_id = None

        # Header
        title = QLabel("Resources")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        subtitle = QLabel("Save links and notes locally. Search, pin, and quickly open resources.")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.75);")

        # Controls
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by title, tags, or URL…")

        self.category = QComboBox()
        self.category.addItems(["All categories"])
        self.category.setMinimumWidth(180)

        self.btn_add = QPushButton("Add")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self.search, 1)
        controls.addWidget(self.category, 0)
        controls.addWidget(self.btn_add, 0)
        controls.addWidget(self.btn_edit, 0)
        controls.addWidget(self.btn_delete, 0)

        # Left: list
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)

        left_box = QGroupBox("Saved")
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.addWidget(self.list)

        # Right: preview/actions
        self.preview_title = QLabel("Select a resource")
        self.preview_title.setStyleSheet("font-size: 16px; font-weight: 600;")

        self.preview_meta = QLabel("")
        self.preview_meta.setWordWrap(True)
        self.preview_meta.setStyleSheet("color: rgba(255,255,255,0.75);")

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)

        self.btn_open = QPushButton("Open")
        self.btn_copy = QPushButton("Copy link")
        self.btn_pin = QPushButton("Pin / Unpin")

        preview_actions = QHBoxLayout()
        preview_actions.setSpacing(8)
        preview_actions.addWidget(self.btn_open)
        preview_actions.addWidget(self.btn_copy)
        preview_actions.addWidget(self.btn_pin)
        preview_actions.addStretch(1)

        right_box = QGroupBox("Details")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.addWidget(self.preview_title)
        right_layout.addWidget(self.preview_meta)
        right_layout.addWidget(self.preview, 1)
        right_layout.addLayout(preview_actions)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(controls)
        layout.addWidget(splitter, 1)

        # Wire
        self.search.textChanged.connect(self._rebuild_list)
        self.category.currentIndexChanged.connect(self._rebuild_list)
        self.list.currentRowChanged.connect(self._on_select)

        self.btn_add.clicked.connect(self._guard(self._add_resource))
        self.btn_edit.clicked.connect(self._guard(self._edit_resource))
        self.btn_delete.clicked.connect(self._guard(self._delete_resource))

        self.btn_open.clicked.connect(self._guard(self._open_resource))
        self.btn_copy.clicked.connect(self._guard(self._copy_link))
        self.btn_pin.clicked.connect(self._guard(self._toggle_pin))

        # UX: double-click to open; Enter to open; Del to delete; Ctrl+F focuses search
        self.list.itemDoubleClicked.connect(lambda _item: self._open_resource())
        QShortcut(QKeySequence("Return"), self.list, activated=self._guard(self._open_resource))
        QShortcut(QKeySequence("Enter"), self.list, activated=self._guard(self._open_resource))
        QShortcut(QKeySequence.Delete, self.list, activated=self._guard(self._delete_resource))
        QShortcut(QKeySequence.Find, self, activated=lambda: self.search.setFocus(Qt.ShortcutFocusReason))

        self._refresh_categories()
        self._rebuild_list()

    def _guard(self, fn):
        def wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                _show_unhandled_exception(self, *sys.exc_info())
                return None
        return wrapped

    # -------------------------
    # Persistence
    # -------------------------
    def _load_resources(self):
        raw = self._settings.value("resources_v1", "[]")
        try:
            items = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(items, list):
                return []
            norm = []
            for r in items:
                if not isinstance(r, dict):
                    continue
                rid = str(r.get("id") or "").strip()
                title = str(r.get("title") or "").strip()
                url = _normalize_url(str(r.get("url") or ""))
                if not rid or not title:
                    continue
                norm.append(
                    {
                        "id": rid,
                        "title": title,
                        "url": url,
                        "category": str(r.get("category") or "General").strip() or "General",
                        "tags": str(r.get("tags") or "").strip(),
                        "notes": str(r.get("notes") or "").strip(),
                        "pinned": bool(r.get("pinned", False)),
                    }
                )
            return norm
        except Exception:
            # If corrupted settings, don't crash; start fresh.
            return []

    def _save_resources(self):
        # Store compact JSON to reduce chance of partial writes.
        self._settings.setValue("resources_v1", json.dumps(self._resources, ensure_ascii=False, separators=(",", ":")))

    # -------------------------
    # UI helpers
    # -------------------------
    def _refresh_categories(self):
        current = self.category.currentText()
        cats = sorted({r.get("category", "General") for r in self._resources if r.get("category")})
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("All categories")
        for c in cats:
            self.category.addItem(c)
        idx = self.category.findText(current)
        self.category.setCurrentIndex(idx if idx >= 0 else 0)
        self.category.blockSignals(False)

    def _matches_filter(self, r: dict) -> bool:
        q = self.search.text().strip().lower()
        cat = self.category.currentText()

        if cat != "All categories" and r.get("category") != cat:
            return False

        if not q:
            return True

        hay = " ".join(
            [
                str(r.get("title", "")),
                str(r.get("url", "")),
                str(r.get("tags", "")),
                str(r.get("notes", "")),
                str(r.get("category", "")),
            ]
        ).lower()
        return q in hay

    def _sorted_resources(self, items):
        # pinned first, then title
        return sorted(items, key=lambda r: (not bool(r.get("pinned")), str(r.get("title", "")).lower()))

    def _rebuild_list(self):
        selected_id = self._current_id

        self.list.blockSignals(True)
        self.list.clear()

        filtered = [r for r in self._resources if self._matches_filter(r)]
        filtered = self._sorted_resources(filtered)

        for r in filtered:
            prefix = "📌 " if r.get("pinned") else ""
            self.list.addItem(f"{prefix}{r.get('title','')}")
            self.list.item(self.list.count() - 1).setData(Qt.UserRole, r.get("id"))

        self.list.blockSignals(False)

        # preserve selection if still present
        if selected_id:
            for i in range(self.list.count()):
                if self.list.item(i).data(Qt.UserRole) == selected_id:
                    self.list.setCurrentRow(i)
                    return

        # otherwise clear preview
        self._set_preview(None)

    def _get_selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _find_by_id(self, rid: str):
        for r in self._resources:
            if r.get("id") == rid:
                return r
        return None

    def _set_preview(self, r: dict | None):
        self._current_id = r.get("id") if r else None
        if not r:
            self.preview_title.setText("Select a resource")
            self.preview_meta.setText("")
            self.preview.setPlainText("")
            self._set_detail_buttons_enabled(False)
            return

        self.preview_title.setText(r.get("title", ""))
        meta = []
        if r.get("category"):
            meta.append(f"Category: {r.get('category')}")
        if r.get("tags"):
            meta.append(f"Tags: {r.get('tags')}")
        if r.get("url"):
            meta.append(f"Link: {r.get('url')}")
        if r.get("pinned"):
            meta.append("Pinned")
        self.preview_meta.setText(" • ".join(meta))

        notes = r.get("notes", "")
        if notes:
            self.preview.setPlainText(notes)
        else:
            self.preview.setPlainText("No notes. Use Edit to add a description or steps.")

        self._set_detail_buttons_enabled(True)

    def _set_detail_buttons_enabled(self, enabled: bool):
        self.btn_open.setEnabled(enabled)
        self.btn_copy.setEnabled(enabled)
        self.btn_pin.setEnabled(enabled)
        self.btn_edit.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)

    # -------------------------
    # Events / actions
    # -------------------------
    def _on_select(self, _row: int):
        rid = self._get_selected_id()
        r = self._find_by_id(rid) if rid else None
        self._set_preview(r)

    def _resource_dialog(self, title: str, initial: dict | None = None):
        d = QDialog(self)
        d.setWindowTitle(title)
        d.setMinimumWidth(520)

        form = QFormLayout(d)
        title_edit = QLineEdit((initial or {}).get("title", ""))
        url_edit = QLineEdit((initial or {}).get("url", ""))
        category_edit = QLineEdit((initial or {}).get("category", "General"))
        tags_edit = QLineEdit((initial or {}).get("tags", ""))

        notes_edit = QPlainTextEdit((initial or {}).get("notes", ""))
        notes_edit.setPlaceholderText("Notes (optional). You can paste steps or reminders here.")
        notes_edit.setMinimumHeight(120)

        title_edit.setPlaceholderText("e.g., Lab results reference ranges")
        url_edit.setPlaceholderText("https://… or file:///… or C:\\path\\file (optional)")
        category_edit.setPlaceholderText("e.g., Medical, Legal, Community")
        tags_edit.setPlaceholderText("comma-separated (optional)")

        form.addRow("Title", title_edit)
        form.addRow("URL", url_edit)
        form.addRow("Category", category_edit)
        form.addRow("Tags", tags_edit)
        form.addRow("Notes", notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)

        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)

        if d.exec() != QDialog.Accepted:
            return None

        data = {
            "title": title_edit.text().strip(),
            "url": _normalize_url(url_edit.text()),
            "category": category_edit.text().strip() or "General",
            "tags": tags_edit.text().strip(),
            "notes": notes_edit.toPlainText().strip(),
        }
        if not data["title"]:
            QMessageBox.warning(self, "Missing title", "Title is required.")
            return None
        return data

    def _add_resource(self):
        data = self._resource_dialog("Add Resource")
        if not data:
            return
        next_id = int(self._settings.value("resources_next_id", 1, type=int))
        rid = str(next_id)
        self._settings.setValue("resources_next_id", next_id + 1)

        r = {"id": rid, "pinned": False, **data}
        self._resources.append(r)
        self._save_resources()
        self._refresh_categories()
        self._rebuild_list()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == rid:
                self.list.setCurrentRow(i)
                break

    def _edit_resource(self):
        rid = self._get_selected_id()
        r = self._find_by_id(rid) if rid else None
        if not r:
            return

        data = self._resource_dialog("Edit Resource", initial=r)
        if not data:
            return

        r.update(data)
        self._save_resources()
        self._refresh_categories()
        self._rebuild_list()
        self._set_preview(r)

    def _delete_resource(self):
        rid = self._get_selected_id()
        r = self._find_by_id(rid) if rid else None
        if not r:
            return
        if QMessageBox.question(self, "Delete resource", f"Delete “{r.get('title','')}”?") != QMessageBox.Yes:
            return
        self._resources = [x for x in self._resources if x.get("id") != rid]
        self._save_resources()
        self._refresh_categories()
        self._rebuild_list()
        # ensure preview cleared after deletion
        self._set_preview(None)

    def _open_resource(self):
        rid = self._get_selected_id()
        r = self._find_by_id(rid) if rid else None
        if not r:
            return

        url = _normalize_url(r.get("url") or "")
        if not url:
            QMessageBox.information(self, "No URL", "This resource has no URL to open.")
            return

        qurl = QUrl(url)
        if not qurl.isValid():
            QMessageBox.warning(self, "Invalid URL", "This resource URL is not valid.")
            return

        ok = QDesktopServices.openUrl(qurl)
        if not ok:
            QMessageBox.warning(self, "Open failed", "Could not open the URL. Check that it is valid.")

    def _copy_link(self):
        rid = self._get_selected_id()
        r = self._find_by_id(rid) if rid else None
        if not r:
            return
        url = (r.get("url") or "").strip()
        if not url:
            QMessageBox.information(self, "No URL", "This resource has no URL to copy.")
            return
        QApplication.clipboard().setText(url)

    def _toggle_pin(self):
        rid = self._get_selected_id()
        r = self._find_by_id(rid) if rid else None
        if not r:
            return
        r["pinned"] = not bool(r.get("pinned"))
        self._save_resources()
        self._rebuild_list()
        self._set_preview(r)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.safe_mode_toggle = QCheckBox("Safe Mode (hide sensitive data)")
        self.safe_now_button = QPushButton("Hide Now (toggle Safe Mode)")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings"))

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addWidget(self.safe_mode_toggle)
        layout.addWidget(self.safe_now_button)

        hint = QLabel("Tip: Safe Mode affects pages that support it (HRT Log, Journal).")
        hint.setStyleSheet("color: rgba(255,255,255,0.65);")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HRT Journey Tracker")
        self.resize(1000, 650)

        self._settings = QSettings("HRTJourneyTracker", "HRTJourneyTracker")
        self._safe_mode = bool(self._settings.value("safe_mode", False, type=bool))

        # Pages
        self.hrt_log_page = MedicationTracker()
        self.journal_page = Journal()
        self.resources_page = ResourcesPage()
        self.settings_page = SettingsPage()

        # Wire settings UI
        self.settings_page.safe_mode_toggle.setChecked(self._safe_mode)

        self.settings_page.safe_mode_toggle.toggled.connect(self.set_safe_mode)
        self.settings_page.safe_now_button.clicked.connect(lambda: self.set_safe_mode(not self._safe_mode))

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.addItems(["HRT Log", "Journal", "Resources", "Settings"])
        self.sidebar.setFixedWidth(180)
        self.sidebar.setCurrentRow(0)

        # Stack
        self.stack = QStackedWidget()
        self.stack.addWidget(self.hrt_log_page)
        self.stack.addWidget(self.journal_page)
        self.stack.addWidget(self.resources_page)
        self.stack.addWidget(self.settings_page)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        # Layout
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.set_safe_mode(self._safe_mode)

    def closeEvent(self, event):
        # Best-effort: ensure resources are flushed if page exists
        try:
            if hasattr(self, "resources_page") and hasattr(self.resources_page, "_save_resources"):
                self.resources_page._save_resources()
        except Exception:
            pass
        super().closeEvent(event)

    def set_safe_mode(self, enabled: bool):
        self._safe_mode = bool(enabled)
        self._settings.setValue("safe_mode", self._safe_mode)

        if hasattr(self.hrt_log_page, "set_safe_mode"):
            self.hrt_log_page.set_safe_mode(self._safe_mode)
        if hasattr(self.journal_page, "set_safe_mode"):
            self.journal_page.set_safe_mode(self._safe_mode)

        self.settings_page.safe_mode_toggle.blockSignals(True)
        self.settings_page.safe_mode_toggle.setChecked(self._safe_mode)
        self.settings_page.safe_mode_toggle.blockSignals(False)


def load_theme(app: QApplication, theme_name: str = "dark"):
    base_dir = Path(__file__).resolve().parent
    qss_path = base_dir / "assets" / "theme.qss"
    try:
        qss = qss_path.read_text(encoding="utf-8")
        app.setProperty("theme", (theme_name or "dark").strip() or "dark")
        app.setStyleSheet(qss)
    except FileNotFoundError:
        print("Theme file not found — running without stylesheet.")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setOrganizationName("HRTJourneyTracker")
    app.setApplicationName("HRTJourneyTracker")

    # new: route Qt/Python exceptions to a dialog instead of hard-crashing
    sys.excepthook = lambda et, e, tb: _show_unhandled_exception(None, et, e, tb)

    # new: actually apply theme if present
    load_theme(app, "dark")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())