# multimodal-ai

A learning playground for local speech AI, driven from one CLI (`main`):

- **listen**: live microphone level, voice activity detection ([Silero VAD](https://github.com/snakers4/silero-vad)),
  speech-to-text ([Whisper](https://huggingface.co/openai/whisper-small.en) on torch via transformers, with word timestamps),
  and optionally speaking each transcript back.
- **say**: text-to-speech with [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (54 voices)
  or [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) (clones a voice from a short recording).
- **record**: record the mic to a file, e.g. a reference clip for voice cloning.

Everything runs locally; models are downloaded once from Hugging Face.

## Requirements

- Linux (Debian/Ubuntu for `make system-deps`), [uv](https://docs.astral.sh/uv/), and `make`
- An NVIDIA GPU with a driver supporting CUDA 13 (580+); models run on `cuda`
- ~12 GB of disk: ~8 GB Python environment, ~4 GB model weights
- Optional: a `.env` file with `HF_TOKEN=...` for authenticated (faster) Hugging Face downloads

## Quick start

```bash
make setup        # PortAudio (sudo), Python env, model weights
make              # list all targets
```

| Command | What it does |
|---|---|
| `make devices` | List audio devices |
| `make listen` | Live mic level and voice activity |
| `make transcribe` | Live speech-to-text |
| `make echo` | Speech-to-text, spoken back (use a headset) |
| `make say TEXT="Hello"` | Speak with kokoro; add `VOICE=bm_george` to change voice |
| `make voices` | List kokoro voices |
| `make record OUT=me.wav DURATION=10` | Record yourself |
| `make clone OUT=me.wav TEXT="Hello"` | Speak in the recorded voice (chatterbox) |
| `make test` / `make lint` / `make format` | Development |

The targets are thin wrappers around `uv run main ...`; see `uv run main sound <command> --help`
for every option. In a terminal, output is a live [rich](https://github.com/Textualize/rich) UI;
when piped, it is plain YAML, e.g. `uv run main sound listen --stt > log.yaml`.

`listen` runs as concurrent components passing messages over a bus
(`Block -> Utterance -> Transcript -> Speech`); see `services/pipeline.py`.

## Layout

```
src/multimodal_ai/
  main.py              # the `main` CLI; mounts the sub-apps, loads .env
  apps/sound.py        # `main sound ...` commands (CLI only)
  ui.py                # listen UIs: RichUI (terminal) and YamlUI (piped)
  services/types.py    # pydantic data models and pipeline messages
  services/bus.py      # message Bus and the thread-based Component
  services/pipeline.py # listen's components: Listen, Stt, Tts
  services/stt.py      # audio capture, VAD, whisper
  services/tts/        # the TTS interface, plus kokoro.py and chatterbox.py
notes/                 # task notes
tests/
```

To add a sub-app: create `apps/<name>.py` with `app = typer.Typer()` and mount it in
`main.py` with `app.add_typer(<name>.app, name="<name>")`.

## Dependency notes

`pyproject.toml` has two `[tool.uv]` workarounds so everything shares one torch (CUDA 13):

- `override-dependencies`: chatterbox pins `torch==2.6.0`; overridden to `>=2.9`.
- `constraint-dependencies`: `setuptools<81`, because chatterbox's watermarker still imports `pkg_resources`.

Speech-to-text uses Whisper through `transformers` rather than faster-whisper: faster-whisper
runs on CTranslate2, whose ARM (aarch64) wheels have no CUDA, while torch's do.
