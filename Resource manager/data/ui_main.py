from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QGroupBox, QFormLayout, QAbstractItemView, QMenu
)

class LinkManagerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Link & Resource Manager")
        self.resize(680, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel("Resource Manager")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)

        subtitle = QLabel("Save links locally. Double-click to open.")
        subtitle.setStyleSheet("color: #666;")

        # --- Add link (card) ---
        add_group = QGroupBox("Add link")
        add_form = QFormLayout(add_group)
        add_form.setLabelAlignment(Qt.AlignRight)
        add_form.setFormAlignment(Qt.AlignTop)
        add_form.setHorizontalSpacing(10)
        add_form.setVerticalSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., PySide6 docs")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("e.g., https://doc.qt.io/qtforpython/")

        add_form.addRow("Title:", self.title_input)
        add_form.addRow("URL:", self.url_input)

        add_btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.setDefault(True)
        self.clear_inputs_btn = QPushButton("Clear")
        add_btn_row.addStretch(1)
        add_btn_row.addWidget(self.clear_inputs_btn)
        add_btn_row.addWidget(self.add_btn)
        add_form.addRow("", add_btn_row)

        # --- Saved links (card) ---
        list_group = QGroupBox("Saved links")
        list_layout = QVBoxLayout(list_group)
        list_layout.setSpacing(8)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title or URL…")
        self.clear_all_btn = QPushButton("Clear all")
        self.clear_all_btn.setToolTip("Remove all saved links")
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.clear_all_btn, 0)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)

        btn_row = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.copy_btn = QPushButton("Copy URL")
        self.remove_btn = QPushButton("Remove")
        btn_row.addStretch(1)
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.remove_btn)

        list_layout.addLayout(search_row)
        list_layout.addWidget(self.list_widget, 1)
        list_layout.addLayout(btn_row)

        # --- Status line ---
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")

        # --- Assemble ---
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(add_group)
        root.addWidget(list_group, 1)
        root.addWidget(self.status_label)

        # --- Small, readable default styles (keeps it simple) ---
        self.setStyleSheet("""
            QGroupBox { font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QLineEdit { padding: 6px; }
            QPushButton { padding: 6px 10px; }
        """)