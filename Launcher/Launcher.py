import sys
import subprocess
from pathlib import Path
from datetime import datetime
import traceback

from PySide6.QtCore import Qt, QSettings, QTimer, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QFont, QDesktopServices, QKeySequence, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QScrollArea,
    QGraphicsOpacityEffect,
)


WORKSPACE_TITLE = "HRT Journey Tracker — Launcher"
ORG_NAME = "HRTJourneyTracker"
APP_NAME = "Launcher"

APP_SCAN_MAX_DEPTH = 2
APP_SCAN_EXCLUDE_DIRS = {"launcher", ".git", "__pycache__", "build", "dist", "storage", "assets", ".venv", "venv"}
APP_SCAN_EXCLUDE_FILES = {
    "__init__.py",
    "setup.py",
    "conftest.py",
}

APP_ENTRY_PRIORITY = ("main.py", "app.py", "run.py",)  # fallback names when <FolderName>.py not present

SETTINGS_RECENTS_GROUP = "recents"  # QSettings group
SETTINGS_MAX_RECENTS = 8


DARK_QSS = """
/* --- Base --- */
QWidget {
    background: #111315;
    color: #E6E6E6;
    font-size: 13px;
}
QMainWindow::separator { background: #2A2E33; width: 1px; height: 1px; }
QMenuBar {
    background: #111315;
    border-bottom: 1px solid #24282D;
}
QMenuBar::item { background: transparent; padding: 6px 10px; }
QMenuBar::item:selected { background: #1B1F24; border-radius: 6px; }
QMenu {
    background: #15181B;
    border: 1px solid #2A2E33;
}
QMenu::item { padding: 6px 12px; }
QMenu::item:selected { background: #22262B; }
QToolTip {
    background: #111315;
    color: #E6E6E6;
    border: 1px solid #2A2E33;
}

/* --- Buttons / inputs --- */
QPushButton {
    background: #1B1F24;
    border: 1px solid #2A2E33;
    padding: 8px 12px;
    border-radius: 8px;
}
QPushButton:hover { background: #21262C; }
QPushButton:pressed { background: #161A1E; }
QPushButton:disabled { color: #888; background: #15181B; border-color: #20242A; }

QScrollArea { background: transparent; }
QScrollBar:vertical, QScrollBar:horizontal { background: transparent; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #2A2E33;
    border-radius: 6px;
    min-height: 28px;
    min-width: 28px;
}
QScrollBar::handle:hover { background: #343A41; }
QScrollBar::add-line, QScrollBar::sub-line { background: transparent; border: none; }

/* --- Cards / panels --- */
QFrame#Card {
    background: #15181B;
    border: 1px solid #2A2E33;
    border-radius: 10px;
}

/* --- Labels --- */
QLabel#Subtitle { color: #AAB2BA; }
QLabel#Hint { color: #8A939C; font-size: 11px; }
"""

LIGHT_QSS = """
/* --- Base --- */
QWidget {
    background: #F6F7F9;
    color: #1B1F24;
    font-size: 13px;
}
QMainWindow::separator { background: #D6DAE0; width: 1px; height: 1px; }
QMenuBar {
    background: #F6F7F9;
    border-bottom: 1px solid #E1E5EA;
}
QMenuBar::item { background: transparent; padding: 6px 10px; }
QMenuBar::item:selected { background: #E9EDF2; border-radius: 6px; }
QMenu {
    background: #FFFFFF;
    border: 1px solid #D6DAE0;
}
QMenu::item { padding: 6px 12px; }
QMenu::item:selected { background: #EEF2F7; }
QToolTip {
    background: #FFFFFF;
    color: #1B1F24;
    border: 1px solid #D6DAE0;
}

/* --- Buttons / inputs --- */
QPushButton {
    background: #FFFFFF;
    border: 1px solid #D6DAE0;
    padding: 8px 12px;
    border-radius: 8px;
}
QPushButton:hover { background: #F0F3F7; }
QPushButton:pressed { background: #E9EDF2; }
QPushButton:disabled { color: #777; background: #F3F5F8; border-color: #E1E5EA; }

QScrollArea { background: transparent; }
QScrollBar:vertical, QScrollBar:horizontal { background: transparent; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #C9CFD8;
    border-radius: 6px;
    min-height: 28px;
    min-width: 28px;
}
QScrollBar::handle:hover { background: #B8BFC9; }
QScrollBar::add-line, QScrollBar::sub-line { background: transparent; border: none; }

/* --- Cards / panels --- */
QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #D6DAE0;
    border-radius: 10px;
}

/* --- Labels --- */
QLabel#Subtitle { color: #4F5B66; }
QLabel#Hint { color: #5D6873; font-size: 11px; }
"""

