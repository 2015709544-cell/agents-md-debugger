# Contributing

Contributions should make instruction discovery easier to inspect without overstating parity with Codex internals.

## Bug reports

- Include `agents-md-debugger explain <target> --json` with private paths redacted.
- State your Codex version and the effective discovery-related configuration.
- Provide a minimal public directory tree when possible; never publish secrets or private instructions.
- Explain expected and observed file selection.

## Pull requests

1. Keep the change focused.
2. Add a filesystem-based test for the behavior or regression.
3. Run `ruff check .`, `pytest`, and `python -m build`.
4. Cite current public Codex documentation when changing resolver semantics.

The project must remain usable offline and must not transmit instruction content.
