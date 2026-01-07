import aubio
import numpy as np

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