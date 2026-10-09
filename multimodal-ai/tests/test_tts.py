import numpy as np
import pytest

from multimodal_ai.services import stt
from multimodal_ai.services.tts import TTS
from multimodal_ai.services.tts.chatterbox import ChatterboxTTS
from multimodal_ai.services.tts.kokoro import KokoroTTS


def test_tts_is_abstract():
    with pytest.raises(TypeError):
        TTS()


# The same test runs once per engine: that is the point of the interface.
@pytest.mark.parametrize("engine_class", [KokoroTTS, ChatterboxTTS])
def test_roundtrip_through_whisper(engine_class):
    engine: TTS = engine_class()
    engine.initialize()
    audio = engine.synthesize("Hello world, this is a test.")
    assert audio.dtype == np.float32 and len(audio) > engine.samplerate  # > 1 s

    # Resample to 16 kHz for whisper (linear interpolation is fine for a test).
    t16 = np.arange(0, len(audio), engine.samplerate / 16000)
    audio16 = np.interp(t16, np.arange(len(audio)), audio).astype(np.float32)
    segments, _ = stt.load_whisper().transcribe(audio16, language="en", beam_size=1)
    text = "".join(s.text for s in segments).lower()
    assert "hello world" in text and "test" in text


def test_kokoro_word_timings():
    engine = KokoroTTS()
    engine.initialize()
    text = "Hello there, the weather is 10 degrees today!"
    audio, words = engine.synthesize_timed(text)
    assert "".join(w.text + w.whitespace for w in words) == text
    starts = [w.start for w in words]
    assert all(s is not None for s in starts) and starts == sorted(starts)
    assert words[-1].end <= len(audio) / engine.samplerate
