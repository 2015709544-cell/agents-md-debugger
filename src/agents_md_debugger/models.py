from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class InstructionFile:
    path: str
    scope: str
    kind: str
    size_bytes: int
    loaded_bytes: int
    status: str
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Explanation:
    target: str
    working_directory: str
    project_root: str
    root_marker: str | None
    config_path: str | None
    max_bytes: int
    fallbacks: tuple[str, ...]
    global_files: tuple[InstructionFile, ...]
    project_files: tuple[InstructionFile, ...]
    total_project_bytes: int
    truncated: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "target": self.target,
            "working_directory": self.working_directory,
            "project_root": self.project_root,
            "root_marker": self.root_marker,
            "config_path": self.config_path,
            "settings": {
                "project_doc_max_bytes": self.max_bytes,
                "project_doc_fallback_filenames": list(self.fallbacks),
            },
            "global_files": [item.to_dict() for item in self.global_files],
            "project_files": [item.to_dict() for item in self.project_files],
            "total_project_bytes": self.total_project_bytes,
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