SETTINGS_THEME_KEY = "ui/theme"  # "dark" | "light"


def _launcher_dir() -> Path:
    return Path(__file__).resolve().parent


def _workspace_root() -> Path:
    """
    This file lives in .../HRT Journey tracker/Launcher/Launcher.py.
    Workspace root is the parent folder of 'Launcher'.
    """
    return _launcher_dir().parent


def _script_path(rel: str) -> Path:
    # keep rel paths stable even if user launches from a different CWD
    return (_workspace_root() / rel).resolve()


def _validate_script(parent, script: Path) -> tuple[bool, str]:
    if not script.exists():
        return False, f"Could not find:\n{script}"
    if script.is_dir():
        return False, f"Path points to a folder, not a file:\n{script}"
    if script.suffix.lower() != ".py":
        return False, f"Not a Python script:\n{script}"
    return True, ""


def _start_script(parent, script: Path) -> bool:
    ok, msg = _validate_script(parent, script)
    if not ok:
        QMessageBox.critical(parent, "Not found", msg)
        return False
    try:
        # Use the current interpreter; ensure CWD is the script directory.
        subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(script.parent),
            close_fds=(sys.platform != "win32"),
        )
        return True
    except Exception as e:
        QMessageBox.critical(parent, "Launch failed", f"Could not start:\n{script}\n\n{e}")
        return False


def _is_probably_entry_script(p: Path) -> bool:
    if p.suffix.lower() != ".py":
        return False
    if p.name.lower() in APP_SCAN_EXCLUDE_FILES:
        return False
    # avoid picking things in storage/build/dist/etc
    lowered_parts = {part.lower() for part in p.parts}
    if any(d in lowered_parts for d in APP_SCAN_EXCLUDE_DIRS):
        return False
    return True


def _pick_entry_script_for_folder(folder: Path) -> Path | None:
    """
    Deterministic selection to avoid launching random helper modules:
    Priority:
      1) <FolderName>.py (ignoring spaces/_/- differences)
      2) main.py / app.py / run.py
      3) if exactly one .py exists at folder root, use it
    """
    try:
        py_files = [p for p in folder.glob("*.py") if _is_probably_entry_script(p)]
    except OSError:
        return None
    if not py_files:
        return None

    folder_key = folder.name.lower().replace(" ", "").replace("-", "").replace("_", "")
    by_key = {p.stem.lower().replace(" ", "").replace("-", "").replace("_", ""): p for p in py_files}

    # 1) <FolderName>.py
    if folder_key in by_key:
        return by_key[folder_key]

    # 2) common entrypoint names
    for name in APP_ENTRY_PRIORITY:
        p = folder / name
        if p.exists() and _is_probably_entry_script(p):
            return p

    # 3) only-one-script-at-root heuristic
    if len(py_files) == 1:
        return py_files[0]

    return None


def _discover_apps() -> list[dict]:
    """
    Finds launchable apps in workspace root subfolders.
    Heuristic: pick the first reasonable *.py “entry” within each subfolder.
    """
    root = _workspace_root()
    apps: list[dict] = []

    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name.lower() in APP_SCAN_EXCLUDE_DIRS:
            continue

        script = _pick_entry_script_for_folder(child)
        if script is None and APP_SCAN_MAX_DEPTH >= 2:
            # Depth-2 fallback: allow <Folder>/<Folder>.py inside one nested folder (common pattern)
            try:
                nested_candidates = []
                for sub in child.iterdir():
                    if not sub.is_dir():
                        continue
                    if sub.name.lower() in APP_SCAN_EXCLUDE_DIRS:
                        continue
                    picked = _pick_entry_script_for_folder(sub)
                    if picked is not None:
                        nested_candidates.append(picked)
                if len(nested_candidates) == 1:
                    script = nested_candidates[0]
            except OSError:
                script = None

        if script is None:
            continue

        apps.append(
            {
                "id": f"{child.name}:{script.relative_to(root)}",
                "name": child.name,
                "script": script.resolve(),
                "label": f"Open {child.name}",
            }
        )

    return apps


