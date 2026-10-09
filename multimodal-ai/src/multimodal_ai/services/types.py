"""Shared data types (pydantic models) used across services and CLI apps.

Why pydantic?
- A model is a class whose annotated attributes become validated fields.
  `Device(index="3", ...)` coerces "3" -> 3; `Device(index="x", ...)` raises
  a ValidationError. So bad data fails loudly at the boundary.
- `model.model_dump()` turns a model into plain dicts/lists/scalars, which is
  what we feed to `yaml.safe_dump` for scripting output (see yamlio.py).
- `Model.model_validate(dict)` goes the other way, e.g. after `yaml.safe_load`.
"""

from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, computed_field


class Device(BaseModel):
    """One PortAudio device, as reported by `sounddevice.query_devices()`."""

    index: int  # the number you pass as `device=` to sounddevice
    name: str
    hostapi: str  # e.g. "ALSA"; sounddevice gives an index, we store the name
    inputs: int  # max input channels (0 => output-only device)
    outputs: int  # max output channels (0 => input-only device)
    samplerate: float  # the device's default sample rate in Hz
    default: bool  # True if it is the default input or output device


class StreamConfig(BaseModel):
    """Parameters for opening an audio input stream.

    Silero VAD only accepts mono 16 kHz audio in chunks of exactly 512
    samples (32 ms), so every field is pinned with `Literal`: pydantic
    rejects any other value, e.g. `StreamConfig(samplerate=8000)` raises
    ValidationError. Just use `StreamConfig()`.
    """

    samplerate: Literal[16000] = 16000  # Hz
    blocksize: Literal[512] = 512  # samples per callback
    channels: Literal[1] = 1  # mono

    # A @property is computed, not a field: it is not validated or dumped.
    @property
    def block_duration(self) -> float:
        """Seconds of audio per block (0.032 s)."""
        return self.blocksize / self.samplerate


class VadConfig(BaseModel):
    """Settings for silero-vad's `VADIterator`.

    `Field(...)` adds constraints on top of the type: here pydantic rejects a
    threshold outside [0, 1] and negative durations.
    """

    # Silero outputs a speech probability per 512-sample chunk. Speech starts
    # when it rises to >= threshold, and ends when it stays below
    # threshold - 0.15 for min_silence_duration_ms.
    threshold: float = Field(0.5, ge=0, le=1)
    min_silence_duration_ms: int = Field(300, ge=0)
    speech_pad_ms: int = Field(100, ge=0)  # widen each segment on both sides


class VadEvent(BaseModel):
    """A speech segment boundary reported by `VADIterator`."""

    kind: Literal["start", "end"]  # VADIterator returns {"start": n} or {"end": n}
    sample: int  # n: offset in samples since the stream started (padding applied)

    # @computed_field is a @property that pydantic *does* include in
    # model_dump(), so `seconds` shows up in the YAML output.
    @computed_field
    @property
    def seconds(self) -> float:
        return self.sample / 16000


class Block(BaseModel):
    """One block of captured audio plus its timing info.

    Produced in the PortAudio callback, consumed from a queue elsewhere.
    """

    # pydantic only knows how to validate standard types. To hold a numpy
    # array we opt in to "arbitrary types": pydantic then just checks
    # isinstance(value, np.ndarray) and does no conversion.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: int  # sequence number, 0, 1, 2, ... in capture order
    adc_time: float  # stream time (s) when the first sample hit the ADC
    current_time: float  # stream time (s) when the callback was invoked
    status: str  # "" normally; e.g. "input overflow" if samples were dropped
    indata: np.ndarray  # mono samples: shape (512,), dtype float32 in [-1, 1]

    # Filled in later by the consumer, if VAD is on. Pydantic models are
    # mutable: `block.event = ...` works (it is not re-validated by default).
    event: VadEvent | None = None


class Transcript(BaseModel):
    """Whisper's transcription of one utterance (VAD start .. end)."""

    start: float  # stream time (s) of the first sample, incl. pre-speech buffer
    duration: float  # seconds of audio sent to whisper
    text: str  # all segment texts joined: the part we display

    # Everything else whisper returned, kept for later. faster-whisper gives
    # dataclasses (Segment, TranscriptionInfo); we store them as plain dicts
    # via dataclasses.asdict, so this module needn't import faster_whisper
    # (slow). `Any` means pydantic accepts the values without checking them.
    # Each segment has "words": a list of {start, end, word, probability}.
    # Word times are seconds from the start of *this* audio; add `start` to
    # place them on the stream clock (the same clock as VadEvent.seconds).
    segments: list[dict[str, Any]]
    info: dict[str, Any]


class Voice(BaseModel):
    """A Kokoro voice. Its name encodes language and gender: "af_heart" is
    American English (a), female (f), named heart."""

    name: str
    lang_code: str  # first letter; Kokoro's pipeline must be loaded with it
    language: str
    gender: Literal["female", "male"]
