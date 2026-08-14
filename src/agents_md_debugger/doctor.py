from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .config import Settings
from .discovery import IGNORED_DIRS, scan_tree
from .models import Diagnostic


def _relative(path: str, root: Path) -> str:
    return Path(path).relative_to(root).as_posix()


def diagnose(root: str | Path, settings: Settings) -> list[Diagnostic]:
    project_root = Path(root).expanduser().resolve()
    files = scan_tree(project_root, settings)
    diagnostics: list[Diagnostic] = []

    by_scope: dict[str, list] = defaultdict(list)
    for item in files:
        by_scope[item.scope].append(item)
        rel = _relative(item.path, project_root)
        if item.status == "empty":
            diagnostics.append(Diagnostic("AMD001", "warning", rel, "Empty instruction file is ignored by Codex."))
        if item.status == "shadowed":
            diagnostics.append(Diagnostic("AMD002", "warning", rel, item.reason or "Instruction file is shadowed."))
        if item.size_bytes > settings.max_bytes:
            diagnostics.append(Diagnostic("AMD003", "warning", rel, f"File is {item.size_bytes} bytes, above the configured {settings.max_bytes}-byte project budget."))

    instruction_paths = {Path(item.path).resolve() for item in files}
    for scope, items in by_scope.items():
        scope_dir = project_root if scope == "." else project_root / scope
        descendants = [
            path
            for path in scope_dir.rglob("*")
            if path.is_file()
            and path.resolve() not in instruction_paths
            and not any(part in IGNORED_DIRS for part in path.relative_to(scope_dir).parts)
        ]
        if not descendants:
            candidate = next((item for item in items if item.status == "candidate"), items[0])
            diagnostics.append(Diagnostic("AMD004", "note", _relative(candidate.path, project_root), "No non-instruction files exist in this directory scope."))

    seen_lines: dict[str, tuple[str, int]] = {}
    for item in files:
        if item.status != "candidate":
            continue
        rel = _relative(item.path, project_root)
        text = Path(item.path).read_text(encoding="utf-8", errors="replace")
        for number, raw in enumerate(text.splitlines(), 1):
            normalized = " ".join(raw.strip().lower().split())
            if len(normalized) < 20 or normalized.startswith(("#", "<!--")):
                continue
            previous = seen_lines.get(normalized)
            if previous and previous[0] != rel:
                diagnostics.append(Diagnostic("AMD005", "note", f"{rel}:{number}", f"Duplicates instruction text from {previous[0]}:{previous[1]}."))
            else:
                seen_lines[normalized] = (rel, number)

    diagnostics.sort(key=lambda item: (item.path, item.code))
    return diagnostics
