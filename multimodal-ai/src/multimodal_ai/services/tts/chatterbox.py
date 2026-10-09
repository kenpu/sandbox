"""Chatterbox TTS engine by Resemble AI (https://huggingface.co/ResembleAI/chatterbox).

English only. Its standout feature is zero-shot voice cloning: give it a few
seconds of someone speaking (a WAV file) and it speaks in that voice. Every
output carries an inaudible Perth watermark marking it as AI-generated.
"""

import io
import warnings
from contextlib import contextmanager, redirect_stderr, redirect_stdout

import numpy as np

from multimodal_ai.services.tts import TTS


@contextmanager
def _quiet():
    """Silence chatterbox's chatter: prints to stdout (which would corrupt our
    YAML output), tqdm progress bars on stderr, and deprecation warnings.
    Exceptions still propagate normally."""
    with (
        redirect_stdout(io.StringIO()),
        redirect_stderr(io.StringIO()),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore")
        yield


class ChatterboxTTS(TTS):
    samplerate = 24000  # Chatterbox's S3Gen vocoder outputs 24 kHz

    def initialize(
        self,
        voice: str | None = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        device: str = "cuda",
    ) -> None:
        """Load the model (about 3.2 GB, downloaded on first use).

        voice: path to a reference WAV to clone; None uses the built-in voice.
        exaggeration: emotional intensity; 0.5 is neutral, higher is livelier.
        cfg_weight: how closely to follow the reference voice's style/pacing;
          lower values give slower, more deliberate speech.
        """
        # Imported here, not at the top: it pulls in torch, diffusers, etc.
        # Aliased because our class has the same name.
        from chatterbox.tts import ChatterboxTTS as Model

        with _quiet():
            self.model = Model.from_pretrained(device=device)
            if voice:
                # Extract the speaker embedding once, instead of on every call.
                self.model.prepare_conditionals(voice, exaggeration=exaggeration)
        self.exaggeration, self.cfg_weight = exaggeration, cfg_weight

        # The first generation is very slow (~10 s: GPU kernel setup), so do a
        # tiny one now; later synthesize() calls then measure a warm model.
        self.synthesize("Hi.")

    def synthesize(self, text: str) -> np.ndarray:
        with _quiet():
            wav = self.model.generate(
                text, exaggeration=self.exaggeration, cfg_weight=self.cfg_weight
            )
        # generate() returns a torch tensor of shape (1, samples).
        return wav.squeeze(0).cpu().numpy().astype(np.float32)
