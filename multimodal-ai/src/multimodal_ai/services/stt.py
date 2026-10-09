"""Speech-to-text services: audio devices, microphone capture, voice activity."""

import itertools
import math
import queue
import time
import unicodedata
import warnings
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


class Whisper:
    """OpenAI Whisper on torch (Hugging Face transformers), with word timestamps.

    `name` is e.g. "tiny.en", "base.en", "small.en", "medium.en", "large-v3",
    or a full Hugging Face id. The weights download on first use.

    Why not faster-whisper? It runs on CTranslate2, whose ARM (aarch64) wheels
    have no CUDA; torch does, so this runs on the GPU everywhere torch does.
    """

    samplerate = 16000  # what whisper expects
    window = 30 * samplerate  # whisper hears at most 30 s at a time
    seconds_per_frame = 0.02  # one encoder frame = 20 ms of audio

    def __init__(self, name: str = "small.en", device: str | None = None) -> None:
        # Imported here, not at the top: torch and transformers are slow to import.
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        from transformers.utils import logging

        # Quiet the "Loading weights" bar and generate()'s deprecation notices,
        # which would scribble over the listen UI.
        logging.disable_progress_bar()
        logging.set_verbosity_error()
        if "/" not in name:
            name = f"openai/whisper-{name}"
        self.torch = torch
        self.name = name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.processor = WhisperProcessor.from_pretrained(name)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            name, dtype=self.dtype
        )
        self.model.to(self.device).eval()

        config = self.model.generation_config
        self.multilingual = config.is_multilingual
        tokenizer = self.processor.tokenizer
        if self.multilingual:
            tokenizer.set_prefix_tokens(language="en", task="transcribe")
        # The prompt the decoder starts from, e.g. <|startoftranscript|><|notimestamps|>.
        self.prefix = tokenizer.prefix_tokens
        self.eot = tokenizer.eos_token_id
        # Which cross-attention heads (layer, head) follow the audio in time.
        self.alignment_heads = config.alignment_heads

    def transcribe(self, audio: np.ndarray) -> list[HeardWord]:
        """Transcribe 16 kHz mono float32 audio of any length into timed words."""
        words = []
        for offset in range(0, len(audio), self.window):
            for w in self._transcribe_window(audio[offset : offset + self.window]):
                w.start += offset / self.samplerate
                w.end += offset / self.samplerate
                words.append(w)
        return words

    def _transcribe_window(self, audio: np.ndarray) -> list[HeardWord]:
        torch = self.torch
        features = self.processor(
            audio, sampling_rate=self.samplerate, return_tensors="pt"
        ).input_features.to(self.device, self.dtype)
        with torch.inference_mode():
            # Run the encoder once; decoding and alignment both reuse its output.
            encoded = self.model.model.encoder(features)
            kwargs = {"language": "en"} if self.multilingual else {}
            tokens = self.model.generate(
                encoder_outputs=encoded, num_beams=1, **kwargs
            )[0]
            tokens = [t for t in tokens.tolist() if t < self.eot]  # drop special tokens
            if not tokens:
                return []
            times = self._align(encoded, tokens, num_frames=math.ceil(len(audio) / 320))

        # A token starting with a space starts a new word; others (",", "n't")
        # attach to the previous word.
        tokenizer = self.processor.tokenizer
        pieces = [tokenizer.decode([t]) for t in tokens]
        starts = [i for i, p in enumerate(pieces) if i == 0 or p.startswith(" ")]
        bounds = [*starts, len(tokens)]
        return [
            HeardWord(
                word=tokenizer.decode(tokens[a:b]),
                start=float(times[a]),
                end=float(times[b]),
            )
            for a, b in itertools.pairwise(bounds)
        ]

    def _align(self, encoded, tokens: list[int], num_frames: int) -> np.ndarray:
        """When each token starts, in seconds, plus when the text ends.

        Following OpenAI's whisper/timing.py: feed the decoded tokens back
        through the decoder once, read the alignment heads' cross-attention
        (which audio frame each token attends to), and find the best monotonic
        token-to-frame path with dynamic time warping.
        """
        torch = self.torch
        seq = torch.tensor([[*self.prefix, *tokens, self.eot]], device=self.device)
        # The fast attention kernel (sdpa) doesn't return attention weights;
        # switch to the plain one just for this pass.
        self.model.set_attn_implementation("eager")
        try:
            out = self.model(
                encoder_outputs=encoded, decoder_input_ids=seq, output_attentions=True
            )
        finally:
            self.model.set_attn_implementation("sdpa")
        # Row i is the step that predicts token i (the last row predicts eot);
        # columns are encoder frames, cropped to the real audio (the rest is padding).
        n = len(self.prefix)
        w = torch.stack(
            [
                out.cross_attentions[layer][0, head]
                for layer, head in self.alignment_heads
            ]
        )
        w = w[:, n - 1 : -1, :num_frames].float()
        # Standardize each frame over tokens, smooth along time (median of 7), average heads.
        w = (w - w.mean(-2, keepdim=True)) / w.std(-2, keepdim=True, unbiased=False)
        if w.shape[-1] > 3:
            w = torch.nn.functional.pad(w, (3, 3), mode="reflect")
            w = w.unfold(-1, 7, 1).median(-1).values
        matrix = w.mean(0).cpu().numpy()
        token_index, frame_index = _dtw(-matrix)
        # Each token starts at the frame where the path first reaches it.
        first = np.diff(token_index, prepend=-1).astype(bool)
        return frame_index[first] * self.seconds_per_frame


def _dtw(cost: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cheapest monotonic path through `cost` (tokens x frames), from the top
    left to the bottom right, moving right, down, or diagonally. Returns the
    path's row and column indices."""
    n, m = cost.shape
    acc = np.full((n + 1, m + 1), np.inf)
    acc[0, 0] = 0
    for i in range(1, n + 1):
        # The best of "diagonal" and "down" for a whole row at once; "right"
        # depends on the cell just filled, so that part stays a loop.
        above = np.minimum(acc[i - 1, :-1], acc[i - 1, 1:])
        row = acc[i]
        for j in range(1, m + 1):
            row[j] = cost[i - 1, j - 1] + min(above[j - 1], row[j - 1])
    rows, cols = [], []
    i, j = n, m
    while i > 0 and j > 0:
        rows.append(i - 1)
        cols.append(j - 1)
        step = np.argmin([acc[i - 1, j - 1], acc[i - 1, j], acc[i, j - 1]])
        i, j = (i - 1, j - 1) if step == 0 else (i - 1, j) if step == 1 else (i, j - 1)
    return np.array(rows[::-1]), np.array(cols[::-1])


def load_whisper(name: str = "small.en", device: str | None = None) -> Whisper:
    """Load whisper; `device` defaults to "cuda" when torch sees a GPU, else "cpu"."""
    return Whisper(name, device)


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


def transcribe(model: Whisper, utterance: Utterance) -> Transcript:
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
