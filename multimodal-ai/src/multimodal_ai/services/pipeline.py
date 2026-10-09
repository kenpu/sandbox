"""The components of `main sound listen`, each running in its own thread:

    PortAudio callback --(private queue)--> listen --Block------------> UI
                                              |----Utterance--> stt
                                              |                  |--Transcript--> UI, tts
                                              |                                    |--Speech--> UI (plays it)
                                              <--------------------Playback-------------------- UI

Long steps (whisper, TTS) run in their own threads, so listen keeps up with
the audio and the UI stays responsive whatever their latency. Short,
non-blocking steps are fused into one thread with no queues in between
(listen does RMS, muting, VAD and utterance collection per block).
New stages (e.g. an LLM between stt and tts) are new Components that
consume one message type and publish another.
"""

import itertools
import queue
import time

from multimodal_ai.services import stt
from multimodal_ai.services.bus import Bus, Component
from multimodal_ai.services.tts import kokoro
from multimodal_ai.services.types import (
    Playback,
    Shutdown,
    Speech,
    StreamConfig,
    Transcript,
    Utterance,
    VadConfig,
)


class Listen(Component):
    """Capture audio; annotate each Block (rms, muted, VAD event); publish
    it, and publish an Utterance whenever VAD ends a stretch of speech."""

    consumes = (Playback,)
    mute_margin = 0.3  # seconds of extra muting for output latency and echo

    def __init__(self, bus: Bus, vad: VadConfig | None, duration: float = 0) -> None:
        super().__init__(bus, "listen")
        self.config = StreamConfig()
        self.vad_config = vad
        self.n_blocks = (
            round(duration / self.config.block_duration) if duration > 0 else None
        )

    def setup(self) -> None:
        self.detect = stt.vad_detector(self.vad_config) if self.vad_config else None
        self.collect = stt.speech_collector(pre_speech_ms=300)

    def run(self) -> None:
        # Two sources to watch: audio blocks from the PortAudio callback (on
        # a private queue, since the callback must never block), and control
        # messages in the inbox. Poll the inbox between blocks.
        audio: queue.Queue = queue.Queue()
        mute_until = 0.0  # input stream time; blocks captured before it are muted
        utterance_ids = itertools.count()
        try:
            with stt.input_stream(audio, self.config) as stream:
                while True:
                    while not self.inbox.empty():
                        msg = self.inbox.get_nowait()
                        if isinstance(msg, Shutdown):
                            return
                        if isinstance(msg, Playback):
                            # stream.time is on the same clock as Block.adc_time.
                            # max(): a short reply must not cut an ongoing mute.
                            end = stream.time + msg.duration + self.mute_margin
                            mute_until = max(mute_until, end)
                    try:
                        b = audio.get(timeout=0.1)  # timeout: keep polling the inbox
                    except queue.Empty:
                        continue
                    if self.n_blocks is not None and b.index >= self.n_blocks:
                        self.bus.publish(Shutdown(reason="duration reached"))
                        return

                    b.rms = stt.rms(b.indata)
                    b.muted = b.adc_time < mute_until
                    if b.muted:
                        # Silence rather than skipping the block: VAD counts
                        # samples, so its timestamps stay in step with the stream.
                        b.indata[:] = 0
                    if self.detect:
                        b.event = self.detect(b.indata)
                        if blocks := self.collect(b):
                            self.bus.publish(
                                stt.make_utterance(next(utterance_ids), blocks)
                            )
                    self.bus.publish(b)
        except Exception as e:  # noqa: BLE001 - any crash: report, shut down
            self.fail(e)


class Stt(Component):
    """Utterance -> Transcript, with whisper. Saying just "terminate"
    (ignoring case and punctuation) shuts everything down."""

    stop_phrase = "terminate"

    consumes = (Utterance,)

    def __init__(self, bus: Bus) -> None:
        super().__init__(bus, "stt")

    def setup(self) -> None:
        self.whisper = stt.load_whisper()

    def handle(self, msg: Utterance) -> None:
        transcript = stt.transcribe(self.whisper, msg)
        self.bus.publish(transcript)  # first, so UIs still show it
        if stt.normalize(transcript.text) == self.stop_phrase:
            self.bus.publish(Shutdown(reason=f'voice command "{self.stop_phrase}"'))


class Tts(Component):
    """Transcript -> Speech, with kokoro."""

    consumes = (Transcript,)

    def __init__(self, bus: Bus, voice: str = "af_alloy") -> None:
        super().__init__(bus, "tts")
        self.voice = voice

    def setup(self) -> None:
        self.engine = kokoro.KokoroTTS()
        # A voice's first letter is its accent (af_alloy -> "a").
        self.engine.initialize(voice=self.voice, lang_code=self.voice[0])

    def handle(self, msg: Transcript) -> None:
        if not msg.text:
            return
        t0 = time.perf_counter()
        audio, words = self.engine.synthesize_timed(msg.text)
        self.bus.publish(
            Speech(
                utterance_id=msg.utterance_id,
                text=msg.text,
                voice=self.voice,
                samplerate=self.engine.samplerate,
                audio=audio,
                duration=len(audio) / self.engine.samplerate,
                synth_seconds=time.perf_counter() - t0,
                words=words,
            )
        )
