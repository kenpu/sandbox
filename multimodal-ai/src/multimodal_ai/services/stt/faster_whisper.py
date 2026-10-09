"""Whisper on CTranslate2 via faster-whisper: an optional STT engine.

Install with `uv sync --extra faster-whisper`. On ARM Linux (the DGX Spark)
that installs a CTranslate2 built with CUDA from ~/src (see ~/src/README.md):
the PyPI wheels for ARM are CPU-only. Elsewhere it is the PyPI wheel, which
on x86 needs CUDA 12's cuBLAS (see `_preload_cublas12`).
"""

import ctypes
from pathlib import Path

import numpy as np

from multimodal_ai.services.stt import STT
from multimodal_ai.services.types import HeardWord


def _preload_cublas12() -> None:
    """Make CUDA 12's cuBLAS visible to CTranslate2, if it is installed.

    PyPI's x86 CTranslate2 is built against CUDA 12 and dlopens libcublas.so.12,
    but torch brought CUDA 13. The `nvidia-cublas-cu12` wheel (x86 only, in the
    faster-whisper extra) supplies it, off the loader path; loading it by full
    path with RTLD_GLOBAL lets CTranslate2's dlopen find it. Our ARM build links
    CUDA 13 itself, so there this finds nothing and does nothing.
    """
    try:
        import nvidia.cublas
    except ImportError:
        return
    for root in nvidia.cublas.__path__:
        for lib in ("libcublasLt.so.12", "libcublas.so.12"):
            if (path := Path(root) / "lib" / lib).exists():
                ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)


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
        _preload_cublas12()

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
