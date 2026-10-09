"""Whisper on torch via Hugging Face transformers: the default STT engine.

It runs on the GPU wherever torch does (including ARM, where faster-whisper's
PyPI CTranslate2 has no CUDA). On the GB10 it is as fast as faster-whisper on
a CUDA build of CTranslate2; see the README's benchmark.
"""

import itertools
import math

import numpy as np

from multimodal_ai.services.stt import STT, normalize
from multimodal_ai.services.types import HeardWord


class TransformersWhisper(STT):
    """OpenAI Whisper on torch (Hugging Face transformers), with word timestamps.

    `model` may also be a full Hugging Face id, e.g. "distil-whisper/distil-small.en".
    """

    window = 30 * STT.samplerate  # whisper hears at most 30 s at a time
    seconds_per_frame = 0.02  # one encoder frame = 20 ms of audio

    def initialize(self, model: str = "small.en", device: str | None = None) -> None:
        # Imported here, not at the top: torch and transformers are slow to import.
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        from transformers.utils import logging

        # Quiet the "Loading weights" bar and generate()'s deprecation notices,
        # which would scribble over the listen UI.
        logging.disable_progress_bar()
        logging.set_verbosity_error()
        name = model if "/" in model else f"openai/whisper-{model}"
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
        words = []
        for a, b in itertools.pairwise(bounds):
            # The word ends where its trailing punctuation starts: "rain." ends
            # with "rain", not after the pause the "." gets aligned into.
            end = b
            while end - 1 > a and normalize(pieces[end - 1]) == "":
                end -= 1
            words.append(
                HeardWord(
                    word=tokenizer.decode(tokens[a:b]),
                    start=float(times[a]),
                    end=float(times[end]),
                )
            )
        return words

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
