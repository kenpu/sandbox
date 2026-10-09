"""Sound sub-app: CLI over `multimodal_ai.services.stt`."""

import queue
import sys
import time
from contextlib import nullcontext
from enum import Enum
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import typer
import yaml
from pydantic import ValidationError
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from multimodal_ai.keyboard import keypress
from multimodal_ai.services import stt as stt_service
from multimodal_ai.services.tts import TTS, chatterbox, kokoro
from multimodal_ai.services.types import (
    Block,
    StreamConfig,
    Transcript,
    VadConfig,
    VadEvent,
)

app = typer.Typer(help="Sound input/output.", no_args_is_help=True)


@app.command()
def devices(
    list_all: bool = typer.Option(False, "--list", help="List all devices."),
) -> None:
    """Show the default sound devices, or all of them with --list."""
    devs = stt_service.query_devices()
    if not list_all:
        devs = [d for d in devs if d.default]

    # Terminal: rich table. Scripting (piped/redirected): plain YAML.
    if not sys.stdout.isatty():
        typer.echo(
            yaml.safe_dump([d.model_dump() for d in devs], sort_keys=False), nl=False
        )
        return

    table = Table(title="Sound devices")
    for col in ("#", "Name", "Host API", "In", "Out", "Rate"):
        table.add_column(
            col, justify="right" if col in ("#", "In", "Out", "Rate") else "left"
        )
    for d in devs:
        table.add_row(
            ("* " if d.default else "") + str(d.index),
            d.name,
            d.hostapi,
            str(d.inputs),
            str(d.outputs),
            f"{d.samplerate:g}",
        )
    Console().print(table)


def level_bar(rms: float, width: int = 40) -> str:
    """Map RMS to a dBFS meter spanning -60..0 dB."""
    db = 20 * np.log10(max(rms, 1e-10))
    n = int(width * min(max((db + 60) / 60, 0), 1))
    return f"[green]{'█' * n}[/][dim]{'·' * (width - n)}[/] {db:6.1f} dBFS"


def render(
    b: Block,
    level: float,
    speaking: bool | None,
    last: VadEvent | None,
    transcript: Transcript | None,
    stt_on: bool,
    tts_status: str,
) -> Panel:
    grid = Table.grid(padding=(0, 2))
    grid.add_row("block", str(b.index))
    grid.add_row("adc time", f"{b.adc_time:.3f} s")
    grid.add_row("current time", f"{b.current_time:.3f} s")
    grid.add_row("latency", f"{(b.current_time - b.adc_time) * 1000:.1f} ms")
    grid.add_row("rms", f"{level:.5f}  {level_bar(level)}")
    if speaking is None:
        grid.add_row("vad", "[dim]off[/]")
    else:
        grid.add_row(
            "vad", "[bold red]● speech[/]" if speaking else "[dim]○ silence[/]"
        )
        if last:
            grid.add_row("last event", f"{last.kind} @ {last.seconds:.3f} s")
    grid.add_row("tts", tts_status)

    # Text(...) shows the transcript literally; a plain str would be parsed as
    # rich markup, so e.g. "[laughs]" would vanish.
    if transcript:
        latest = Text(transcript.text)
    else:
        latest = Text("no transcription yet" if stt_on else "stt off", style="dim")
    return Panel(
        Group(grid, Rule(style="dim"), latest),
        title="listen",
        subtitle="press any key to stop",
    )


