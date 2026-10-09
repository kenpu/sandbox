"""User interfaces for the listen pipeline (see services/pipeline.py).

A UI runs in the main thread (terminal and keyboard belong there). It
drains its inbox, plays Speech (publishing Playback so listen mutes the
mic), polls the keyboard, and renders. Backends differ only in how they
show messages: RichUI draws a live panel, YamlUI prints one YAML list item
per message for scripting. Other backends (web, 3D) would subclass UI too.
"""

import queue
import sys
import time
from collections import deque
from contextlib import AbstractContextManager, nullcontext

import numpy as np
import sounddevice as sd
import typer
import yaml
from pydantic import BaseModel
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from multimodal_ai.keyboard import keypress
from multimodal_ai.services.bus import Bus
from multimodal_ai.services.types import (
    Block,
    Playback,
    Shutdown,
    Speech,
    Transcript,
    Utterance,
    VadEvent,
)


def level_bar(rms: float, width: int = 40) -> str:
    """Map RMS to a dBFS meter spanning -60..0 dB."""
    db = 20 * np.log10(max(rms, 1e-10))
    n = int(width * min(max((db + 60) / 60, 0), 1))
    return f"[green]{'█' * n}[/][dim]{'·' * (width - n)}[/] {db:6.1f} dBFS"


class UI:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus
        self.inbox = bus.subscribe(Block, Utterance, Transcript, Speech)
        self.playing_until = 0.0  # time.monotonic() when playback ends
        # Replies wait here while another plays: sd.play() would cut it off.
        self.to_play: deque[Speech] = deque()
        self.now_playing: Speech | None = None
        self.play_started = 0.0  # time.monotonic() when now_playing started

    # --- for backends to override ---
    def display(self) -> AbstractContextManager:
        """Context held open while the UI runs (e.g. a rich Live display)."""
        return nullcontext()

    def show(self, msg: BaseModel) -> None:
        """Take in one message (update state, or print it)."""

    def refresh(self) -> None:
        """Redraw after a batch of messages."""

    # --- the loop ---
    def run(self) -> Shutdown:
        """Run until a Shutdown arrives; return it."""
        with keypress() as key_pressed, self.display():
            while True:
                if key_pressed():
                    self.bus.publish(Shutdown(reason="key pressed"))
                self.play_next()
                try:  # timeout: keep polling the keyboard when nothing arrives
                    batch = [self.inbox.get(timeout=0.05)]
                except queue.Empty:
                    continue
                # Drain what else is waiting and redraw once, so rendering
                # never falls behind the audio.
                while not self.inbox.empty():
                    batch.append(self.inbox.get_nowait())
                for msg in batch:
                    if isinstance(msg, Shutdown):
                        return msg
                    if isinstance(msg, Speech):
                        self.to_play.append(msg)
                    self.show(msg)
                self.play_next()
                self.refresh()

    def play_next(self) -> None:
        """Start the next queued reply, if nothing is playing."""
        if self.to_play and time.monotonic() >= self.playing_until:
            speech = self.to_play.popleft()
            sd.play(speech.audio, speech.samplerate)  # returns immediately
            self.now_playing, self.play_started = speech, time.monotonic()
            self.playing_until = self.play_started + speech.duration
            # Tell listen to mute the mic for this long.
            self.bus.publish(
                Playback(utterance_id=speech.utterance_id, duration=speech.duration)
            )


class YamlUI(UI):
    """One YAML list item per message (raw audio left out), for scripting."""

    def show(self, msg: BaseModel) -> None:
        row = {"type": type(msg).__name__} | msg.model_dump(
            mode="json", exclude={"indata", "audio"}
        )
        typer.echo(yaml.safe_dump([row], sort_keys=False), nl=False)
        sys.stdout.flush()


