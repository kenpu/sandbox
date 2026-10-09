import numpy as np
import pytest

from multimodal_ai.services import stt
from multimodal_ai.services.tts.kokoro import KokoroTTS
from multimodal_ai.services.types import Block


@pytest.fixture(scope="module")
def speech() -> np.ndarray:
    """Kokoro speech, resampled to 16 kHz for whisper."""
    engine = KokoroTTS()
    engine.initialize()
    audio = engine.synthesize("The quick brown fox jumps over the lazy dog.")
    t16 = np.arange(0, len(audio), engine.samplerate / 16000)
    return np.interp(t16, np.arange(len(audio)), audio).astype(np.float32)


def test_stt_is_abstract():
    with pytest.raises(TypeError):
        stt.STT()


def test_word_timings(speech):
    words = stt.load("tiny.en").transcribe(speech)
    text = "".join(w.word for w in words).strip().lower()
    assert text.startswith("the quick brown fox")
    starts = [w.start for w in words]
    assert starts == sorted(starts)
    assert all(w.start <= w.end for w in words)
    assert words[-1].end <= len(speech) / 16000 + 0.1


def test_transcribe_keeps_utterance_timing():
    # Silence: we check structure, not text.
    blocks = [
        Block(
            index=i,
            adc_time=0,
            current_time=0,
            status="",
            indata=np.zeros(512, np.float32),
        )
        for i in range(10, 41)
    ]
    utterance = stt.make_utterance(7, blocks)
    assert (utterance.first_block, utterance.last_block) == (10, 40)
    t = stt.transcribe(stt.load("tiny.en", device="cpu"), utterance)
    assert t.utterance_id == 7
    assert t.start == 10 * 0.032
    assert t.duration == 31 * 0.032
    assert t.text == "".join(w.word for w in t.words).strip()