@app.command()
def listen(
    duration: float = typer.Option(
        0, "--duration", help="Seconds to listen; <= 0 listens forever."
    ),
    vad: bool = typer.Option(True, "--vad/--no-vad", help="Voice activity detection."),
    threshold: float = typer.Option(0.5, help="VAD speech probability threshold."),
    min_silence_duration_ms: int = typer.Option(
        300, help="Silence (ms) needed to end a speech segment."
    ),
    speech_pad_ms: int = typer.Option(100, help="Padding (ms) around speech segments."),
    stt: bool = typer.Option(
        False, "--stt/--no-stt", help="Transcribe each utterance (needs --vad)."
    ),
    tts: bool = typer.Option(
        False, "--tts/--no-tts", help="Speak each transcript back (needs --stt)."
    ),
    voice: str = typer.Option("af_alloy", "--voice", help="Kokoro voice for --tts."),
) -> None:
    """Listen on the default input (mono, 16 kHz, 512-sample blocks); show RMS.

    With --stt, each utterance found by VAD is transcribed by whisper.
    With --tts, each transcript is then spoken back with kokoro.
    Stops after --duration, on any keypress, or on Ctrl-C.
    """
    if stt and not vad:
        raise typer.BadParameter("--stt needs --vad to find utterances.")
    if tts and not stt:
        raise typer.BadParameter("--tts needs --stt to have text to speak.")
    config = StreamConfig()
    # Load the model before opening the stream so blocks don't pile up meanwhile.
    try:
        vad_config = VadConfig(
            threshold=threshold,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
        )
    except ValidationError as e:  # report as a CLI usage error, not a traceback
        raise typer.BadParameter(str(e)) from None
    tty = sys.stdout.isatty()
    with Console().status("Loading models…") if tty else nullcontext():
        detect = stt_service.vad_detector(vad_config) if vad else None
        whisper = stt_service.load_whisper() if stt else None
        speaker: TTS | None = None
        if tts:
            speaker = kokoro.KokoroTTS()
            # A voice's first letter is its accent (af_alloy -> "a"), so use
            # the matching phoneme rules.
            speaker.initialize(voice=voice, lang_code=voice[0])
    # While our own speech plays, the mic hears it; left alone, VAD would
    # trigger and we'd transcribe and repeat ourselves forever. So blocks
    # captured before `mute_until` (input stream time, like Block.adc_time)
    # are replaced by silence. The margin covers output latency and echo.
    mute_until = 0.0
    mute_margin = 0.3  # seconds
    synth_seconds: float | None = None  # of the latest spoken reply
    collect = stt_service.speech_collector(pre_speech_ms=300)
    transcript: Transcript | None = None  # the latest one
    speaking = False if vad else None  # None means "VAD off"
    last: VadEvent | None = None
    q: queue.Queue[Block] = queue.Queue()
    n_blocks = round(duration / config.block_duration) if duration > 0 else None
    try:
        with (
            stt_service.input_stream(q, config) as stream,
            Live(auto_refresh=False) if tty else nullcontext() as live,
            keypress() as key_pressed,
        ):
            while True:
                b = q.get()
                if key_pressed() or (n_blocks is not None and b.index >= n_blocks):
                    break
                # Computed here, in the consumer, not in the audio callback.
                level = stt_service.rms(b.indata)
                muted = b.adc_time < mute_until
                if muted:
                    # Silence rather than skipping the block: VAD counts
                    # samples, so its timestamps stay in step with the stream.
                    b.indata = np.zeros_like(b.indata)
                if detect:
                    b.event = detect(b.indata)
                    if b.event:
                        last, speaking = b.event, b.event.kind == "start"
                new_transcript = None
                if whisper and (utterance := collect(b)):
                    # Blocks the loop while whisper runs; meanwhile the audio
                    # callback keeps queueing blocks, and we catch up after.
                    new_transcript = transcript = stt_service.transcribe(
                        whisper, utterance
                    )
                spoken = None
                if speaker and new_transcript and new_transcript.text:
                    t0 = time.perf_counter()
                    speech = speaker.synthesize(new_transcript.text)
                    synth_seconds = time.perf_counter() - t0
                    sd.play(speech, speaker.samplerate)  # returns immediately
                    played = len(speech) / speaker.samplerate
                    mute_until = stream.time + played + mute_margin
                    spoken = {
                        "voice": voice,
                        "duration": played,
                        "synth_seconds": synth_seconds,
                    }
                if live:
                    if not speaker:
                        tts_status = "[dim]off[/]"
                    else:
                        playing = stream.time < mute_until
                        tts_status = (
                            "[cyan]🔊 speaking[/]" if playing else "[dim]idle[/]"
                        )
                        if synth_seconds is not None:
                            tts_status += f"  [dim]last synth {synth_seconds:.3f} s[/]"
                    live.update(
                        render(b, level, speaking, last, transcript, stt, tts_status),
                        refresh=True,
                    )
                else:  # one YAML list item per block, without the raw samples
                    row = b.model_dump(exclude={"indata", "status"}) | {"rms": level}
                    if new_transcript:  # only on the block that ended speech
                        row["transcript"] = new_transcript.model_dump(mode="json")
                    if spoken:
                        row["tts"] = spoken
                    if muted:
                        row["muted"] = True
                    typer.echo(yaml.safe_dump([row], sort_keys=False), nl=False)
    except KeyboardInterrupt:
        pass


