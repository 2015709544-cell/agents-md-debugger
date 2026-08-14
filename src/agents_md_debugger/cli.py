from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_settings
from .discovery import explain_path, scan_tree
from .doctor import diagnose
from .reporters import json_dump, render_doctor, render_explanation, render_scan


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="Codex config.toml path (default: $CODEX_HOME/config.toml)")
    parser.add_argument("--max-bytes", type=int, help="override project_doc_max_bytes")
    parser.add_argument("--fallback", action="append", dest="fallbacks", help="override fallback filenames; repeat for multiple names")
    parser.add_argument("--root-marker", action="append", dest="root_markers", help="override project root markers; repeat for multiple names")
    parser.add_argument("--codex-home", help="override CODEX_HOME for global instruction discovery")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agents-md-debugger", description="Inspect Codex AGENTS.md discovery without starting a model session.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="list instruction files and same-directory selection status")
    scan.add_argument("root", nargs="?", default=".")
    _common(scan)

    explain = subparsers.add_parser("explain", help="show the effective instruction chain for a file or directory")
    explain.add_argument("target")
    explain.add_argument("--project-root", help="use an explicit project root")
    _common(explain)

    doctor = subparsers.add_parser("doctor", help="diagnose empty, shadowed, oversized, duplicate, and empty-scope files")
    doctor.add_argument("root", nargs="?", default=".")
    doctor.add_argument("--fail-on", choices=("warning", "error", "never"), default="never")
    _common(doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config, max_bytes=args.max_bytes, fallbacks=args.fallbacks, root_markers=args.root_markers, codex_home=args.codex_home)
        if args.command == "scan":
            root = str(Path(args.root).expanduser().resolve())
            items = scan_tree(root, settings)
            output = json_dump({"schema_version": 1, "root": root, "files": [item.to_dict() for item in items]}) if args.json else render_scan(items, root)
            code = 0
        elif args.command == "explain":
            result = explain_path(args.target, settings, args.project_root)
            output = json_dump(result.to_dict()) if args.json else render_explanation(result)
            code = 0
        else:
            root = str(Path(args.root).expanduser().resolve())
            items = diagnose(root, settings)
            output = json_dump({"schema_version": 1, "root": root, "diagnostics": [item.to_dict() for item in items]}) if args.json else render_doctor(items, root)
            severities = {item.severity for item in items}
            code = int(args.fail_on == "warning" and bool(severities & {"warning", "error"}) or args.fail_on == "error" and "error" in severities)
    except (OSError, ValueError) as exc:
        print(f"agents-md-debugger: {exc}", file=sys.stderr)
        return 2
    print(output)
    return code
