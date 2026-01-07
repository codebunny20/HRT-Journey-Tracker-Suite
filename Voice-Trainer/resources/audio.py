import sounddevice as sd
import soundfile as sf
import numpy as np
import os

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