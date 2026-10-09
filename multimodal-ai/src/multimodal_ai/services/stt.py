"""Speech-to-text services: audio devices, microphone capture, voice activity."""

import ctypes
import itertools
import math
import queue
import time
import unicodedata
import warnings
from collections import deque
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import numpy as np
import sounddevice as sd

from multimodal_ai.services.types import (
    Block,
    Device,
    StreamConfig,
    Transcript,
    Utterance,
    VadConfig,
    VadEvent,
)


def query_devices() -> list[Device]:
    default_in, default_out = sd.default.device
    return [
        Device(
            index=d["index"],
            name=d["name"],
            hostapi=sd.query_hostapis(d["hostapi"])["name"],
            inputs=d["max_input_channels"],
            outputs=d["max_output_channels"],
            samplerate=d["default_samplerate"],
            default=d["index"] in (default_in, default_out),
        )
        for d in sd.query_devices()
    ]


def recorder(q: queue.Queue[np.ndarray], samplerate: int) -> sd.InputStream:
    """Create (not start) a plain mono input stream at any sample rate.

    Unlike `input_stream` (fixed at 16 kHz / 512 samples for VAD), this just
    puts each block's samples on `q`; PortAudio picks the block size.
    """

    def callback(indata, frames, time_info, status):
        q.put(indata[:, 0].copy())  # copy: PortAudio reuses the buffer

    return sd.InputStream(samplerate=samplerate, channels=1, callback=callback)


def input_stream(q: queue.Queue[Block], config: StreamConfig) -> sd.InputStream:
    """Create (not start) an input stream that puts each `Block` on `q`.

    Use it as a context manager: `with input_stream(q, cfg): ... q.get() ...`
    """
    counter = itertools.count()

    # Runs on PortAudio's audio thread: do minimal work, hand off via queue.
    def callback(indata, frames, time_info, status):
        q.put(
            Block(
                index=next(counter),
                adc_time=time_info.inputBufferAdcTime,
                current_time=time_info.currentTime,
                status=str(status),
                # indata is (frames, channels); take the one mono channel.
                # PortAudio reuses this buffer after we return, so copy it.
                indata=indata[:, 0].copy(),
            )
        )

    return sd.InputStream(
        samplerate=config.samplerate,
        channels=config.channels,
        blocksize=config.blocksize,
        callback=callback,
    )


def rms(indata: np.ndarray) -> float:
    """Root-mean-square level of the samples."""
    return float(np.sqrt(np.mean(indata**2)))


def vad_detector(config: VadConfig) -> Callable[[np.ndarray], VadEvent | None]:
    """Load silero-vad; return a function to call on each block's samples, in order.

    It returns a `VadEvent` when speech starts or ends, otherwise None. It is
    stateful (it tracks the current sample and whether speech is ongoing), so
    use one detector per stream.
    """
    # Imported here, not at the top: torch takes seconds to import, and
    # commands like `sound devices` shouldn't pay for it.
    import torch
    from silero_vad import VADIterator, load_silero_vad

    # silero-vad's loader uses torch.jit.load, which warns it is deprecated.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        model = load_silero_vad()
    iterator = VADIterator(
        model,
        threshold=config.threshold,
        sampling_rate=StreamConfig().samplerate,
        min_silence_duration_ms=config.min_silence_duration_ms,
        speech_pad_ms=config.speech_pad_ms,
    )

    def detect(indata: np.ndarray) -> VadEvent | None:
        result = iterator(torch.from_numpy(indata))  # None, {"start": n}, {"end": n}
        if result is None:
            return None
        ((kind, sample),) = result.items()
        return VadEvent(kind=kind, sample=sample)

    return detect


def load_whisper(
    name: str = "small.en", device: str = "cuda", compute_type: str = "float16"
):
    """Load a faster-whisper model (downloaded from Hugging Face on first use).

    `name` is e.g. "tiny.en", "base.en", "small.en", "medium.en", "large-v3".
    On CPU, use compute_type="int8".
    """
    if device == "cuda":
        # faster-whisper runs on CTranslate2, which is built against CUDA 12,
        # but torch brought CUDA 13. The `nvidia-cublas-cu12` wheel supplies
        # libcublas.so.12; it isn't on the loader path, so load it by full
        # path first (RTLD_GLOBAL makes it visible to CTranslate2's dlopen).
        import nvidia.cublas

        libdir = Path(nvidia.cublas.__path__[0]) / "lib"
        for lib in ("libcublasLt.so.12", "libcublas.so.12"):
            ctypes.CDLL(str(libdir / lib), mode=ctypes.RTLD_GLOBAL)

    from faster_whisper import WhisperModel

    return WhisperModel(name, device=device, compute_type=compute_type)


def speech_collector(pre_speech_ms: int = 300) -> Callable[[Block], list[Block] | None]:
    """Return a function to call on each block (after VAD set `block.event`).

    It returns the list of blocks making up one utterance when an `end` event
    arrives, otherwise None. The utterance is: up to `pre_speech_ms` of blocks
    before the `start` event (VAD may trigger late and clip the first sound),
    then every block from `start` through `end`.
    """
    # deque(maxlen=n) drops the oldest item when full: a ring buffer.
    pre: deque[Block] = deque(
        maxlen=math.ceil(pre_speech_ms / 1000 / StreamConfig().block_duration)
    )
    utterance: list[Block] | None = None  # None while not in speech

    def collect(b: Block) -> list[Block] | None:
        nonlocal utterance
        kind = b.event.kind if b.event else None
        if utterance is None:
            if kind == "start":
                utterance = [*pre, b]
                pre.clear()
            else:
                pre.append(b)
            return None
        utterance.append(b)
        if kind == "end":
            done, utterance = utterance, None
            return done
        return None

    return collect


def normalize(text: str) -> str:
    """Lowercase, drop all punctuation, trim: "Terminate." -> "terminate".

    Unicode categories starting with "P" are punctuation (. , ! ? … — " etc.).
    """
    kept = (c for c in text.lower() if not unicodedata.category(c).startswith("P"))
    return "".join(kept).strip()


def make_utterance(id: int, blocks: list[Block]) -> Utterance:
    """Join the blocks' samples into one Utterance."""
    config = StreamConfig()
    audio = np.concatenate([b.indata for b in blocks])
    return Utterance(
        id=id,
        first_block=blocks[0].index,
        last_block=blocks[-1].index,
        start=blocks[0].index * config.block_duration,
        duration=len(audio) / config.samplerate,
        audio=audio,
    )


def transcribe(model, utterance: Utterance) -> Transcript:
    """Transcribe an utterance; the result keeps the utterance's id and timing."""
    t0 = time.perf_counter()
    # word_timestamps=True: after decoding, whisper aligns each word to the
    # audio (cross-attention + dynamic time warping), filling Segment.words.
    segments, info = model.transcribe(
        utterance.audio,
        language="en",
        beam_size=1,
        vad_filter=False,
        word_timestamps=True,
    )
    # `segments` is a lazy generator: the decoding happens as we iterate it.
    seg_dicts = [asdict(s) for s in segments]
    return Transcript(
        utterance_id=utterance.id,
        start=utterance.start,
        duration=utterance.duration,
        text="".join(s["text"] for s in seg_dicts).strip(),
        transcribe_seconds=time.perf_counter() - t0,
        segments=seg_dicts,
        info=asdict(info),
    )
