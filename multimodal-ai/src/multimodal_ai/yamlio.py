"""Read and write pydantic models as YAML."""

from pathlib import Path

import yaml
from pydantic import BaseModel


def load_yaml[M: BaseModel](path: str | Path, model: type[M]) -> M:
    """Parse the YAML file at PATH and validate it as MODEL."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return model.model_validate(data or {})


def dump_yaml(obj: BaseModel, path: str | Path) -> None:
    """Write OBJ to PATH as YAML (JSON-compatible types, field order kept)."""
    data = obj.model_dump(mode="json")
    Path(path).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
