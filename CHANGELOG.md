# Changelog

Notable changes will be recorded here. Semantic Versioning begins with the first stable release.

## [Unreleased]

## [0.1.1] - 2026-08-14

### Added

- A runnable layered-instructions example under `examples/demo-repo`.
- `--version` output, issue forms, a pull request template, and an Action self-test.
- Coverage for Unicode and spaced paths, `.git` files, UTF-8 byte budgets, explicit roots,
  and read failures.

### Changed

- Installation documentation now uses a tagged GitHub release and includes uninstall steps.
- The README now includes project badges and reproducible example output.

## [0.1.0] - 2026-08-14

### Added

- `scan`, `explain`, and `doctor` commands with text and JSON output.
- Codex config support for byte limits, fallback filenames, and project root markers.
- Global and project instruction metadata reporting without printing instruction content.
- Composite GitHub Action and cross-version Python CI.
