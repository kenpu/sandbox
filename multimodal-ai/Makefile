# Run `make` (or `make help`) to list the targets.
# Some take variables, e.g.  make say TEXT="Hi there" VOICE=bm_george

# HF_TOKEN for `make models` (the `main` CLI reads .env by itself).
-include .env
ifdef HF_TOKEN
export HF_TOKEN
endif

MAIN     := uv run main
TEXT     ?= Hello! This is a text to speech test.
VOICE    ?=
OUT      ?= me.wav
DURATION ?= 10

.DEFAULT_GOAL := help
.PHONY: help setup system-deps sync models test lint format \
        devices listen transcribe echo say voices record clone

help: ## Show this help
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | \
		awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

# --- setup -----------------------------------------------------------------

setup: system-deps sync models ## Everything: system package, Python env, model weights

system-deps: ## Install PortAudio if missing (Debian/Ubuntu, needs sudo)
	@ldconfig -p | grep -q libportaudio.so.2 || sudo apt install -y libportaudio2

sync: ## Create .venv and install the Python dependencies
	uv sync

sync-faster-whisper: ## Like sync, plus the optional faster-whisper STT engine
	uv sync --extra faster-whisper

models: ## Pre-download model weights (~4 GB) into ~/.cache/huggingface
	uv run hf download openai/whisper-small.en config.json generation_config.json \
		model.safetensors preprocessor_config.json tokenizer.json tokenizer_config.json \
		vocab.json merges.txt normalizer.json added_tokens.json special_tokens_map.json
	uv run hf download hexgrad/Kokoro-82M config.json kokoro-v1_0.pth \
		voices/af_heart.pt voices/af_alloy.pt
	uv run hf download ResembleAI/chatterbox ve.safetensors t3_cfg.safetensors \
		s3gen.safetensors tokenizer.json conds.pt

# --- development -----------------------------------------------------------

test: ## Run the tests (loads the models, ~30 s)
	uv run pytest -q

lint: ## Check lint and formatting
	uv run ruff check . && uv run ruff format --check .

format: ## Fix lint and formatting
	uv run ruff format . && uv run ruff check --fix .

# --- sound commands --------------------------------------------------------

devices: ## List audio devices
	$(MAIN) sound devices --list

listen: ## Live mic level and voice activity
	$(MAIN) sound listen

transcribe: ## Live speech-to-text
	$(MAIN) sound listen --stt

transcribe-fw: ## Live speech-to-text with faster-whisper (needs sync-faster-whisper)
	$(MAIN) sound listen --stt --stt-engine faster-whisper

echo: ## Live speech-to-text, spoken back with TTS (headset recommended)
	$(MAIN) sound listen --stt --tts

say: ## Speak TEXT with kokoro (optional VOICE, see `make voices`)
	$(MAIN) sound say $(if $(VOICE),--voice $(VOICE)) "$(TEXT)"

voices: ## List kokoro voices
	$(MAIN) sound say --list-voices

record: ## Record DURATION seconds from the mic to OUT (default me.wav)
	$(MAIN) sound record $(OUT) --duration $(DURATION)

clone: ## Speak TEXT in the voice recorded in OUT (chatterbox)
	$(MAIN) sound say --voice $(OUT) "$(TEXT)"
