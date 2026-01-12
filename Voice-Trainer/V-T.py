import sys
import os
import datetime  # NEW
import json  # NEW

import numpy as np
import sounddevice as sd
import soundfile as sf
import aubio

from PySide6.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QPushButton, QLabel, QSpinBox, QFileDialog, QComboBox,
    QGroupBox, QFormLayout, QHBoxLayout,
    QLineEdit,
    QStackedWidget,  # NEW
    QListWidget, QPlainTextEdit,  # NEW (notes page UI)
    QCheckBox,  # NEW (settings UI)
)
from PySide6.QtCore import QThread, Signal
from PySide6.QtCore import QTimer  # NEW

# -------------------- audio.py (inlined) --------------------

SAMPLE_RATE = 44100

def _hostapi_name(hostapi_index: int | None) -> str:
    try:
        if hostapi_index is None:
            return "Unknown"
        apis = sd.query_hostapis()
        if 0 <= int(hostapi_index) < len(apis):
            return apis[int(hostapi_index)].get("name", "Unknown")
    except Exception:
        pass
    return "Unknown"

def _default_input_device_indices() -> set[int]:
    """Best-effort set of indices that may be considered default input devices."""
    out: set[int] = set()
    try:
        d = sd.default.device
        if isinstance(d, (list, tuple)) and len(d) >= 1 and d[0] not in (-1, None):
            out.add(int(d[0]))
        elif d not in (-1, None):
            out.add(int(d))
    except Exception:
        pass
    # Some backends expose a per-hostapi default input; include those too.
    try:
        for api in sd.query_hostapis():
            idx = api.get("default_input_device", None)
            if idx not in (-1, None):
                out.add(int(idx))
    except Exception:
        pass
    return out

def list_input_devices():
    """Return [(device_index, display_name), ...] for devices with input channels."""
    devices = sd.query_devices()
    defaults = _default_input_device_indices()
    out = []
    for i, d in enumerate(devices):
        try:
            max_in = int(d.get("max_input_channels", 0))
            if max_in > 0:
                name = d.get("name", f"Device {i}")
                hostapi_idx = d.get("hostapi", None)
                hostapi = _hostapi_name(hostapi_idx)
                is_default = " (default)" if i in defaults else ""
                # Friendlier + searchable label
                label = f"{name}{is_default} — {hostapi} — in:{max_in}"
                out.append((i, label))
        except Exception:
            continue

    # Put likely choices first: defaults, then more input channels, then name.
    def _sort_key(item):
        idx, label = item
        try:
            d = devices[idx]
            max_in = int(d.get("max_input_channels", 0))
        except Exception:
            max_in = 0
        is_default = 0 if idx in defaults else 1
        return (is_default, -max_in, label.lower())

    out.sort(key=_sort_key)
    return out

def _default_input_device_ok() -> bool:
    try:
        dev = sd.default.device
        in_dev = dev[0] if isinstance(dev, (list, tuple)) else dev
        if in_dev is None or in_dev == -1:
            return False
        info = sd.query_devices(in_dev)
        return info.get("max_input_channels", 0) > 0
    except Exception:
        return False

def record_clip(duration_sec: float, output_path: str, input_device: int | None = None):
    frames = int(duration_sec * SAMPLE_RATE)
    if frames <= 0:
        raise ValueError("duration must be > 0")

    # If user didn't pick a device, require a usable system default.
    if input_device is None and not _default_input_device_ok():
        raise RuntimeError("No default input device available")

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    audio = sd.rec(
        frames,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=(input_device, None) if input_device is not None else None,
    )
    sd.wait()

    audio = np.asarray(audio).reshape(-1)
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)

    sf.write(output_path, audio, SAMPLE_RATE)
    return output_path

def load_audio(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    data, sr = sf.read(path, always_2d=False)
    data = np.asarray(data)

    if data.ndim > 1:
        data = data[:, 0]
    if data.dtype != np.float32:
        data = data.astype(np.float32, copy=False)

    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
    return data, sr

# -------------------- analysis.py (inlined) --------------------

def estimate_pitch_track(audio: np.ndarray, sample_rate: int, hop_size: int = 512):
    if audio is None or len(audio) == 0:
        return np.array([], dtype=np.float32)

    audio = np.asarray(audio, dtype=np.float32)
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)

    pitch_o = aubio.pitch("yin", 2048, hop_size, sample_rate)
    pitch_o.set_unit("Hz")
    pitch_o.set_silence(-40)

    pitches = []
    for i in range(0, len(audio), hop_size):
        frame = audio[i:i + hop_size]
        if len(frame) < hop_size:
            frame = np.pad(frame, (0, hop_size - len(frame)), mode="constant")

        # skip frames that are basically silence
        if np.max(np.abs(frame)) < 1e-3:
            continue

        pitch = float(pitch_o(frame)[0])
        pitches.append(pitch)

    pitches = np.array(pitches, dtype=np.float32)
    pitches = pitches[np.isfinite(pitches)]
    pitches = pitches[(pitches > 50.0) & (pitches < 500.0)]
    return pitches

