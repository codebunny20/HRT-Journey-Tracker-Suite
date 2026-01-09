import sys
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QMenu,
    QWidget,
    QListWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl, Qt

# --- ADDED: persistence for LinkStorage ---
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class LinkManagerUI(QWidget):
    """Minimal UI used by LinkManagerApp when a separate generated UI is not present."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Link Manager")

        # Input fields
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Title")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URL")

        # Buttons
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.open_btn = QPushButton("Open")
        self.copy_btn = QPushButton("Copy URL")
        self.clear_inputs_btn = QPushButton("Clear Inputs")
        self.clear_all_btn = QPushButton("Clear All")

        # List and status
        self.list_widget = QListWidget()
        self.status_label = QLabel("Ready")

        # Layout
        top_row = QHBoxLayout()
        top_row.addWidget(self.title_input)
        top_row.addWidget(self.url_input)
        top_row.addWidget(self.add_btn)

        mid_row = QHBoxLayout()
        mid_row.addWidget(self.search_input)
        mid_row.addWidget(self.clear_inputs_btn)
        mid_row.addWidget(self.clear_all_btn)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.remove_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_row)
        main_layout.addLayout(mid_row)
        main_layout.addLayout(btn_row)
        main_layout.addWidget(self.list_widget)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)


class LinkStorage:
    """JSON-backed list storage: [{"title": str, "url": str}, ...]."""

    def __init__(self, path: Optional[str] = None):
        # Store inside a dedicated folder next to this script:
        # Resource manager/storage/links.json
        default_path = Path(__file__).resolve().parent / "storage" / "links.json"
        self.path = Path(path) if path else default_path

        # Ensure storage folder exists on launch
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.data: List[Dict[str, str]] = []
        self.load()

    def load(self) -> None:
        # Ensure folder exists even if called later
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.data = []
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
            if not isinstance(raw, list):
                self.data = []
                return

            out: List[Dict[str, str]] = []
            for it in raw:
                if not isinstance(it, dict):
                    continue
                title = str(it.get("title", "")).strip()
                url = str(it.get("url", "")).strip()
                if title and url:
                    out.append({"title": title, "url": url})
            self.data = out
        except Exception:
            self.data = []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_link(self, title: str, url: str) -> None:
        title = (title or "").strip()
        url = (url or "").strip()
        if not title or not url:
            return

        # De-dupe by URL: update title if URL already exists
        for it in self.data:
            if (it.get("url") or "").strip() == url:
                it["title"] = title
                self.save()
                return

        self.data.append({"title": title, "url": url})
        self.save()

    def remove_link(self, index: int) -> None:
        if 0 <= index < len(self.data):
            self.data.pop(index)
            self.save()

    def update_link(self, index: int, title: str, url: str) -> bool:
        """Update an existing link by index. Returns True if updated."""
        if not (0 <= index < len(self.data)):
            return False

        title = (title or "").strip()
        url = (url or "").strip()
        if not title or not url:
            return False

        # If URL already exists elsewhere, update that record instead and remove this one.
        for i, it in enumerate(self.data):
            if i == index:
                continue
            if (it.get("url") or "").strip() == url:
                it["title"] = title
                # remove original index if it's a different item
                self.data.pop(index)
                self.save()
                return True

        self.data[index] = {"title": title, "url": url}
        self.save()
        return True


class LinkManagerApp(LinkManagerUI):
    def __init__(self):
        super().__init__()
        self.storage = LinkStorage()

        # Ensure right-click emits customContextMenuRequested
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)

        # Load existing links
        self.refresh_list()

        # Connect signals
        self.add_btn.clicked.connect(self.add_link)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.open_btn.clicked.connect(self.open_selected)
        self.copy_btn.clicked.connect(self.copy_selected_url)
        self.clear_inputs_btn.clicked.connect(self.clear_inputs)
        self.clear_all_btn.clicked.connect(self.clear_all)
        self.search_input.textChanged.connect(self.refresh_list)

        self.title_input.returnPressed.connect(self.add_link)
        self.url_input.returnPressed.connect(self.add_link)

        self.list_widget.itemDoubleClicked.connect(lambda *_: self.open_selected())
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)

    def _set_status(self, text: str, timeout_ms: int = 0):
        self.status_label.setText(text)
        if timeout_ms and timeout_ms > 0:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(timeout_ms, lambda: self.status_label.setText("Ready"))

    def _normalize_url(self, url: str) -> str:
        u = (url or "").strip()
        if not u:
            return ""
        if "://" not in u:
            u = "https://" + u
        return u

    def _current_item_data(self):
        item = self.list_widget.currentItem()
        if not item:
            return None
        payload = item.data(Qt.UserRole)
        return payload if isinstance(payload, dict) else None

    def _get_link_by_payload_index(self, payload: dict) -> Tuple[Optional[Dict[str, str]], Optional[int]]:
        try:
            idx = int(payload.get("index"))
        except Exception:
            return None, None
        if idx < 0 or idx >= len(self.storage.data):
            return None, idx
        return self.storage.data[idx], idx

    def refresh_list(self):
        q = (self.search_input.text() or "").strip().lower()

        self.list_widget.clear()
        shown = 0

        # FIX: preserve real storage index when filtering
        for real_idx in range(len(self.storage.data)):
            item = self.storage.data[real_idx]
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()

            hay = f"{title}\n{url}".lower()
            if q and q not in hay:
                continue

            li = self._make_list_item(real_idx, title, url)
            self.list_widget.addItem(li)
            shown += 1

        self._set_status(f"Showing {shown} link(s). Total: {len(self.storage.data)}")

    def _make_list_item(self, idx: int, title: str, url: str):
        # Compact-but-readable: title on top, URL below.
        text = f"{title}\n{url}"
        li = self._make_qitem(text)
        li.setData(Qt.UserRole, {"index": idx, "title": title, "url": url})
        li.setToolTip(url)
        return li

    def _make_qitem(self, text: str):
        from PySide6.QtWidgets import QListWidgetItem
        return QListWidgetItem(text)

    def clear_inputs(self):
        self.title_input.clear()
        self.url_input.clear()
        self.title_input.setFocus()
        self._set_status("Cleared inputs.", 1500)

    def add_link(self):
        title = (self.title_input.text() or "").strip()
        url = self._normalize_url(self.url_input.text())

        if not title:
            QMessageBox.warning(self, "Missing title", "Please enter a title.")
            self.title_input.setFocus()
            return
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a URL.")
            self.url_input.setFocus()
            return

        # Basic URL sanity check
        qurl = QUrl(url)
        if not qurl.isValid() or qurl.scheme() not in ("http", "https"):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid http(s) URL.\n\nExample: https://example.com")
            self.url_input.setFocus()
            return

        self.storage.add_link(title, url)
        self.refresh_list()

        self.title_input.clear()
        self.url_input.clear()
        self.title_input.setFocus()
        self._set_status("Added.", 1500)

    def remove_selected(self):
        payload = self._current_item_data()
        if not payload:
            QMessageBox.warning(self, "No selection", "Select a link first.")
            return

        link, idx = self._get_link_by_payload_index(payload)
        if link is None or idx is None:
            QMessageBox.warning(self, "Invalid selection", "That item no longer exists.")
            self.refresh_list()
            return

        title = str(link.get("title") or "this link").strip() or "this link"
        if QMessageBox.question(self, "Remove link?", f"Remove “{title}”?") != QMessageBox.Yes:
            return

        self.storage.remove_link(idx)
        self.refresh_list()
        self._set_status("Removed.", 1500)

    def open_selected(self):
        payload = self._current_item_data()
        if not payload:
            QMessageBox.warning(self, "No selection", "Select a link first.")
            return

        link, _idx = self._get_link_by_payload_index(payload)
        if link is None:
            QMessageBox.warning(self, "Invalid selection", "That item no longer exists.")
            self.refresh_list()
            return

        url = str(link.get("url") or "").strip()
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))
        self._set_status("Opened in browser.", 1500)

    def copy_selected_url(self):
        payload = self._current_item_data()
        if not payload:
            QMessageBox.warning(self, "No selection", "Select a link first.")
            return

        link, _idx = self._get_link_by_payload_index(payload)
        if link is None:
            QMessageBox.warning(self, "Invalid selection", "That item no longer exists.")
            self.refresh_list()
            return

        url = str(link.get("url") or "").strip()
        if not url:
            return
        QApplication.clipboard().setText(url)
        self._set_status("Copied URL.", 1500)

    def clear_all(self):
        if not self.storage.data:
            self._set_status("Nothing to clear.", 1500)
            return

        if QMessageBox.question(
            self,
            "Clear all?",
            f"Delete all saved links? ({len(self.storage.data)})\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        self.storage.data = []
        self.storage.save()
        self.refresh_list()
        self._set_status("Cleared all links.", 2000)

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        # Ensure actions operate on the item that was right-clicked
        self.list_widget.setCurrentItem(item)

        menu = QMenu(self)
        act_open = menu.addAction("Open")
        act_copy = menu.addAction("Copy URL")
        act_edit = menu.addAction("Edit (load into fields)")
        act_save = menu.addAction("Save Edit (update selected)")
        menu.addSeparator()
        act_remove = menu.addAction("Remove")

        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if chosen == act_open:
            self.open_selected()
        elif chosen == act_copy:
            self.copy_selected_url()
        elif chosen == act_edit:
            self.edit_selected()
        elif chosen == act_save:
            self.save_edit()
        elif chosen == act_remove:
            self.remove_selected()

    def edit_selected(self):
        payload = self._current_item_data()
        if not payload:
            QMessageBox.warning(self, "No selection", "Select a link first.")
            return

        link, idx = self._get_link_by_payload_index(payload)
        if link is None or idx is None:
            QMessageBox.warning(self, "Invalid selection", "That item no longer exists.")
            self.refresh_list()
            return

        # Prefill inputs with the selected link and focus URL for quick fixing
        self.title_input.setText(str(link.get("title") or ""))
        self.url_input.setText(str(link.get("url") or ""))
        self.url_input.setFocus()
        self._set_status("Editing selected link. Modify fields then choose “Save Edit”.", 4000)

    def save_edit(self):
        payload = self._current_item_data()
        if not payload:
            QMessageBox.warning(self, "No selection", "Select a link to save edits.")
            return

        link, idx = self._get_link_by_payload_index(payload)
        if link is None or idx is None:
            QMessageBox.warning(self, "Invalid selection", "That item no longer exists.")
            self.refresh_list()
            return

        title = (self.title_input.text() or "").strip()
        url = self._normalize_url(self.url_input.text())

        if not title:
            QMessageBox.warning(self, "Missing title", "Please enter a title.")
            self.title_input.setFocus()
            return
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a URL.")
            self.url_input.setFocus()
            return

        qurl = QUrl(url)
        if not qurl.isValid() or qurl.scheme() not in ("http", "https"):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Please enter a valid http(s) URL.\n\nExample: https://example.com",
            )
            self.url_input.setFocus()
            return

        if not self.storage.update_link(idx, title, url):
            QMessageBox.warning(self, "Update failed", "Could not update that link.")
            return

        self.refresh_list()
        self._set_status("Saved edits.", 1500)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LinkManagerApp()
    window.show()
    sys.exit(app.exec())