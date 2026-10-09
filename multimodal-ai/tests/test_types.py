import numpy as np
import pytest
from pydantic import ValidationError

from multimodal_ai.services import stt
from multimodal_ai.services.types import Block, StreamConfig, VadConfig, VadEvent


def test_stream_config_fixed_for_vad():
    config = StreamConfig()
    assert (config.samplerate, config.blocksize, config.channels) == (16000, 512, 1)
    assert config.block_duration == 0.032
    with pytest.raises(ValidationError):
        StreamConfig(samplerate=8000)
    with pytest.raises(ValidationError):
        StreamConfig(blocksize=800)
    with pytest.raises(ValidationError):
        StreamConfig(channels=2)


def test_block_requires_ndarray():
    with pytest.raises(ValidationError):
        Block(index=0, adc_time=0, current_time=0, status="", indata=[0.0])


def test_rms():
    indata = np.array([0.5, -0.5, 0.5, -0.5], dtype=np.float32)
    assert stt.rms(indata) == 0.5


def test_vad_config_validation():
    assert VadConfig().min_silence_duration_ms == 300
    with pytest.raises(ValidationError):
        VadConfig(threshold=1.5)


def test_vad_event_seconds_is_dumped():
    assert VadEvent(kind="end", sample=8000).model_dump() == {
        "kind": "end",
        "sample": 8000,
        "seconds": 0.5,
    }


def test_vad_detector_finds_speech_like_tone():
    # 1 s silence, 2 s amplitude-modulated harmonic tone, 1 s silence.
    sr = 16000
    t = np.arange(2 * sr) / sr
    tone = (0.3 * np.sin(2 * np.pi * 150 * t) + 0.2 * np.sin(2 * np.pi * 300 * t)) * (
        0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
    )
    silence = np.zeros(sr)
    audio = np.concatenate([silence, tone, silence]).astype(np.float32)

    detect = stt.vad_detector(VadConfig())
    events = [
        e for i in range(0, len(audio) - 511, 512) if (e := detect(audio[i : i + 512]))
    ]
    assert [e.kind for e in events] == ["start", "end"]
    assert abs(events[0].seconds - 1.0) < 0.2
    assert abs(events[1].seconds - 3.0) < 0.4


def make_block(index: int, kind: str | None = None) -> Block:
    return Block(
        index=index,
        adc_time=0,
        current_time=0,
        status="",
        indata=np.full(512, index, dtype=np.float32),
        event=VadEvent(kind=kind, sample=index * 512) if kind else None,
    )


def test_speech_collector_keeps_pre_speech_buffer():
    collect = stt.speech_collector(pre_speech_ms=300)  # 10 blocks of 32 ms
    kinds = {20: "start", 25: "end"}
    results = [collect(make_block(i, kinds.get(i))) for i in range(30)]
    done = [r for r in results if r]
    assert len(done) == 1 and results[25] is done[0]
    assert [b.index for b in done[0]] == list(range(10, 26))


def test_transcribe_keeps_all_info():
    blocks = [make_block(i) for i in range(10, 41)]
    for b in blocks:
        b.indata[:] = 0  # silence: we check structure, not text
    whisper = stt.load_whisper("tiny.en", device="cpu", compute_type="int8")
    t = stt.transcribe(whisper, blocks)
    assert t.start == 10 * 0.032
    assert t.duration == 31 * 0.032
    assert t.info["language"] == "en"
    assert t.info["transcription_options"]["beam_size"] == 1
    assert t.info["transcription_options"]["word_timestamps"] is True
    assert all("no_speech_prob" in s for s in t.segments)
