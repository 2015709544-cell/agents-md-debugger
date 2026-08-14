from __future__ import annotations

from pathlib import Path

from .config import Settings
from .models import Explanation, InstructionFile

IGNORED_DIRS = {".git", ".hg", ".svn", ".venv", "node_modules", "dist", "build"}


def _content(path: Path) -> bytes:
    return path.read_bytes()


def _is_nonempty(data: bytes) -> bool:
    return bool(data.strip())


def find_project_root(start: Path, markers: tuple[str, ...]) -> tuple[Path, str | None]:
    start = start.resolve()
    if not markers:
        return start, None
    for directory in (start, *start.parents):
        for marker in markers:
            if (directory / marker).exists():
                return directory, marker
    return start, None


def _directories_between(root: Path, working_dir: Path) -> list[Path]:
    try:
        relative = working_dir.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"target is outside project root: {working_dir}") from exc
    directories = [root]
    current = root
    for part in relative.parts:
        current /= part
        directories.append(current)
    return directories


def _select_in_directory(directory: Path, settings: Settings) -> tuple[Path | None, bytes | None]:
    for filename in settings.filenames:
        candidate = directory / filename
        if candidate.is_file():
            data = _content(candidate)
            if _is_nonempty(data):
                return candidate, data
    return None, None


def _global_files(settings: Settings) -> tuple[InstructionFile, ...]:
    if not settings.codex_home:
        return ()
    for filename in ("AGENTS.override.md", "AGENTS.md"):
        candidate = settings.codex_home / filename
        if candidate.is_file():
            data = _content(candidate)
            if _is_nonempty(data):
                return (
                    InstructionFile(
                        str(candidate), "global", filename, len(data), len(data), "loaded"
                    ),
                )
    return ()


def explain_path(target: str | Path, settings: Settings, root: str | Path | None = None) -> Explanation:
    target_path = Path(target).expanduser().resolve()
    working_dir = target_path if target_path.is_dir() else target_path.parent
    if not working_dir.is_dir():
        raise NotADirectoryError(f"target parent is not a directory: {working_dir}")
    if root:
        project_root, marker = Path(root).expanduser().resolve(), "explicit"
    else:
        project_root, marker = find_project_root(working_dir, settings.root_markers)
    if not project_root.is_dir():
        raise NotADirectoryError(f"project root is not a directory: {project_root}")

    remaining = settings.max_bytes
    project_files: list[InstructionFile] = []
    truncated = False
    for directory in _directories_between(project_root, working_dir):
        selected, data = _select_in_directory(directory, settings)
        if selected is None or data is None:
            continue
        loaded = min(len(data), remaining)
        status = "loaded"
        reason = None
        if loaded < len(data):
            status = "truncated" if loaded else "skipped"
            reason = "project_doc_max_bytes exhausted"
            truncated = True
        project_files.append(
            InstructionFile(
                str(selected),
                selected.parent.relative_to(project_root).as_posix() or ".",
                selected.name,
                len(data),
                loaded,
                status,
                reason,
            )
        )
        remaining -= loaded
        if remaining == 0:
            break

    return Explanation(
        str(target_path),
        str(working_dir),
        str(project_root),
        marker,
        str(settings.config_path) if settings.config_path else None,
        settings.max_bytes,
        settings.fallbacks,
        _global_files(settings),
        tuple(project_files),
        settings.max_bytes - remaining,
        truncated,
    )


def scan_tree(root: str | Path, settings: Settings) -> list[InstructionFile]:
    project_root = Path(root).expanduser().resolve()
    if not project_root.is_dir():
        raise NotADirectoryError(f"repository path is not a directory: {project_root}")
    results: list[InstructionFile] = []
    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or path.name not in settings.filenames:
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(project_root).parts):
            continue
        data = _content(path)
        scope = path.parent.relative_to(project_root).as_posix() or "."
        if not _is_nonempty(data):
            status, reason = "empty", "Codex skips empty instruction files"
        else:
            chosen, _ = _select_in_directory(path.parent, settings)
            if chosen == path:
                status, reason = "candidate", None
            else:
                status, reason = "shadowed", f"{chosen.name} has higher priority in this directory"
        results.append(InstructionFile(str(path), scope, path.name, len(data), 0, status, reason))
    return results