def _safe_now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _try_parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _format_when(dt: datetime) -> str:
    # Human-ish, predictable formatting
    try:
        now = datetime.now()
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now" if seconds < 10 else f"{seconds} seconds ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days == 1:
            return f"yesterday at {dt.strftime('%-I:%M %p') if sys.platform != 'win32' else dt.strftime('%I:%M %p').lstrip('0')}"
        # include date + time for older entries
        return dt.strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ")
    except Exception:
        return dt.isoformat(timespec="minutes")


def _diagnose_script(script: Path) -> tuple[bool, str]:
    """
    Fast, inline diagnostics to surface common launch issues without spawning a GUI app process.
    Returns (ok, message). If ok=False, message is user-friendly.
    """
    ok, msg = _validate_script(None, script)  # parent unused when ok path; errors shown by caller
    if not ok:
        return False, msg

    if not script.parent.exists():
        return False, f"Missing folder:\n{script.parent}"

    # Syntax check (py_compile)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            cwd=str(script.parent),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            return False, "Python could not compile this script (syntax/import-time error).\n\n" + (detail or "(no details)")
    except Exception as e:
        return False, f"Could not run py_compile.\n\n{e}"

    # Common dependency check (these apps use PySide6)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", "import PySide6"],
            cwd=str(script.parent),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            return False, (
                "Missing dependency: PySide6.\n\n"
                "Install it with:\n"
                f"{sys.executable} -m pip install PySide6\n\n"
                + (detail or "")
            )
    except Exception as e:
        return False, f"Could not test imports.\n\n{e}"

    return True, ""


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WORKSPACE_TITLE)

        self._settings = QSettings(ORG_NAME, APP_NAME)
        self._launched: set[Path] = set()
        self._theme: str = str(self._settings.value(SETTINGS_THEME_KEY, "dark") or "dark").lower()
        if self._theme not in ("dark", "light"):
            self._theme = "dark"

        root = QWidget(self)
        self.setCentralWidget(root)

        # --- Actions (unchanged behavior)
        self.act_refresh = QAction("Refresh", self)
        self.act_refresh.setShortcut(QKeySequence.Refresh)
        self.act_refresh.triggered.connect(self._rebuild_apps_ui)

        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self._about)

        self.act_open_folder = QAction("Open Workspace Folder", self)
        self.act_open_folder.setShortcut(QKeySequence("Alt+O"))
        self.act_open_folder.triggered.connect(self._open_workspace)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.Quit)
        self.act_quit.triggered.connect(self.close)

        self.act_toggle_theme = QAction("Light theme", self)
        self.act_toggle_theme.setCheckable(True)
        self.act_toggle_theme.setShortcut(QKeySequence("Ctrl+L"))
        self.act_toggle_theme.triggered.connect(self._toggle_theme)

        # --- menu
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.act_open_folder)
        file_menu.addSeparator()
        file_menu.addAction(self.act_refresh)
        file_menu.addSeparator()
        file_menu.addAction(self.act_quit)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.act_toggle_theme)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.act_about)

        # --- Header
        header = QLabel("HRT Journey Tracker")
        header_font = QFont()
        header_font.setPointSize(20)
        header_font.setBold(True)
        header.setFont(header_font)

        self.subtitle = QLabel()
        self.subtitle.setObjectName("Subtitle")
        self.subtitle.setWordWrap(True)

        header_bar = QWidget()
        header_bar_l = QVBoxLayout(header_bar)
        header_bar_l.setContentsMargins(0, 0, 0, 0)
        header_bar_l.setSpacing(4)
        header_bar_l.addWidget(header)
        header_bar_l.addWidget(self.subtitle)

        # --- Left: Apps panel (scrollable grid)
        self._apps: list[dict] = []
        self._app_buttons: list[QPushButton] = []

        apps_title = QLabel("Apps")
        apps_title.setStyleSheet("font-weight: 600;")

        self.apps_grid = QGridLayout()
        self.apps_grid.setHorizontalSpacing(10)
        self.apps_grid.setVerticalSpacing(10)
        self.apps_grid.setContentsMargins(0, 0, 0, 0)

        apps_grid_host = QWidget()
        apps_grid_host.setLayout(self.apps_grid)

        apps_scroll = QScrollArea()
        apps_scroll.setWidgetResizable(True)
        apps_scroll.setFrameShape(QFrame.NoFrame)
        apps_scroll.setWidget(apps_grid_host)

        self.empty = QLabel()
        self.empty.setStyleSheet("color: #a00;")
        self.empty.setWordWrap(True)
        self.empty.hide()

        apps_panel = QFrame()
        apps_panel.setObjectName("Card")
        apps_panel_l = QVBoxLayout(apps_panel)
        apps_panel_l.setContentsMargins(12, 12, 12, 12)
        apps_panel_l.setSpacing(10)
        apps_panel_l.addWidget(apps_title)
        apps_panel_l.addWidget(apps_scroll, 1)
        apps_panel_l.addWidget(self.empty)

        # --- Right: Activity + Diagnostics panel
        activity_title = QLabel("Recent activity")
        activity_title.setStyleSheet("font-weight: 600;")

        self.recent_lbl = QLabel()
        self.recent_lbl.setStyleSheet("color: #444;")
        self.recent_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.recent_lbl.setWordWrap(True)

        diag_title = QLabel("Status")
        diag_title.setStyleSheet("font-weight: 600;")

        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet("color: #444;")
        self.status_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status_lbl.setWordWrap(True)

        # Animated status transitions (fade)
        self._status_fx = QGraphicsOpacityEffect(self.status_lbl)
        self._status_fx.setOpacity(1.0)
        self.status_lbl.setGraphicsEffect(self._status_fx)
        self._status_anim = QPropertyAnimation(self._status_fx, b"opacity", self)
        self._status_anim.setDuration(170)
        self._status_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._pending_status_text: str | None = None
        self._status_anim.finished.connect(self._on_status_anim_finished)

        hint = QLabel("Shortcuts: F5 refresh • Alt+O open folder • Ctrl+Q quit")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)

        side_panel = QFrame()
        side_panel.setObjectName("Card")
        side_panel.setMinimumWidth(320)
        side_panel_l = QVBoxLayout(side_panel)
        side_panel_l.setContentsMargins(12, 12, 12, 12)
        side_panel_l.setSpacing(10)
        side_panel_l.addWidget(activity_title)
        side_panel_l.addWidget(self.recent_lbl)
        side_panel_l.addSpacing(6)
        side_panel_l.addWidget(diag_title)
        side_panel_l.addWidget(self.status_lbl)
        side_panel_l.addStretch(1)
        side_panel_l.addWidget(hint)

        # --- Main split row
        main_row = QHBoxLayout()
        main_row.setSpacing(12)
        main_row.addWidget(apps_panel, 3)
        main_row.addWidget(side_panel, 2)
        main_row.setStretch(0, 3)
        main_row.setStretch(1, 2)

        # --- Footer (fixed actions)
        footer = QFrame()
        footer.setFrameShape(QFrame.NoFrame)
        footer_l = QHBoxLayout(footer)
        footer_l.setContentsMargins(0, 0, 0, 0)
        footer_l.setSpacing(10)

        open_folder_btn = QPushButton("Open Workspace Folder")
        open_folder_btn.setShortcut(QKeySequence("Alt+O"))
        open_folder_btn.clicked.connect(self._open_workspace)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setShortcut(QKeySequence.Refresh)
        refresh_btn.clicked.connect(self._rebuild_apps_ui)

        quit_btn = QPushButton("Quit")
        quit_btn.setShortcut(QKeySequence.Quit)
        quit_btn.clicked.connect(self.close)

        footer_l.addWidget(open_folder_btn, 1)
        footer_l.addWidget(refresh_btn, 0)
        footer_l.addWidget(quit_btn, 0)

        # --- Compose root layout
        root_l = QVBoxLayout(root)
        root_l.setContentsMargins(16, 14, 16, 14)
        root_l.setSpacing(12)
        root_l.addWidget(header_bar)
        root_l.addLayout(main_row, 1)
        root_l.addWidget(footer)

        self._restore_window_state()
        self.setMinimumWidth(860)
        self.setMinimumHeight(440)

        self._apply_theme(self._theme, persist=False)
        self._rebuild_apps_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_apps_grid()

    def _about(self):
        QMessageBox.information(
            self,
            "About",
            "HRT Journey Tracker — Launcher\n\n"
            "Scans subfolders in the workspace and provides launch buttons for each app.\n"
            "Tip: Put an entry script like <FolderName>.py or main.py in the app folder.\n\n"
            "Shortcuts\n"
            "- Refresh: F5\n"
            "- Open Workspace Folder: Alt+O\n"
            "- Quit: Ctrl+Q\n"
            "- Launch app: Alt+<letter> (auto-assigned; see button text/tooltip)\n",
        )

    def _clear_grid(self):
        for btn in self._app_buttons:
            btn.setParent(None)
        self._app_buttons.clear()

    def _read_recent_map(self) -> dict[str, str]:
        self._settings.beginGroup(SETTINGS_RECENTS_GROUP)
        try:
            keys = self._settings.allKeys()
            out: dict[str, str] = {}
            for k in keys:
                v = self._settings.value(k)
                if isinstance(v, str) and v:
                    out[k] = v
            return out
        finally:
            self._settings.endGroup()

    def _write_recent(self, script: Path) -> None:
        self._settings.beginGroup(SETTINGS_RECENTS_GROUP)
        try:
            self._settings.setValue(str(script), _safe_now_iso())
            # best-effort cap: remove oldest extras
            m = self._read_recent_map()
            if len(m) > SETTINGS_MAX_RECENTS:
                parsed = []
                for k, v in m.items():
                    dt = _try_parse_iso(v) or datetime.min
                    parsed.append((dt, k))
                parsed.sort()  # oldest first
                for _, k in parsed[: max(0, len(m) - SETTINGS_MAX_RECENTS)]:
                    self._settings.remove(k)
        finally:
            self._settings.endGroup()

    def _render_recent_activity(self) -> None:
        if not getattr(self, "_apps", None):
            self.recent_lbl.setText("No apps discovered yet.")
            return

        m = self._read_recent_map()
        lines: list[str] = []
        for a in self._apps:
            script = a["script"]
            ts = m.get(str(script), "")
            if not ts:
                lines.append(f"{a['name']} last opened: never")
                continue
            dt = _try_parse_iso(ts)
            if not dt:
                lines.append(f"{a['name']} last opened: {ts}")
            else:
                lines.append(f"{a['name']} last opened: {_format_when(dt)}")
        self.recent_lbl.setText("\n".join(lines))

    def _rebuild_apps_ui(self):
        self._apps = _discover_apps()
        self._clear_grid()

        ws = _workspace_root()
        self.subtitle.setText(f"Workspace: {ws}")

        used: set[str] = set()

        def pick_shortcut(title: str) -> str | None:
            for ch in title:
                c = ch.upper()
                if "A" <= c <= "Z" and c not in used:
                    used.add(c)
                    return f"Alt+{c}"
            return None

        for appinfo in self._apps:
            btn = QPushButton(appinfo["label"])
            btn.setToolTip(str(appinfo["script"]))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _=False, s=appinfo["script"], b=btn: self._launch(s, b))

            sc = pick_shortcut(appinfo["name"])
            if sc:
                btn.setShortcut(QKeySequence(sc))

            self._app_buttons.append(btn)

        self._reflow_apps_grid()

        if not self._apps:
            self.empty.setText("No apps found. Add a subfolder with a launchable .py script (e.g., MyTool/MyTool.py).")
            self.empty.show()
        else:
            self.empty.hide()

        self._refresh_button_states()
        self._render_recent_activity()

    def _reflow_apps_grid(self):
        # remove current positions
        while self.apps_grid.count():
            item = self.apps_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(self.centralWidget())

        if not self._app_buttons:
            return

        # Responsive columns: use apps panel width (more accurate than centralWidget width)
        host_w = self.centralWidget().width()
        available = max(1, host_w - 48)
        cols = max(1, min(4, available // 260))

        for i, btn in enumerate(self._app_buttons):
            r, c = divmod(i, cols)
            self.apps_grid.addWidget(btn, r, c)

    def _refresh_button_states(self) -> None:
        if not getattr(self, "_apps", None):
            self._set_status("No apps found to launch.")
            return

        missing: list[str] = []
        for a in self._apps:
            ok, _ = _validate_script(self, a["script"])
            if not ok:
                missing.append(f"- {a['script']}")

        if missing:
            self._set_status(f"Found {len(self._apps)} app(s). Some are unavailable:\n" + "\n".join(missing))
        else:
            self._set_status(f"Found {len(self._apps)} app(s). Ready.")

        self._render_recent_activity()

    def _restore_window_state(self) -> None:
        geo = self._settings.value("geometry")
        state = self._settings.value("windowState")
        if geo is not None:
            self.restoreGeometry(geo)
        if state is not None:
            self.restoreState(state)

    def _save_window_state(self) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())

    def closeEvent(self, event):
        self._save_window_state()
        event.accept()

    def _apply_theme(self, theme: str, persist: bool = True) -> None:
        theme = (theme or "dark").lower()
        if theme not in ("dark", "light"):
            theme = "dark"
        self._theme = theme

        # Keep action in sync
        light = theme == "light"
        self.act_toggle_theme.blockSignals(True)
        self.act_toggle_theme.setChecked(light)
        self.act_toggle_theme.setText("Light theme")
        self.act_toggle_theme.blockSignals(False)

        QApplication.instance().setStyleSheet(LIGHT_QSS if light else DARK_QSS)
        if persist:
            self._settings.setValue(SETTINGS_THEME_KEY, theme)

    def _toggle_theme(self, checked: bool) -> None:
        self._apply_theme("light" if checked else "dark")

    def _on_status_anim_finished(self) -> None:
        # Phase 1: faded out -> swap text -> fade in
        if self._pending_status_text is not None and self._status_fx.opacity() <= 0.01:
            self.status_lbl.setText(self._pending_status_text)
            self._pending_status_text = None
            self._status_anim.stop()
            self._status_anim.setStartValue(0.0)
            self._status_anim.setEndValue(1.0)
            self._status_anim.start()

    def _set_status(self, text: str) -> None:
        # If unchanged, skip animation to avoid flicker
        if self.status_lbl.text() == text:
            return

        self._pending_status_text = text

        # Restart to fade out; finished-handler will fade back in
        self._status_anim.stop()
        self._status_anim.setStartValue(float(self._status_fx.opacity()))
        self._status_anim.setEndValue(0.0)
        self._status_anim.start()

    def _launch(self, script: Path, btn: QPushButton) -> None:
        # Guard against rapid double-clicks
        btn.setEnabled(False)
        QTimer.singleShot(600, lambda: btn.setEnabled(True))

        # Guard against opening tons of duplicates from the launcher
        if script in self._launched:
            ret = QMessageBox.question(
                self,
                "Already launched",
                "This app was already launched from the launcher.\n\nLaunch another instance?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                self._set_status("Launch cancelled.")
                return

        ok, diag = _diagnose_script(script)
        if not ok:
            self._set_status(f"Cannot launch:\n{script}\n\n{diag}")
            QMessageBox.critical(self, "Cannot launch", f"{script}\n\n{diag}")
            return

        self._set_status(f"Launching:\n{script}")
        if _start_script(self, script):
            self._launched.add(script)
            self._write_recent(script)
            self._render_recent_activity()
            self._set_status(f"Launched:\n{script.name}")
        else:
            self._set_status("Launch failed. See error dialog.")
            self._refresh_button_states()

    def _open_workspace(self) -> None:
        ws = _workspace_root()
        QDesktopServices.openUrl(ws.as_uri())
        self._set_status(f"Opened folder:\n{ws}")


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)

    # Apply theme globally (Window will override based on settings immediately after init)
    app.setStyleSheet(DARK_QSS)

    win = LauncherWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