@app.command()
def record(
    output: Path = typer.Argument(..., help="Audio file to write (.wav, .flac, .ogg)."),
    duration: float = typer.Option(
        0, "--duration", help="Seconds to record; <= 0 records until a key is pressed."
    ),
    samplerate: int = typer.Option(
        24000, "--samplerate", help="Hz; 24000 matches the TTS engines' output."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite OUTPUT if it exists."),
) -> None:
    """Record mono audio from the default input to OUTPUT.

    Stops after --duration, on any keypress, or on Ctrl-C; what was recorded
    so far is saved in every case. Handy for making a chatterbox --voice clip.
    """
    if output.exists() and not force:
        raise typer.BadParameter(f"{output} exists; use --force to overwrite.")

    q: queue.Queue[np.ndarray] = queue.Queue()
    chunks: list[np.ndarray] = []  # recorded blocks, in order
    target = round(duration * samplerate) if duration > 0 else None
    recorded = 0  # samples so far
    tty = sys.stdout.isatty()
    try:
        with (
            stt_service.recorder(q, samplerate),
            Live(auto_refresh=False) if tty else nullcontext() as live,
            keypress() as key_pressed,
        ):
            while not key_pressed() and (target is None or recorded < target):
                chunk = q.get()
                chunks.append(chunk)
                recorded += len(chunk)
                if live:
                    level = stt_service.rms(chunk)
                    live.update(
                        Panel(
                            f"[bold red]● REC[/]  {recorded / samplerate:5.1f} s\n"
                            f"{level_bar(level)}",
                            title=str(output),
                            subtitle="press any key to stop",
                        ),
                        refresh=True,
                    )
    except KeyboardInterrupt:
        pass  # fall through and save what we have

    audio = np.concatenate(chunks)[:target] if chunks else np.zeros(0, np.float32)
    # soundfile picks the format from the extension; WAV defaults to 16-bit PCM.
    sf.write(output, audio, samplerate)

    seconds = len(audio) / samplerate
    if tty:
        Console().print(f"[dim]saved {output} · {seconds:.1f} s · {samplerate} Hz[/]")
    else:
        info = {"output": str(output), "samplerate": samplerate, "duration": seconds}
        typer.echo(yaml.safe_dump(info, sort_keys=False), nl=False)


class Engine(str, Enum):
    """TTS engines for `say`. Typer turns an Enum into a list of choices."""

    kokoro = "kokoro"
    chatterbox = "chatterbox"


@app.command()
def say(
    text: str | None = typer.Argument(
        None, help="Text to speak; read stdin if omitted."
    ),
    engine_name: Engine | None = typer.Option(
        None,
        "--engine",
        help="Text-to-speech engine. Default: chatterbox if --voice is an audio "
        "file (voice cloning), else kokoro.",
    ),
    voice: str | None = typer.Option(
        None,
        "--voice",
        help="kokoro: voice name (default af_heart, see --list-voices). "
        "chatterbox: audio file to clone, e.g. from `sound record` "
        "(default: built-in voice).",
    ),
    speed: float = typer.Option(
        1.0, "--speed", help="Speaking rate multiplier (kokoro only)."
    ),
    lang_code: str = typer.Option(
        "a", "--lang-code", help="Language/accent code (kokoro only)."
    ),
    exaggeration: float = typer.Option(
        0.5,
        "--exaggeration",
        min=0.0,
        help="Emotional intensity; 0.5 is neutral, higher is livelier "
        "(chatterbox only).",
    ),
    list_voices: bool = typer.Option(
        False, "--list-voices", help="List kokoro voices and exit, without speaking."
    ),
    list_languages: bool = typer.Option(
        False,
        "--list-languages",
        help="List kokoro languages and exit, without speaking.",
    ),
) -> None:
    """Speak TEXT with a text-to-speech engine."""
    tty = sys.stdout.isatty()

    if list_voices:
        voices = kokoro.list_voices()
        if not tty:
            typer.echo(
                yaml.safe_dump([v.model_dump() for v in voices], sort_keys=False),
                nl=False,
            )
            return
        table = Table(title="Kokoro voices")
        for col in ("Name", "Language", "Gender"):
            table.add_column(col)
        for v in voices:
            table.add_row(v.name, v.language, v.gender)
        Console().print(table)
        return

    if list_languages:
        if not tty:
            rows = [
                {"lang_code": c, "language": n} for c, n in kokoro.LANGUAGES.items()
            ]
            typer.echo(yaml.safe_dump(rows, sort_keys=False), nl=False)
            return
        table = Table(title="Kokoro languages")
        table.add_column("Code")
        table.add_column("Language")
        for code, name in kokoro.LANGUAGES.items():
            table.add_row(code, name)
        Console().print(table)
        return

    # Each engine takes its own initialize() options; check them up front so
    # mistakes fail fast, before the slow model load.
    voice_is_file = voice is not None and Path(voice).is_file()
    if engine_name is None:
        # Only chatterbox can clone a recording; kokoro voices are names.
        engine_name = Engine.chatterbox if voice_is_file else Engine.kokoro
    engine: TTS  # typed as the interface: the code below works for any engine
    if engine_name is Engine.kokoro:
        if voice_is_file:
            raise typer.BadParameter(
                "kokoro can't clone a recording; use --engine chatterbox."
            )
        if exaggeration != 0.5:
            raise typer.BadParameter("--exaggeration is chatterbox only.")
        if lang_code not in kokoro.LANGUAGES:
            raise typer.BadParameter(
                f"Unknown language code {lang_code!r}; see --list-languages."
            )
        engine = kokoro.KokoroTTS()
        options = {"voice": voice or "af_heart", "lang_code": lang_code, "speed": speed}
    else:
        if speed != 1.0 or lang_code != "a":
            raise typer.BadParameter("--speed and --lang-code are kokoro only.")
        if voice and not Path(voice).is_file():
            raise typer.BadParameter(
                f"chatterbox --voice must be an audio file: {voice}"
            )
        engine = chatterbox.ChatterboxTTS()
        options = {"voice": voice, "exaggeration": exaggeration}

    if text is None:
        text = sys.stdin.read()  # e.g. `echo hello | main sound say`
    text = text.strip()
    if not text:
        raise typer.BadParameter("Nothing to say: give TEXT or pipe it on stdin.")

    # Status messages go to stderr so stdout stays clean for YAML.
    with (
        Console(stderr=True).status("Loading model…")
        if tty
        else nullcontext() as status
    ):
        t0 = time.perf_counter()
        engine.initialize(**options)
        t1 = time.perf_counter()
        if status:
            status.update("Synthesizing…")
        audio = engine.synthesize(text)
        t2 = time.perf_counter()

    load_seconds, synth_seconds = t1 - t0, t2 - t1
    duration = len(audio) / engine.samplerate
    if tty:
        # Real-time factor: synthesis time / audio length; < 1 is faster than real time.
        settings = ", ".join(f"{k}={v}" for k, v in options.items())
        Console().print(
            f"[dim]{engine_name.value} ({settings}) · audio {duration:.2f} s[/]\n"
            f"[dim]load {load_seconds:.2f} s · synthesis {synth_seconds:.3f} s "
            f"(RTF {synth_seconds / duration:.2f})[/]"
        )
    else:
        info = {
            "engine": engine_name.value,
            **options,
            "samplerate": engine.samplerate,
            "duration": duration,
            "load_seconds": load_seconds,
            "synth_seconds": synth_seconds,
        }
        typer.echo(yaml.safe_dump(info, sort_keys=False), nl=False)
    sd.play(audio, engine.samplerate)
    sd.wait()  # block until playback finishes
