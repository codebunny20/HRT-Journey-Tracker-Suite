# Explanation of `V-T.py` (Voice Trainer - Prototype)

This script is a small desktop GUI app (PySide6) that can:
- record a short mono audio clip from a selected input device (microphone),
- or load an existing audio file,
- then estimate the speaker’s pitch (fundamental frequency) and display an average pitch value in Hz.

It is written as one file but contains three conceptual parts “inlined” as comments:
- `audio.py` (recording + loading audio),
- `analysis.py` (pitch estimation),
- `ui_main.py` (Qt UI + background recording thread).

---

## 1) Dependencies / Imports

Key libraries used:
- `sounddevice` (`sd`): records audio from microphone devices.
- `soundfile` (`sf`): reads/writes audio files (WAV/FLAC/etc).
- `numpy`: audio array manipulation and cleanup (NaNs/shape).
- `aubio`: pitch detection (YIN algorithm via `aubio.pitch`).
- `PySide6`: Qt-based GUI (widgets/layouts + `QThread`).

---

## 2) Audio utilities (the “audio.py” section)

### Constants
- `SAMPLE_RATE = 44100`: recording sample rate (Hz).

### `list_input_devices()`
- Queries all devices from `sd.query_devices()`.
- Filters to devices where `max_input_channels > 0`.
- Returns a list of tuples:
  - `(device_index, display_name)`
- The display name includes basic info like input channel count and `hostapi`.

Used to populate the “Microphone” dropdown in the UI.

### `_default_input_device_ok()`
- Checks whether the OS/system default input device is valid and has input channels.
- If there’s no usable default device, recording without selecting a device will fail early with a clearer error.

### `record_clip(duration_sec, output_path, input_device=None)`
Records a mono clip and saves it to disk.

Flow:
1. Converts `duration_sec` to number of frames (`frames = duration_sec * SAMPLE_RATE`).
2. Ensures there is a valid input device (either user-selected or a usable system default).
3. Creates the output directory if needed.
4. Records audio with:
   - `sd.rec(frames, samplerate=44100, channels=1, dtype="float32", device=...)`
5. Waits for completion using `sd.wait()`.
6. Flattens the recorded buffer to a 1D array and cleans up invalid values:
   - `np.nan_to_num(... nan=0, posinf=0, neginf=0)`
7. Saves the audio via `sf.write(output_path, audio, SAMPLE_RATE)`.

Returns the output path (string).

### `load_audio(path)`
Loads audio from disk and normalizes it into a float32 mono NumPy array:
- Reads using `sf.read(path, always_2d=False)`, returning `(data, sr)`.
- If multi-channel, it keeps only the first channel (`data[:, 0]`).
- Converts to `np.float32` and replaces NaNs/infs with 0.
- Returns `(data, sr)`.

---

## 3) Pitch analysis (the “analysis.py” section)

### `estimate_pitch_track(audio, sample_rate, hop_size=512)`
Estimates a sequence of pitch values (Hz) across the clip.

How it works:
1. Validates audio is non-empty and converts to float32.
2. Creates an aubio pitch tracker:
   - `aubio.pitch("yin", 2048, hop_size, sample_rate)`
   - unit set to Hz (`set_unit("Hz")`)
   - silence threshold set to `-40` dB (`set_silence(-40)`)
3. Iterates over frames of `hop_size` samples.
4. Pads the last frame if needed.
5. Skips frames that are almost silent:
   - `if np.max(np.abs(frame)) < 1e-3: continue`
6. Runs aubio pitch detection on each frame and stores the result.
7. Filters results:
   - keeps only finite values
   - keeps only pitches between 50 Hz and 500 Hz (basic human voice range guard)

Returns: `np.ndarray` of pitch values in Hz.

### `estimate_average_pitch(audio, sample_rate)`
- Calls `estimate_pitch_track(...)`.
- If no pitch values are found, returns `None`.
- Otherwise returns the median pitch (`np.median(pitches)`) as the “average”.
  - Median is robust against outliers and brief detection errors.

---

## 4) UI + threading (the “ui_main.py” section)

### `RecordWorker(QThread)`
A background worker thread so recording doesn’t freeze the UI.

- Constructor takes:
  - `duration`, `out_path`, and optional `input_device_index`.
- `run()` calls `record_clip(...)`.
- Emits Qt signals:
  - `finished(path)` on success
  - `failed(error_message)` on exception

### `MainWindow(QWidget)`
The main GUI window.

#### Layout (three groups)
1. **Input**
   - Microphone dropdown (`QComboBox`) + Refresh button
   - Choose Audio File button (loads an existing file)
   - Clear button (stop using selected file, fall back to last recording)
   - Label that shows current input selection

2. **Recording**
   - Duration spin box (1–30 seconds, default 5)
   - Record button (records to `last_recording.wav`)

3. **Analysis**
   - Analyze button
   - Pitch label (shows result)
   - Status label (user-facing messages)

#### State variables
- `self.last_path`: path to `last_recording.wav` stored next to the script (stable relative location).
- `self.current_input_path`: if set, analysis uses this file instead of the recording.
- `self._device_map`: maps combo box indices to actual `sounddevice` device indices (or `None` for system default).
- `self.record_thread`: holds the active `RecordWorker`.

#### Key methods
- `refresh_devices()`: repopulates device dropdown; includes “System Default” option.
- `_selected_input_device_index()`: returns the selected device index (or `None`).
- `_refresh_analyze_enabled()`: enables Analyze if either:
  - a file is selected, or
  - `last_recording.wav` exists.
- `_display_input_path()`: updates the input label + enables/disables Clear button.
- `choose_audio_file()`: opens file dialog, sets `current_input_path`, updates UI.
- `clear_selected_file()`: clears `current_input_path`.
- `start_recording()`: disables buttons, starts `RecordWorker` thread.
- `on_record_finished(path)`: updates status, re-enables controls.
- `on_record_failed(message)`: shows an improved hint if failure seems device-related.
- `analyze_current_input()`:
  - decides which file to analyze (`current_input_path` or `last_path`)
  - loads audio (`load_audio`)
  - computes `avg_pitch` (`estimate_average_pitch`)
  - updates pitch label and status label

---

## 5) Entrypoint

At the bottom:
- Creates a `QApplication`
- Instantiates and shows `MainWindow`
- Runs `app.exec()` and exits with its return code

---

## How to use (runtime behavior)
1. Pick a microphone from the dropdown (or keep “System Default”).
2. Click **Record** to create `last_recording.wav`.
3. Click **Analyze** to compute and display the median pitch in Hz.
4. Alternatively, click **Choose Audio File...** to analyze a pre-existing file.
5. Use **Clear** to stop using the selected file and revert to analyzing the last recording.

---

## Notes / Limitations
- pitch detection is limited to 50–500 Hz and skips near-silent frames, so very quiet recordings may result in “not detected”.
- MP3 support depends on how `soundfile/libsndfile` is installed on the system; WAV/FLAC/OGG are typically safest.
- recording is mono (1 channel) and stored in float32 WAV.