class RichUI(UI):
    """A live panel: low-level block details on top, latest results below."""

    def __init__(self, bus: Bus, vad: bool, stt: bool, tts: bool) -> None:
        super().__init__(bus)
        self.vad, self.stt, self.tts = vad, stt, tts
        self.block: Block | None = None
        self.speaking = False  # between VAD start and end
        self.last_event: VadEvent | None = None
        self.pending: set[int] = set()  # utterance ids sent to stt, not back yet
        self.transcript: Transcript | None = None
        self.speech: Speech | None = None
        self.live = Live(auto_refresh=False)

    def display(self) -> AbstractContextManager:
        return self.live

    def show(self, msg: BaseModel) -> None:
        if isinstance(msg, Block):
            self.block = msg
            if msg.event:
                self.last_event = msg.event
                self.speaking = msg.event.kind == "start"
        elif isinstance(msg, Utterance):
            self.pending.add(msg.id)
        elif isinstance(msg, Transcript):
            self.pending.discard(msg.utterance_id)
            self.transcript = msg
        elif isinstance(msg, Speech):
            self.speech = msg

    def refresh(self) -> None:
        if self.block:
            self.live.update(self.render(self.block), refresh=True)

    def render(self, b: Block) -> Panel:
        grid = Table.grid(padding=(0, 2))
        grid.add_row("block", str(b.index))
        grid.add_row("adc time", f"{b.adc_time:.3f} s")
        grid.add_row("current time", f"{b.current_time:.3f} s")
        grid.add_row("latency", f"{(b.current_time - b.adc_time) * 1000:.1f} ms")
        grid.add_row("rms", f"{b.rms:.5f}  {level_bar(b.rms)}")
        if not self.vad:
            grid.add_row("vad", "[dim]off[/]")
        else:
            if b.muted:
                state = "[cyan]muted (playing)[/]"
            elif self.speaking:
                state = "[bold red]● speech[/]"
            else:
                state = "[dim]○ silence[/]"
            grid.add_row("vad", state)
            if self.last_event:
                e = self.last_event
                grid.add_row("last event", f"{e.kind} @ {e.seconds:.3f} s")

        stt = "[dim]off[/]"
        if self.stt:
            stt = (
                f"[yellow]transcribing ({len(self.pending)})[/]"
                if self.pending
                else "[dim]idle[/]"
            )
            if self.transcript:
                stt += f"  [dim]last {self.transcript.transcribe_seconds:.3f} s[/]"
        grid.add_row("stt", stt)

        tts = "[dim]off[/]"
        if self.tts:
            playing = time.monotonic() < self.playing_until
            tts = "[cyan]🔊 speaking[/]" if playing else "[dim]idle[/]"
            if self.to_play:
                tts += f" [cyan](+{len(self.to_play)} queued)[/]"
            if self.speech:
                tts += f"  [dim]last synth {self.speech.synth_seconds:.3f} s[/]"
        grid.add_row("tts", tts)

        # Text(...) shows the transcript literally; a plain str would be parsed
        # as rich markup, so e.g. "[laughs]" would vanish.
        if (karaoke := self.karaoke()) is not None:
            latest = karaoke
        elif self.transcript:
            latest = Text(self.transcript.text)
        else:
            latest = Text(
                "no transcription yet" if self.stt else "stt off", style="dim"
            )
        return Panel(
            Group(grid, Rule(style="dim"), latest),
            title="listen",
            subtitle="press any key to stop",
        )

    def karaoke(self) -> Text | None:
        """While speech with word timings plays, its text with the word
        being spoken highlighted; None otherwise. Redrawn on every refresh
        (~30 times a second, driven by incoming blocks)."""
        speech = self.now_playing
        t = time.monotonic() - self.play_started  # position in the audio
        if not speech or not speech.words or t >= speech.duration:
            return None
        text = Text()
        for w in speech.words:
            if w.start is not None and w.end is not None and w.start <= t < w.end:
                style = "bold black on yellow"  # being spoken now
            elif w.end is not None and w.end <= t:
                style = ""  # already spoken
            else:
                style = "dim"  # still to come
            text.append(w.text, style=style)
            text.append(w.whitespace)
        return text
