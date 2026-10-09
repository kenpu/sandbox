"""Kokoro-82M TTS engine (https://huggingface.co/hexgrad/Kokoro-82M)."""

import warnings

import numpy as np

from multimodal_ai.services.tts import TTS
from multimodal_ai.services.types import Voice

REPO_ID = "hexgrad/Kokoro-82M"

# Kokoro lang_code -> language. Only "a" and "b" work out of the box here;
# "j" and "z" need extra misaki packages (misaki[ja], misaki[zh]), and the
# rest rely on espeak-ng alone, so quality varies.
LANGUAGES = {
    "a": "American English",
    "b": "British English",
    "e": "Spanish",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "j": "Japanese",
    "p": "Brazilian Portuguese",
    "z": "Mandarin Chinese",
}


def list_voices() -> list[Voice]:
    """List the voices in the Hugging Face repo (needs network)."""
    from huggingface_hub import list_repo_files

    names = sorted(
        f.removeprefix("voices/").removesuffix(".pt")
        for f in list_repo_files(REPO_ID)
        if f.startswith("voices/") and f.endswith(".pt")
    )
    return [
        Voice(
            name=n,
            lang_code=n[0],
            language=LANGUAGES.get(n[0], "unknown"),
            gender="female" if n[1] == "f" else "male",
        )
        for n in names
    ]


class KokoroTTS(TTS):
    """Kokoro pipeline = misaki (text -> phonemes, via spaCy + espeak-ng
    fallback) + the 82M-parameter Kokoro model (phonemes -> audio)."""

    samplerate = 24000  # Kokoro always outputs 24 kHz mono float32

    def initialize(
        self,
        lang_code: str = "a",
        voice: str = "af_heart",
        speed: float = 1.0,
        device: str = "cuda",
    ) -> None:
        """Load the pipeline (weights download from Hugging Face on first use).

        lang_code: a key of LANGUAGES; picks the text -> phoneme rules (accent).
        voice: picks the timbre, e.g. af_heart, am_michael, bf_emma, bm_george
          (<accent><gender>_<name>). Voice and lang_code can be mixed.
        """
        if lang_code not in LANGUAGES:
            raise ValueError(f"Unknown Kokoro lang_code {lang_code!r}")
        # Imported here, not at the top: torch and spaCy are slow to import.
        from kokoro import KPipeline

        # Kokoro's model code triggers harmless torch deprecation warnings.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            warnings.simplefilter("ignore", FutureWarning)
            self.pipeline = KPipeline(
                lang_code=lang_code, repo_id=REPO_ID, device=device
            )
        self.lang_code, self.voice, self.speed = lang_code, voice, speed

        # So later synthesize() calls measure a warm model: fetch the voice
        # file now, and run one tiny synthesis to absorb first-call GPU setup.
        self.pipeline.load_voice(voice)
        self.synthesize("Hi.")

    def synthesize(self, text: str) -> np.ndarray:
        # The pipeline splits long text into chunks and yields one result per
        # chunk; each has .graphemes (text), .phonemes, and .audio (a tensor).
        chunks = [
            r.audio.cpu().numpy()
            for r in self.pipeline(text, voice=self.voice, speed=self.speed)
        ]
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
