# agents-md-debugger

[![CI](https://github.com/2015709544-cell/agents-md-debugger/actions/workflows/ci.yml/badge.svg)](https://github.com/2015709544-cell/agents-md-debugger/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/2015709544-cell/agents-md-debugger)](https://github.com/2015709544-cell/agents-md-debugger/releases)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![MIT License](https://img.shields.io/github/license/2015709544-cell/agents-md-debugger)](LICENSE)

See exactly which `AGENTS.md` instructions Codex is expected to discover for any file in a repository—without starting a model session.

```text
$ agents-md-debugger explain src/api/user.py
Project root: /work/my-app
Project instruction budget: 1840/32768 bytes

Effective project instruction chain (root -> working directory):
  1. AGENTS.md [scope ./**, loaded]
  2. src/AGENTS.md [scope src/**, loaded]
  3. src/api/AGENTS.override.md [scope src/api/**, loaded]
```

The tool is local-only, deterministic, and key-free. It never sends instruction contents anywhere.

> Status: early alpha. This is an independent community tool, not an OpenAI product. It models the public Codex documentation and may lag behind Codex internals.

## Why

Layered `AGENTS.md` files are useful, but discovery problems are hard to inspect: which project root was selected, which file won in a directory, whether a fallback was active, and where the byte budget was exhausted.

`agents-md-debugger` turns those questions into three small commands:

- `scan`: inventory instruction files and show same-directory selection/shadowing;
- `explain`: resolve the expected global and project instruction chain for a target;
- `doctor`: flag empty, shadowed, oversized, duplicated, and empty-scope files.

## Install

Python 3.11+:

```bash
python -m pip install "git+https://github.com/2015709544-cell/agents-md-debugger.git@v0.1.1"
agents-md-debugger --version
```

Development install:

```bash
python -m pip install -e ".[dev]"
```

Uninstall:

```bash
python -m pip uninstall agents-md-debugger
```

## Usage

```bash
agents-md-debugger scan .
agents-md-debugger explain src/api/user.py
agents-md-debugger explain src/api/user.py --json
agents-md-debugger doctor . --fail-on warning
```

The shorter `amd-debug` alias provides the same commands.

### Try the included example

From this repository's root:

```bash
agents-md-debugger explain examples/demo-repo/src/api/user.py --project-root examples/demo-repo
```

The checked-in fixture produces this three-level chain (absolute paths above it are omitted):

```text
Project instruction budget: 263/32768 bytes

Effective project instruction chain (root -> working directory):
  1. AGENTS.md [scope ./**, 113/113 bytes, loaded]
  2. src/AGENTS.md [scope src/**, 74/74 bytes, loaded]
  3. src/api/AGENTS.override.md [scope src/api/**, 76/76 bytes, loaded]
```

By default the tool reads these public Codex settings from `$CODEX_HOME/config.toml` (or `~/.codex/config.toml`):

- `project_doc_max_bytes`;
- `project_doc_fallback_filenames`;
- `project_root_markers`.

It reports global instruction file metadata from `$CODEX_HOME`, but never prints file contents. Override settings without editing your configuration:

```bash
agents-md-debugger explain src/api/user.py \
  --max-bytes 65536 \
  --fallback TEAM_GUIDE.md \
  --root-marker .git
```

## Discovery model

The implementation follows the current public Codex documentation:

1. Global scope selects the first non-empty `AGENTS.override.md` or `AGENTS.md` in the Codex home.
2. Project scope starts at the detected project root and walks to the target's directory.
3. Each directory selects at most one non-empty file in this order: `AGENTS.override.md`, `AGENTS.md`, configured fallback names.
4. Files merge root-to-target; later, more local instructions have higher precedence.
5. Empty files are skipped and the project byte budget can truncate the chain.

`explain path/to/file` models starting Codex from that file's parent directory. It does not claim to inspect a running or resumed Codex session.

## Doctor diagnostics

| Code | Meaning |
|---|---|
| AMD001 | empty instruction file is ignored |
| AMD002 | lower-priority file is shadowed in the same directory |
| AMD003 | one file exceeds the configured project byte budget |
| AMD004 | instruction scope contains no non-instruction files |
| AMD005 | exact normalized instruction line is duplicated across selected files |

Diagnostics are structural hints. The tool does not decide whether Markdown instructions conflict, whether they are good instructions, or whether Codex will follow them.

## GitHub Action

Use the tagged release in another repository:

```yaml
name: AGENTS.md doctor
on: [push, pull_request]

permissions:
  contents: read

jobs:
  doctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: 2015709544-cell/agents-md-debugger@v0.1.1
        with:
          fail-on: warning
```

## Known limitations

- This is a documentation-based preview, not Codex's internal resolver.
- It does not inspect session rehydration, TUI state, prompt assembly, symlink cycles, or I/O behavior inside Codex.
- `explain` uses the target's parent as the modeled working directory.
- Duplicate detection is intentionally conservative and line-based.
- Project-local configuration layers and managed configuration are not yet resolved; pass the effective config explicitly when needed.

## Development

```bash
ruff check .
pytest
python -m build
```

Every behavior change should include a minimal filesystem fixture in a test. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- compare preview output with a redacted Codex session log;
- explain project-local and managed configuration provenance;
- report I/O and symlink edge cases;
- emit shell-completion metadata and richer CI annotations.

Roadmap items are intentions, not shipped features.

## References

- [OpenAI: Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [OpenAI: Advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#project-instructions-discovery)
- [AGENTS.md open format](https://agents.md/)

## License

MIT. See [LICENSE](LICENSE).
