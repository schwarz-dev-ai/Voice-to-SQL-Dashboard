"""Speech-to-text using a local faster-whisper model.

Anthropic's API has no audio endpoint, so transcription runs on this machine -
the recording never leaves it and no second API key is needed.

The model is loaded lazily on first use and then held in memory, because loading
it costs ~10 seconds; Streamlit reruns the script on every interaction, so
reloading per run would make the UI crawl.
"""

from __future__ import annotations

import importlib.util
import io
import os
import threading
import wave

import numpy as np

# "base" balances accuracy and speed on CPU; "tiny" is faster, "small"/"medium" are
# more accurate. Override with WHISPER_MODEL.
DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "base")
_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

# Below this RMS (on the 16-bit scale) a recording is treated as silence. A muted
# or unselected microphone yields exactly 0; room tone sits well above this.
_SILENCE_RMS = 20.0

_model = None
_model_lock = threading.Lock()


class SilentAudioError(RuntimeError):
    """The recording contains no audible signal.

    This is a *microphone* problem, not a recognition failure, and it is worth
    saying so: Whisper does not return an empty string on silence, it invents
    text - most often "you" or "Thank you." - which reads like a broken app.
    """


def is_available() -> bool:
    """True when faster-whisper is installed, without importing it."""
    return importlib.util.find_spec("faster_whisper") is not None


def _load_model():
    """Load the model once, on first use."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # re-check: another thread may have loaded it
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:  # pragma: no cover - depends on environment
                    raise RuntimeError(
                        "faster-whisper is not installed. Run: pip install faster-whisper"
                    ) from exc
                _model = WhisperModel(
                    DEFAULT_MODEL, device=_DEVICE, compute_type=_COMPUTE_TYPE
                )
    return _model


def signal_rms(audio: bytes) -> float | None:
    """Return the RMS level of a WAV clip, or ``None`` if it cannot be read.

    ``None`` means "unknown" (not a WAV we understand) - the caller should go on
    and let the model try, rather than reporting a false silence.
    """
    try:
        with wave.open(io.BytesIO(audio), "rb") as handle:
            width = handle.getsampwidth()
            frames = handle.readframes(handle.getnframes())
    except (wave.Error, EOFError):
        return None

    if not frames:
        return 0.0

    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(width)
    if dtype is None:
        return None

    samples = np.frombuffer(frames, dtype=dtype).astype(np.float64)
    if width == 1:  # 8-bit WAV is unsigned, centred on 128
        samples -= 128.0
    return float(np.sqrt(np.mean(samples**2)))


def transcribe(audio: bytes | io.IOBase, language: str | None = None) -> str:
    """Transcribe recorded audio (WAV bytes or a file-like object) to plain text.

    ``language`` is a spoken-language code such as ``"en"`` or ``"de"``. ``None``
    asks the model to detect it, which is unreliable on short clips - prefer
    passing an explicit code.

    Returns an empty string when the clip holds no recognisable speech. Raises
    :class:`SilentAudioError` when there is no signal at all, so a dead
    microphone is reported as such instead of surfacing Whisper's invention.
    """
    data = audio if isinstance(audio, bytes) else audio.read()
    if not data:
        raise SilentAudioError("No audio was recorded.")

    level = signal_rms(data)
    if level is not None and level < _SILENCE_RMS:
        raise SilentAudioError(
            f"The recording is silent (level {level:.1f}). Check that the correct "
            "microphone is selected and not muted."
        )

    model = _load_model()
    # `segments` is a generator - the transcription work happens as it is consumed.
    segments, _info = model.transcribe(
        io.BytesIO(data),
        language=language,
        beam_size=5,
        # VAD drops non-speech before decoding, which is the main defence against
        # Whisper hallucinating sentences out of background noise.
        vad_filter=True,
        condition_on_previous_text=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
