"""Text-to-speech: the `TTS` interface. Implementations live in submodules,
e.g. `multimodal_ai.services.tts.kokoro.KokoroTTS`.

An abstract base class (ABC) states what every TTS engine must provide.
Methods marked @abstractmethod have no body here; a subclass must override
them all, or Python refuses to instantiate it (TypeError). Code that only
needs "some TTS engine" types its variable as `TTS` and works with any of them.
"""

from abc import ABC, abstractmethod

import numpy as np

from multimodal_ai.services.types import SpokenWord


class TTS(ABC):
    # Sample rate (Hz) of the audio returned by `synthesize`. A plain class
    # attribute: each implementation sets its own value.
    samplerate: int

    @abstractmethod
    def initialize(self) -> None:
        """Load the model and get it ready to synthesize. May be slow.

        Implementations add their own keyword options (voice, language, ...).
        Call once, before `synthesize`.
        """

    @abstractmethod
    def synthesize(self, text: str) -> np.ndarray:
        """Speak `text`; return mono float32 samples at `self.samplerate`."""

    # Not abstract: a default that engines may override. Engines that know
    # when each word is spoken (kokoro) return timings; others return none.
    def synthesize_timed(self, text: str) -> tuple[np.ndarray, list[SpokenWord]]:
        """Like `synthesize`, plus the timing of each word in the audio."""
        return self.synthesize(text), []
