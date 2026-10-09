"""Whisper on CTranslate2 via faster-whisper: an optional STT engine.

Install with `uv sync --extra faster-whisper`. On ARM Linux (the DGX Spark)
that installs a CTranslate2 built with CUDA from ~/src (see ~/src/README.md):
the PyPI wheels for ARM are CPU-only. Elsewhere it is the PyPI wheel.
"""

import numpy as np

from multimodal_ai.services.stt import STT
from multimodal_ai.services.types import HeardWord


class FasterWhisper(STT):
    """faster-whisper (https://github.com/SYSTRAN/faster-whisper), with word timestamps."""

    def initialize(self, model: str = "small.en", device: str | None = None) -> None:
        # Imported here, not at the top: CTranslate2 is slow to load. This is
        # the installed `faster_whisper` package: an absolute import never
        # finds this module, despite the shared name.
        try:
            import ctranslate2
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "the faster-whisper engine is optional: uv sync --extra faster-whisper"
            ) from e

        self.device = device or (
            "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        )
        # float16 on the GPU; int8 on the CPU, where 4 threads beat all 20
        # cores (mixed big and little cores) by about 4.5x.
        self.model = WhisperModel(
            model,
            device=self.device,
            compute_type="float16" if self.device == "cuda" else "int8",
            cpu_threads=4,
        )

    def transcribe(self, audio: np.ndarray) -> list[HeardWord]:
        segments, _ = self.model.transcribe(
            audio,
            language="en",
            beam_size=1,
            vad_filter=False,  # our VAD already cut the utterance
            word_timestamps=True,
        )
        # `segments` is a lazy generator: the decoding happens as we iterate it.
        return [
            HeardWord(word=w.word, start=w.start, end=w.end)
            for s in segments
            for w in s.words or []
        ]
