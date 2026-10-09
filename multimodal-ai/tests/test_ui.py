import time

import numpy as np

from multimodal_ai.services.bus import Bus
from multimodal_ai.services.types import Speech, SpokenWord
from multimodal_ai.ui import RichUI


def speech() -> Speech:
    words = [
        SpokenWord(text="Hello", whitespace=" ", start=0.2, end=0.6),
        SpokenWord(text="there", whitespace="", start=0.6, end=0.9),
        SpokenWord(text="!", whitespace="", start=0.9, end=1.0),
    ]
    return Speech(
        utterance_id=0,
        text="Hello there!",
        voice="af_alloy",
        samplerate=24000,
        audio=np.zeros(24000, np.float32),
        duration=1.0,
        synth_seconds=0.0,
        words=words,
    )


def styles_at(ui: RichUI, t: float) -> dict[str, str]:
    ui.play_started = time.monotonic() - t
    text = ui.karaoke()
    styled = {text.plain[s.start : s.end]: str(s.style) for s in text.spans}
    # Rich keeps no span for an empty style, so unstyled words are absent.
    return {w: styled.get(w, "") for w in ("Hello", "there", "!")}


def test_karaoke_highlights_the_word_being_spoken():
    ui = RichUI(Bus(), vad=True, stt=True, tts=True)
    ui.now_playing, ui.play_started = speech(), time.monotonic()
    assert ui.karaoke().plain == "Hello there!"
    assert styles_at(ui, 0.4) == {
        "Hello": "bold black on yellow",
        "there": "dim",
        "!": "dim",
    }
    assert styles_at(ui, 0.7) == {
        "Hello": "",
        "there": "bold black on yellow",
        "!": "dim",
    }


def test_no_karaoke_when_idle_or_finished():
    ui = RichUI(Bus(), vad=True, stt=True, tts=True)
    assert ui.karaoke() is None  # nothing playing
    ui.now_playing, ui.play_started = speech(), time.monotonic() - 2.0
    assert ui.karaoke() is None  # playback over
