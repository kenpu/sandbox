"""Speech-to-text services: audio devices, microphone capture, voice activity,
and the `STT` interface. Engines live in submodules, like the TTS engines;
there is one: `transformers_whisper.TransformersWhisper`.
"""

import itertools
import math
import queue
import time
import unicodedata
import warnings
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from multimodal_ai.services.types import (
    Block,
    Device,
    HeardWord,
    StreamConfig,
    Transcript,
    Utterance,
    VadConfig,
    VadEvent,
)


class STT(ABC):
    """What every speech-to-text engine provides. See `TTS` for how ABCs work."""

    samplerate = 16000  # every engine takes 16 kHz mono float32, as whisper does

    @abstractmethod
    def initialize(self, model: str = "small.en", device: str | None = None) -> None:
        """Load `model` (e.g. "tiny.en", "small.en", "large-v3") onto `device`
        ("cuda" or "cpu"; None picks the GPU when the engine can use one).
        May be slow: the weights download on first use. Call once."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> list[HeardWord]:
        """Transcribe audio of any length into timed words."""


def load(model: str = "small.en", device: str | None = None) -> STT:
    """Create and initialize the STT engine."""
    # Imported here, not at the top: it pulls in torch and transformers (slow).
    from multimodal_ai.services.stt.transformers_whisper import TransformersWhisper

    stt = TransformersWhisper()
    stt.initialize(model, device)
    return stt


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


def transcribe(model: STT, utterance: Utterance) -> Transcript:
    """Transcribe an utterance; the result keeps the utterance's id and timing."""
    t0 = time.perf_counter()
    words = model.transcribe(utterance.audio)
    return Transcript(
        utterance_id=utterance.id,
        start=utterance.start,
        duration=utterance.duration,
        text="".join(w.word for w in words).strip(),
        transcribe_seconds=time.perf_counter() - t0,
        words=words,
    )
