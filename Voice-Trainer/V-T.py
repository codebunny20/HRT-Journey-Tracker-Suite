import sys
import os

import numpy as np
import sounddevice as sd
import soundfile as sf
import aubio

from PySide6.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QPushButton, QLabel, QSpinBox, QFileDialog, QComboBox,
    QGroupBox, QFormLayout, QHBoxLayout,
)
from PySide6.QtCore import QThread, Signal

# -------------------- audio.py (inlined) --------------------

SAMPLE_RATE = 44100

def list_input_devices():
    """Return [(device_index, display_name), ...] for devices with input channels."""
    devices = sd.query_devices()
    out = []
    for i, d in enumerate(devices):
        try:
            if int(d.get("max_input_channels", 0)) > 0:
                name = d.get("name", f"Device {i}")
                hostapi = d.get("hostapi", None)
                out.append((i, f"{name} (in:{d['max_input_channels']}, hostapi:{hostapi})"))
        except Exception:
            continue
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Trainer - Prototype")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ---------- Input (device + file) ----------
        input_group = QGroupBox("Input")
        input_layout = QFormLayout(input_group)
        input_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.device_combo = QComboBox()
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

        # Assemble
        root.addWidget(input_group)
        root.addWidget(rec_group)
        root.addWidget(out_group)
        root.addStretch(1)

        # Signals (keep behavior intact)
        self.record_button.clicked.connect(self.start_recording)
        self.choose_button.clicked.connect(self.choose_audio_file)
        self.clear_button.clicked.connect(self.clear_selected_file)
        self.analyze_button.clicked.connect(self.analyze_current_input)
        self.refresh_devices_button.clicked.connect(self.refresh_devices)

        # Use a stable location regardless of current working directory
        root_dir = os.path.abspath(os.path.dirname(__file__))
        self.last_path = os.path.join(root_dir, "last_recording.wav")

        self.current_input_path = None
        self.record_thread = None

        self._device_map = {}
        self.refresh_devices()
        self._refresh_analyze_enabled()

    def refresh_devices(self):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self._device_map.clear()

        self.device_combo.addItem("System Default")
        self._device_map[0] = None

        for dev_index, display in list_input_devices():
            self.device_combo.addItem(display)
            self._device_map[self.device_combo.count() - 1] = dev_index

        self.device_combo.blockSignals(False)

    def _selected_input_device_index(self):
        return self._device_map.get(self.device_combo.currentIndex(), None)

    def _refresh_analyze_enabled(self):
        can_analyze = bool(self.current_input_path) or os.path.exists(self.last_path)
        self.analyze_button.setEnabled(can_analyze)

    def _display_input_path(self):
        if self.current_input_path:
            self.input_label.setText(f"Input: {os.path.basename(self.current_input_path)}")
            self.clear_button.setEnabled(True)
        else:
            fallback = "last recording" if os.path.exists(self.last_path) else "none"
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

    def start_recording(self):
        duration = self.duration_spin.value()
        self.status_label.setText("Recording...")
        self.record_button.setEnabled(False)
        self.analyze_button.setEnabled(False)

        input_dev = self._selected_input_device_index()
        self.record_thread = RecordWorker(duration, self.last_path, input_device_index=input_dev)
        self.record_thread.finished.connect(self.on_record_finished)
        self.record_thread.failed.connect(self.on_record_failed)
        self.record_thread.start()
        self._refresh_analyze_enabled()

    def on_record_finished(self, path):
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

# -------------------- entrypoint --------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())