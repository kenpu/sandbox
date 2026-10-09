from pathlib import Path

from pydantic import BaseModel

from multimodal_ai.yamlio import dump_yaml, load_yaml


class Recording(BaseModel):
    samplerate: int = 16000
    channels: int = 1
    device: str | int | None = None
    output: Path = Path("out.wav")


def test_roundtrip(tmp_path):
    path = tmp_path / "rec.yaml"
    rec = Recording(device="Corsair", output=Path("clips/a.wav"))
    dump_yaml(rec, path)
    assert load_yaml(path, Recording) == rec


def test_defaults_from_empty_file(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    assert load_yaml(path, Recording) == Recording()
