# Voice Trainer — Prototype (`V-T.py`)

A small PySide6 (Qt) desktop GUI app that can **record a short mono clip** from a selected microphone (or load an existing audio file), then estimate the speaker’s **pitch** (fundamental frequency) and display an **average pitch (median) in Hz**.

---

## Data storage (where + format)

- The prototype does not maintain a structured “entries” database.
- It writes/uses a working recording file:
  - `last_recording.wav` stored next to the script (stable relative path).
- You can also analyze any user-selected audio file path (no copy is required).

Audio format notes:
- Recording is mono, `float32`, typically at `44100` Hz.

---

## Analysis output schema (what gets computed)

Pitch analysis produces:
- Pitch track: an array/list of pitch estimates (Hz) across frames
- Average pitch: a single number (Hz) computed as the **median** of valid pitch values

Conceptual output example:

```json
{
  "input_path": "path/to/audio.wav",
  "sample_rate": 44100,
  "pitch_track_hz": [220.1, 219.8, 221.0],
  "average_pitch_hz": 220.1
}
```

Rules/filters:
- Skips near-silent frames.
- Keeps only finite pitch values.
- Keeps only pitches in ~human-voice range (50–500 Hz).

---

## UI: what the user does

### Main window
1. Choose a **Microphone** (or keep “System Default”), optionally click **Refresh** to rescan devices.
2. Either:
   - Click **Record** to create/update `last_recording.wav`, or
   - Click **Choose Audio File...** to select an existing file for analysis.
3. Click **Analyze**:
   - Uses the selected file if set, otherwise uses `last_recording.wav`.
4. Optional: click **Clear** to stop using the selected file and revert to the last recording.

The Analyze button is enabled only when:
- a file is selected, or
- `last_recording.wav` exists.

---

## Key components (how it’s built)

### Audio utilities (recording + loading)
- `sounddevice` for recording
- `soundfile` for reading/writing
- Device listing filters to input-capable devices (`max_input_channels > 0`)
- Default-device validation provides clearer errors when no input device is usable

### Pitch analysis
- `aubio.pitch("yin", ...)` (YIN algorithm)
- Frame-based analysis with hop size (default 512)
- Median of valid pitches is used as “average” (robust to outliers)

### UI threading
- Recording runs in a `QThread` worker so the GUI remains responsive.
- Worker emits success/failure signals; failures provide a device-related hint when relevant.

---

## Run

- Requires: Python 3.x, PySide6, numpy, sounddevice, soundfile, aubio
- Run from source: `py .\V-T.py`

---

## Notes / limitations

- Very quiet recordings may result in “pitch not detected” due to silence filtering.
- MP3 support depends on your `libsndfile`/`soundfile` build; WAV/FLAC/OGG are typically safest.
- Recording is mono and stored as float32 WAV.