def estimate_average_pitch(audio: np.ndarray, sample_rate: int):
    pitches = estimate_pitch_track(audio, sample_rate)
    if len(pitches) == 0:
        return None
    return float(np.median(pitches))

# -------------------- ui_main.py (inlined) --------------------

class RecordWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, duration, out_path, input_device_index=None):
        super().__init__()
        self.duration = duration
        self.out_path = out_path
        self.input_device_index = input_device_index

    def run(self):
        try:
            record_clip(self.duration, self.out_path, input_device=self.input_device_index)
            self.finished.emit(self.out_path)
        except Exception as e:
            self.failed.emit(str(e))

class VoiceNoteRecordWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, duration, out_path, input_device_index=None):
        super().__init__()
        self.duration = duration
        self.out_path = out_path
        self.input_device_index = input_device_index

    def run(self):
        try:
            record_clip(self.duration, self.out_path, input_device=self.input_device_index)
            self.finished.emit(self.out_path)
        except Exception as e:
            self.failed.emit(str(e))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Trainer")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # --------- Pages (stack) ---------
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)

        self.page_home = QWidget()
        self.page_record = QWidget()
        self.page_about = QWidget()
        self.page_notes = QWidget()  # NEW
        self.page_settings = QWidget()  # NEW
        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_record)
        self.pages.addWidget(self.page_about)
        self.pages.addWidget(self.page_notes)  
        self.pages.addWidget(self.page_settings) 

        self._build_home_page()
        self._build_record_page()  # contains your existing Input/Recording/Analysis UI
        self._build_about_page()
        self._build_notes_page() 
        self._build_settings_page() 

        self.pages.setCurrentWidget(self.page_home)

        # Use a stable location regardless of current working directory
        root_dir = os.path.abspath(os.path.dirname(__file__))

        self.data_dir = os.path.join(root_dir, "data")
        self.voice_log_dir = os.path.join(self.data_dir, "voice_log")
        self.voice_notes_dir = os.path.join(self.data_dir, "voice_notes")  # NEW
        self.settings_dir = os.path.join(self.data_dir, "settings")  # NEW
        self.settings_path = os.path.join(self.settings_dir, "settings.json")  # NEW
        try:
            os.makedirs(self.voice_log_dir, exist_ok=True)
            os.makedirs(self.voice_notes_dir, exist_ok=True)  # NEW
            os.makedirs(self.settings_dir, exist_ok=True)  # NEW
        except Exception as e:
            # Route warning to the record page status label if available
            try:
                self.status_label.setText(f"Warning: could not create data folders: {e}")
            except Exception:
                pass

        self.last_path = None
        self._record_counter = 0  
        self._note_counter = 0  
        self.note_record_thread = None  
        self._countdown_timer = None  
        self._countdown_remaining = 0  
        self._countdown_on_done = None  
        self._countdown_update_label = None 

        # Countdown settings (persisted)
        self.countdown_enabled = True  # NEW
        self.countdown_seconds = 5     # NEW

        # OPTIONAL: only overwrite status if we didn't already warn above
        if hasattr(self, "status_label") and not (self.status_label.text() or "").startswith("Warning:"):
            self.status_label.setText("Ready.")

        self.current_input_path = None
        self.record_thread = None

        self._device_map = {}
        self._all_devices = []  # list[(dev_index, display)]
        # Settings: None means "System Default"
        self.default_input_device_index = None
        self._settings_device_map = {}  # combobox index -> device index|None

        # Load persisted settings (best-effort) before populating UI-dependent device lists
        self._load_settings()

        try:
            if bool(getattr(self, "_loaded_autorefresh", False)):
                self._all_devices = list_input_devices()
        except Exception:
            pass

        self.refresh_devices()
        self._refresh_analyze_enabled()
        # Apply loaded settings to widgets now that pages exist
        self._apply_settings_to_ui()
        # Ensure device dropdown reflects loaded default choice
        self._refresh_settings_device_combo()
        # Apply settings app-wide (device selection/other runtime effects)
        self.apply_settings_appwide()

        self._update_settings_info(loaded=True)

        self.refresh_voice_notes()  

    # --------- UI builders ---------
    def _build_home_page(self):
        layout = QVBoxLayout(self.page_home)
        layout.setSpacing(10)

        title = QLabel("Voice Trainer")
        title.setStyleSheet("font-weight: 700; font-size: 18px;")
        subtitle = QLabel("Choose a feature:")
        subtitle.setStyleSheet("color: #666;")

        btn_record = QPushButton("Record & Analyze")
        btn_notes = QPushButton("Voice Notes")  
        btn_settings = QPushButton("Settings")  
        btn_about = QPushButton("About / Help")
        btn_quit = QPushButton("Quit")

        btn_record.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_record))
        btn_notes.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_notes))  # NEW
        btn_settings.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_settings))  # NEW
        btn_about.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_about))
        btn_quit.clicked.connect(QApplication.instance().quit)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        layout.addWidget(btn_record)
        layout.addWidget(btn_notes)  
        layout.addWidget(btn_settings)  
        layout.addWidget(btn_about)
        layout.addStretch(1)
        layout.addWidget(btn_quit)

    def _build_about_page(self):
        layout = QVBoxLayout(self.page_about)
        layout.setSpacing(10)

        title = QLabel("About / Help")
        title.setStyleSheet("font-weight: 700; font-size: 16px;")

        body = QLabel(
            "What this app does\n"
            "- Record short clips from a microphone and estimate pitch (Hz).\n"
            "- Save practice recordings and voice notes to disk.\n\n"
            "Record & Analyze\n"
            "- Pick a microphone (or leave 'System Default'). Use Filter to search.\n"
            "- Press Record. If countdown is enabled, recording starts after the countdown.\n"
            "- Press Analyze to estimate pitch for the selected file or the last recording.\n"
            "- Use 'Choose Audio File' to analyze an existing file instead of recording.\n\n"
            "Voice Notes\n"
            "- Records longer notes into the voice notes folder.\n"
            "- Select a note to see file details.\n\n"
            "Settings\n"
            "- Default input device: the microphone used by Record & Analyze / Voice Notes.\n"
            "- Countdown: enable/disable and set seconds.\n"
            "- Save Settings writes to disk and will be loaded next launch.\n\n"
            "Troubleshooting\n"
            "- If recording fails: open Settings and set a Default input device, then Refresh devices.\n"
            "- If a headset just got plugged in: press Refresh in Record & Analyze or Settings.\n"
            "- If pitch is not detected: try a louder clip, reduce background noise, or use a sustained vowel.\n\n"
            "Data locations (relative to this app folder)\n"
            "- Recordings: data/voice_log/\n"
            "- Voice notes: data/voice_notes/\n"
            "- Settings file: data/settings/settings.json\n"
        )
        body.setWordWrap(True)

        back = QPushButton("Back to Home")
        back.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_home))

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch(1)
        layout.addWidget(back)

    def _build_record_page(self):
        root = QVBoxLayout(self.page_record)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        back = QPushButton("Back to Home")
        back.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_home))
        header = QLabel("Record & Analyze")
        header.setStyleSheet("font-weight: 700; font-size: 16px;")
        top_row.addWidget(back)
        top_row.addWidget(header)
        top_row.addStretch(1)
        root.addLayout(top_row)

        # ---------- Input (device + file) ----------
        input_group = QGroupBox("Input")
        input_layout = QFormLayout(input_group)
        input_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.device_filter = QLineEdit()
        self.device_filter.setPlaceholderText("Filter microphones (type to search)...")
        self.device_filter.setClearButtonEnabled(True)

        self.device_combo = QComboBox()
        self.device_combo.setToolTip("Pick the microphone to record from. Use the filter to search.")
        self.refresh_devices_button = QPushButton("Refresh")
        self.refresh_devices_button.setToolTip("Refresh the list after plugging in a headset/earbuds.")

        device_row = QHBoxLayout()
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.refresh_devices_button)

        self.choose_button = QPushButton("Choose Audio File...")
        self.choose_button.setToolTip("Pick an existing audio file to analyze (instead of recording).")

        self.clear_button = QPushButton("Clear")
        self.clear_button.setEnabled(False)
        self.clear_button.setToolTip("Stop using the selected file and fall back to the last recording.")

        file_row = QHBoxLayout()
        file_row.addWidget(self.choose_button, 1)
        file_row.addWidget(self.clear_button)

        self.input_label = QLabel("Input: (none)")
        self.input_label.setToolTip("Shows the currently selected file input (if any).")

        input_layout.addRow("Filter:", self.device_filter)
        input_layout.addRow("Microphone:", device_row)
        input_layout.addRow("Audio file:", file_row)
        input_layout.addRow("", self.input_label)

        # ---------- Recording ----------
        rec_group = QGroupBox("Recording")
        rec_layout = QFormLayout(rec_group)
        rec_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(5)
        self.duration_spin.setToolTip("How long to record from the selected microphone.")

        self.record_button = QPushButton("Record")
        self.record_button.setToolTip("Records a new clip from the selected microphone.")

        rec_layout.addRow("Duration (sec):", self.duration_spin)
        rec_layout.addRow("", self.record_button)

        # ---------- Analysis + status ----------
        out_group = QGroupBox("Analysis")
        out_layout = QVBoxLayout(out_group)
        out_layout.setSpacing(6)

        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setEnabled(False)
        self.analyze_button.setToolTip("Analyzes the selected file, or the last recording if no file is selected.")

        self.pitch_label = QLabel("Pitch: -")
        self.pitch_label.setStyleSheet("font-weight: 600; font-size: 14px;")

        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)

        out_layout.addWidget(self.analyze_button)
        out_layout.addWidget(self.pitch_label)
        out_layout.addWidget(self.status_label)

        root.addWidget(input_group)
        root.addWidget(rec_group)
        root.addWidget(out_group)
        root.addStretch(1)

        # Signals (behavior unchanged)
        self.record_button.clicked.connect(self.start_recording)
        self.choose_button.clicked.connect(self.choose_audio_file)
        self.clear_button.clicked.connect(self.clear_selected_file)
        self.analyze_button.clicked.connect(self.analyze_current_input)
        self.refresh_devices_button.clicked.connect(self.refresh_devices)
        self.device_filter.textChanged.connect(self.apply_device_filter)

    def _build_notes_page(self):
        root = QVBoxLayout(self.page_notes)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        back = QPushButton("Back to Home")
        back.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_home))
        header = QLabel("Voice Notes")
        header.setStyleSheet("font-weight: 700; font-size: 16px;")
        top_row.addWidget(back)
        top_row.addWidget(header)
        top_row.addStretch(1)
        root.addLayout(top_row)

        # Minimal scaffold UI (you can wire this up to recordings/metadata next)
        info = QLabel("Placeholder page for voice notes (list + details).")
        info.setStyleSheet("color: #666;")

        self.notes_list = QListWidget()
        self.notes_list.setToolTip("Voice notes will appear here.")

        self.note_details = QPlainTextEdit()
        self.note_details.setPlaceholderText("Select a note to see details here...")
        self.note_details.setReadOnly(True)

        # NEW: record controls
        rec_group = QGroupBox("Record Voice Note")
        rec_layout = QFormLayout(rec_group)
        rec_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.note_duration_spin = QSpinBox()
        self.note_duration_spin.setRange(1, 600)
        self.note_duration_spin.setValue(10)
        self.note_duration_spin.setToolTip("How long to record a voice note.")

        self.note_record_button = QPushButton("Record")
        self.note_record_button.setToolTip("Record a new voice note into data/voice_notes.")

        self.note_status_label = QLabel("Ready.")
        self.note_status_label.setWordWrap(True)

        rec_layout.addRow("Duration (sec):", self.note_duration_spin)
        rec_layout.addRow("", self.note_record_button)
        rec_layout.addRow("", self.note_status_label)

        # keep duration in sync with settings default once note UI exists
        try:
            if hasattr(self, "edit_default_note_duration"):
                self.note_duration_spin.setValue(int(self.edit_default_note_duration.value()))
        except Exception:
            pass

        # Signals
        self.note_record_button.clicked.connect(self.start_voice_note_recording)
        self.notes_list.currentRowChanged.connect(self.on_voice_note_selected)

        actions = QHBoxLayout()
        self.btn_new_note = QPushButton("New Note (todo)")
        self.btn_play_note = QPushButton("Play (todo)")
        self.btn_delete_note = QPushButton("Delete (todo)")
        for b in (self.btn_new_note, self.btn_play_note, self.btn_delete_note):
            b.setEnabled(False)  # scaffold only
        actions.addWidget(self.btn_new_note)
        actions.addWidget(self.btn_play_note)
        actions.addWidget(self.btn_delete_note)
        actions.addStretch(1)

        root.addWidget(info)
        root.addWidget(self.notes_list, 2)
        root.addWidget(rec_group)
        root.addLayout(actions)
        root.addWidget(self.note_details, 1)

    def _build_settings_page(self):
        root = QVBoxLayout(self.page_settings)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        back = QPushButton("Back to Home")
        back.clicked.connect(lambda: self.pages.setCurrentWidget(self.page_home))
        header = QLabel("Settings")
        header.setStyleSheet("font-weight: 700; font-size: 16px;")
        top_row.addWidget(back)
        top_row.addWidget(header)
        top_row.addStretch(1)
        root.addLayout(top_row)

        form_group = QGroupBox("General")
        form = QFormLayout(form_group)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Placeholder settings (wire to persistence later if desired)
        self.chk_autorefresh_devices = QCheckBox("Auto-refresh device list on open (placeholder)")
        self.chk_autorefresh_devices.setChecked(False)

        self.edit_default_note_duration = QSpinBox()
        self.edit_default_note_duration.setRange(1, 600)
        self.edit_default_note_duration.setValue(10)
        self.edit_default_note_duration.setToolTip("Default duration for voice notes (placeholder).")

        # NEW: Default input device selector
        self.settings_device_combo = QComboBox()
        self.settings_device_combo.setToolTip("Choose the default microphone used for recordings.")
        self.settings_refresh_devices_button = QPushButton("Refresh devices")
        self.settings_refresh_devices_button.setToolTip("Re-scan microphones and update this list.")

        device_row = QHBoxLayout()
        device_row.addWidget(self.settings_device_combo, 1)
        device_row.addWidget(self.settings_refresh_devices_button)

        # NEW: Countdown settings
        self.chk_enable_countdown = QCheckBox("Enable countdown before recording")
        self.chk_enable_countdown.setChecked(True)

        self.spin_countdown_seconds = QSpinBox()
        self.spin_countdown_seconds.setRange(3, 60)
        self.spin_countdown_seconds.setValue(5)
        self.spin_countdown_seconds.setToolTip("Countdown length before recording starts (minimum 3 seconds).")

        form.addRow("", self.chk_autorefresh_devices)
        form.addRow("Default voice note duration (sec):", self.edit_default_note_duration)
        form.addRow("Default input device:", device_row)
        form.addRow("", self.chk_enable_countdown)
        form.addRow("Countdown seconds:", self.spin_countdown_seconds)

        # CHANGED: replace placeholder label with a real, updatable status label
        self.settings_info = QLabel("")
        self.settings_info.setStyleSheet("color: #666;")
        self.settings_info.setWordWrap(True)

        root.addWidget(form_group)
        root.addWidget(self.settings_info)
        root.addStretch(1)

        # Signals
        self.settings_refresh_devices_button.clicked.connect(self.refresh_devices)
        self.settings_device_combo.currentIndexChanged.connect(self.on_settings_default_device_changed)

        # NEW/CHANGED: apply immediately when changed (still allow Save for persistence)
        self.chk_autorefresh_devices.toggled.connect(self.on_any_setting_changed)
        self.edit_default_note_duration.valueChanged.connect(self.on_any_setting_changed)

        self.chk_enable_countdown.toggled.connect(self.on_countdown_settings_changed)  # NEW
        self.spin_countdown_seconds.valueChanged.connect(self.on_countdown_settings_changed)  # NEW

        # NEW: Save button + status
        self.settings_save_button = QPushButton("Save Settings")
        self.settings_save_status = QLabel("")
        self.settings_save_status.setStyleSheet("color: #666;")
        self.settings_save_status.setWordWrap(True)
        self.settings_save_button.clicked.connect(self.save_settings)

        root.addWidget(self.settings_save_button)
        root.addWidget(self.settings_save_status)

    def apply_device_filter(self):
        """Rebuild combo based on current filter text."""
        text = (self.device_filter.text() or "").strip().lower()

        # Preserve selection by device index (or None for system default)
        prev_dev = self._selected_input_device_index()

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self._device_map.clear()

        self.device_combo.addItem("System Default")
        self._device_map[0] = None

        for dev_index, display in self._all_devices:
            if text and text not in display.lower():
                continue
            self.device_combo.addItem(display)
            self._device_map[self.device_combo.count() - 1] = dev_index

        # Restore selection if possible
        if prev_dev is None:
            self.device_combo.setCurrentIndex(0)
        else:
            for combo_i, dev_i in self._device_map.items():
                if dev_i == prev_dev:
                    self.device_combo.setCurrentIndex(combo_i)
                    break

        self.device_combo.blockSignals(False)

    def refresh_devices(self):
        # Re-query + rebuild using current filter, while preserving selection.
        self._all_devices = list_input_devices()
        self.apply_device_filter()
        self._refresh_settings_device_combo()
        # Keep the chosen default device enforced after refresh
        self.apply_settings_appwide()

    def _refresh_settings_device_combo(self):
        """Rebuild Settings->Default input device dropdown."""
        if not hasattr(self, "settings_device_combo"):
            return

        prev = self.default_input_device_index
        self.settings_device_combo.blockSignals(True)
        self.settings_device_combo.clear()
        self._settings_device_map.clear()

        self.settings_device_combo.addItem("System Default")
        self._settings_device_map[0] = None

        for dev_index, display in self._all_devices:
            self.settings_device_combo.addItem(display)
            self._settings_device_map[self.settings_device_combo.count() - 1] = dev_index

        # restore selection
        if prev is None:
            self.settings_device_combo.setCurrentIndex(0)
        else:
            for combo_i, dev_i in self._settings_device_map.items():
                if dev_i == prev:
                    self.settings_device_combo.setCurrentIndex(combo_i)
                    break

        self.settings_device_combo.blockSignals(False)

    def on_settings_default_device_changed(self, combo_index: int):
        """Apply selected default device and sync the Record page microphone selection."""
        self.default_input_device_index = self._settings_device_map.get(combo_index, None)
        self.apply_settings_appwide()
        self._update_settings_info(loaded=False)

    def on_countdown_settings_changed(self):
        """Apply countdown UI state immediately and keep widgets consistent."""
        try:
            enabled = bool(self.chk_enable_countdown.isChecked())
            self.spin_countdown_seconds.setEnabled(enabled)
            self.countdown_enabled = enabled
            self.countdown_seconds = int(self.spin_countdown_seconds.value())
            self._update_settings_info(loaded=False)
        except Exception:
            return

    def _selected_input_device_index(self):
        return self._device_map.get(self.device_combo.currentIndex(), None)

    def _next_recording_path(self) -> str:
        """Create a unique output path so recordings never overwrite each other."""
        self._record_counter = (self._record_counter + 1) % 1000
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{ts}_{self._record_counter:03d}.wav"
        return os.path.join(self.voice_log_dir, filename)

    def _next_voice_note_path(self) -> str:
        self._note_counter = (self._note_counter + 1) % 1000
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voice_note_{ts}_{self._note_counter:03d}.wav"
        return os.path.join(self.voice_notes_dir, filename)

    def refresh_voice_notes(self):
        if not hasattr(self, "notes_list"):
            return
        self.notes_list.clear()
        try:
            if not os.path.isdir(self.voice_notes_dir):
                return
            files = [f for f in os.listdir(self.voice_notes_dir) if f.lower().endswith(".wav")]
            files.sort(reverse=True)
            self.notes_list.addItems(files)
        except Exception as e:
            if hasattr(self, "note_status_label"):
                self.note_status_label.setText(f"Could not load voice notes: {e}")

    def on_voice_note_selected(self, row: int):
        if row < 0 or not hasattr(self, "notes_list"):
            return
        name = self.notes_list.item(row).text()
        path = os.path.join(self.voice_notes_dir, name)
        try:
            size_kb = os.path.getsize(path) / 1024.0
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
            self.note_details.setPlainText(
                f"File: {name}\nPath: {path}\nModified: {mtime}\nSize: {size_kb:.1f} KB\n"
            )
        except Exception as e:
            self.note_details.setPlainText(f"Could not read note details: {e}")

    def _start_countdown(self, seconds: int, update_label_fn, on_done_fn):
        """Non-blocking countdown (updates UI once per second), then calls on_done_fn()."""

        # NEW: app-wide enable/disable + configurable seconds (min 3 when enabled)
        try:
            if not bool(getattr(self, "countdown_enabled", True)):
                if callable(update_label_fn):
                    update_label_fn("Recording...")
                if callable(on_done_fn):
                    on_done_fn()
                return
            seconds = int(getattr(self, "countdown_seconds", seconds or 0))
        except Exception:
            seconds = int(seconds or 0)

        seconds = max(3, int(seconds or 0))  # minimum 3 seconds when enabled
        # cancel any prior countdown
        try:
            if self._countdown_timer is not None:
                self._countdown_timer.stop()
        except Exception:
            pass

        self._countdown_remaining = seconds
        self._countdown_update_label = update_label_fn
        self._countdown_on_done = on_done_fn

        def _tick():
            r = int(self._countdown_remaining)
            if r <= 0:
                try:
                    self._countdown_timer.stop()
                except Exception:
                    pass
                # clear "starting in" message right before starting
                try:
                    if callable(self._countdown_update_label):
                        self._countdown_update_label("Recording...")
                except Exception:
                    pass
                if callable(self._countdown_on_done):
                    self._countdown_on_done()
                return

            try:
                if callable(self._countdown_update_label):
                    self._countdown_update_label(f"Starting in {r}...")
            except Exception:
                pass
            self._countdown_remaining -= 1

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(_tick)
        _tick()  # show immediately
        self._countdown_timer.start()

    def start_voice_note_recording(self):
        if self.note_record_thread is not None and self.note_record_thread.isRunning():
            return

        if hasattr(self, "note_record_button"):
            self.note_record_button.setEnabled(False)

        out_path = self._next_voice_note_path()
        duration = int(self.note_duration_spin.value()) if hasattr(self, "note_duration_spin") else 10
        input_dev = self._selected_input_device_index()

        def _set_status(msg: str):
            if hasattr(self, "note_status_label"):
                self.note_status_label.setText(msg)

        def _begin_recording():
            self.note_record_thread = VoiceNoteRecordWorker(duration, out_path, input_device_index=input_dev)
            self.note_record_thread.finished.connect(self.on_voice_note_record_finished)
            self.note_record_thread.failed.connect(self.on_voice_note_record_failed)
            self.note_record_thread.start()

        self._start_countdown(5, _set_status, _begin_recording)

    def on_voice_note_record_finished(self, path: str):
        if hasattr(self, "note_status_label"):
            self.note_status_label.setText(f"Saved: {path}")
        if hasattr(self, "note_record_button"):
            self.note_record_button.setEnabled(True)
        self.refresh_voice_notes()

    def on_voice_note_record_failed(self, message: str):
        lower = (message or "").lower()
        if "input" in lower and ("device" in lower or "no default" in lower):
            message = f"{message} (try setting a default mic in Settings or pick one on Record & Analyze)"
        if hasattr(self, "note_status_label"):
            self.note_status_label.setText(f"Recording failed: {message}")
        if hasattr(self, "note_record_button"):
            self.note_record_button.setEnabled(True)

    def start_recording(self):
        duration = self.duration_spin.value()

        self.record_button.setEnabled(False)
        self.analyze_button.setEnabled(False)

        input_dev = self._selected_input_device_index()
        out_path = self._next_recording_path()

        def _set_status(msg: str):
            self.status_label.setText(msg)

        def _begin_recording():
            self.record_thread = RecordWorker(duration, out_path, input_device_index=input_dev)
            self.record_thread.finished.connect(self.on_record_finished)
            self.record_thread.failed.connect(self.on_record_failed)
            self.record_thread.start()
            self._refresh_analyze_enabled()

        self._start_countdown(5, _set_status, _begin_recording)

    def on_record_finished(self, path):
        self.last_path = path
        self.status_label.setText(f"Recording saved: {path}")
        self.record_button.setEnabled(True)
        self._display_input_path()
        self._refresh_analyze_enabled()

    def on_record_failed(self, message: str):
        lower = message.lower()
        if "input" in lower and ("device" in lower or "no default" in lower):
            message = f"{message} (try picking your headset/earbuds in Input device and refresh)"
        self.status_label.setText(f"Recording failed: {message}")
        self.record_button.setEnabled(True)
        self._display_input_path()
        self._refresh_analyze_enabled()

    def analyze_current_input(self):
        path = self.current_input_path or self.last_path
        if not path or not os.path.exists(path):
            self.status_label.setText("No input available. Record or choose a file first.")
            self._refresh_analyze_enabled()
            return

        self.status_label.setText(f"Analyzing: {os.path.basename(path)}")
        try:
            audio, sr = load_audio(path)
            if audio is None or len(audio) == 0:
                self.pitch_label.setText("Pitch: not detected")
                self.status_label.setText("Analysis done (empty audio).")
                return

            avg_pitch = estimate_average_pitch(audio, sr)
            if avg_pitch is None:
                self.pitch_label.setText("Pitch: not detected")
            else:
                self.pitch_label.setText(f"Pitch: {avg_pitch:.1f} Hz")
            self.status_label.setText("Analysis done.")
        except Exception as e:
            self.status_label.setText(f"Analysis failed: {e}")
        finally:
            self._refresh_analyze_enabled()

    def _refresh_analyze_enabled(self):
        can_analyze = bool(self.current_input_path) or (bool(self.last_path) and os.path.exists(self.last_path))
        self.analyze_button.setEnabled(can_analyze)

    def _display_input_path(self):
        if self.current_input_path:
            self.input_label.setText(f"Input: {os.path.basename(self.current_input_path)}")
            self.clear_button.setEnabled(True)
        else:
            fallback = "last recording" if (self.last_path and os.path.exists(self.last_path)) else "none"
            self.input_label.setText(f"Input: (none) — fallback: {fallback}")
            self.clear_button.setEnabled(False)

    def choose_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose audio file",
            os.path.abspath(os.path.dirname(__file__)),
            "Audio files (*.wav *.flac *.ogg *.aiff *.aif *.mp3);;All files (*.*)",
        )
        if not path:
            return
        self.current_input_path = path
        self._display_input_path()
        self.status_label.setText("Selected file. Ready to analyze.")
        self._refresh_analyze_enabled()

    def clear_selected_file(self):
        self.current_input_path = None
        self._display_input_path()
        self.status_label.setText("Cleared selected file.")
        self._refresh_analyze_enabled()

    def _load_settings(self):
        """Best-effort load settings from data/settings/settings.json."""
        try:
            if not os.path.exists(self.settings_path):
                return
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            # None => System Default; otherwise int device index
            dev = data.get("default_input_device_index", None)
            self.default_input_device_index = None if dev in (None, -1, "default") else int(dev)
            self._loaded_autorefresh = bool(data.get("autorefresh_devices", False))
            self._loaded_default_note_duration = int(data.get("default_voice_note_duration_sec", 10))

            # NEW: countdown settings
            self.countdown_enabled = bool(data.get("countdown_enabled", True))
            self.countdown_seconds = max(3, int(data.get("countdown_seconds", 5)))
        except Exception:
            # Ignore corrupted/partial config; keep defaults
            self.default_input_device_index = None
            self._loaded_autorefresh = False
            self._loaded_default_note_duration = 10
            self.countdown_enabled = True  # NEW
            self.countdown_seconds = 5     # NEW

    def _apply_settings_to_ui(self):
        """Apply loaded settings to widgets (only if they exist)."""
        # These are safe no-ops if widgets aren't created yet.
        if hasattr(self, "chk_autorefresh_devices"):
            self.chk_autorefresh_devices.setChecked(getattr(self, "_loaded_autorefresh", False))
        if hasattr(self, "edit_default_note_duration"):
            self.edit_default_note_duration.setValue(getattr(self, "_loaded_default_note_duration", 10))
        # Voice notes: default duration should propagate to the voice notes duration control if present
        if hasattr(self, "note_duration_spin"):
            self.note_duration_spin.setValue(getattr(self, "_loaded_default_note_duration", 10))

        # NEW: countdown UI
        if hasattr(self, "chk_enable_countdown"):
            self.chk_enable_countdown.setChecked(bool(getattr(self, "countdown_enabled", True)))
        if hasattr(self, "spin_countdown_seconds"):
            self.spin_countdown_seconds.setValue(int(getattr(self, "countdown_seconds", 5)))
            self.spin_countdown_seconds.setEnabled(bool(getattr(self, "countdown_enabled", True)))

    def apply_settings_appwide(self):
        """
        Apply current settings across the app:
        - Enforce default input device selection in the Record page microphone combo
        - Apply default voice note duration to voice notes duration spinbox (if present)
        - Optionally auto-refresh devices (on demand)
        """
        # 1) Default input device -> enforce selection in Record page combo.
        try:
            if hasattr(self, "device_combo"):
                if self.default_input_device_index is None:
                    self.device_combo.setCurrentIndex(0)  # System Default
                else:
                    # Find matching device index in current combo mapping
                    for combo_i, dev_i in self._device_map.items():
                        if dev_i == self.default_input_device_index:
                            self.device_combo.setCurrentIndex(combo_i)
                            break
        except Exception:
            pass

        # 2) Default voice note duration -> apply to voice notes UI if built.
        try:
            if hasattr(self, "edit_default_note_duration") and hasattr(self, "note_duration_spin"):
                self.note_duration_spin.setValue(int(self.edit_default_note_duration.value()))
        except Exception:
            pass

        # 3) Auto-refresh devices -> make it app-wide (launch + whenever enabled and list is stale)
        try:
            if hasattr(self, "chk_autorefresh_devices") and self.chk_autorefresh_devices.isChecked():
                # Refresh if empty OR if current selection disappeared
                if not self._all_devices:
                    self._all_devices = list_input_devices()
                # Rebuild both dropdowns from the latest list.
                self.apply_device_filter()
                self._refresh_settings_device_combo()
        except Exception:
            pass

        # 4) Countdown settings -> keep runtime values and UI consistent
        try:
            if hasattr(self, "chk_enable_countdown") and hasattr(self, "spin_countdown_seconds"):
                self.countdown_enabled = bool(self.chk_enable_countdown.isChecked())
                self.countdown_seconds = max(3, int(self.spin_countdown_seconds.value()))
                self.spin_countdown_seconds.setEnabled(self.countdown_enabled)
        except Exception:
            pass

    def save_settings(self):
        """Save current settings UI values to data/settings/settings.json."""
        try:
            os.makedirs(self.settings_dir, exist_ok=True)
            data = {
                "default_input_device_index": self.default_input_device_index,
                "autorefresh_devices": bool(self.chk_autorefresh_devices.isChecked()) if hasattr(self, "chk_autorefresh_devices") else False,
                "default_voice_note_duration_sec": int(self.edit_default_note_duration.value()) if hasattr(self, "edit_default_note_duration") else 10,
                "countdown_enabled": bool(self.chk_enable_countdown.isChecked()) if hasattr(self, "chk_enable_countdown") else True,
                "countdown_seconds": max(3, int(self.spin_countdown_seconds.value())) if hasattr(self, "spin_countdown_seconds") else 5,
            }
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            if hasattr(self, "settings_save_status"):
                self.settings_save_status.setText(f"Saved to: {self.settings_path}")

            # Apply immediately so settings affect the whole app right away
            self.apply_settings_appwide()

            # NEW: reflect persistence status
            self._update_settings_info(loaded=True)

        except Exception as e:
            if hasattr(self, "settings_save_status"):
                self.settings_save_status.setText(f"Save failed: {e}")

    # NEW: single place to keep Settings page text current
    def _update_settings_info(self, loaded: bool = False):
        if not hasattr(self, "settings_info"):
            return
        try:
            exists = os.path.exists(self.settings_path)
            lines = []
            lines.append("Settings persistence: enabled")
            lines.append(f"File: {self.settings_path}")
            if loaded:
                lines.append("Status: loaded" if exists else "Status: using defaults (no file yet)")
            else:
                lines.append("Status: modified (not saved yet)")
            self.settings_info.setText("\n".join(lines))
        except Exception as e:
            self.settings_info.setText(f"Settings info unavailable: {e}")

    # NEW: apply non-countdown settings immediately + mark UI as dirty
    def on_any_setting_changed(self, *args, **kwargs):
        self.apply_settings_appwide()
        self._update_settings_info(loaded=False)

# -------------------- entrypoint --------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # Allow Ctrl+C to close the app without a long traceback in the console.
        sys.exit(0)
