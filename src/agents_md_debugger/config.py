from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    max_bytes: int = 32_768
    fallbacks: tuple[str, ...] = ()
    root_markers: tuple[str, ...] = (".git",)
    codex_home: Path | None = None
    config_path: Path | None = None

    @property
    def filenames(self) -> tuple[str, ...]:
        return ("AGENTS.override.md", "AGENTS.md", *self.fallbacks)


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def load_settings(
    config_path: str | Path | None = None,
    *,
    max_bytes: int | None = None,
    fallbacks: list[str] | None = None,
    root_markers: list[str] | None = None,
    codex_home: str | Path | None = None,
) -> Settings:
    home = Path(codex_home).expanduser().resolve() if codex_home else default_codex_home()
    config = Path(config_path).expanduser().resolve() if config_path else home / "config.toml"
    values: dict[str, object] = {}
    if config.is_file():
        with config.open("rb") as handle:
            values = tomllib.load(handle)

    configured_max = values.get("project_doc_max_bytes", 32_768)
    configured_fallbacks = values.get("project_doc_fallback_filenames", [])
    configured_markers = values.get("project_root_markers", [".git"])

    final_max = max_bytes if max_bytes is not None else int(configured_max)
    final_fallbacks = fallbacks if fallbacks is not None else list(configured_fallbacks)
    final_markers = root_markers if root_markers is not None else list(configured_markers)
    if final_max < 0:
        raise ValueError("project document byte limit cannot be negative")
    for label, items in (("fallback filename", final_fallbacks), ("root marker", final_markers)):
        if not all(isinstance(item, str) and item and Path(item).name == item for item in items):
            raise ValueError(f"every {label} must be a non-empty basename")

    return Settings(
        max_bytes=final_max,
        fallbacks=tuple(final_fallbacks),
        root_markers=tuple(final_markers),
        codex_home=home,
        config_path=config if config.is_file() else None,
    )
