from __future__ import annotations

import json
from pathlib import Path

from .models import Diagnostic, Explanation, InstructionFile


def _display(path: str, root: str) -> str:
    try:
        return Path(path).relative_to(root).as_posix()
    except ValueError:
        return path


def render_explanation(explanation: Explanation) -> str:
    lines = [
        f"Target: {explanation.target}",
        f"Working directory: {explanation.working_directory}",
        f"Project root: {explanation.project_root}",
        f"Root marker: {explanation.root_marker or 'none'}",
        f"Project instruction budget: {explanation.total_project_bytes}/{explanation.max_bytes} bytes",
        "",
        "Global instruction source:",
    ]
    if explanation.global_files:
        for item in explanation.global_files:
            lines.append(f"  {item.path} ({item.size_bytes} bytes, {item.status})")
    else:
        lines.append("  none")
    lines.extend(["", "Effective project instruction chain (root -> working directory):"])
    if not explanation.project_files:
        lines.append("  none")
    for index, item in enumerate(explanation.project_files, 1):
        path = _display(item.path, explanation.project_root)
        suffix = f", {item.reason}" if item.reason else ""
        lines.append(f"  {index}. {path} [scope {item.scope}/**, {item.loaded_bytes}/{item.size_bytes} bytes, {item.status}{suffix}]")
    lines.extend(["", "Later files have higher precedence. This tool does not interpret semantic conflicts inside Markdown."])
    return "\n".join(lines)


def render_scan(items: list[InstructionFile], root: str) -> str:
    lines = [f"Instruction files under {root}:"]
    if not items:
        lines.append("  none")
    for item in items:
        suffix = f" - {item.reason}" if item.reason else ""
        lines.append(f"  {_display(item.path, root)} [scope {item.scope}/**, {item.status}, {item.size_bytes} bytes]{suffix}")
    return "\n".join(lines)


def render_doctor(items: list[Diagnostic], root: str) -> str:
    errors = sum(item.severity == "error" for item in items)
    warnings = sum(item.severity == "warning" for item in items)
    notes = sum(item.severity == "note" for item in items)
    lines = [f"Doctor: {errors} error(s), {warnings} warning(s), {notes} note(s)"]
    if not items:
        lines.append("No structural problems detected.")
    for item in items:
        lines.append(f"[{item.severity.upper()}] {item.code} {item.path}: {item.message}")
    lines.append("Diagnostics describe file discovery structure, not whether Codex will follow an instruction.")
    return "\n".join(lines)


def json_dump(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)
