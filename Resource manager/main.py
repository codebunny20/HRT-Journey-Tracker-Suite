import sys
from PySide6.QtWidgets import QApplication, QMessageBox, QMenu
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl, Qt

from data.ui_main import LinkManagerUI
from data.storage import LinkStorage

class LinkManagerApp(LinkManagerUI):
    def __init__(self):
        super().__init__()
        self.storage = LinkStorage()

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

    def refresh_list(self):
        q = (self.search_input.text() or "").strip().lower()

        self.list_widget.clear()
        shown = 0

        for idx, item in enumerate(self.storage.data):
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()

            hay = f"{title}\n{url}".lower()
            if q and q not in hay:
                continue

            li = self._make_list_item(idx, title, url)
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

        idx = int(payload["index"])
        title = payload.get("title") or "this link"

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
        url = str(payload.get("url") or "").strip()
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))
        self._set_status("Opened in browser.", 1500)

    def copy_selected_url(self):
        payload = self._current_item_data()
        if not payload:
            QMessageBox.warning(self, "No selection", "Select a link first.")
            return
        url = str(payload.get("url") or "").strip()
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

        menu = QMenu(self)
        act_open = menu.addAction("Open")
        act_copy = menu.addAction("Copy URL")
        menu.addSeparator()
        act_remove = menu.addAction("Remove")

        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if chosen == act_open:
            self.open_selected()
        elif chosen == act_copy:
            self.copy_selected_url()
        elif chosen == act_remove:
            self.remove_selected()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LinkManagerApp()
    window.show()
    sys.exit(app.exec())